#!/usr/bin/env python3
"""
Generates animated, self-contained SVG profile cards into cards/.

Usage:
  python scripts/generate_cards.py          # Animated SVGs (default)
  STATIC=1 python scripts/generate_cards.py # Final-frame static SVGs for screenshots
"""

from __future__ import annotations

import base64
import html
import io
import json
import os
import textwrap
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

STATIC = os.getenv("STATIC", "0") == "1"
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "stats.json"
OUT_DIR = ROOT / "cards"

# ==============================================================================
# 1. THEME & PROFILE CONFIGURATION
#    Matched to the Hermes Agent CLI dark/amber aesthetic in README.md.
#    Drop in custom website hex codes, font paths, or links here anytime.
# ==============================================================================
THEME = {
    "bg": "#0d1117",              # Primary card canvas (GitHub Dark)
    "surface": "#161b22",         # Elevated inner panel / track fill
    "border": "#30363d",          # Subtle 1px border
    "text_primary": "#f0f6fc",    # Headings & KPI values
    "text_secondary": "#c9d1d9",  # Taglines & descriptions
    "text_muted": "#8b949e",      # Metadata & axis labels
    "accent": "#F59E0B",          # Primary brand amber (bars, cursor, highlights)
    "accent_secondary": "#22C55E",  # Secondary emerald green (status indicator)
    # 5-step heatmap ramp from 0 contributions -> max contributions in brand amber
    "heatmap": ["#161b22", "#451a03", "#92400e", "#d97706", "#f59e0b"],
    # Local TTF/OTF fonts subset via fontTools.subset (pyftsubset) -> base64 WOFF
    "font_sans_path": ROOT / "assets" / "fonts" / "Inter.ttf",
    "font_mono_path": ROOT / "assets" / "fonts" / "FiraCode.ttf",
    "font_sans_fallback": "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono_fallback": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
}

PROFILE = {
    "name": "Jay Sonar",
    "handle": "@Jaysonar07",
    "tagline": "Cybersecurity & Full-Stack Engineer building resilient web, blockchain & AI systems.",
    "status": "ONLINE · CSIT '29 @ SSPU PUNE",
    # Set to None to render the geometric radar emblem instead of a portrait
    "avatar_path": ROOT / "assets" / "avatar.png",
    "tiles": [
        {
            "kicker": "01 / GITHUB",
            "title": "Repositories",
            "sub": "@Jaysonar07 ↗",
            "url": "https://github.com/Jaysonar07?tab=repositories",
        },
        {
            "kicker": "02 / NETWORK",
            "title": "LinkedIn",
            "sub": "Jay Sonar ↗",
            "url": "https://www.linkedin.com/in/jay-sonar-573637275/",
        },
        {
            "kicker": "03 / CONTACT",
            "title": "Email",
            "sub": "jaysonar2007@gmail.com ↗",
            "url": "mailto:jaysonar2007@gmail.com",
        },
    ],
    "featured_repos": [
        {
            "name": "ScholarParchment",
            "tag": "WEB3 · GOVTECH",
            "desc": "National scholarship management & Direct Benefit Transfer platform with Next.js, Solidity & Supabase.",
            "lang": "TypeScript",
            "lang_color": "#3178c6",
            "stars": "1",
            "forks": "0",
        },
        {
            "name": "WiseupAI",
            "tag": "AI · FINTECH",
            "desc": "Bilingual AI financial companion helping students track spending and build smarter savings habits.",
            "lang": "TypeScript",
            "lang_color": "#3178c6",
            "stars": "1",
            "forks": "0",
        },
        {
            "name": "Queuely",
            "tag": "REAL-TIME · OPS",
            "desc": "Dual-screen clinic & event queue management system with live sync, wait estimates & offline support.",
            "lang": "TypeScript",
            "lang_color": "#3178c6",
            "stars": "1",
            "forks": "0",
        },
        {
            "name": "CypherArena",
            "tag": "SECURITY · LABS",
            "desc": "Gamified cybersecurity & learning arena built with TypeScript and interactive AI-assisted challenges.",
            "lang": "TypeScript",
            "lang_color": "#3178c6",
            "stars": "0",
            "forks": "0",
        },
    ],
}


# ==============================================================================
# 2. FONT SUBSETTING (pyftsubset engine -> base64 WOFF data URI)
# ==============================================================================
def build_subset_font_css(font_path: Path | None, family_name: str, glyphs: str) -> str:
    """Subsets a font to only the rendered glyphs and returns an @font-face WOFF data URI."""
    if not font_path or not Path(font_path).exists():
        return ""

    unique_chars = "".join(sorted(set(glyphs)))
    font = TTFont(str(font_path))
    options = Options()
    options.flavor = "woff"
    options.desubroutinize = True

    subsetter = Subsetter(options=options)
    subsetter.populate(text=unique_chars)
    subsetter.subset(font)

    buf = io.BytesIO()
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f"@font-face {{\n"
        f"  font-family: '{family_name}';\n"
        f"  src: url('data:font/woff;base64,{b64}') format('woff');\n"
        f"  font-weight: 100 900;\n"
        f"  font-style: normal;\n"
        f"}}"
    )


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def plural_days(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def base_style(font_css: str, extra_css: str = "") -> str:
    """Shared SVG stylesheet with prefers-reduced-motion & STATIC=1 support."""
    if STATIC:
        return f"""<style>
      {font_css}
      .sans {{ font-family: 'BrandSans', {THEME['font_sans_fallback']}; }}
      .mono {{ font-family: 'BrandMono', {THEME['font_mono_fallback']}; }}
      {extra_css}
    </style>"""

    return f"""<style>
      {font_css}
      .sans {{ font-family: 'BrandSans', {THEME['font_sans_fallback']}; }}
      .mono {{ font-family: 'BrandMono', {THEME['font_mono_fallback']}; }}
      @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
      }}
      @keyframes blink {{
        0%, 49% {{ opacity: 1; }}
        50%, 100% {{ opacity: 0; }}
      }}
      @keyframes pulseGlow {{
        0%, 100% {{ opacity: 0.45; }}
        50%      {{ opacity: 1; }}
      }}
      .reveal {{
        opacity: 0;
        animation: fadeUp 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }}
      .cursor {{
        animation: blink 1.1s infinite;
      }}
      .status-dot {{
        animation: pulseGlow 2.4s infinite;
      }}
      .reduced-only {{
        display: none;
      }}
      {extra_css}
      @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
          animation: none !important;
          transition: none !important;
          opacity: 1 !important;
          transform: none !important;
        }}
        .anim-only {{
          display: none !important;
        }}
        .reduced-only {{
          display: inline !important;
        }}
      }}
    </style>"""


# ==============================================================================
# 3. CARD RENDERERS
# ==============================================================================
def render_hero(font_css: str, delay: float = 0.05) -> str:
    w, h = 900, 176
    avatar_block = ""
    text_x = 36

    avatar_path = PROFILE.get("avatar_path")
    if avatar_path and Path(avatar_path).exists():
        raw = Path(avatar_path).read_bytes()
        mime = "image/png" if str(avatar_path).lower().endswith(".png") else "image/jpeg"
        b64 = base64.b64encode(raw).decode("ascii")
        text_x = 156
        avatar_block = f"""
  <defs>
    <clipPath id="avatarClip"><rect x="36" y="40" width="96" height="96" rx="20" /></clipPath>
  </defs>
  <rect x="33" y="37" width="102" height="102" rx="23" fill="{THEME['surface']}" stroke="{THEME['accent']}" stroke-width="1.5" stroke-opacity="0.7" />
  <image href="data:{mime};base64,{b64}" x="36" y="40" width="96" height="96" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice" />"""
    else:
        smil_rot = (
            ""
            if STATIC
            else '<animateTransform attributeName="transform" type="rotate" from="0 32 32" to="360 32 32" dur="18s" repeatCount="indefinite" />'
        )
        avatar_block = f"""
  <g transform="translate(800, 56)">
    <rect x="0" y="0" width="64" height="64" rx="16" fill="{THEME['surface']}" stroke="{THEME['border']}" />
    <g class="anim-only">
      <circle cx="32" cy="32" r="18" fill="none" stroke="{THEME['accent']}" stroke-width="1.5" stroke-dasharray="4 4">{smil_rot}</circle>
    </g>
    <g class="reduced-only">
      <circle cx="32" cy="32" r="18" fill="none" stroke="{THEME['accent']}" stroke-width="1.5" stroke-dasharray="4 4" />
    </g>
    <circle cx="32" cy="32" r="5" fill="{THEME['accent']}" />
  </g>"""

    reveal_0 = "" if STATIC else f'class="reveal" style="animation-delay: {delay:.2f}s"'
    reveal_1 = "" if STATIC else f'class="reveal" style="animation-delay: {delay + 0.10:.2f}s"'
    reveal_2 = "" if STATIC else f'class="reveal" style="animation-delay: {delay + 0.20:.2f}s"'
    dot_cls = "" if STATIC else 'class="status-dot"'
    cursor_cls = "mono" if STATIC else "mono cursor"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <defs>
    <radialGradient id="heroGlow" cx="12%" cy="0%" r="75%">
      <stop offset="0%" stop-color="{THEME['accent']}" stop-opacity="0.16" />
      <stop offset="100%" stop-color="{THEME['bg']}" stop-opacity="0" />
    </radialGradient>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="url(#heroGlow)" />
  {avatar_block}

  <g {reveal_0}>
    <circle cx="{text_x + 5}" cy="46" r="4" fill="{THEME['accent_secondary']}" {dot_cls} />
    <text x="{text_x + 17}" y="50" fill="{THEME['text_muted']}" font-size="11.5" class="mono" letter-spacing="0.06em">{esc(PROFILE['status'])}</text>
    <rect x="760" y="34" width="106" height="24" rx="6" fill="{THEME['surface']}" stroke="{THEME['border']}" />
    <text x="813" y="50" text-anchor="middle" fill="{THEME['accent']}" font-size="11.5" class="mono">{esc(PROFILE['handle'])}</text>
  </g>

  <g {reveal_1}>
    <text x="{text_x}" y="98" fill="{THEME['text_primary']}" font-size="38" font-weight="700" class="sans" letter-spacing="-0.02em">{esc(PROFILE['name'])}<tspan fill="{THEME['accent']}" font-size="36" font-weight="500" class="{cursor_cls}" dx="4">_</tspan></text>
  </g>

  <g {reveal_2}>
    <text x="{text_x}" y="132" fill="{THEME['text_secondary']}" font-size="14.5" class="sans">{esc(PROFILE['tagline'])}</text>
  </g>
</svg>"""


def render_tile(tile: dict, font_css: str, delay: float) -> str:
    w, h = 290, 96
    reveal = "" if STATIC else f'class="reveal" style="animation-delay: {delay:.2f}s"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <rect x="1" y="14" width="3.5" height="{h - 28}" rx="1.75" fill="{THEME['accent']}" opacity="0.9" />

  <g {reveal}>
    <text x="22" y="30" fill="{THEME['accent']}" font-size="11" class="mono" letter-spacing="0.08em">{esc(tile['kicker'])}</text>
    <text x="22" y="56" fill="{THEME['text_primary']}" font-size="19" font-weight="600" class="sans">{esc(tile['title'])}</text>
    <text x="22" y="77" fill="{THEME['text_muted']}" font-size="12" class="mono">{esc(tile['sub'])}</text>
  </g>
</svg>"""


def render_activity(stats: dict, font_css: str, delay: float) -> str:
    w, h = 900, 240
    months = stats["monthly"][-12:]
    max_val = max((m["count"] for m in months), default=1) or 1

    chart_x, chart_y, chart_w, chart_h = 36, 92, 560, 102
    bar_slot = chart_w / max(len(months), 1)
    bar_w = min(28, bar_slot * 0.58)

    anim_bars = []
    static_bars = []
    for idx, m in enumerate(months):
        count = m["count"]
        ratio = count / max_val
        bh = 4 if count == 0 else max(8, round(ratio * chart_h))
        bx = chart_x + idx * bar_slot + (bar_slot - bar_w) / 2
        by = chart_y + chart_h - bh
        bar_fill = THEME["border"] if count == 0 else THEME["accent"]
        bar_delay = delay + 0.15 + idx * 0.04

        track = f'<rect x="{bx:.1f}" y="{chart_y}" width="{bar_w:.1f}" height="{chart_h}" rx="5" fill="{THEME["surface"]}" />'
        label = f'<text x="{bx + bar_w / 2:.1f}" y="{chart_y + chart_h + 20}" text-anchor="middle" fill="{THEME["text_muted"]}" font-size="11" class="mono">{esc(m["label"])}</text>'
        val_lbl = (
            f'<text x="{bx + bar_w / 2:.1f}" y="{by - 6:.1f}" text-anchor="middle" fill="{THEME["text_secondary"]}" font-size="10" class="mono">{count}</text>'
            if count > 0
            else ""
        )

        static_bar = f"""
        {track}
        <rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh}" rx="5" fill="{bar_fill}" />
        {val_lbl}
        {label}"""
        static_bars.append(static_bar)

        if not STATIC:
            smil = f"""
          <animate attributeName="height" from="0" to="{bh}" dur="0.55s" begin="{bar_delay:.2f}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />
          <animate attributeName="y" from="{chart_y + chart_h}" to="{by:.1f}" dur="0.55s" begin="{bar_delay:.2f}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />"""
            val_reveal = f'<g class="reveal" style="animation-delay: {bar_delay + 0.15:.2f}s">{val_lbl}</g>' if val_lbl else ""
            anim_bars.append(f"""
        {track}
        <rect x="{bx:.1f}" y="{chart_y + chart_h}" width="{bar_w:.1f}" height="0" rx="5" fill="{bar_fill}">{smil}
        </rect>
        {val_reveal}
        {label}""")

    if STATIC:
        bars_block = "".join(static_bars)
    else:
        bars_block = f"""
  <g class="anim-only">
    {''.join(anim_bars)}
  </g>
  <g class="reduced-only">
    {''.join(static_bars)}
  </g>"""

    kpis = [
        ("CURRENT STREAK", plural_days(stats["current_streak"]), THEME["accent"]),
        ("ACTIVE DAYS", plural_days(stats["active_days"]), THEME["accent_secondary"]),
        ("BUSIEST DAY", f"{stats['busiest_day']} ({stats['busiest_day_count']})", THEME["accent"]),
    ]
    kpi_svg = []
    for i, (label, val, dot_color) in enumerate(kpis):
        ky = 52 + i * 58
        reveal = "" if STATIC else f'class="reveal" style="animation-delay: {delay + 0.15 + i * 0.08:.2f}s"'
        kpi_svg.append(f"""
  <g {reveal}>
    <rect x="632" y="{ky - 20}" width="232" height="48" rx="10" fill="{THEME['surface']}" stroke="{THEME['border']}" />
    <circle cx="648" cy="{ky - 5}" r="3" fill="{dot_color}" />
    <text x="657" y="{ky - 2}" fill="{THEME['text_muted']}" font-size="10" class="mono" letter-spacing="0.06em">{esc(label)}</text>
    <text x="646" y="{ky + 18}" fill="{THEME['text_primary']}" font-size="16" font-weight="600" class="sans">{esc(val)}</text>
  </g>""")

    header_reveal = "" if STATIC else f'class="reveal" style="animation-delay: {delay:.2f}s"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {header_reveal}>
    <text x="36" y="42" fill="{THEME['text_primary']}" font-size="18" font-weight="600" class="sans">Monthly Contributions</text>
    <text x="36" y="62" fill="{THEME['text_muted']}" font-size="12" class="mono">{stats['total_contributions']} contributions in the last 12 months</text>
  </g>

  {bars_block}
  {''.join(kpi_svg)}
</svg>"""


def render_repo(repo: dict, font_css: str, delay: float) -> str:
    w, h = 442, 164
    reveal = "" if STATIC else f'class="reveal" style="animation-delay: {delay:.2f}s"'
    tag_w = max(72, len(repo["tag"]) * 6.8 + 18)

    wrapped = textwrap.wrap(repo["desc"], width=56)[:2]
    if len(textwrap.wrap(repo["desc"], width=56)) > 2 and wrapped:
        wrapped[-1] = wrapped[-1][:53].rstrip() + "..."
    desc_tspans = "".join(
        f'<tspan x="24" dy="{"0" if i == 0 else "18"}">{esc(line)}</tspan>'
        for i, line in enumerate(wrapped)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="15" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {reveal}>
    <rect x="24" y="20" width="{tag_w:.1f}" height="20" rx="5" fill="{THEME['surface']}" stroke="{THEME['border']}" />
    <text x="33" y="33.5" fill="{THEME['accent']}" font-size="10" class="mono" letter-spacing="0.06em">{esc(repo['tag'])}</text>

    <text x="24" y="66" fill="{THEME['text_primary']}" font-size="19" font-weight="600" class="sans">{esc(repo['name'])}</text>
    <text x="24" y="88" fill="{THEME['text_secondary']}" font-size="12.5" class="sans">{desc_tspans}</text>

    <circle cx="29" cy="140" r="5" fill="{esc(repo['lang_color'])}" />
    <text x="41" y="144" fill="{THEME['text_muted']}" font-size="12" class="mono">{esc(repo['lang'])}</text>
    <text x="148" y="144" fill="{THEME['text_muted']}" font-size="12" class="mono">★ {esc(repo['stars'])}   ⑂ {esc(repo['forks'])}</text>
    <text x="418" y="144" text-anchor="end" fill="{THEME['accent']}" font-size="12" class="mono">View ↗</text>
  </g>
</svg>"""


def render_heatmap(stats: dict, font_css: str, delay: float) -> str:
    w, h = 900, 182
    weeks = stats["weeks"][-52:]
    cell = 12
    gap = 3.5
    start_x = 46
    start_y = 54
    palette = THEME["heatmap"]

    cells = []
    for wi, week in enumerate(weeks):
        col_delay = delay + 0.08 + wi * 0.012
        for di, level in enumerate(week[:7]):
            cx = start_x + wi * (cell + gap)
            cy = start_y + di * (cell + gap)
            idx = min(max(int(level), 0), len(palette) - 1)
            color = palette[idx]
            if not STATIC and idx > 0:
                cells.append(
                    f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="2.5" '
                    f'fill="{color}" class="cell-anim" style="animation-delay: {col_delay:.2f}s" />'
                )
            else:
                cells.append(
                    f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="2.5" fill="{color}" />'
                )

    day_labels = [(1, "Mon"), (3, "Wed"), (5, "Fri")]
    days_svg = "".join(
        f'<text x="36" y="{start_y + row * (cell + gap) + 9:.1f}" text-anchor="end" fill="{THEME["text_muted"]}" font-size="10" class="mono">{lbl}</text>'
        for row, lbl in day_labels
    )

    legend = "".join(
        f'<rect x="{772 + i * 16}" y="25" width="11" height="11" rx="2" fill="{c}" />'
        for i, c in enumerate(palette)
    )

    extra_css = (
        ""
        if STATIC
        else """
      .cell-anim {
        opacity: 0;
        animation: fadeIn 0.35s ease forwards;
      }"""
    )
    header_reveal = "" if STATIC else f'class="reveal" style="animation-delay: {delay:.2f}s"'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css, extra_css)}
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {header_reveal}>
    <text x="46" y="34" fill="{THEME['text_primary']}" font-size="15" font-weight="600" class="sans">Contribution Graph<tspan fill="{THEME['text_muted']}" font-size="11.5" font-weight="400" class="mono" dx="10">· {stats['total_contributions']} total</tspan></text>
    <text x="764" y="34" text-anchor="end" fill="{THEME['text_muted']}" font-size="10" class="mono">Less</text>
    {legend}
    <text x="858" y="34" fill="{THEME['text_muted']}" font-size="10" class="mono">More</text>
  </g>

  {days_svg}
  {''.join(cells)}
</svg>"""


# ==============================================================================
# 4. MAIN ENTRYPOINT
# ==============================================================================
def load_stats() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {
        "total_contributions": 35,
        "current_streak": 2,
        "active_days": 9,
        "busiest_day": "Tue",
        "busiest_day_count": 14,
        "monthly": [
            {"label": m, "count": c}
            for m, c in zip(
                ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
                [0, 0, 5, 0, 0, 0, 10, 0, 0, 5, 5, 10],
            )
        ],
        "weeks": [[0] * 7 for _ in range(52)],
    }


def merge_featured_repos(stats: dict) -> list[dict]:
    """Merges live repo counts from stats.json into PROFILE['featured_repos']."""
    live = stats.get("repos", {})
    merged = []
    for repo in PROFILE["featured_repos"]:
        entry = dict(repo)
        if repo["name"] in live:
            info = live[repo["name"]]
            entry["stars"] = str(info.get("stars", entry["stars"]))
            entry["forks"] = str(info.get("forks", entry["forks"]))
            if info.get("lang"):
                entry["lang"] = info["lang"]
            if info.get("lang_color"):
                entry["lang_color"] = info["lang_color"]
        merged.append(entry)
    return merged


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = load_stats()
    repos = merge_featured_repos(stats)

    # Collect every character rendered across all cards for exact pyftsubset glyph pruning
    all_text = (
        PROFILE["name"]
        + PROFILE["handle"]
        + PROFILE["tagline"]
        + PROFILE["status"]
        + "".join(t["kicker"] + t["title"] + t["sub"] for t in PROFILE["tiles"])
        + "".join(r["name"] + r["tag"] + r["desc"] + r["lang"] + str(r["stars"]) + str(r["forks"]) for r in repos)
        + "Monthly Contributions contributions in the last 12 months CURRENT STREAK ACTIVE DAYS BUSIEST DAY day days"
        + "Contribution Graph total Less More Mon Wed Fri View ↗ ★ ⑂ _ · ..."
        + "".join(m["label"] + str(m["count"]) for m in stats["monthly"])
        + f"{stats['total_contributions']}{stats['current_streak']}{stats['active_days']}{stats['busiest_day']}{stats['busiest_day_count']}"
        + "0123456789"
    )

    sans_css = build_subset_font_css(THEME["font_sans_path"], "BrandSans", all_text)
    mono_css = build_subset_font_css(THEME["font_mono_path"], "BrandMono", all_text)
    font_css = f"{sans_css}\n{mono_css}".strip()

    outputs = {
        "hero.svg": render_hero(font_css, delay=0.05),
        "tile-1.svg": render_tile(PROFILE["tiles"][0], font_css, delay=0.25),
        "tile-2.svg": render_tile(PROFILE["tiles"][1], font_css, delay=0.35),
        "tile-3.svg": render_tile(PROFILE["tiles"][2], font_css, delay=0.45),
        "activity.svg": render_activity(stats, font_css, delay=0.55),
    }

    for idx, repo in enumerate(repos, start=1):
        outputs[f"repo-{idx}.svg"] = render_repo(repo, font_css, delay=0.75 + (idx - 1) * 0.10)

    outputs["heatmap.svg"] = render_heatmap(stats, font_css, delay=0.75 + len(repos) * 0.10)

    for filename, svg in outputs.items():
        (OUT_DIR / filename).write_text(svg, encoding="utf-8")
        print(f"Wrote {OUT_DIR / filename} ({'STATIC' if STATIC else 'ANIMATED'})")


if __name__ == "__main__":
    main()
