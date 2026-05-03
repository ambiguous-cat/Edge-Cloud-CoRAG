PAPER_SEARCH_COMMANDS = {"/论文检索", "/paper_search", "/papers"}


def is_paper_search_command(text: str) -> bool:
    """Return True when the user explicitly requests paper search."""
    if not text:
        return False
    lowered = text.strip().lower()
    return any(command in lowered for command in PAPER_SEARCH_COMMANDS)


def remove_paper_search_command(text: str) -> str:
    """Remove paper search command tokens while preserving the user's topic text."""
    cleaned = text or ""
    for command in PAPER_SEARCH_COMMANDS:
        cleaned = cleaned.replace(command, "")
    return " ".join(cleaned.split())
