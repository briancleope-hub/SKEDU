"""
wallpaper_ui.py - the Streamlit part of the wallpaper feature.
Call render_wallpaper_section(schedule, DAYS, course_color) from app.py.
"""
from datetime import date

import streamlit as st
from PIL import Image, UnidentifiedImageError

from wallpaper import PHONE_SIZES, make_wallpaper, to_png_bytes


def classes_for_day(schedule, day, color_for):
    """Pick one day's classes from the full schedule, sorted by start time, with colors."""
    todays = [dict(row, Color=color_for(row["Course"])) for row in schedule if row["Day"] == day]
    return sorted(todays, key=lambda row: row["Start"])


def render_wallpaper_section(schedule, days, color_for):
    """Show the upload box, options, preview, and download button."""
    st.markdown("### Make a wallpaper")

    uploaded = st.file_uploader("Upload a background image", type=["png", "jpg", "jpeg", "webp"])
    col1, col2 = st.columns(2)
    today_index = date.today().weekday()  # Monday = 0, same order as DAYS
    day = col1.selectbox("Day", days, index=today_index, key="wallpaper_day")
    phone = col2.selectbox("Phone size", list(PHONE_SIZES.keys()))

    if uploaded is None:
        st.info("Upload an image to see your wallpaper preview.")
        return

    try:
        background = Image.open(uploaded)
    except UnidentifiedImageError:
        st.error("This file can't be read as an image. Upload a PNG, JPG, or WEBP.")
        return

    classes = classes_for_day(schedule, day, color_for)
    with st.spinner("Making your wallpaper..."):
        wallpaper = make_wallpaper(background, day, classes, PHONE_SIZES[phone])

    st.image(wallpaper, caption="Preview", width=280)
    st.download_button(
        "Download wallpaper",
        data=to_png_bytes(wallpaper),
        file_name=f"skeduu-{day.lower()}.png",
        mime="image/png",
    )