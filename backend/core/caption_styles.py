"""
caption_styles.py — ASS style definitions for animated video captions.
Each style defines the visual appearance and animation technique.
"""
from typing import Optional


# Supported caption styles
CAPTION_STYLES = ["karaoke", "word_pop", "typewriter", "highlight", "bounce"]

# Default font sizes per video ratio
FONT_SIZE_BY_RATIO = {
    "9:16": 62,   # Vertical/Reels — bigger text visually
    "16:9": 48,   # Horizontal/YouTube — smaller, wider space
    "1:1": 52,    # Square
}

# Margin from bottom edge (pixels) by ratio
MARGIN_V_BY_RATIO = {
    "9:16": 120,
    "16:9": 60,
    "1:1": 80,
}


def get_font_size(ratio: str, custom_size: Optional[int] = None) -> int:
    return custom_size or FONT_SIZE_BY_RATIO.get(ratio, 52)


def get_margin_v(ratio: str, custom_margin: Optional[int] = None) -> int:
    return custom_margin or MARGIN_V_BY_RATIO.get(ratio, 80)


def build_ass_header(
    style: str,
    ratio: str,
    font: str = "Helvetica-Bold",
    primary_color: str = "FFFFFF",   # BGR hex (no #, no alpha)
    active_color: str = "FFD700",    # Word being spoken (karaoke/highlight)
    outline: int = 3,
    shadow: int = 2,
    position: str = "bottom",        # top | center | bottom
    custom_font_size: Optional[int] = None,
    custom_margin_v: Optional[int] = None,
) -> str:
    """Generate the ASS header (script info + styles) for a given combination."""

    font_size = get_font_size(ratio, custom_font_size)
    margin_v = get_margin_v(ratio, custom_margin_v)

    # Dynamic resolution based on ratio to ensure font size is proportional
    # Standard: 1920x1080 (16:9)
    # Vertical: 1080x1920 (9:16)
    play_res_x = 1920
    play_res_y = 1080
    if ratio == "9:16":
        play_res_x = 1080
        play_res_y = 1920
    elif ratio == "1:1":
        play_res_x = 1080
        play_res_y = 1080

    # ASS alignment: 2=bottom-center, 5=center-center, 8=top-center
    alignment_map = {"bottom": 2, "center": 5, "top": 8}
    alignment = alignment_map.get(position, 2)

    # Convert HTML hex colors to ASS BGR (no alpha) format &H00BBGGRR
    def _to_ass_color(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            r, g, b = h[0:2], h[2:4], h[4:6]
            return f"&H00{b}{g}{r}"
        return "&H00FFFFFF"

    primary_ass = _to_ass_color(primary_color)
    active_ass = _to_ass_color(active_color)
    outline_color = "&H00000000"  # Black outline
    shadow_color = "&H80000000"   # Semi-transparent black shadow

    header = f"""[Script Info]
Title: Tudio Animated Captions
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_ass},{active_ass},{outline_color},{shadow_color},-1,0,0,0,100,100,0,0,1,{outline},{shadow},{alignment},10,10,{margin_v},1
Style: Active,{font},{font_size},{active_ass},{primary_ass},{outline_color},{shadow_color},-1,0,0,0,100,100,0,0,1,{outline + 1},{shadow},2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def _ts(seconds: float) -> str:
    """Convert float seconds to ASS timestamp format h:mm:ss.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def group_words_into_lines(
    words: list[dict],
    words_per_line: int = 4,
    max_gap_seconds: float = 1.0,
) -> list[list[dict]]:
    """
    Group word-level timestamps into display lines.
    Breaks when max words_per_line reached or a silence gap is detected.
    """
    if not words:
        return []

    groups: list[list[dict]] = []
    current_group: list[dict] = []

    for i, word in enumerate(words):
        # Break on silence gap
        if current_group and (word["start"] - current_group[-1]["end"]) > max_gap_seconds:
            groups.append(current_group)
            current_group = []

        current_group.append(word)

        if len(current_group) >= words_per_line:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    return groups


# ─── Style Generators ────────────────────────────────────────────────────────

def render_karaoke(groups: list[list[dict]]) -> str:
    """
    Karaoke style: each word is coloured as it's spoken.
    Uses ASS {\k<centiseconds>}word timing tags.
    """
    lines = []
    for group in groups:
        group_start = group[0]["start"]
        group_end = group[-1]["end"]

        parts = []
        for word in group:
            duration_cs = max(1, int((word["end"] - word["start"]) * 100))
            parts.append(f"{{\\k{duration_cs}}}{word['word']} ")

        text = "".join(parts).rstrip()
        line = f"Dialogue: 0,{_ts(group_start)},{_ts(group_end)},Default,,0,0,0,,{text}"
        lines.append(line)

    return "\n".join(lines)


def render_word_pop(groups: list[list[dict]]) -> str:
    """
    Word Pop style: each word appears individually at its timestamp.
    Multiple words visible simultaneously as they accumulate in the line.
    """
    lines = []
    for group in groups:
        group_end = group[-1]["end"]
        # Each word appears from its start and stays until the line ends
        visible_words = []
        for idx, word in enumerate(group):
            word_start = word["start"]
            # Accumulate words that should be visible at this timestamp
            segment_end = group[idx + 1]["start"] if idx + 1 < len(group) else group_end
            
            visible_words.append(word["word"])
            text = " ".join(visible_words)
            # Draw current word in active colour
            active_text = " ".join(visible_words[:-1])
            if active_text:
                active_text += " "
            active_part = f"{{\\c&H00FFD700&}}{word['word']}{{\\c&H00FFFFFF&}}"
            display = active_text + active_part if active_text else active_part
            
            line = f"Dialogue: 0,{_ts(word_start)},{_ts(segment_end)},Default,,0,0,0,,{display}"
            lines.append(line)

    return "\n".join(lines)


def render_typewriter(groups: list[list[dict]]) -> str:
    """
    Typewriter style: full line revealed word by word.
    Simulated via progressive word reveals.
    """
    return render_word_pop(groups)  # Word-reveal is the closest pure-ASS approximation


def render_highlight(groups: list[list[dict]]) -> str:
    """
    Highlight style: entire line visible, current word highlighted.
    """
    lines = []
    for group in groups:
        group_start = group[0]["start"]
        group_end = group[-1]["end"]

        for idx, word in enumerate(group):
            word_start = word["start"]
            word_end = group[idx + 1]["start"] if idx + 1 < len(group) else group_end

            parts = []
            for j, w in enumerate(group):
                if j == idx:
                    parts.append(f"{{\\c&H00FFD700&\\bord4}}{w['word']}{{\\c&H00FFFFFF&\\bord3}}")
                else:
                    parts.append(f"{{\\c&H80FFFFFF&}}{w['word']}{{\\c&H00FFFFFF&}}")

            text = " ".join(parts)
            line = f"Dialogue: 0,{_ts(word_start)},{_ts(word_end)},Default,,0,0,0,,{text}"
            lines.append(line)

    return "\n".join(lines)


def render_bounce(groups: list[list[dict]]) -> str:
    """
    Bounce style: each word pops in with a scale-from-0 animation.
    Individual word dialogs with \\t() transform.
    """
    lines = []
    for group in groups:
        group_end = group[-1]["end"]
        for idx, word in enumerate(group):
            word_start = word["start"]
            word_end = group[idx + 1]["start"] if idx + 1 < len(group) else group_end
            # Scale from 0→110→100% in 150ms
            text = f"{{\\fscx0\\fscy0\\t(0,80,\\fscx110\\fscy110)\\t(80,150,\\fscx100\\fscy100)}}{word['word']}"
            line = f"Dialogue: 0,{_ts(word_start)},{_ts(word_end)},Default,,0,0,0,,{text}"
            lines.append(line)

    return "\n".join(lines)


STYLE_RENDERERS = {
    "karaoke": render_karaoke,
    "word_pop": render_word_pop,
    "typewriter": render_typewriter,
    "highlight": render_highlight,
    "bounce": render_bounce,
}


def generate_ass_content(
    word_groups: list[list[dict]],
    style: str,
    ratio: str,
    options: dict,
) -> str:
    """
    Full ASS file content generator.
    options keys: font, primary_color, active_color, outline, shadow, position,
                  font_size, margin_v, words_per_line
    """
    renderer = STYLE_RENDERERS.get(style, render_karaoke)
    header = build_ass_header(
        style=style,
        ratio=ratio,
        font=options.get("font", "Helvetica-Bold"),
        primary_color=options.get("primary_color", "FFFFFF"),
        active_color=options.get("active_color", "FFD700"),
        outline=options.get("outline", 3),
        shadow=options.get("shadow", 2),
        position=options.get("position", "bottom"),
        custom_font_size=options.get("font_size"),
        custom_margin_v=options.get("margin_v"),
    )
    body = renderer(word_groups)
    return header + body
