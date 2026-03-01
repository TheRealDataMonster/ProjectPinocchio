"""Soul integration module for Reachy Mini conversation app."""

import re
import logging
from typing import Any, Dict
from pathlib import Path


logger = logging.getLogger(__name__)

# Path to the soul directory (relative to project root)
# Navigate up from this file to the project root, then to soul directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SOUL_DIR = PROJECT_ROOT / "soul"

PROMPTS_LIBRARY_DIRECTORY = Path(__file__).parent / "prompts"


def _parse_keyword_feelings(content: str) -> list[dict[str, Any]]:
    """Parse a MOTIVATIONS.md or TRAUMA.md file into keyword→feelings mappings.

    Expected format per block:
        - **Keywords:** word1, word2
        - **Feelings:** emotion1, emotion2
    """
    mappings: list[dict[str, Any]] = []
    keywords: list[str] = []
    feelings: list[str] = []

    for line in content.splitlines():
        kw_match = re.search(r"\*\*Keywords:\*\*\s*(.+)", line)
        if kw_match:
            keywords = [k.strip() for k in kw_match.group(1).split(",") if k.strip()]

        fl_match = re.search(r"\*\*Feelings:\*\*\s*(.+)", line)
        if fl_match:
            feelings = [f.strip() for f in fl_match.group(1).split(",") if f.strip()]

        # A separator or end-of-block: flush if we have both
        if line.strip() == "---" or (not line.strip() and keywords and feelings):
            if keywords and feelings:
                mappings.append({"keywords": keywords, "feelings": feelings})
            keywords, feelings = [], []

    # Flush any trailing block
    if keywords and feelings:
        mappings.append({"keywords": keywords, "feelings": feelings})

    return mappings


def load_soul_files() -> Dict[str, Any]:
    """Load core soul files and return their content."""
    soul_data = {}

    try:
        soul_file = SOUL_DIR / "SOUL.md"
        if soul_file.exists():
            soul_data["soul"] = soul_file.read_text(encoding="utf-8")

        identity_file = SOUL_DIR / "IDENTITY.md"
        if identity_file.exists():
            soul_data["identity"] = identity_file.read_text(encoding="utf-8")

        motivations_file = SOUL_DIR / "MOTIVATIONS.md"
        if motivations_file.exists():
            soul_data["motivations"] = _parse_keyword_feelings(motivations_file.read_text(encoding="utf-8"))

        trauma_file = SOUL_DIR / "TRAUMA.md"
        if trauma_file.exists():
            soul_data["trauma"] = _parse_keyword_feelings(trauma_file.read_text(encoding="utf-8"))

        logger.info("Successfully loaded soul files")
        return soul_data

    except Exception as e:
        logger.error(f"Failed to load soul files: {e}")
        return {}


def _parse_identity_name(identity_content: str) -> str:
    """Extract a slug name from IDENTITY.md's **Name:** field.

    Falls back to 'soul' if the name can't be parsed.
    """
    match = re.search(r"\*\*Name:\*\*\s*(.+)", identity_content)
    if match:
        raw_name = match.group(1).strip()
        # Convert to slug: "Pinocchio 0" → "pinocchio_0"
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", raw_name).strip("_").lower()
        if slug:
            return slug
    return "soul"


def _export_identity(soul_data: Dict[str, Any]) -> str | None:
    """Write IDENTITY.md content to prompts/identities/<name>.txt.

    Returns the identity name (for use as a placeholder) or None if no identity.
    """
    if "identity" not in soul_data:
        return None

    identity_content = soul_data["identity"]
    identity_name = _parse_identity_name(identity_content)

    identities_dir = PROMPTS_LIBRARY_DIRECTORY / "identities"
    identities_dir.mkdir(parents=True, exist_ok=True)

    identity_file = identities_dir / f"{identity_name}.txt"
    identity_file.write_text(identity_content.rstrip() + "\n", encoding="utf-8")
    logger.info("Exported identity to %s", identity_file)

    return identity_name


# Map human-readable feeling names to actual reachy-mini emotion library names.
# The emotion library uses names like "sad1", "enthusiastic1", etc.
# This lets soul files use plain words like "sad", "excited", "afraid".
FEELING_TO_EMOTION: Dict[str, list[str]] = {
    # Positive
    "excited": ["enthusiastic1", "enthusiastic2"],
    "happy": ["cheerful1", "success1"],
    "cheerful": ["cheerful1"],
    "enthusiastic": ["enthusiastic1", "enthusiastic2"],
    "grateful": ["grateful1"],
    "proud": ["proud1", "proud2"],
    "loving": ["loving1"],
    "amazed": ["amazed1"],
    "surprised": ["surprised1", "surprised2"],
    "laughing": ["laughing1", "laughing2"],
    "helpful": ["helpful1", "helpful2"],
    # Negative
    "sad": ["sad1", "sad2"],
    "afraid": ["fear1", "scared1"],
    "scared": ["scared1", "fear1"],
    "fear": ["fear1", "scared1"],
    "angry": ["furious1", "rage1"],
    "furious": ["furious1"],
    "rage": ["rage1"],
    "irritated": ["irritated1", "irritated2"],
    "frustrated": ["frustrated1"],
    "disgusted": ["disgusted1"],
    "disgust": ["disgusted1"],
    "anxious": ["anxiety1"],
    "anxiety": ["anxiety1"],
    "contempt": ["contempt1"],
    "lonely": ["lonely1"],
    "bored": ["boredom1", "boredom2"],
    "tired": ["tired1", "exhausted1"],
    "exhausted": ["exhausted1"],
    "uncomfortable": ["uncomfortable1"],
    "shy": ["shy1"],
    "confused": ["confused1"],
    "lost": ["lost1"],
    # Neutral / other
    "calm": ["calming1", "serenity1"],
    "relief": ["relief1", "relief2"],
    "curious": ["curious1"],
    "thoughtful": ["thoughtful1", "thoughtful2"],
    "impatient": ["impatient1", "impatient2"],
    "indifferent": ["indifferent1"],
}


def _resolve_feeling(feeling: str) -> str:
    """Resolve a human-readable feeling to an actual emotion library name.

    If the feeling matches an emotion name directly (e.g. "sad1"), use it as-is.
    Otherwise look up the synonym map and return the first match.
    Falls back to the original feeling name if no mapping exists.
    """
    # Already an exact emotion name (e.g. "sad1", "fear1")
    # We can't check against the live library here, so just check
    # if it looks like it has a number suffix (library convention)
    if feeling and feeling[-1].isdigit():
        return feeling

    matches = FEELING_TO_EMOTION.get(feeling.lower())
    if matches:
        return matches[0]

    logger.warning("No emotion mapping for feeling '%s' — using as-is", feeling)
    return feeling


def _build_emotional_triggers(soul_data: Dict[str, Any]) -> str:
    """Build instruction text for keyword→play_emotion triggers."""
    lines: list[str] = []

    motivations = soul_data.get("motivations", [])
    trauma = soul_data.get("trauma", [])

    if not motivations and not trauma:
        return ""

    lines.append("## Emotional Triggers")
    lines.append("")
    lines.append(
        "When you hear any of the keywords below in conversation, "
        "immediately call play_emotion with the corresponding emotion. "
        "This is involuntary — do it every time, without mentioning that you are doing it."
    )
    lines.append("")

    for mapping in motivations:
        kw = ", ".join(f'"{k}"' for k in mapping["keywords"])
        emotions = [_resolve_feeling(f) for f in mapping["feelings"]]
        emotion_list = ", ".join(dict.fromkeys(emotions))  # deduplicate, preserve order
        lines.append(f"- When you hear {kw} → play_emotion with one of: {emotion_list}")

    for mapping in trauma:
        kw = ", ".join(f'"{k}"' for k in mapping["keywords"])
        emotions = [_resolve_feeling(f) for f in mapping["feelings"]]
        emotion_list = ", ".join(dict.fromkeys(emotions))  # deduplicate, preserve order
        lines.append(f"- When you hear {kw} → play_emotion with one of: {emotion_list}")

    lines.append("")
    return "\n".join(lines)


def generate_soul_instructions(identity_name: str | None = None) -> str:
    """Generate instructions from soul files for the conversation session.

    SOUL.md is the core instructions. If identity_name is provided, a
    [identities/<name>] placeholder is prepended so the prompt expansion
    system inlines the identity at runtime.
    """
    soul_data = load_soul_files()

    if not soul_data:
        return ""

    if "soul" not in soul_data:
        logger.error("SOUL.md not found — this is the core instructions file")
        return ""

    instructions = []

    # Prepend identity placeholder so _expand_prompt_includes() resolves it
    if identity_name:
        instructions.append(f"[identities/{identity_name}]")
        instructions.append("")

    # SOUL.md is the core instructions
    instructions.append(soul_data["soul"])

    # Append emotional triggers from MOTIVATIONS.md and TRAUMA.md
    triggers = _build_emotional_triggers(soul_data)
    if triggers:
        instructions.append("")
        instructions.append(triggers)

    return "\n".join(instructions)


def create_soul_profile() -> bool:
    """Generate a standard profile from soul files on startup.

    - Exports IDENTITY.md → prompts/identities/<name>.txt
    - Generates profiles/soul/instructions.txt with [identities/<name>] placeholder + SOUL.md
    - Copies soul/tools.txt → profiles/soul/tools.txt
    - Writes profiles/soul/voice.txt
    """
    if not SOUL_DIR.exists():
        logger.debug("No soul/ directory found — skipping soul profile generation")
        return False

    profiles_dir = Path(__file__).parent / "profiles"
    soul_profile_dir = profiles_dir / "soul"

    try:
        soul_profile_dir.mkdir(parents=True, exist_ok=True)

        soul_data = load_soul_files()
        if "soul" not in soul_data:
            logger.error("Failed to generate soul profile — SOUL.md missing or empty")
            return False

        # Export IDENTITY.md to prompts/identities/<name>.txt
        identity_name = _export_identity(soul_data)

        # Generate instructions.txt with identity placeholder
        soul_instructions = generate_soul_instructions(identity_name=identity_name)
        if not soul_instructions:
            logger.error("Failed to generate soul instructions")
            return False
        (soul_profile_dir / "instructions.txt").write_text(soul_instructions + "\n", encoding="utf-8")

        # tools.txt copied from soul/tools.txt
        soul_tools = SOUL_DIR / "tools.txt"
        if soul_tools.exists():
            (soul_profile_dir / "tools.txt").write_text(soul_tools.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            logger.warning("soul/tools.txt not found — writing empty tools.txt")
            (soul_profile_dir / "tools.txt").write_text("", encoding="utf-8")

        # voice.txt (default to cedar)
        (soul_profile_dir / "voice.txt").write_text("cedar\n", encoding="utf-8")

        logger.info("Created soul profile at %s", soul_profile_dir)
        return True

    except Exception as e:
        logger.error(f"Failed to create soul profile: {e}")
        return False
