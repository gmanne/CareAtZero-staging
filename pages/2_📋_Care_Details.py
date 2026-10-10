import streamlit as st
import os
import sys

# Ensure project root is strictly first in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not sys.path or sys.path[0] != PROJECT_ROOT:
    if PROJECT_ROOT in sys.path:
        sys.path.remove(PROJECT_ROOT)
    sys.path.insert(0, PROJECT_ROOT)

from database.db import get_site_by_id, get_event_by_id, is_care_saved, toggle_saved_care
from scoring.care_access_score import calculate_care_access_score
from utils.calendar import generate_ics_calendar
from utils.export import generate_shareable_referral_text
from utils.geo import get_directions_url, geocode_location, haversine_distance, get_user_current_zip
from utils.styles import inject_custom_css, render_header, LOGO_PATH
from utils.dates import today_str, format_checked_date, format_event_dates
from live.sources import find_record


st.set_page_config(
    page_title="Care Details | CareAtZero",
    page_icon=LOGO_PATH,
    layout="wide"
)

inject_custom_css()
render_header("details")

# Check if a care option is selected in session state
selected_id = st.session_state.get("selected_care_id")
selected_type = st.session_state.get("selected_care_type", "site")

if not selected_id:
    # Default fallback: pick first site or event
    st.info("No specific care option selected. Showing default safety-net option.")
    selected_id = "site_shac_01"
    selected_type = "site"

# Where the user searched from (also used to find the live record and its distance)
user_loc = st.session_state.get("search_loc") or get_user_current_zip()
u_lat, u_lon, loc_label = geocode_location(user_loc)

# Fetch record: live data first, then the saved directory
record = find_record(selected_id, u_lat, u_lon)

if not record:
    st.error(f"Care option with ID '{selected_id}' not found.")
    if st.button("⬅️ Return to Search"):
        st.switch_page("pages/1_🔍_Find_Free_Care.py")
    st.stop()

FACILITY_LABELS = {
    "fqhc": "Federally funded community health center",
    "free_clinic": "Free & charitable clinic",
    "behavioral_health": "Behavioral health treatment facility",
    "mobile": "Mobile clinic",
}

# Basic fields
title = record.get("title") or record.get("name")
cost_class = record.get("cost_class", "Sliding Scale")
is_event = record.get("record_type") == "event"
full_addr = f"{record.get('address')}, {record.get('city')}, {record.get('state')} {record.get('zip_code')}"

# Calculate score breakdown for details (for the type of care the user searched for)
has_location = record.get("latitude") is not None and record.get("longitude") is not None
dist = haversine_distance(u_lat, u_lon, record.get("latitude"), record.get("longitude")) if has_location else 0.0
score, breakdown, reasons = calculate_care_access_score(
    record=record,
    service_needed=st.session_state.get("selected_service", "Medical"),
    distance_miles=dist,
    reference_date_str=today_str()
)

# Back button & Breadcrumb
if st.button("Back to results", icon=":material/arrow_back:", type="tertiary"):
    st.switch_page("pages/1_🔍_Find_Free_Care.py")

# Title Header & Badges
cost_badge = {
    "Free": "<span class='badge-free'>100% FREE CARE ($0)</span>",
    "Very Low Cost": "<span class='badge-lowcost'>VERY LOW COST ($5-$25)</span>",
    "Sliding Scale": "<span class='badge-sliding'>SLIDING SCALE DISCOUNT</span>",
}.get(cost_class, "<span class='badge-sliding'>COST: ASK THE CLINIC</span>")
type_badge = "<span class='badge-event'>🚐 MOBILE / POP-UP EVENT</span>" if is_event else "<span class='badge-lowcost'>🏥 PERMANENT SAFETY-NET CLINIC</span>"

st.markdown(f"""
<div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 18px; padding: 16px; margin-bottom: 14px;">
    <div style="margin-bottom: 8px;">{cost_badge} {type_badge}</div>
    <div class="cz-title" style="font-size: 24px; margin: 6px 0 6px 0;">{title}</div>
    <div style="font-size: 0.95rem; color: #475569; margin-bottom: 12px;">
        📍 <strong>{full_addr}</strong> • <span style="color:#2563EB; font-weight:600;">{dist} miles from {user_loc}</span>
    </div>
    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <span class="score-badge" style="font-size: 0.95rem;">
            ⭐ Care Access Score: <strong>{score}/100</strong>
        </span>
        <span class="trust-pill">
            🛡️ Uninsured Acceptance: {record.get('uninsured_acceptance', 'All Welcome')}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main actions: directions first, then call / calendar / take the info along
maps_url = get_directions_url(full_addr, record.get("latitude"), record.get("longitude"))
st.link_button("Get directions", maps_url, icon=":material/directions:", type="primary", use_container_width=True)

act1, act2 = st.container(key="row_detail_actions").columns(2)
with act1:
    phone_num = record.get("phone", "")
    if phone_num:
        clean_phone = phone_num.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        st.link_button("Call", f"tel:{clean_phone}", icon=":material/call:", use_container_width=True)
    else:
        st.button("No phone listed", disabled=True, use_container_width=True)

with act2:
    # Add to Calendar (.ics download)
    ics_data = generate_ics_calendar(record)
    file_name = f"careatzero_{record.get('id')}.ics"
    st.download_button(
        label="Add to calendar",
        data=ics_data,
        file_name=file_name,
        mime="text/calendar",
        icon=":material/calendar_add_on:",
        use_container_width=True
    )

# Take the details along (no account needed): download or copy to text someone
referral_text = generate_shareable_referral_text(record, score, reasons)
st.download_button(
    label="Download info",
    data=referral_text,
    file_name=f"referral_{record.get('id')}.txt",
    mime="text/plain",
    icon=":material/download:",
    use_container_width=True
)
with st.expander("Copy this info to text or share"):
    st.code(referral_text, language="text")

st.markdown("---")

# Two Column Detailed Information
left_col, right_col = st.columns([1.6, 1.4])

with left_col:
    # 1. What to Bring & Readiness Checklist
    st.subheader("What to bring")
    st.markdown("*Review and prepare these items before your visit:*")

    docs = record.get("documents_required", [])
    if not docs or "None" in docs[0]:
        st.success("✅ **No ID or income documentation required** for this care event/clinic! (Bring a list of any current prescription medications if taking them).")
    else:
        for doc in docs:
            st.checkbox(f"**{doc}**", key=f"chk_{doc}")

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # 2. Timing & Appointment Policy
    st.subheader("When to go")
    if is_event:
        st.markdown(f"""
        - **Dates:** {format_event_dates(record.get('date_start'), record.get('date_end'))}
        - **Hours:** {record.get('time_details')}
        - **Intake Rule:** {record.get('appointment_rule')}
        - **Organizer:** {record.get('organizer_name')}
        """)
    else:
        st.markdown(f"""
        - **Operating Hours:** {record.get('hours_summary')}
        - **Appointment Rule:** {record.get('appointment_rule')}
        - **Facility type:** {FACILITY_LABELS.get(record.get('type') or '', (record.get('type') or 'Clinic').replace('_', ' ').title())}
        """)

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # 3. Services Offered
    st.subheader("Services")
    services = record.get("services", [])
    st.markdown(" ".join(f"<span class='trust-pill'>{s}</span>" for s in services), unsafe_allow_html=True)

    if record.get("notes"):
        st.markdown(f"**Special Notes:** {record.get('notes')}")

with right_col:
    # 4. Care Access Score Breakdown
    st.subheader("Care Access Score")
    st.markdown(f"Care Access Score: **{score}/100** *(Transparent 100-Point Model)*")

    # Score breakdown metric cards
    for signal, pts in breakdown.items():
        st.progress(pts / 35.0 if "35%" in signal else (pts / 25.0 if "25%" in signal else pts / 15.0), text=f"{signal}: **{pts} pts**")

    st.markdown("**Why this matches:**")
    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # 5. Verified Source & Freshness
    st.subheader("Where this comes from")
    source_name = record.get("source_name", "Official Directory Feed")
    source_url = record.get("source_url", "https://careatzero.org")
    last_checked = format_checked_date(record.get("last_checked")) if record.get("last_checked") else "Not listed"
    if record.get("is_live"):
        status_label, status_color = f"LIVE — fetched {last_checked}", "green"
    elif "manually verified" in source_name or "saved copy" in source_name:
        status_label, status_color = f"Saved directory — last verified {last_checked}", "orange"
    else:
        status_label = (record.get("source_status") or "active").upper()
        status_color = "green" if status_label == "ACTIVE" else "orange"
    website = record.get("website") or source_url

    st.markdown(f"""
    - **Primary Source:** [{source_name}]({source_url})
    - **Last checked:** {last_checked}
    - **Data status:** <span style="color: {status_color}; font-weight: 600;">{status_label}</span>
    - **Website:** [{website}]({website})
    """, unsafe_allow_html=True)




