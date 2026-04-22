import {
  API_TIMEOUT_MS,
  getApiBaseUrl,
  resolveApiTarget,
  type ApiTarget,
  type RouteMode,
} from './apiConfig'
import { getHttpClient } from './httpClient'

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SendRagChatRequest {
  query: string
  routeMode: RouteMode
  target?: ApiTarget
  topK: number
  similarityThreshold: number
  history: ChatHistoryMessage[]
}

interface RagChatResponse {
  response?: unknown
}

interface StreamEventPayload extends Record<string, unknown> {
  type?: unknown
  content?: unknown
  done?: unknown
  response_time?: unknown
  char_count?: unknown
  estimated_tokens?: unknown
  chunk_count?: unknown
  retrieved_documents?: unknown
  context_length?: unknown
  filter_stats?: unknown
}

export type RagStreamEvent =
  | RagStreamContentEvent
  | RagStreamInfoEvent
  | RagStreamErrorEvent
  | RagStreamDoneEvent

interface RagStreamBaseEvent {
  done: boolean
  raw: StreamEventPayload
}

export interface RagStreamContentEvent extends RagStreamBaseEvent {
  type: 'content'
  content: string
}

export interface RagStreamInfoEvent extends RagStreamBaseEvent {
  type: 'info'
  content: string
  responseTime?: number
  charCount?: number
  estimatedTokens?: number
  chunkCount?: number
}

export interface RagStreamErrorEvent extends RagStreamBaseEvent {
  type: 'error'
  content: string
}

export interface RagStreamDoneEvent extends RagStreamBaseEvent {
  type: 'done'
  content: string
}

type RagStreamErrorCode =
  | 'http'
  | 'network'
  | 'timeout'
  | 'parse'
  | 'unexpected_end'

export class RagStreamError extends Error {
  readonly code: RagStreamErrorCode
  readonly target: ApiTarget
  readonly statusCode?: number

  constructor(
    message: string,
    code: RagStreamErrorCode,
    target: ApiTarget,
    statusCode?: number,
    cause?: unknown,
  ) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'RagStreamError'
    this.code = code
    this.target = target
    this.statusCode = statusCode
  }
}

function normalizeTopK(value: number): number {
  const rounded = Math.floor(value)
  return rounded > 0 ? rounded : 1
}

function toNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function toContentString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function splitSseBlocks(buffer: string): { blocks: string[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const parts = normalized.split('\n\n')
  return {
    blocks: parts.slice(0, -1),
    rest: parts[parts.length - 1] ?? '',
  }
}

function extractDataLine(block: string): string | null {
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }

  if (dataLines.length === 0) {
    return null
  }

  return dataLines.join('\n')
}

function parseStreamPayload(dataText: string, target: ApiTarget): StreamEventPayload {
  try {
    const parsed = JSON.parse(dataText) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('invalid_payload')
    }
    return parsed as StreamEventPayload
  } catch (error) {
    throw new RagStreamError('收到无法解析的流式数据。', 'parse', target, undefined, error)
  }
}

function normalizeEvents(payload: StreamEventPayload): RagStreamEvent[] {
  const content = toContentString(payload.content)
  const done = payload.done === true
  const typeValue = typeof payload.type === 'string' ? payload.type : ''
  const events: RagStreamEvent[] = []

  if (typeValue === 'content') {
    events.push({
      type: 'content',
      content,
      done,
      raw: payload,
    })
  } else if (typeValue === 'info') {
    events.push({
      type: 'info',
      content,
      done,
      raw: payload,
      responseTime: toNumber(payload.response_time),
      charCount: toNumber(payload.char_count),
      estimatedTokens: toNumber(payload.estimated_tokens),
      chunkCount: toNumber(payload.chunk_count),
    })
  } else if (typeValue === 'error') {
    events.push({
      type: 'error',
      content: content || '服务端返回错误。',
      done,
      raw: payload,
    })
  } else if (typeValue === 'done') {
    events.push({
      type: 'done',
      content,
      done: true,
      raw: payload,
    })
  } else if (done) {
    events.push({
      type: 'done',
      content,
      done: true,
      raw: payload,
    })
  } else {
    events.push({
      type: 'content',
      content,
      done: false,
      raw: payload,
    })
  }

  if (done && typeValue !== 'done') {
    events.push({
      type: 'done',
      content,
      done: true,
      raw: payload,
    })
  }

  return events
}

async function readErrorDetail(response: Response): Promise<string | null> {
  const contentType = response.headers.get('content-type') ?? ''
  try {
    if (contentType.includes('application/json')) {
      const payload = (await response.json()) as unknown
      if (payload && typeof payload === 'object') {
        const detail = (payload as { detail?: unknown }).detail
        if (typeof detail === 'string' && detail.trim()) {
          return detail
        }
      }
    }

    const text = await response.text()
    if (text.trim()) {
      return text
    }
  } catch {
    return null
  }

  return null
}

export async function sendRagChat({
  query,
  routeMode,
  target,
  topK,
  similarityThreshold,
  history,
}: SendRagChatRequest): Promise<string> {
  const resolvedTarget = target ?? resolveApiTarget(routeMode)
  const payload = {
    query,
    top_k: normalizeTopK(topK),
    stream: false,
    history,
    similarity_threshold: similarityThreshold,
  }

  const { data } = await getHttpClient(resolvedTarget).post<RagChatResponse>(
    '/rag_chat',
    payload,
  )

  if (!data || typeof data.response !== 'string') {
    throw new Error('后端返回了无法识别的聊天响应格式。')
  }

  return data.response
}

export async function* streamRagChat({
  query,
  routeMode,
  target,
  topK,
  similarityThreshold,
  history,
}: SendRagChatRequest): AsyncGenerator<RagStreamEvent> {
  const resolvedTarget = target ?? resolveApiTarget(routeMode)
  const controller = new AbortController()
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  let timeoutPhase: 'first_chunk' | 'inactivity' = 'first_chunk'
  const armTimeout = (phase: 'first_chunk' | 'inactivity') => {
    timeoutPhase = phase
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS)
  }
  const clearTimeoutGuard = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }
  const payload = {
    query,
    top_k: normalizeTopK(topK),
    stream: true,
    history,
    similarity_threshold: similarityThreshold,
  }
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  let gotTerminalEvent = false

  try {
    armTimeout('first_chunk')

    const response = await fetch(`${getApiBaseUrl(resolvedTarget)}/rag_chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/plain',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })

    if (!response.ok) {
      const detail = await readErrorDetail(response)
      const message = detail
        ? `请求失败（${response.status}）：${detail}`
        : `请求失败，状态码 ${response.status}。`
      throw new RagStreamError(message, 'http', resolvedTarget, response.status)
    }

    if (!response.body) {
      throw new RagStreamError('未收到流式响应数据。', 'network', resolvedTarget)
    }

    reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) {
        break
      }

      armTimeout('inactivity')

      buffer += decoder.decode(value, { stream: true })
      const { blocks, rest } = splitSseBlocks(buffer)
      buffer = rest

      for (const block of blocks) {
        const dataLine = extractDataLine(block)
        if (!dataLine) {
          continue
        }

        const payloadEvent = parseStreamPayload(dataLine, resolvedTarget)
        for (const event of normalizeEvents(payloadEvent)) {
          if (event.type === 'done') {
            gotTerminalEvent = true
          }
          yield event
        }
      }
    }

    buffer += decoder.decode()
    const tailDataLine = extractDataLine(buffer)
    if (tailDataLine) {
      const payloadEvent = parseStreamPayload(tailDataLine, resolvedTarget)
      for (const event of normalizeEvents(payloadEvent)) {
        if (event.type === 'done') {
          gotTerminalEvent = true
        }
        yield event
      }
    }

    if (!gotTerminalEvent) {
      throw new RagStreamError(
        '流式响应在完成前中断，请重试。',
        'unexpected_end',
        resolvedTarget,
      )
    }
  } catch (error) {
    if (error instanceof RagStreamError) {
      throw error
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      const message =
        timeoutPhase === 'first_chunk'
          ? '请求超时，请检查网络或稍后重试。'
          : '流式响应长时间无数据，连接可能中断，请重试。'
      throw new RagStreamError(
        message,
        'timeout',
        resolvedTarget,
        undefined,
        error,
      )
    }

    if (error instanceof TypeError) {
      throw new RagStreamError(
        '网络连接中断，请检查服务状态后重试。',
        'network',
        resolvedTarget,
        undefined,
        error,
      )
    }

    if (error instanceof Error) {
      throw new RagStreamError(
        error.message,
        'network',
        resolvedTarget,
        undefined,
        error,
      )
    }

    throw new RagStreamError('流式请求失败，请稍后重试。', 'network', resolvedTarget)
  } finally {
    clearTimeoutGuard()
    if (reader) {
      try {
        await reader.cancel()
      } catch {
        // Ignore reader cancellation failures.
      }
    }
  }
}
