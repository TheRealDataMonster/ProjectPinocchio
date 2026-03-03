import logging
from typing import Any, Dict
from pathlib import Path

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
MEMORY_DIR = PROJECT_ROOT / "soul" / "memory"


class RecallMemory(Tool):
    """Recall what happened on a specific date from memory files. Use when asked about past events or memories."""

    name = "recall_memory"
    description = (
        "Recall what happened on a specific date from memory files. "
        "Use when the user asks about past events, what happened on a date, or memories."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date to recall in YYYY-MM-DD format (e.g. '2026-03-01')",
            },
        },
        "required": ["date"],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        """Read and return the memory file for the given date."""
        date_str = kwargs.get("date", "")
        logger.info("Tool call: recall_memory date=%s", date_str)

        memory_file = MEMORY_DIR / f"{date_str}.md"
        if not memory_file.exists():
            return {"status": "no_memory", "message": f"No memory found for {date_str}."}

        try:
            content = memory_file.read_text(encoding="utf-8").strip()
            return {"status": "ok", "date": date_str, "memory": content}
        except Exception as e:
            logger.error("Failed to read memory file %s: %s", memory_file, e)
            return {"status": "error", "message": f"Failed to read memory for {date_str}."}
