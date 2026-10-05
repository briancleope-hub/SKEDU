import streamlit as st
import csv
import os
import re
import hashlib
from html import escape  # NEW: makes user text safe inside HTML
from datetime import time

from wallpaper_ui import render_wallpaper_section  # NEW

st.set_page_config(page_title="skeduu", page_icon="📅", layout="wide")
st.markdown(
    "<h1 style='color:#FF69B4;'>skeduu</h1>",
    unsafe_allow_html=True,
)

COLUMNS = ["Course", "Day", "Start", "End", "Instructor", "Location"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

PALETTE = [
    "#FF6B6B", "#4ECDC4", "#FFD93D", "#6A0572", "#1A936F",
    "#3D5A80", "#EE6C4D", "#9B5DE5", "#00BBF9", "#F15BB5",
]

def course_color(course_name):
    digest = hashlib.md5(course_name.encode()).hexdigest()
    index = int(digest, 16) % len(PALETTE)
    return PALETTE[index]

def safe_username(raw):
    # keep only letters, numbers, underscore, hyphen — everything else stripped
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", raw.strip())
    return cleaned.lower()

def load_schedule(data_file):
    if os.path.exists(data_file):
        with open(data_file, newline="", encoding="utf-8") as f:  # CHANGED: utf-8 for Vietnamese
            return list(csv.DictReader(f))
    return []

def save_schedule(data_file, schedule):
    with open(data_file, "w", newline="", encoding="utf-8") as f:  # CHANGED: utf-8
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(schedule)

# --- Username gate ---
if "username" not in st.session_state:
    st.session_state.username = ""

with st.sidebar:
    username_input = st.text_input("Your username", value=st.session_state.username)
    st.session_state.username = username_input

username = safe_username(st.session_state.username)

if not username:
    st.info("Enter a username in the sidebar to load or create your schedule.")
    st.stop()

DATA_FILE = f"schedule_{username}.csv"
st.markdown(f"Hello, **{username}**!")

schedule = load_schedule(DATA_FILE)

# --- Add class form ---
with st.sidebar:
    with st.form("add_class", clear_on_submit=True):
        course = st.text_input("Course name")
        day = st.selectbox("Day", DAYS)
        start = st.time_input("Start", value=time(9, 0))
        end = st.time_input("End", value=time(10, 0))
        instructor = st.text_input("Instructor")
        location = st.text_input("Room")
        submitted = st.form_submit_button("Add class")

# CHANGED: removed the duplicate copy of this block, and moved save + success
# INSIDE the else, so a conflicting class is no longer saved.
if submitted and course:
    new_start = start.strftime("%H:%M")
    new_end = end.strftime("%H:%M")

    conflict = None
    for r in schedule:
        if r["Day"] == day:
            if new_start < r["End"] and r["Start"] < new_end:
                conflict = r
                break

    if new_end <= new_start:  # NEW: catch "ends before it starts"
        st.error("End time must be after start time.")
    elif conflict:
        st.error(f"Conflict with {conflict['Course']} ({conflict['Start']}-{conflict['End']}) on {day}!")
    else:
        schedule.append({
            "Course": course,
            "Day": day,
            "Start": new_start,
            "End": new_end,
            "Instructor": instructor,
            "Location": location,
        })
        save_schedule(DATA_FILE, schedule)
        st.success(f"Added {course} to {day}, {new_start}-{new_end}!")

# --- Weekly color-coded grid (view only) ---
GRID_START_HOUR = 7
GRID_END_HOUR = 21
ROW_HEIGHT_PX = 40

def time_to_row(hhmm):
    h, m = map(int, hhmm.split(":"))
    return (h - GRID_START_HOUR) + (m / 60)

st.markdown("### Weekly view")

total_hours = GRID_END_HOUR - GRID_START_HOUR

# Grid lines + hour labels
grid_html = f"""
<div style="display:grid; grid-template-columns: 60px repeat({len(DAYS)}, 1fr);
            border: 1px solid #444;">
"""
grid_html += "<div></div>"
for d in DAYS:
    grid_html += f"<div style='text-align:center; font-weight:bold; padding:4px;'>{d}</div>"

for hour in range(GRID_START_HOUR, GRID_END_HOUR):
    grid_html += f"<div style='font-size:11px; color:#888; border-top:1px solid #333; height:{ROW_HEIGHT_PX}px;'>{hour:02d}:00</div>"
    for _ in DAYS:
        grid_html += f"<div style='border-top:1px solid #333; border-left:1px solid #333; height:{ROW_HEIGHT_PX}px;'></div>"
grid_html += "</div>"

# Class blocks, absolutely positioned within their own layer
blocks_html = f"""
<div style="position:absolute; top:0; left:0; width:100%; height:100%;
            display:grid; grid-template-columns: 60px repeat({len(DAYS)}, 1fr);
            pointer-events:none;">
"""
blocks_html += "<div></div>" * (len(DAYS) + 1)  # header row spacer

header_row_px = ROW_HEIGHT_PX  # matches the header row's rendered height

for i, d in enumerate(DAYS):
    for r in schedule:
        if r["Day"] != d:
            continue
        top = header_row_px + time_to_row(r["Start"]) * ROW_HEIGHT_PX
        height = (time_to_row(r["End"]) - time_to_row(r["Start"])) * ROW_HEIGHT_PX
        color = course_color(r["Course"])
        block_style = (
            f"position:absolute; top:{top}px; height:{height}px; width:95%; "
            f"background:{color}; border-radius:4px; padding:2px 4px; "
            f"font-size:11px; color:white; overflow:hidden;"
        )
        # CHANGED: escape() user-typed text before putting it in HTML
        blocks_html += (
            f'<div style="grid-column:{i+2}; grid-row:1; position:relative; height:0;">'
            f'<div style="{block_style}">{escape(r["Course"])}<br>{r["Start"]}-{r["End"]}<br>'
            f'<span style="font-size:9px;">{escape(r["Instructor"])} · {escape(r["Location"])}</span></div>'
            f'</div>'
        )
# Wrapper: relative container so the absolute overlay is scoped to it only
st.markdown(
    f"<div style='position:relative;'>{grid_html}{blocks_html}</div>",
    unsafe_allow_html=True,
)

# --- List view with delete buttons ---
st.markdown("### Manage classes")
cols = st.columns(len(DAYS))
for col, d in zip(cols, DAYS):
    with col:
        st.markdown(f"**{d}**")
        todays = [r for r in schedule if r["Day"] == d]
        todays.sort(key=lambda r: r["Start"])
        for i, row in enumerate(todays):
            color = course_color(row["Course"])
            st.markdown(
                f"<span style='color:{color};'>●</span> {row['Start']}–{row['End']}: {escape(row['Course'])}"
                f" <span style='color:#888; font-size:11px;'>({escape(row['Instructor'])}, {escape(row['Location'])})</span>",
                unsafe_allow_html=True,
            )
            if st.button("🗑", key=f"del_{d}_{i}"):
                schedule.remove(row)
                save_schedule(DATA_FILE, schedule)
                st.rerun()

# --- NEW: phone wallpaper ---
render_wallpaper_section(schedule, DAYS, course_color)