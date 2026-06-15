"""Source-backed infographic generation with Qwen3-VL legibility verification.

Pipeline (chosen approach: SVG + Qwen3-VL check):

1. Gather source-backed content for a topic from the local ``genai_research``
   corpus (no invented facts).
2. Author a self-contained **SVG** infographic. SVG uses real vector ``<text>``,
   so the words are always correct (never "painted" into pixels). Qwen
   (``qwen3.7-plus``) authors it when available; a deterministic Python template
   is the always-valid fallback.
3. **Structural check** (deterministic, always runs): confirm every intended
   string is present as real text and the font sizes are legible.
4. **Visual verification** with ``qwen3-vl-plus``: render the SVG to PNG and ask
   the vision model to read it back and flag anything illegible, overlapping, or
   cut off. If a renderer or the Qwen key is unavailable, this step is skipped
   and the structural check stands on its own.
5. If verification fails on a Qwen-authored SVG, fall back to the clean template.

Everything degrades gracefully: with no Qwen key and no renderer, you still get a
valid, legible, source-backed SVG plus the structural verification.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

from . import llm_provider
from .audit import write_audit_event
from .settings import get_settings
from .tools import search_course_material_impl

CANVAS_W = 1000
CANVAS_H = 1400
MIN_FONT = 16

_XML_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;"}


def _esc(text: str) -> str:
    return "".join(_XML_ESCAPES.get(ch, ch) for ch in str(text))


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text.strip(), width=width) or [""]


# ---------------------------------------------------------------------------
# Content gathering (grounded in genai_research)
# ---------------------------------------------------------------------------

def _gather_content(topic: str, k: int, tenant_id: str | None) -> dict[str, Any]:
    payload = search_course_material_impl(query=topic, k=k, tenant_id=tenant_id)
    cards: list[dict[str, Any]] = []
    for result in payload.get("results", [])[:5]:
        summary = (result.get("summary") or "").strip()
        cards.append(
            {
                "heading": result.get("title") or "Untitled record",
                "record_type": result.get("record_type"),
                "lines": _wrap(summary, 64)[:3] if summary else ["(no summary in corpus)"],
            }
        )
    sources = []
    for ref in payload.get("source_refs", [])[:5]:
        sources.append({"title": ref.get("title"), "path": ref.get("path"), "citations": ref.get("citations") or []})
    return {
        "title": topic.strip().title()[:60] or "GenAI Topic",
        "subtitle": "Source-backed summary from the genai_research corpus",
        "cards": cards or [{"heading": "No matching corpus records", "record_type": None, "lines": ["Try another topic."]}],
        "sources": sources,
    }


def intended_strings(content: dict[str, Any]) -> list[str]:
    """The strings that MUST be present and legible in the rendered infographic."""
    out = [content["title"], content["subtitle"]]
    out.extend(card["heading"] for card in content["cards"])
    return [s for s in out if s]


# ---------------------------------------------------------------------------
# SVG authoring
# ---------------------------------------------------------------------------

def _template_svg(content: dict[str, Any]) -> str:
    """Deterministic, always-valid, always-legible SVG built from the content."""
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="#0f172a"/>',
        f'<rect x="0" y="0" width="{CANVAS_W}" height="140" fill="#1d4ed8"/>',
        f'<text x="50" y="78" font-size="40" font-weight="bold" fill="#ffffff">{_esc(content["title"])}</text>',
        f'<text x="50" y="116" font-size="20" fill="#dbeafe">{_esc(content["subtitle"])}</text>',
    ]
    y = 190
    for card in content["cards"]:
        card_h = 40 + 26 * len(card["lines"]) + 24
        parts.append(f'<rect x="50" y="{y}" width="900" height="{card_h}" rx="14" fill="#1e293b" stroke="#334155"/>')
        badge = (card.get("record_type") or "record").upper()
        parts.append(f'<text x="74" y="{y + 38}" font-size="22" font-weight="bold" fill="#38bdf8">{_esc(card["heading"])}</text>')
        parts.append(f'<text x="812" y="{y + 38}" font-size="16" fill="#94a3b8">{_esc(badge)}</text>')
        ty = y + 70
        for line in card["lines"]:
            parts.append(f'<text x="74" y="{ty}" font-size="18" fill="#e2e8f0">{_esc(line)}</text>')
            ty += 26
        y += card_h + 22
    parts.append(f'<text x="50" y="{CANVAS_H - 40}" font-size="16" fill="#94a3b8">Sources: genai_research corpus ({len(content["sources"])} records)</text>')
    parts.append("</svg>")
    return "\n".join(parts)


_QWEN_SVG_SYSTEM = (
    "You are an infographic designer that outputs ONLY a single self-contained SVG. "
    "Rules: width=1000 height=1400 with a viewBox; use ONLY <svg>,<g>,<rect>,<line>,<text>,<tspan>; "
    "NO <image>, NO external URLs, NO scripts, NO foreignObject; every word must be a real <text> element; "
    "font-size at least 16; high contrast; keep all content inside the canvas; wrap long lines yourself. "
    "Return the SVG markup only, no markdown fences, no commentary."
)


def _qwen_svg(content: dict[str, Any]) -> str:
    lines = [f"Title: {content['title']}", f"Subtitle: {content['subtitle']}", "Sections:"]
    for card in content["cards"]:
        lines.append(f"- {card['heading']} ({card.get('record_type')}): {' '.join(card['lines'])}")
    lines.append("Footer must read: Sources: genai_research corpus")
    user = "Build an infographic SVG from this source-backed content:\n" + "\n".join(lines)
    svg = llm_provider.chat(
        [{"role": "system", "content": _QWEN_SVG_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=2600,
    )
    svg = svg.strip()
    if svg.startswith("```"):
        svg = re.sub(r"^```[a-zA-Z]*\n?", "", svg)
        svg = re.sub(r"\n?```$", "", svg).strip()
    start = svg.find("<svg")
    end = svg.rfind("</svg>")
    if start == -1 or end == -1:
        raise llm_provider.LLMUnavailable("Qwen did not return an <svg> document")
    return svg[start : end + len("</svg>")]


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _extract_svg_texts(svg: str) -> list[str]:
    raw = re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.DOTALL)
    texts: list[str] = []
    for chunk in raw:
        inner = re.sub(r"<[^>]+>", " ", chunk)  # strip tspans
        inner = re.sub(r"\s+", " ", inner).strip()
        # unescape the few entities we emit
        for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
            inner = inner.replace(ent, ch)
        if inner:
            texts.append(inner)
    return texts


def _font_sizes(svg: str) -> list[int]:
    return [int(float(m)) for m in re.findall(r'font-size="(\d+(?:\.\d+)?)"', svg)]


def structural_check(svg: str, intended: list[str]) -> dict[str, Any]:
    texts = _extract_svg_texts(svg)
    haystack = " ".join(texts).lower()
    present, missing = [], []
    for want in intended:
        (present if want.lower() in haystack else missing).append(want)
    sizes = _font_sizes(svg)
    return {
        "has_text_elements": bool(texts),
        "text_element_count": len(texts),
        "intended_present": present,
        "intended_missing": missing,
        "all_intended_present": not missing,
        "min_font_size": min(sizes) if sizes else None,
        "min_font_ok": (min(sizes) >= MIN_FONT) if sizes else False,
        "ok": (not missing) and bool(texts) and (min(sizes) >= MIN_FONT if sizes else False),
    }


def _render_png(svg: str) -> bytes | None:
    """Render SVG to PNG if a renderer is available, else return None."""
    try:
        import cairosvg  # type: ignore

        return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=CANVAS_W, output_height=CANVAS_H)
    except Exception:
        return None


_VL_PROMPT = (
    "You are a QA reviewer for an infographic image. "
    "1) Read and list every text string you can see. "
    "2) Decide if ALL text is fully legible and not cut off, overlapping, or garbled. "
    'Respond ONLY as compact JSON: {"legible": true|false, '
    '"unreadable_or_cutoff": ["..."], "all_text": ["..."], "notes": "..."}'
)


def verify_with_vl(png: bytes, intended: list[str]) -> dict[str, Any]:
    raw = llm_provider.vision(_VL_PROMPT, png)
    text = raw.strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    parsed: dict[str, Any] = {}
    if match:
        import json

        try:
            parsed = json.loads(match.group(0))
        except Exception:
            parsed = {}
    read = " ".join(str(s) for s in parsed.get("all_text", [])).lower()
    intended_seen = [s for s in intended if s.lower() in read] if read else []
    return {
        "vl_used": True,
        "legible": bool(parsed.get("legible", False)),
        "unreadable_or_cutoff": parsed.get("unreadable_or_cutoff", []),
        "intended_read_back": intended_seen,
        "notes": parsed.get("notes", ""),
        "raw": text[:600],
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def generate_infographic(
    topic: str,
    *,
    k: int = 5,
    tenant_id: str | None = None,
    learner_id: str | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Generate a source-backed infographic and verify its text is legible."""
    content = _gather_content(topic, k=k, tenant_id=tenant_id)
    intended = intended_strings(content)

    generator = "qwen3.7-plus"
    try:
        svg = _qwen_svg(content)
    except llm_provider.LLMUnavailable:
        svg, generator = _template_svg(content), "deterministic_template"

    structural = structural_check(svg, intended)
    # If a Qwen-authored SVG dropped required text or used tiny fonts, fall back.
    if generator == "qwen3.7-plus" and not structural["ok"]:
        svg, generator = _template_svg(content), "deterministic_template_fallback"
        structural = structural_check(svg, intended)

    png = _render_png(svg)
    verification: dict[str, Any] = {"vl_used": False, "renderer_available": png is not None}
    if png is not None and llm_provider.embeddings_available():
        try:
            verification = {**verification, **verify_with_vl(png, intended)}
            # If the VL model says a Qwen SVG is not legible, fall back to template + re-render.
            if generator.startswith("qwen") and not verification.get("legible", True):
                svg, generator = _template_svg(content), "deterministic_template_vl_fallback"
                structural = structural_check(svg, intended)
                png = _render_png(svg)
                if png is not None:
                    verification = {**verification, **verify_with_vl(png, intended), "vl_used": True}
        except llm_provider.LLMUnavailable as exc:
            verification = {**verification, "vl_used": False, "reason": str(exc)[:120]}

    paths: dict[str, str] = {}
    if save:
        out_dir = get_settings().data_dir / "infographics"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] or "infographic"
        svg_path = out_dir / f"{slug}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        paths["svg"] = str(svg_path)
        if png is not None:
            png_path = out_dir / f"{slug}.png"
            png_path.write_bytes(png)
            paths["png"] = str(png_path)

    legible = verification.get("legible") if verification.get("vl_used") else structural["ok"]
    result = {
        "topic": topic,
        "generator": generator,
        "svg": svg,
        "intended_strings": intended,
        "structural_check": structural,
        "verification": verification,
        "legible_and_correct": bool(structural["ok"] and (legible if legible is not None else True)),
        "sources": content["sources"],
        "paths": paths,
    }
    write_audit_event(
        "infographic_generated",
        learner_id=learner_id,
        tenant_id=tenant_id,
        outcome="ok" if result["legible_and_correct"] else "needs_review",
        metadata={"topic": topic, "generator": generator, "vl_used": verification.get("vl_used", False)},
    )
    return result
