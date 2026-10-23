import json
import sqlite3
from pathlib import Path

import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "data" / "fitness_agent.db"

st.set_page_config(
    page_title="Fitness Network Research",
    layout="wide",
)

st.title("Fitness Network Research")
st.caption("Review saved webpage captures and AI extractions.")

if not DATABASE_PATH.exists():
    st.error("Database not found. Run import_captures.py first.")
    st.stop()

# Open the database in read-only mode.
with sqlite3.connect(
    DATABASE_PATH.as_uri() + "?mode=ro",
    uri=True,
) as connection:
    connection.row_factory = sqlite3.Row
    captures = [
        dict(row)
        for row in connection.execute("""
            SELECT *
            FROM captures
            ORDER BY checked_at_utc DESC, id DESC
        """).fetchall()
    ]

if not captures:
    st.info("No captures stored yet.")
    st.stop()

st.metric("Stored page captures", len(captures))
st.caption("This is a capture count, not a venue count.")

capture_by_id = {capture["id"]: capture for capture in captures}

selected_id = st.selectbox(
    "Choose a capture",
    options=list(capture_by_id),
    format_func=lambda capture_id: (
        f"{capture_by_id[capture_id]['checked_at_utc']} | "
        f"{capture_by_id[capture_id]['brand_name'] or 'Unknown brand'} | "
        f"Capture {capture_id}"
    ),
)

capture = capture_by_id[selected_id]
extraction = json.loads(capture["extraction_json"])
venue = extraction.get("venue", {})

st.write("Source:", capture["source_url"])
st.write("Checked at UTC:", capture["checked_at_utc"])
st.write("Review status:", capture["review_status"])

if extraction.get("input_truncated"):
    st.warning("Only part of the webpage was supplied to the model.")

st.info(
    "Matching evidence confirms text exists. "
    "It does not establish operating status or correct interpretation."
)

left, right = st.columns(2)

with left:
    st.subheader("Extracted information")

    st.write("Brand:", venue.get("name") or "Unknown")
    st.write("Services:", venue.get("services", []))
    st.write("Programmes:", venue.get("programmes", []))

    st.subheader("Branch candidates")
    branches = venue.get("branches", [])

    if branches:
        st.dataframe(branches, use_container_width=True)
    else:
        st.caption("No retained branches in this capture.")

    st.subheader("Packages")
    packages = venue.get("packages", [])

    if packages:
        st.dataframe(packages, use_container_width=True)
    else:
        st.caption("No retained packages in this capture.")

    st.subheader("Deals")
    deals = venue.get("deals", [])

    if deals:
        st.dataframe(deals, use_container_width=True)
    else:
        st.caption("No retained deals in this capture.")

    with st.expander("Flagged items"):
        st.json(extraction.get("rejected_items", {}))

    with st.expander("Full extraction"):
        st.json(extraction)

with right:
    st.subheader("Saved webpage text")

    search = st.text_input(
        "Find text in this capture",
        placeholder="For example: Chevrons or 19.90",
    )

    webpage_text = capture["webpage_text"]

    if search:
        lines = webpage_text.splitlines()
        matching_indices = [
            index
            for index, line in enumerate(lines)
            if search.casefold() in line.casefold()
        ]

        st.write(f"Matching lines: {len(matching_indices)}")

        for index in matching_indices[:20]:
            start = max(0, index - 2)
            end = min(len(lines), index + 3)
            st.code("\n".join(lines[start:end]), language=None)

        if len(matching_indices) > 20:
            st.caption("Showing the first 20 matches.")

    st.text_area(
        "Full source text",
        value=webpage_text,
        height=650,
        disabled=True,
    )