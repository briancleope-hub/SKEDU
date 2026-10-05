"""
wallpaper.py - turns one day of a Skedu schedule into a phone wallpaper.

No Streamlit in here on purpose: this file only knows about images.
That makes it easy to test on its own and reuse later.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

PHONE_SIZES = {
    "Android (1080 x 2400)": (1080, 2400),
    "iPhone (1179 x 2556)": (1179, 2556),
}

FONT_DIR = Path(__file__).parent / "fonts"


def load_font(size, bold=False):
    """Load a font from the fonts/ folder, or fall back to Pillow's built-in one."""
    filename = "BeVietnamPro-Bold.ttf" if bold else "BeVietnamPro-Regular.ttf"
    path = FONT_DIR / filename
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def fit_to_screen(image, size):
    """Resize and crop the image so it exactly fills the phone screen."""
    image = ImageOps.exif_transpose(image)  # fixes photos that come in sideways
    return ImageOps.fit(image.convert("RGB"), size, method=Image.LANCZOS)


def shorten(text, font, max_width, draw):
    """Cut text and add '…' if it's too wide to fit."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def draw_schedule_card(background, day_name, classes):
    """Draw a frosted-glass card with the day's classes onto the background.

    classes: list of dicts with Skedu's columns: Course, Start, End, Location,
    Instructor, plus an optional "Color" (hex string).
    """
    width, height = background.size
    scale = width / 1080  # design at 1080px wide, scale for other phones

    pad = int(56 * scale)
    title_h = int(150 * scale)
    row_h = int(130 * scale)
    card_w = width - 2 * int(64 * scale)
    card_h = title_h + max(len(classes), 1) * row_h + pad

    # Sit below the lock-screen clock, but never run into the bottom edge.
    card_x = (width - card_w) // 2
    card_y = min(int(height * 0.40), height - card_h - int(height * 0.08))
    card_y = max(card_y, int(height * 0.28))
    box = (card_x, card_y, card_x + card_w, card_y + card_h)
    radius = int(44 * scale)

    # 1. Blur only the area behind the card (the "frosted glass" look).
    mask = Image.new("L", background.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)
    blurred = background.filter(ImageFilter.GaussianBlur(int(28 * scale)))
    result = Image.composite(blurred, background, mask).convert("RGBA")

    # 2. Darken the card a bit so white text is readable on any wallpaper.
    tint = Image.new("RGBA", background.size, (0, 0, 0, 0))
    ImageDraw.Draw(tint).rounded_rectangle(box, radius, fill=(10, 12, 20, 130))
    result = Image.alpha_composite(result, tint)

    # 3. Write the text.
    draw = ImageDraw.Draw(result)
    title_font = load_font(int(60 * scale), bold=True)
    time_font = load_font(int(34 * scale), bold=True)
    subject_font = load_font(int(42 * scale), bold=True)
    room_font = load_font(int(32 * scale))

    text_x = card_x + pad + int(12 * scale)  # room for the color bar
    time_col = int(200 * scale)
    text_w = card_w - 2 * pad - time_col

    draw.text((text_x, card_y + pad), day_name, font=title_font, fill="white")

    y = card_y + title_h
    if not classes:
        draw.text((text_x, y), "No classes today", font=subject_font, fill=(230, 230, 235))
        return result.convert("RGB")

    for i, lesson in enumerate(classes):
        if i > 0:  # thin line between rows
            draw.line((text_x, y - 10 * scale, card_x + card_w - pad, y - 10 * scale),
                      fill=(255, 255, 255), width=max(1, int(2 * scale)))

        # Colored bar = same color the course has in the weekly grid
        bar_x = text_x - int(22 * scale)
        draw.rounded_rectangle((bar_x, y + 4 * scale, bar_x + 8 * scale, y + 96 * scale),
                               radius=int(4 * scale), fill=lesson.get("Color", "#FFD678"))

        # Left column: start time (big) and end time (small)
        draw.text((text_x, y), lesson["Start"], font=time_font, fill=(255, 214, 120))
        draw.text((text_x, y + 50 * scale), lesson["End"], font=room_font, fill=(200, 200, 210))

        # Right column: course name, then "Room · Instructor"
        course = shorten(lesson["Course"], subject_font, text_w, draw)
        draw.text((text_x + time_col, y), course, font=subject_font, fill="white")
        details = " · ".join(p for p in (lesson.get("Location", ""), lesson.get("Instructor", "")) if p)
        details = shorten(details, room_font, text_w, draw)
        draw.text((text_x + time_col, y + 56 * scale), details, font=room_font, fill=(200, 200, 210))
        y += row_h

    return result.convert("RGB")


def make_wallpaper(image, day_name, classes, size):
    """The main function: background image + schedule -> finished wallpaper."""
    background = fit_to_screen(image, size)
    return draw_schedule_card(background, day_name, classes)


def to_png_bytes(image):
    """Turn a Pillow image into PNG bytes so Streamlit can offer it as a download."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()