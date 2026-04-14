"""
Output formatting helpers for MCP tool responses.

Every tool returns a single string containing:
1. A markdown header with key facts (human-readable, immediate value for Claude)
2. A fenced JSON block with the full structured response (for Claude to pivot on fields)
3. A credit usage line at the bottom
"""
import json
from typing import Any


def render(
    title: str,
    facts: list[str],
    data: dict[str, Any],
) -> str:
    """
    Single-section tool output.

    Args:
        title: Short description, e.g. "Breach Search: user@example.com"
        facts: 3–6 key facts as plain strings (shown as bullet list)
        data:  Raw API response dict (may contain _credits key)
    """
    credits_meta = data.get("_credits", {})
    clean = {k: v for k, v in data.items() if k != "_credits"}

    facts_md = "\n".join(f"- {f}" for f in facts) if facts else "- No results"
    credits_line = _credits_line(credits_meta)

    return (
        f"## {title}\n\n"
        f"{facts_md}\n"
        f"{credits_line}\n\n"
        f"```json\n{json.dumps(clean, indent=2, default=str)}\n```"
    )


def render_multi(
    title: str,
    sections: list[str | None],
    results: list[Any],
) -> str:
    """
    Multi-section output for meta-tools that chain multiple API calls.

    Args:
        title:    Overall heading, e.g. "Full Breach Profile: user@example.com"
        sections: Section names matching results (None entries are skipped)
        results:  List of API response dicts or Exception instances
    """
    parts = [f"## {title}\n"]
    total_credits = 0
    any_success = False

    for section, result in zip(sections, results):
        if section is None:
            continue
        if isinstance(result, Exception):
            parts.append(f"### {section}\n> Error: {result}\n")
        else:
            if isinstance(result, dict):
                c = result.get("_credits", {})
                total_credits += c.get("credits_used", 0) if isinstance(c, dict) else 0
                clean = {k: v for k, v in result.items() if k != "_credits"}
                parts.append(
                    f"### {section}\n"
                    f"```json\n{json.dumps(clean, indent=2, default=str)}\n```\n"
                )
                any_success = True
            else:
                parts.append(f"### {section}\n> Unexpected result type: {type(result)}\n")

    if not any_success:
        parts.append("> All sub-calls failed. Check errors above.\n")

    parts.append(f"\n> **Total credits used: {total_credits}**")
    return "\n".join(parts)


def _credits_line(credits_meta: dict[str, Any]) -> str:
    if not credits_meta:
        return ""
    used = credits_meta.get("credits_used", "?")
    remaining = credits_meta.get("credits_remaining", "?")
    total = credits_meta.get("credits_total", "?")
    if remaining == -1:
        return f"\n> Credits used: {used} | Unlimited plan"
    return f"\n> Credits used: {used} | Remaining: {remaining}/{total}"


def error_response(title: str, error: Exception) -> str:
    """Uniform error output so Claude always sees a structured failure message."""
    error_type = type(error).__name__
    return (
        f"## {title}\n\n"
        f"**Error ({error_type}):** {error}\n\n"
        f"> Tip: Check the error message above for next steps."
    )
