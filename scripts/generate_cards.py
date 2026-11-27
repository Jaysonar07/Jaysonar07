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
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    Image = None
    ImageEnhance = None
    ImageOps = None

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
    "tech_stack": [
        {"name": "TypeScript", "role": "PRIMARY · TYPESAFE", "icon": "typescript"},
        {"name": "Python", "role": "AI & SECURITY", "icon": "python"},
        {"name": "JavaScript", "role": "WEB · ES2024", "icon": "javascript"},
        {"name": "React", "role": "UI LIBRARY", "icon": "react"},
        {"name": "Next.js", "role": "FULL-STACK", "icon": "nextjs"},
        {"name": "Node.js", "role": "BACKEND RUNTIME", "icon": "nodejs"},
        {"name": "Solidity", "role": "SMART CONTRACTS", "icon": "solidity"},
        {"name": "PostgreSQL", "role": "DATABASE", "icon": "postgresql"},
        {"name": "PHP", "role": "SERVER & WEB", "icon": "php"},
        {"name": "Tailwind CSS", "role": "STYLING", "icon": "tailwind"},
        {"name": "Kali Linux", "role": "APPSEC & PENTEST", "icon": "kalilinux"},
        {"name": "Git", "role": "VERSION CONTROL", "icon": "git"},
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


ASCII_RAMP = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "


def build_ascii_portrait_svg(x: int, y: int, delay: float) -> str:
    """Converts assets/avatar.png into high-detail SVG ASCII art lines, or renders a fallback ASCII emblem."""
    lines: list[str] = []

    if Image and PROFILE["avatar_path"] and Path(PROFILE["avatar_path"]).exists():
        img = Image.open(PROFILE["avatar_path"]).convert("L")
        w_px, h_px = img.size
        # Tighter head-and-shoulders portrait crop so facial features have maximum character density
        img = img.crop((int(w_px * 0.08), int(h_px * 0.02), int(w_px * 0.92), int(h_px * 0.86)))
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Contrast(img).enhance(1.25)
        img = ImageEnhance.Sharpness(img).enhance(1.6)

        cols, rows = 112, 60
        img = img.resize((cols, rows), Image.Resampling.LANCZOS)
        for r in range(rows):
            row_chars = []
            for c in range(cols):
                nx = (c - cols / 2) / (cols / 2)
                ny = (r - rows / 2) / (rows / 2)
                dist = (nx * nx + ny * ny) ** 0.5
                if dist >= 1.0:
                    row_chars.append(" ")
                    continue
                lum = float(img.getpixel((c, r)))
                # Subtle gamma lift keeps facial midtones crisp against dark backgrounds
                lum = 255.0 * ((lum / 255.0) ** 0.88)
                # Smoothly feather outer circular vignette into the warm paper background
                if dist > 0.68:
                    t = ((dist - 0.68) / 0.32) ** 1.5
                    lum = lum * (1.0 - t) + 255.0 * t
                idx = min(len(ASCII_RAMP) - 1, max(0, int((lum / 255.0) * (len(ASCII_RAMP) - 1))))
                row_chars.append(ASCII_RAMP[idx])
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
    is_hi_res = len(lines) > 25
    line_height = 5.0 if is_hi_res else 11.5
    font_size = 4.6 if is_hi_res else 9.5
    ink_color = "#262523" if is_hi_res else "#575652"
    step_delay = 0.007 if is_hi_res else 0.012
    for idx, line in enumerate(lines):
        ly = y + idx * line_height
        line_delay = delay + 0.12 + idx * step_delay
        cls_attr = 'class="mono"' if STATIC else f'class="mono reveal" style="animation-delay:{line_delay:.2f}s"'
        svg_lines.append(
            f'<text x="{x}" y="{ly:.1f}" fill="{ink_color}" font-size="{font_size}" '
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
    portrait_svg = build_ascii_portrait_svg(x=542, y=45, delay=delay)

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


TECH_ICONS = {
    "typescript": """
      <rect x="2" y="2" width="20" height="20" rx="4" fill="#3178C6" />
      <path d="M10.8 11.4H8.4v6.8H6.6v-6.8H4.2V9.9h6.6v1.5zm1.4 5.2c.5.3 1.2.5 1.9.5.8 0 1.2-.3 1.2-.8 0-.5-.4-.7-1.4-1.1-1.3-.5-2-1.1-2-2.3 0-1.3 1-2.2 2.7-2.2.8 0 1.5.2 2 .4l-.4 1.4c-.4-.2-1-.4-1.6-.4-.7 0-1.1.3-1.1.7 0 .5.4.7 1.5 1.1 1.3.5 1.9 1.2 1.9 2.3 0 1.3-1 2.3-2.9 2.3-.9 0-1.8-.2-2.2-.5l.4-1.4z" fill="#FFFFFF" />
    """,
    "python": """
      <path d="M11.9 2C8.7 2 8.9 3.4 8.9 3.4v1.5h3.1v.5H6.5S4 5.1 4 8.4s2.2 3.2 2.2 3.2h1.3v-1.6s-.1-2.2 2.1-2.2h3.7s2 0 2-2V3.6S15.6 2 11.9 2zm-1.8 1.1c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7z" fill="#3776AB" />
      <path d="M12.1 22c3.2 0 3-1.4 3-1.4v-1.5H12v-.5h5.5s2.5.3 2.5-3-2.2-3.2-2.2-3.2h-1.3V14s.1 2.2-2.1 2.2h-3.7s-2 0-2 2v2.2S8.4 22 12.1 22zm1.8-1.1c-.4 0-.7-.3-.7-.7s.3-.7.7-.7.7.3.7.7-.3.7-.7.7z" fill="#EAB308" />
    """,
    "javascript": """
      <rect x="2" y="2" width="20" height="20" rx="4" fill="#FACC15" />
      <path d="M11.1 16.4c0 1.7-1 2.5-2.5 2.5-1 0-1.8-.4-2.2-1.1l1.2-.8c.2.4.5.7 1 .7.5 0 .8-.2.8-.9v-4.9h1.7v4.5zm2.1.3c.4.6 1 .9 1.9.9.8 0 1.3-.3 1.3-.8 0-.5-.4-.8-1.4-1.2l-.5-.2c-1.4-.5-2.2-1.2-2.2-2.5 0-1.2 1-2.1 2.6-2.1 1.1 0 1.9.4 2.5 1.3l-1.3.8c-.3-.5-.7-.7-1.2-.7-.5 0-.9.3-.9.7 0 .5.3.7 1.3 1.1l.5.2c1.6.6 2.4 1.3 2.4 2.6 0 1.5-1.2 2.3-2.9 2.3-1.6 0-2.6-.7-3.1-1.6l1.2-.8z" fill="#141413" />
    """,
    "react": """
      <circle cx="12" cy="12" r="2.1" fill="#0EA5E9" />
      <ellipse cx="12" cy="12" rx="9.5" ry="3.8" fill="none" stroke="#0EA5E9" stroke-width="1.4" />
      <ellipse cx="12" cy="12" rx="9.5" ry="3.8" fill="none" stroke="#0EA5E9" stroke-width="1.4" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="9.5" ry="3.8" fill="none" stroke="#0EA5E9" stroke-width="1.4" transform="rotate(120 12 12)" />
    """,
    "nextjs": """
      <circle cx="12" cy="12" r="9.8" fill="#141413" />
      <path d="M8.5 16.2V8.2h1.4l5.8 7.5-.9.7-4.9-6.3v6.1H8.5zm5.6-8h1.4v5.2h-1.4V8.2z" fill="#F4F3EF" />
    """,
    "nodejs": """
      <polygon points="12,2.2 20.5,7.1 20.5,16.9 12,21.8 3.5,16.9 3.5,7.1" fill="#16A34A" />
      <path d="M9.2 15.2V8.8h1.5l2.7 4.1V8.8h1.4v6.4h-1.5l-2.7-4.1v4.1H9.2z" fill="#FFFFFF" />
    """,
    "solidity": """
      <polygon points="12,2 6.8,10.2 12,13.1 17.2,10.2" fill="#3F3F3C" />
      <polygon points="12,2 12,13.1 17.2,10.2" fill="#141413" />
      <polygon points="12,22 6.8,13.8 12,16.7 17.2,13.8" fill="#73726E" />
      <polygon points="12,22 12,16.7 17.2,13.8" fill="#3F3F3C" />
    """,
    "postgresql": """
      <path d="M16.8 4.4c-1.4-.9-3.1-.8-4.8-.1-1.7-.7-3.4-.8-4.8.1C5 5.8 4.4 9 5.5 11.7c.7 1.8 2 3.1 3.3 3.7v3.1c0 .9.7 1.5 1.5 1.5h.9c.7 0 1.2-.5 1.2-1.2v-2.2c.9-.1 1.7-.5 2.4-1.1l1.2 2.4c.3.6 1 .8 1.6.5.6-.3.8-1 .5-1.6l-1.3-2.6c1.1-1.2 1.8-2.9 1.8-4.7 0-2.4-.7-4.1-1.8-5.1z" fill="#2563EB" />
      <circle cx="9.6" cy="8.5" r="0.9" fill="#FFFFFF" />
      <circle cx="14.4" cy="8.5" r="0.9" fill="#FFFFFF" />
    """,
    "php": """
      <ellipse cx="12" cy="12" rx="10" ry="6.2" fill="#6366F1" />
      <path d="M5.4 14.3l.9-4.6h1.9c1 0 1.6.5 1.4 1.5-.2 1-.9 1.6-2 1.6H6.7l-.3 1.5h-1zm1.5-2.4h.7c.5 0 .8-.2.9-.7.1-.4-.1-.6-.6-.6h-.7l-.3 1.3zm3.2 2.4l.9-4.6h1l-.3 1.4h.9c.9 0 1.4.4 1.2 1.3l-.4 1.9h-1l.4-1.8c.1-.4-.1-.6-.5-.6h-.7l-.5 2.4h-1zm4.5 0l.9-4.6h1.9c1 0 1.6.5 1.4 1.5-.2 1-.9 1.6-2 1.6h-.9l-.3 1.5h-1zm1.5-2.4h.7c.5 0 .8-.2.9-.7.1-.4-.1-.6-.6-.6h-.7l-.3 1.3z" fill="#FFFFFF" />
    """,
    "tailwind": """
      <path d="M12 6c-2.7 0-4.3 1.3-5 4 1-1.3 2.2-1.8 3.5-1.5.8.2 1.3.7 1.9 1.3 1 1 2.1 2.2 4.6 2.2 2.7 0 4.3-1.3 5-4-1 1.3-2.2 1.8-3.5 1.5-.8-.2-1.3-.7-1.9-1.3C15.6 7.2 14.5 6 12 6zm-5 6c-2.7 0-4.3 1.3-5 4 1-1.3 2.2-1.8 3.5-1.5.8.2 1.3.7 1.9 1.3 1 1 2.1 2.2 4.6 2.2 2.7 0 4.3-1.3 5-4-1 1.3-2.2 1.8-3.5 1.5-.8-.2-1.3-.7-1.9-1.3-1-1-2.1-2.2-4.6-2.2z" fill="#0284C7" />
    """,
    "kalilinux": """
      <path d="M12 2.2L4.2 5.6v5.9c0 4.9 3.3 9.2 7.8 10.5 4.5-1.3 7.8-5.6 7.8-10.5V5.6L12 2.2z" fill="#141413" />
      <path d="M8.4 9.5l3.1 2.4-3.1 2.4M12.5 14.5h3.2" fill="none" stroke="#2563EB" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
    """,
    "git": """
      <rect x="4.5" y="4.5" width="15" height="15" rx="3" transform="rotate(45 12 12)" fill="#EA580C" />
      <circle cx="10.2" cy="9.2" r="1.3" fill="#FFFFFF" />
      <circle cx="10.2" cy="14.8" r="1.3" fill="#FFFFFF" />
      <circle cx="14.6" cy="12" r="1.3" fill="#FFFFFF" />
      <path d="M10.2 10.5v3M10.8 9.8l3 1.7" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round" />
    """,
}


def render_stack(font_css: str, delay: float) -> str:
    w, h = 900, 356
    items = PROFILE["tech_stack"]
    cols = 4
    start_x, start_y = 46, 134
    cell_w, cell_h = 193, 60
    gap_x, gap_y = 12, 12

    tiles_svg = []
    for idx, item in enumerate(items):
        row = idx // cols
        col = idx % cols
        x = start_x + col * (cell_w + gap_x)
        y = start_y + row * (cell_h + gap_y)
        item_delay = delay + 0.12 + row * 0.08 + col * 0.04
        icon_inner = TECH_ICONS.get(item["icon"], "")

        tiles_svg.append(f"""
  <g {anim_attr(item_delay)}>
    <rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="12" fill="#ECEAE3" fill-opacity="0.55" stroke="{THEME['border']}" />
    <rect x="{x + 11}" y="{y + 12}" width="36" height="36" rx="9" fill="#FFFFFF" stroke="{THEME['border']}" />
    <svg x="{x + 19}" y="{y + 20}" width="20" height="20" viewBox="0 0 24 24">
      {icon_inner}
    </svg>
    <text x="{x + 57}" y="{y + 28}" fill="{THEME['text_primary']}" font-size="14" font-weight="600" class="sans">{esc(item['name'])}</text>
    <text x="{x + 57}" y="{y + 44}" fill="{THEME['text_muted']}" font-size="9.2" class="mono" letter-spacing="0.06em">{esc(item['role'])}</text>
  </g>""")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {anim_attr(delay)}>
    <rect x="46" y="42" width="8" height="8" rx="2" fill="{THEME['accent']}" />
    <text x="62" y="49.5" fill="{THEME['text_muted']}" font-size="11" class="mono" letter-spacing="0.14em">TOOLCHAIN &amp; LANGUAGES</text>
    <text x="854" y="49.5" text-anchor="end" fill="{THEME['text_muted']}" font-size="11" class="mono" letter-spacing="0.14em">FULL-STACK · SECURITY · AI</text>
    <text x="46" y="102" fill="{THEME['text_primary']}" font-size="44" class="serif" letter-spacing="-0.02em">Technologies I <tspan fill="{THEME['accent']}" class="serif-italic">build with</tspan></text>
  </g>

  {''.join(tiles_svg)}
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
    w, h = 900, 288
    weeks = stats["weeks"][-52:]
    month_markers = stats.get("month_markers", [])
    cell = 12.6
    gap = 3.0
    step = cell + gap
    start_x = 46
    start_y = 114
    palette = THEME["heatmap"]

    cells = []
    for wi, week in enumerate(weeks):
        col_delay = delay + 0.12 + wi * 0.012
        for di, level in enumerate(week[:7]):
            cx = start_x + wi * step
            cy = start_y + di * step
            color = palette[min(max(int(level), 0), len(palette) - 1)]
            cls = "" if STATIC else "cell-pop"
            style = "" if STATIC else f'style="animation-delay:{col_delay:.2f}s"'
            cells.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="2.8" '
                f'fill="{color}" class="{cls}" {style} />'
            )

    months_svg = []
    month_y = start_y + 7 * step + 22
    if month_markers:
        for m in month_markers:
            mx = start_x + m["week_idx"] * step
            months_svg.append(
                f'<text x="{mx:.1f}" y="{month_y:.1f}" '
                f'fill="{THEME["text_muted"]}" font-size="11" class="mono">{esc(m["label"])}</text>'
            )
    else:
        fallback_months = ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
        for i, lbl in enumerate(fallback_months):
            mx = start_x + int(i * 4.3) * step
            months_svg.append(
                f'<text x="{mx:.1f}" y="{month_y:.1f}" '
                f'fill="{THEME["text_muted"]}" font-size="11" class="mono">{lbl}</text>'
            )

    legend_y = 78
    legend = "".join(
        f'<rect x="{748 + i * 14}" y="{legend_y}" width="11" height="11" rx="2.5" fill="{c}" />'
        for i, c in enumerate(palette)
    )

    total = stats.get("total_contributions", 0)
    contrib_word = "contribution" if total == 1 else "contributions"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
  {base_style(font_css)}
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="{THEME['bg']}" stroke="{THEME['border']}" />

  <g {anim_attr(delay)}>
    <text x="46" y="66" fill="{THEME['text_primary']}" font-size="38" class="serif" letter-spacing="-0.02em">Every day, <tspan fill="{THEME['accent']}" class="serif-italic">in blue</tspan></text>
    <text x="46" y="90" fill="{THEME['text_muted']}" font-size="11.5" class="mono">{total:,} {contrib_word} in the last year</text>
    <text x="854" y="54" text-anchor="end" fill="{THEME['text_muted']}" font-size="11" class="mono" letter-spacing="0.14em">REFRESHED DAILY</text>
    <text x="740" y="{legend_y + 9.5:.1f}" text-anchor="end" fill="{THEME['text_muted']}" font-size="10.5" class="mono">less</text>
    {legend}
    <text x="854" y="{legend_y + 9.5:.1f}" text-anchor="end" fill="{THEME['text_muted']}" font-size="10.5" class="mono">more</text>
  </g>

  {''.join(cells)}
  {''.join(months_svg)}
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
        + "".join(s["name"] + s["role"] for s in PROFILE["tech_stack"])
        + "TOOLCHAIN & LANGUAGES FULL-STACK · SECURITY · AI Technologies I build with"
        + "Every day, in blue REFRESHED DAILY contribution contributions in the last year less more ↗ ... "
        + ASCII_RAMP
        + "".join(m["label"] for m in stats.get("month_markers", []))
        + f"{stats.get('total_contributions', 0):,}"
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
        "stack.svg": render_stack(font_css, delay=0.60),
        "repo-1.svg": render_repo(PROFILE["featured_repos"][0], font_css, delay=0.90),
        "repo-2.svg": render_repo(PROFILE["featured_repos"][1], font_css, delay=1.00),
        "repo-3.svg": render_repo(PROFILE["featured_repos"][2], font_css, delay=1.10),
        "heatmap.svg": render_heatmap(stats, font_css, delay=1.20),
    }

    for filename, svg in outputs.items():
        (OUT_DIR / filename).write_text(svg, encoding="utf-8")
        print(f"Wrote {OUT_DIR / filename} ({'STATIC' if STATIC else 'ANIMATED'})")


if __name__ == "__main__":
    main()
