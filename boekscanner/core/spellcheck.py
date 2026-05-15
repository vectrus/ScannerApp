"""Nederlandse (en multi-taal) spellingscontrole via LanguageTool.

LanguageTool draait lokaal in een Java-proces dat ``language_tool_python``
voor ons start. Eerste start kan even duren (downloads ~250 MB).
We laden lazy en cachen de instance per taal.

Als Java/LanguageTool niet beschikbaar is geven we lege resultaten terug
(de app blijft dan gewoon werken zonder spellcheck).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from loguru import logger

try:
    import language_tool_python  # type: ignore
    _HAS_LT = True
except Exception:  # pragma: no cover
    language_tool_python = None  # type: ignore
    _HAS_LT = False


@dataclass
class SpellSuggestion:
    offset: int
    length: int
    message: str
    rule_id: str
    suggestions: List[str]


_instances: Dict[str, "language_tool_python.LanguageTool"] = {}


def _get_tool(language: str):
    if not _HAS_LT:
        return None
    if language in _instances:
        return _instances[language]
    try:
        tool = language_tool_python.LanguageTool(language)
        _instances[language] = tool
        logger.info("LanguageTool geladen voor taal: {}", language)
        return tool
    except Exception as exc:
        logger.warning("Kan LanguageTool niet starten ({}): {}", language, exc)
        return None


def check_text(text: str, language: str = "nl-NL") -> List[SpellSuggestion]:
    """Geef een lijst suggesties terug. Lege lijst als spellcheck niet kan."""
    tool = _get_tool(language)
    if tool is None or not text.strip():
        return []
    try:
        matches = tool.check(text)
    except Exception as exc:
        logger.warning("Spellcheck mislukte: {}", exc)
        return []
    return [
        SpellSuggestion(
            offset=m.offset,
            length=m.errorLength,
            message=m.message,
            rule_id=m.ruleId,
            suggestions=list(m.replacements[:5]),
        )
        for m in matches
    ]


def shutdown() -> None:
    """Sluit alle LanguageTool-processen netjes af."""
    for tool in _instances.values():
        try:
            tool.close()
        except Exception:
            pass
    _instances.clear()
