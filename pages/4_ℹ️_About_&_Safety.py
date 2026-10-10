import streamlit as st
import os
import sys

# Ensure project root is strictly first in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not sys.path or sys.path[0] != PROJECT_ROOT:
    if PROJECT_ROOT in sys.path:
        sys.path.remove(PROJECT_ROOT)
    sys.path.insert(0, PROJECT_ROOT)

from live.sources import load_live_data
from utils.dates import format_checked_date
from utils.geo import geocode_location
from utils.styles import inject_custom_css, render_header, LOGO_PATH


st.set_page_config(
    page_title="About & Trust Principles | CareAtZero",
    page_icon=LOGO_PATH,
    layout="wide"
)

inject_custom_css()
render_header("about")

st.markdown('<div class="cz-title">About CareAtZero</div>'
            '<div class="cz-sub">Our mission, sources, scoring and privacy.</div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["Mission", "Scoring", "Sources", "Privacy"])

with t1:
    st.subheader("Our Mission")
    st.markdown("""
    **CareAtZero** is a free, mobile-first web application designed to help uninsured and low-income individuals and families find **genuinely free or very-low-cost medical, dental, vision, and behavioral healthcare** they can realistically access soon.

    ### The Problem We Solve
    Free and safety-net healthcare exists, but the information is fragmented across federal directories, charitable clinic networks, mobile clinic calendars, and local public health feeds.

    An uninsured person often faces:
    - Calling clinics only to find out they are not free or require insurance.
    - Missing time-sensitive pop-up events (like RAM or mobile dental buses).
    - Arriving without required income or residency documents.
    - Searching directories that rank by distance rather than the realistic time to care.

    **CareAtZero bridges this gap** by normalizing safety-net data, verifying cost tiers, scoring realistic accessibility, and giving patients a clear document checklist before they travel.
    """)

with t2:
    st.subheader("Care Access Score Methodology")
    st.markdown("""
    Rather than relying on opaque AI or simple distance sorting, CareAtZero uses an open, transparent **100-Point Care Access Scoring Model**:
    """)

    st.markdown("""
    | Match Signal | Weight | How It Is Evaluated |
    | :--- | :--- | :--- |
    | **Cost Fit** | **35%** | **Free ($0 fee)** receives maximum 35 pts; **Very Low Cost ($5-$25)** receives 25 pts; **Sliding Scale** receives 18-20 pts based on income band fit. |
    | **Time to Care / Availability** | **25%** | Pop-up event happening **Today (25 pts)** or **This Week (22-24 pts)**; permanent clinics with daily walk-in access receive 20-24 pts. |
    | **Service Match** | **15%** | Exact match for requested service (Dental, Medical, Vision, Behavioral Health) receives 15 pts. |
    | **Eligibility Confidence** | **10%** | Barrier-free clinics with no ID/income document barriers receive 10 pts; standard sliding scale verification receives 8 pts. |
    | **Distance / Transit Burden** | **10%** | Proximity to user: <5 mi (10 pts), 5-15 mi (8 pts), 15-30 mi (6 pts), >30 mi (2-4 pts). |
    | **Data Freshness & Completeness** | **5%** | Verified from official directory in the current cycle (5 pts); stale or unverified records are penalized. |
    """)

    st.info("💡 **Strict Business Rule:** A provider is **never labeled Free** unless the underlying source explicitly verifies $0 patient charge for that service.")

with t3:
    st.subheader("Live data sources")
    st.markdown("Every search uses current records from these official public sources, "
                "fetched automatically and refreshed every few hours:")

    search_loc = st.session_state.get("search_loc") or "27601"
    a_lat, a_lon, _ = geocode_location(search_loc)
    with st.spinner("Checking the live sources..."):
        live = load_live_data(a_lat, a_lon)

    rows = []
    for src in live.statuses:
        rows.append({
            "Source": f"[{src.name}]({src.url})",
            "Provides": src.provides,
            "Status": f"Live · {src.count} records" if src.ok else "Unavailable right now",
            "Checked": format_checked_date(src.checked),
        })
    st.markdown("| Source | Provides | Status | Checked |\n|---|---|---|---|\n" +
                "\n".join(f"| {r['Source']} | {r['Provides']} | {r['Status']} | {r['Checked']} |" for r in rows))

    st.markdown("""
**Also used**
- **U.S. Census Bureau ZIP code list**, to place any U.S. ZIP code on the map.
- **Community pop-up events** (mobile dental buses, county health vans and similar) that don't publish
  a schedule online. These are entered by hand from the organizer, marked *manually verified*, and shown
  only until their end date.

**If a source is down**, the app leaves it out and says so, instead of guessing. If every clinic source
is down, it shows a saved copy of the CareAtZero directory (last verified September 2026), clearly labeled.
    """)
    if live.using_saved_directory:
        st.warning("Right now the live clinic sources can't be reached, so searches use the saved directory.")

with t4:
    st.subheader("Privacy, Safety & Medical Disclaimers")
    st.markdown("""
    ### 🔒 Privacy Guarantee
    - **No Protected Health Information (PHI) Stored:** CareAtZero never asks for or stores your medical history, diagnosis, Social Security Number, or payment info.
    - **No User Account Required:** Search freely without creating a login.
    - **Nothing Saved About You:** Searches are not stored. To keep a clinic's details, use **Download info** or copy the text on its detail screen. It stays on your phone, not on a server.

    ### ⚠️ Medical Advice & Emergency Disclaimer
    CareAtZero is an informational resource navigation directory and **does not provide medical diagnosis, treatment advice, or triage**. 

    - **Life-Threatening Emergency:** Call **911** immediately or go to the nearest emergency department.
    - **Suicide & Crisis Lifeline:** Call or text **988** (Free, confidential 24/7 mental health support).
    """)



