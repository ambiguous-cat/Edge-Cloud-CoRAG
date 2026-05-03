import json
import logging
import os
import select
import shlex
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("paper_search.arxiv_mcp")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MCP_ARGS = "Arxiv-Paper-MCP/build/index.js"


class ArxivMCPClient:
    """Minimal stdio MCP client for the bundled Arxiv-Paper-MCP server."""

    def __init__(self):
        self.command = os.getenv("ARXIV_MCP_COMMAND", "node")
        self.args = shlex.split(os.getenv("ARXIV_MCP_ARGS", DEFAULT_MCP_ARGS))
        self.timeout = float(os.getenv("ARXIV_MCP_TIMEOUT", "45"))
        self.mode = os.getenv("ARXIV_MCP_MODE", "cli").strip().lower()
        self.process = None
        self.request_id = 0
        self.lock = threading.Lock()
        self.initialized = False

    def _start(self):
        if self.process and self.process.poll() is None:
            return

        logger.info("starting Arxiv MCP server | command=%s | args=%s | cwd=%s", self.command, self.args, PROJECT_ROOT)
        self.process = subprocess.Popen(
            [self.command, *self.args],
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        logger.info("Arxiv MCP process started | pid=%s", self.process.pid)
        self._start_stderr_logger()
        self.initialized = False
        self._initialize()

    def _start_stderr_logger(self):
        if not self.process or not self.process.stderr:
            return

        def pipe_stderr():
            try:
                for raw_line in iter(self.process.stderr.readline, b""):
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        logger.info("Arxiv MCP stderr | %s", line)
            except Exception:
                logger.exception("failed while reading Arxiv MCP stderr")

        thread = threading.Thread(target=pipe_stderr, daemon=True)
        thread.start()

    def _write_message(self, message: Dict[str, Any]):
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        self.process.stdin.write(header + payload)
        self.process.stdin.flush()

    def _read_with_timeout(self, length: int, deadline: float) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for Arxiv MCP response after {self.timeout:.1f}s")

            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                raise TimeoutError(f"Timed out waiting for Arxiv MCP response after {self.timeout:.1f}s")

            chunk = self.process.stdout.read(length - len(chunks))
            if not chunk:
                raise RuntimeError("Arxiv MCP server stopped before sending a response")
            chunks.extend(chunk)
        return bytes(chunks)

    def _read_message(self) -> Dict[str, Any]:
        deadline = time.time() + self.timeout
        header_bytes = bytearray()
        while b"\r\n\r\n" not in header_bytes:
            chunk = self._read_with_timeout(1, deadline)
            header_bytes.extend(chunk)

        headers = header_bytes.decode("ascii", errors="replace")
        content_length = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break

        if content_length is None:
            raise RuntimeError(f"Missing Content-Length header from MCP server: {headers!r}")

        body = self._read_with_timeout(content_length, deadline)
        if len(body) != content_length:
            raise RuntimeError("Incomplete MCP response body")
        return json.loads(body.decode("utf-8"))

    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self.request_id += 1
        request_id = self.request_id
        logger.info("MCP request started | id=%s | method=%s", request_id, method)
        self._write_message({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        })

        while True:
            response = self._read_message()
            if response.get("id") != request_id:
                continue
            if "error" in response:
                logger.error("MCP request failed | id=%s | method=%s | error=%s", request_id, method, response["error"])
                raise RuntimeError(f"MCP request failed: {response['error']}")
            logger.info("MCP request done | id=%s | method=%s", request_id, method)
            return response.get("result", {})

    def _send_notification(self, method: str, params: Dict[str, Any] = None):
        self._write_message({
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        })

    def _initialize(self):
        logger.info("initializing Arxiv MCP server")
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "rag-cloud-api", "version": "1.0.0"},
        })
        self._send_notification("notifications/initialized")
        self.initialized = True
        logger.info("Arxiv MCP server initialized")

    def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        if self.mode == "cli":
            return self._call_tool_cli(name, arguments or {})

        with self.lock:
            try:
                self._start()
                logger.info("MCP tool call started | tool=%s | arguments=%s", name, arguments or {})
                return self._send_request("tools/call", {
                    "name": name,
                    "arguments": arguments or {},
                })
            except Exception:
                logger.exception("MCP tool call failed, terminating MCP process | tool=%s", name)
                self._terminate_process()
                raise

    def _call_tool_cli(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        command = [
            self.command,
            *self.args,
            "--call-tool",
            name,
            json.dumps(arguments, ensure_ascii=False),
        ]
        logger.info("MCP CLI tool call started | tool=%s | arguments=%s", name, arguments)
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                f"Arxiv MCP CLI tool failed: {completed.stderr.strip() or completed.stdout.strip()}"
            )

        stdout = completed.stdout.strip()
        if not stdout:
            raise RuntimeError("Arxiv MCP CLI returned empty stdout")

        logger.info("MCP CLI tool call done | tool=%s | stdout_chars=%s", name, len(stdout))
        return json.loads(stdout)

    def _terminate_process(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.initialized = False

    def close(self):
        with self.lock:
            self._terminate_process()


_client = ArxivMCPClient()


def call_tool(name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    return _client.call_tool(name, arguments)


def extract_text_content(result: Dict[str, Any]) -> str:
    parts: List[str] = []
    for item in result.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text", "")))
    return "\n".join(part for part in parts if part)
