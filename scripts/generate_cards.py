#!/usr/bin/env python3
"""
Generates animated, editorial-styled SVG profile cards into cards/.
Usage:
  python scripts/generate_cards.py          # Animated output
  STATIC=1 python scripts/generate_cards.py # Final frame for screenshots
"""

import base64
import html
import io
import json
import os
import textwrap
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

STATIC = os.getenv("STATIC", "0") == "1"
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "stats.json"
OUT_DIR = ROOT / "cards"

# ==============================================================================
# 1. EDITORIAL THEME & PROFILE CONFIGURATION
# ==============================================================================
THEME = {
    "bg": "#F4F3EF",              # Warm paper card fill
    "border": "#E4E2DC",          # Subtle 1px card border & dividers
    "text_primary": "#141413",    # High-contrast ink black
    "text_secondary": "#3F3F3C",  # Body copy
    "text_muted": "#73726E",      # Monospace kickers & axis labels
    "bar_default": "#141413",     # Standard monthly bar fill
    "bar_current": "#D2D0C8",     # Current partial month bar fill
    "accent": "#2563EB",          # Cobalt blue accent (peak bar, dot, italic accent)
    # 5-step heatmap palette (0 -> max contributions in cobalt blue)
    "heatmap": ["#E5E4DF", "#C7D8FD", "#8FB2FA", "#5285F5", "#2563EB"],
    # Local font files to subset & embed as base64 WOFF data URIs
    "font_serif_path": ROOT / "assets" / "fonts" / "InstrumentSerif-Regular.ttf",
    "font_serif_italic_path": ROOT / "assets" / "fonts" / "InstrumentSerif-Italic.ttf",
    "font_sans_path": ROOT / "assets" / "fonts" / "Inter-Regular.ttf",
    "font_mono_path": ROOT / "assets" / "fonts" / "JetBrainsMono-Regular.ttf",
    "font_serif_fallback": "'Instrument Serif', 'Playfair Display', Georgia, 'Times New Roman', serif",
    "font_sans_fallback": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono_fallback": "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}

PROFILE = {
    "kicker": "CYBERSECURITY & FULL-STACK ENGINEER",
    "first_name": "Jay",
    "last_name": "Sonar",
    "bio_line_1": "I build full-stack systems, research security,",
    "bio_line_2": "and ship open-source software in public.",
    "url_label": "github.com/Jaysonar07",
    # Optional portrait image path -> auto-converted into ASCII art portrait
    "avatar_path": ROOT / "assets" / "avatar.png",
    "tiles": [
        {"kicker": "01 / CODE", "title": "GitHub", "sub": "@Jaysonar07 ↗"},
        {"kicker": "02 / NETWORK", "title": "LinkedIn", "sub": "Jay Sonar ↗"},
        {"kicker": "03 / DIRECT", "title": "Email", "sub": "jaysonar2007@gmail.com ↗"},
    ],
    "featured_repos": [
        {
            "kicker": "WEB3 · SOLIDITY",
            "name": "ScholarParchment",
            "desc": "Transparent blockchain fund tracking platform built with Next.js & Supabase.",
            "lang": "TypeScript",
        },
        {
            "kicker": "AI · FINTECH",
            "name": "WiseupAI",
            "desc": "AI-powered personal finance tracker with habit analytics & smart savings plans.",
            "lang": "TypeScript",
        },
        {
            "kicker": "REAL-TIME SYSTEMS",
            "name": "Queuely",
            "desc": "Smart real-time queue management and logging system engineered for live events.",
            "lang": "TypeScript",
        },
    ],
}


# ==============================================================================
# 2. FONT SUBSETTING & ASCII PORTRAIT HELPERS
# ==============================================================================
def build_subset_font_css(
    font_path: Path, family_name: str, glyphs: str, italic: bool = False
) -> str:
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
    style = "italic" if italic else "normal"
    return (
        f"@font-face {{\n"
        f"  font-family: '{family_name}';\n"
        f"  src: url('data:font/woff;base64,{b64}') format('woff');\n"
        f"  font-weight: 100 900;\n"
        f"  font-style: {style};\n"
        f"}}"
    )


def build_ascii_portrait_svg(x: int, y: int, delay: float) -> str:
    """Converts assets/avatar.png into crisp SVG ASCII art lines, or renders a fallback ASCII emblem."""
    ramp = "@%#*+=-:. "
    lines: list[str] = []

    if Image and PROFILE["avatar_path"] and Path(PROFILE["avatar_path"]).exists():
        img = Image.open(PROFILE["avatar_path"]).convert("L")
        img = ImageOps.autocontrast(img, cutoff=2)
        cols, rows = 58, 36
        img = img.resize((cols, rows))
        for r in range(rows):
            row_chars = []
            for c in range(cols):
                nx = (c - cols / 2) / (cols / 2)
                ny = (r - rows / 2) / (rows / 2)
                if nx * nx + ny * ny > 0.96:
                    row_chars.append(" ")
                    continue
                lum = img.getpixel((c, r))
                idx = int((lum / 255) * (len(ramp) - 1))
                row_chars.append(ramp[idx])
            lines.append("".join(row_chars))
    else:
        lines = [
            "                 ..::++====++::..                 ",
            "             .:+*################*+:.             ",
            "           :+###*+==--::::::--==+*###+:           ",
            "         .+##*=-..              ..-=*##+.         ",
            "        :##*-..    ..::====::..    ..-*##:        ",
            "       :##=.     .:+*########*+:.     .=##:       ",
            "      .##+.     :+##*=-....-=*##+:     .+##.      ",
            "      :##:     .##*-..      ..-*##.     :##:      ",
            "      +##.     +##:    .##.    :##+     .##+      ",
            "      +##.     +##:   .####.   :##+     .##+      ",
            "      :##:     .##*-..      ..-*##.     :##:      ",
            "      .##+.     :+##*=-....-=*##+:     .+##.      ",
            "       :##=.     .:+*########*+:.     .=##:       ",
            "        :##*-..    ..::====::..    ..-*##:        ",
            "         .+##*=-..              ..-=*##+.         ",
            "           :+###*+==--::::::--==+*###+:           ",
            "             .:+*################*+:.             ",
            "                 ..::++====++::..                 ",
        ]

    svg_lines = []
    line_height = 6.2 if len(lines) > 25 else 11.5
    font_size = 5.6 if len(lines) > 25 else 9.5
    for idx, line in enumerate(lines):
        ly = y + idx * line_height
        line_delay = delay + 0.12 + idx * 0.012
        cls_attr = 'class="mono"' if STATIC else f'class="mono reveal" style="animation-delay:{line_delay:.2f}s"'
        svg_lines.append(
            f'<text x="{x}" y="{ly:.1f}" fill="#575652" font-size="{font_size}" '
            f'xml:space="preserve" {cls_attr}>{esc(line)}</text>'
        )
    return "\n".join(svg_lines)


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def base_style(font_css: str) -> str:
    if STATIC:
        return f"""<style>
      {font_css}
      .serif {{ font-family: 'BrandSerif', {THEME['font_serif_fallback']}; }}
      .serif-italic {{ font-family: 'BrandSerifItalic', {THEME['font_serif_fallback']}; font-style: italic; }}
      .sans {{ font-family: 'BrandSans', {THEME['font_sans_fallback']}; }}
      .mono {{ font-family: 'BrandMono', {THEME['font_mono_fallback']}; }}
    </style>"""

    return f"""<style>
      {font_css}
      .serif {{ font-family: 'BrandSerif', {THEME['font_serif_fallback']}; }}
      .serif-italic {{ font-family: 'BrandSerifItalic', {THEME['font_serif_fallback']}; font-style: italic; }}
      .sans {{ font-family: 'BrandSans', {THEME['font_sans_fallback']}; }}
      .mono {{ font-family: 'BrandMono', {THEME['font_mono_fallback']}; }}

      @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes popIn {{
        from {{ opacity: 0; transform: scale(0.65); }}
        to   {{ opacity: 1; transform: scale(1); }}
      }}
      .reveal {{
        opacity: 0;
        animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }}
      .cell-pop {{
        opacity: 0;
        transform-box: fill-box;
        transform-origin: center;
        animation: popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }}
      .reduced-only {{
        display: none;
      }}
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


def anim_attr(delay: float, cls: str = "reveal") -> str:
    if STATIC:
        return ""
    return f'class="{cls}" style="animation-delay: {delay:.2f}s"'


# ==============================================================================
# 3. CARD RENDERERS
# ==============================================================================
def render_hero(font_css: str, delay: float = 0.05) -> str:
    w, h = 900, 390
    portrait_svg = build_ascii_portrait_svg(x=545, y=68, delay=delay)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <!-- Top Kicker -->
  <g {anim_attr(delay)}>
    <rect x="52" y="48" width="9" height="9" rx="2.5" fill="{THEME['accent']}" />
    <text x="72" y="56.5" fill="{THEME['text_muted']}" font-size="11.5" class="mono" letter-spacing="0.14em">{esc(PROFILE['kicker'])}</text>
  </g>

  <!-- Large Stacked Serif Name -->
  <g {anim_attr(delay + 0.10)}>
    <text x="50" y="156" fill="{THEME['text_primary']}" font-size="84" font-weight="400" class="serif" letter-spacing="-0.02em">{esc(PROFILE['first_name'])}</text>
  </g>
  <g {anim_attr(delay + 0.18)}>
    <text x="50" y="236" fill="{THEME['text_primary']}" font-size="84" font-weight="400" class="serif" letter-spacing="-0.02em">{esc(PROFILE['last_name'])}</text>
  </g>

  <!-- Two-line Bio & Link -->
  <g {anim_attr(delay + 0.28)}>
    <text x="52" y="286" fill="{THEME['text_secondary']}" font-size="16" class="sans">{esc(PROFILE['bio_line_1'])}</text>
    <text x="52" y="310" fill="{THEME['text_secondary']}" font-size="16" class="sans">{esc(PROFILE['bio_line_2'])}</text>
  </g>

  <g {anim_attr(delay + 0.36)}>
    <text x="52" y="346" fill="{THEME['text_primary']}" font-size="12.5" class="mono">{esc(PROFILE['url_label'])}<tspan fill="{THEME['accent']}" font-size="13" dx="8">↗</tspan></text>
  </g>

  <!-- Right-side ASCII Portrait -->
  {portrait_svg}
</svg>"""


def render_tile(tile: dict, font_css: str, delay: float) -> str:
    w, h = 290, 114
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {anim_attr(delay)}>
    <rect x="24" y="23" width="7" height="7" rx="2" fill="{THEME['accent']}" />
    <text x="38" y="30" fill="{THEME['text_muted']}" font-size="10.5" class="mono" letter-spacing="0.12em">{esc(tile['kicker'])}</text>
    <text x="24" y="66" fill="{THEME['text_primary']}" font-size="30" font-weight="400" class="serif">{esc(tile['title'])}</text>
    <text x="24" y="92" fill="{THEME['text_muted']}" font-size="11.5" class="mono">{esc(tile['sub'])}</text>
  </g>
</svg>"""


def render_activity(stats: dict, font_css: str, delay: float) -> str:
    w, h = 900, 356
    months = stats["monthly"][-12:]
    max_val = max((m["count"] for m in months), default=1) or 1
    peak_idx = max(range(len(months)), key=lambda i: months[i]["count"], default=0)

    chart_x, chart_y, chart_w, chart_h = 46, 174, 540, 124
    bar_slot = chart_w / max(len(months), 1)
    bar_w = min(36, bar_slot * 0.74)

    anim_bars = []
    static_bars = []
    for idx, m in enumerate(months):
        count = m["count"]
        ratio = count / max_val
        bh = 5 if count == 0 else max(12, round(ratio * chart_h))
        bx = chart_x + idx * bar_slot + (bar_slot - bar_w) / 2
        by = chart_y + chart_h - bh
        bar_delay = delay + 0.16 + idx * 0.04

        is_peak = idx == peak_idx and count > 0
        is_last = idx == len(months) - 1 and not is_peak
        if count == 0:
            fill = THEME["border"]
        elif is_peak:
            fill = THEME["accent"]
        elif is_last:
            fill = THEME["bar_current"]
        else:
            fill = THEME["bar_default"]

        label = f'<text x="{bx + bar_w / 2:.1f}" y="{chart_y + chart_h + 22}" text-anchor="middle" fill="{THEME["text_muted"]}" font-size="11" class="mono">{esc(m["label"])}</text>'
        peak_static = ""
        peak_anim = ""
        if is_peak:
            peak_static = (
                f'<text x="{bx + bar_w / 2:.1f}" y="{by - 10:.1f}" text-anchor="middle" '
                f'fill="{THEME["accent"]}" font-size="11.5" font-weight="600" class="mono">{count:,}</text>'
            )
            peak_anim = (
                f'<text x="{bx + bar_w / 2:.1f}" y="{by - 10:.1f}" text-anchor="middle" '
                f'fill="{THEME["accent"]}" font-size="11.5" font-weight="600" class="mono reveal" '
                f'style="animation-delay:{bar_delay + 0.25:.2f}s">{count:,}</text>'
            )

        static_bars.append(f"""
        {peak_static}
        <rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh}" rx="5" fill="{fill}" />
        {label}""")

        if not STATIC:
            smil = f"""
            <animate attributeName="height" from="0" to="{bh}" dur="0.65s" begin="{bar_delay:.2f}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />
            <animate attributeName="y" from="{chart_y + chart_h}" to="{by:.1f}" dur="0.65s" begin="{bar_delay:.2f}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />"""
            anim_bars.append(f"""
        {peak_anim}
        <rect x="{bx:.1f}" y="{chart_y + chart_h}" width="{bar_w:.1f}" height="0" rx="5" fill="{fill}">{smil}
        </rect>
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

    rx = 656
    total_days = stats.get("window_days", 365)
    streak = stats["current_streak"]
    streak_unit = "day" if streak == 1 else "days"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <!-- Top Left Heading -->
  <g {anim_attr(delay)}>
    <text x="46" y="64" fill="{THEME['text_muted']}" font-size="11" class="mono" letter-spacing="0.14em">THE LAST 12 MONTHS ON GITHUB</text>
    <text x="46" y="116" fill="{THEME['text_primary']}" font-size="48" class="serif" letter-spacing="-0.02em">{stats['total_contributions']:,} <tspan class="serif-italic">contributions</tspan></text>
  </g>

  {bars_block}

  <!-- Right Column KPI Stack -->
  <g {anim_attr(delay + 0.15)}>
    <text x="{rx}" y="106" fill="{THEME['text_primary']}" font-size="42" class="serif">{streak} <tspan class="serif-italic">{streak_unit}</tspan></text>
    <text x="{rx}" y="128" fill="{THEME['text_muted']}" font-size="13" class="sans">current streak</text>
    <line x1="{rx}" y1="148" x2="854" y2="148" stroke="{THEME['border']}" />
  </g>

  <g {anim_attr(delay + 0.25)}>
    <text x="{rx}" y="198" fill="{THEME['text_primary']}" font-size="42" class="serif">{stats['active_days']} <tspan fill="#9E9D99">/ {total_days}</tspan></text>
    <text x="{rx}" y="220" fill="{THEME['text_muted']}" font-size="13" class="sans">days with a commit</text>
    <line x1="{rx}" y1="240" x2="854" y2="240" stroke="{THEME['border']}" />
  </g>

  <g {anim_attr(delay + 0.35)}>
    <text x="{rx}" y="290" fill="{THEME['text_primary']}" font-size="42" class="serif">{stats['busiest_day_count']}</text>
    <text x="{rx}" y="312" fill="{THEME['text_muted']}" font-size="13" class="sans">on the busiest day ({esc(stats['busiest_day'])})</text>
  </g>
</svg>"""


def render_repo(repo: dict, font_css: str, delay: float) -> str:
    w, h = 290, 174
    wrapped = textwrap.wrap(repo["desc"], width=36)[:3]
    if len(textwrap.wrap(repo["desc"], width=36)) > 3 and wrapped:
        wrapped[-1] = wrapped[-1][:33].rstrip() + "..."
    desc_tspans = "".join(
        f'<tspan x="22" dy="{"0" if i == 0 else "17"}">{esc(line)}</tspan>'
        for i, line in enumerate(wrapped)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {anim_attr(delay)}>
    <rect x="22" y="22" width="7" height="7" rx="2" fill="{THEME['accent']}" />
    <text x="36" y="29" fill="{THEME['text_muted']}" font-size="10" class="mono" letter-spacing="0.12em">{esc(repo['kicker'])}</text>

    <text x="22" y="64" fill="{THEME['text_primary']}" font-size="27" font-weight="400" class="serif">{esc(repo['name'])}</text>

    <text x="22" y="88" fill="{THEME['text_secondary']}" font-size="12.5" class="sans">{desc_tspans}</text>

    <text x="22" y="152" fill="{THEME['text_muted']}" font-size="11" class="mono">{esc(repo['lang'])}</text>
    <text x="268" y="152" text-anchor="end" fill="{THEME['accent']}" font-size="12" class="mono">↗</text>
  </g>
</svg>"""


def render_heatmap(stats: dict, font_css: str, delay: float) -> str:
    w, h = 900, 294
    weeks = stats["weeks"][-52:]
    month_markers = stats.get("month_markers", [])
    cell = 13.5
    gap = 3.2
    start_x = 46
    start_y = 112
    palette = THEME["heatmap"]

    cells = []
    for wi, week in enumerate(weeks):
        col_delay = delay + 0.12 + wi * 0.012
        for di, level in enumerate(week[:7]):
            cx = start_x + wi * (cell + gap)
            cy = start_y + di * (cell + gap)
            color = palette[min(max(int(level), 0), len(palette) - 1)]
            cls = "" if STATIC else "cell-pop"
            style = "" if STATIC else f'style="animation-delay:{col_delay:.2f}s"'
            cells.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{color}" class="{cls}" {style} />'
            )

    months_svg = []
    if month_markers:
        for m in month_markers:
            mx = start_x + m["week_idx"] * (cell + gap)
            months_svg.append(
                f'<text x="{mx:.1f}" y="{start_y + 7 * (cell + gap) + 22:.1f}" '
                f'fill="{THEME["text_muted"]}" font-size="11" class="mono">{esc(m["label"])}</text>'
            )
    else:
        fallback_months = ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
        for i, lbl in enumerate(fallback_months):
            mx = start_x + int(i * 4.3) * (cell + gap)
            months_svg.append(
                f'<text x="{mx:.1f}" y="{start_y + 7 * (cell + gap) + 22:.1f}" '
                f'fill="{THEME["text_muted"]}" font-size="11" class="mono">{lbl}</text>'
            )

    legend_y = start_y + 7 * (cell + gap) + 11
    legend = "".join(
        f'<rect x="{758 + i * 14}" y="{legend_y:.1f}" width="11" height="11" rx="2.5" fill="{c}" />'
        for i, c in enumerate(palette)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {anim_attr(delay)}>
    <text x="46" y="76" fill="{THEME['text_primary']}" font-size="40" class="serif" letter-spacing="-0.02em">Every day, <tspan fill="{THEME['accent']}" class="serif-italic">in blue</tspan></text>
    <text x="854" y="72" text-anchor="end" fill="{THEME['text_muted']}" font-size="11" class="mono" letter-spacing="0.14em">REFRESHED DAILY</text>
  </g>

  {''.join(cells)}
  {''.join(months_svg)}

  <g {anim_attr(delay + 0.55)}>
    <text x="748" y="{legend_y + 9.5:.1f}" text-anchor="end" fill="{THEME['text_muted']}" font-size="11" class="mono">less</text>
    {legend}
    <text x="836" y="{legend_y + 9.5:.1f}" fill="{THEME['text_muted']}" font-size="11" class="mono">more</text>
  </g>
</svg>"""


# ==============================================================================
# 4. MAIN ENTRYPOINT
# ==============================================================================
def load_stats() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {
        "total_contributions": 648,
        "current_streak": 19,
        "active_days": 184,
        "window_days": 365,
        "busiest_day": "Wed",
        "busiest_day_count": 24,
        "monthly": [
            {"label": m, "count": c}
            for m, c in zip(
                ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
                [48, 46, 38, 94, 42, 42, 31, 26, 19, 21, 34, 12],
            )
        ],
        "weeks": [[(w * 3 + d) % 5 for d in range(7)] for w in range(52)],
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = load_stats()

    all_text = (
        PROFILE["kicker"]
        + PROFILE["first_name"]
        + PROFILE["last_name"]
        + PROFILE["bio_line_1"]
        + PROFILE["bio_line_2"]
        + PROFILE["url_label"]
        + "".join(t["kicker"] + t["title"] + t["sub"] for t in PROFILE["tiles"])
        + "".join(r["kicker"] + r["name"] + r["desc"] + r["lang"] for r in PROFILE["featured_repos"])
        + "THE LAST 12 MONTHS ON GITHUB contributions day days current streak / days with a commit on the busiest day"
        + "Every day, in blue REFRESHED DAILY less more ↗ @%#*+=-:. ..."
        + "".join(m["label"] + f"{m['count']:,}" for m in stats["monthly"])
        + "".join(m["label"] for m in stats.get("month_markers", []))
        + f"{stats['total_contributions']:,}{stats['current_streak']}{stats['active_days']}{stats.get('window_days', 365)}{stats['busiest_day']}{stats['busiest_day_count']}"
        + "0123456789"
    )

    serif_css = build_subset_font_css(THEME["font_serif_path"], "BrandSerif", all_text, italic=False)
    serif_it_css = build_subset_font_css(THEME["font_serif_italic_path"], "BrandSerifItalic", all_text, italic=True)
    sans_css = build_subset_font_css(THEME["font_sans_path"], "BrandSans", all_text)
    mono_css = build_subset_font_css(THEME["font_mono_path"], "BrandMono", all_text)
    font_css = "\n".join(filter(None, [serif_css, serif_it_css, sans_css, mono_css]))

    outputs = {
        "hero.svg": render_hero(font_css, delay=0.05),
        "tile-1.svg": render_tile(PROFILE["tiles"][0], font_css, delay=0.30),
        "tile-2.svg": render_tile(PROFILE["tiles"][1], font_css, delay=0.40),
        "tile-3.svg": render_tile(PROFILE["tiles"][2], font_css, delay=0.50),
        "activity.svg": render_activity(stats, font_css, delay=0.60),
        "repo-1.svg": render_repo(PROFILE["featured_repos"][0], font_css, delay=0.85),
        "repo-2.svg": render_repo(PROFILE["featured_repos"][1], font_css, delay=0.95),
        "repo-3.svg": render_repo(PROFILE["featured_repos"][2], font_css, delay=1.05),
        "heatmap.svg": render_heatmap(stats, font_css, delay=1.15),
    }

    for filename, svg in outputs.items():
        (OUT_DIR / filename).write_text(svg, encoding="utf-8")
        print(f"Wrote {OUT_DIR / filename} ({'STATIC' if STATIC else 'ANIMATED'})")


if __name__ == "__main__":
    main()
