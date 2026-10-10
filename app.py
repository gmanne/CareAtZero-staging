import streamlit as st
import os
import sys

# Ensure project root is strictly first in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if not sys.path or sys.path[0] != PROJECT_ROOT:
    if PROJECT_ROOT in sys.path:
        sys.path.remove(PROJECT_ROOT)
    sys.path.insert(0, PROJECT_ROOT)

from database.db import get_all_events, init_db, DB_PATH
from data.seed_data import seed_database
from utils.styles import inject_custom_css, render_header, render_emergency_banner, LOGO_PATH
from utils.dates import today_str, format_checked_date, format_event_dates
from live.sources import load_live_data
from utils.geo import (
    NC_ZIP_COORDINATES, get_user_current_zip, detect_user_location,
    set_simulated_location, US_SIMULATION_PRESETS, geocode_location, haversine_distance,
    inject_client_geo_detector, safe_city_name
)


# Set page configuration
st.set_page_config(
    page_title="CareAtZero | Free & low-cost care. Know where to go.",
    page_icon=LOGO_PATH,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database if needed
if not os.path.exists(DB_PATH):
    seed_database()

# Inject styling
inject_custom_css()

# Logo bar + bottom tab bar
render_header("home")

# Inject client-side location detector (fetches real user location directly in browser on mobile and desktop)
inject_client_geo_detector()


st.markdown('<div class="cz-title">Find free care near you</div>'
            '<div class="cz-sub">No insurance needed. Pick what you need below.</div>',
            unsafe_allow_html=True)
render_emergency_banner()

# Care type: 2x2 cards, tap one to select it (Medical by default)
st.markdown("**What do you need?**")

care_cards = [
    ("Medical", ":material/stethoscope:", "Check-ups, sick visits"),
    ("Dental", ":material/dentistry:", "Cleanings, extractions"),
    ("Vision", ":material/visibility:", "Eye exams, glasses"),
    ("Behavioral Health", ":material/psychology:", "Counseling, crisis care"),
]
if "home_service" not in st.session_state:
    st.session_state["home_service"] = st.session_state.get("selected_service", "Medical")

for row_start in (0, 2):
    with st.container(key=f"row_care_{row_start}"):
        card_cols = st.columns(2)
        for col, (service, icon, desc) in zip(card_cols, care_cards[row_start:row_start + 2]):
            with col:
                with st.container(key=f"svc_{service.replace(' ', '_').lower()}"):
                    label = "Mental health" if service == "Behavioral Health" else service
                    if st.button(f"{label}  \n:gray[{desc}]", icon=icon, key=f"care_card_{service}",
                                 use_container_width=True,
                                 type="primary" if st.session_state["home_service"] == service else "secondary"):
                        st.session_state["home_service"] = service
                        st.rerun()

# Quick Location Search Box
user_detected_zip = get_user_current_zip()

saved_loc = st.session_state.get("search_loc")
if saved_loc and str(saved_loc).strip():
    default_loc = str(saved_loc).strip()
else:
    default_loc = user_detected_zip
    st.session_state["search_loc"] = user_detected_zip

loc_info = detect_user_location()
city_label = safe_city_name(loc_info.get("city", ""))
location_desc = f"{city_label} ({user_detected_zip})" if city_label else user_detected_zip

timing_labels = {"Today": "Today", "This Week": "This week", "Flexible (Upcoming)": "Any time"}

with st.form(key="home_quick_search_form", clear_on_submit=False, border=False):
    quick_loc = st.text_input(
        "Where are you? (ZIP code or city)",
        value=default_loc,
        placeholder=f"e.g., {user_detected_zip} or Raleigh",
        help=f"Detected location: {location_desc}",
        key="home_search_loc_input"
    )
    quick_timing = st.segmented_control(
        "When do you need care?", list(timing_labels), format_func=timing_labels.get,
        default="This Week", key="home_timing"
    ) or "This Week"
    search_submitted = st.form_submit_button("Find free care", icon=":material/search:", type="primary",
                                             use_container_width=True, key="home_find_care_submit_btn")

if search_submitted:
    target_search = str(quick_loc).strip() if quick_loc and str(quick_loc).strip() else default_loc
    st.session_state["selected_service"] = st.session_state["home_service"]
    st.session_state["search_loc"] = target_search
    st.session_state["search_timing"] = quick_timing
    if hasattr(st, "query_params"):
        st.query_params.pop("client_zip", None)
        st.query_params.pop("client_city", None)
        st.query_params.pop("client_lat", None)
        st.query_params.pop("client_lon", None)
    st.switch_page("pages/1_🔍_Find_Free_Care.py")

loc_col_a = st.container()
with loc_col_a:
    st.caption(f"Detected location: {location_desc}")
    if st.button("Use my location", icon=":material/my_location:", key="btn_redetect_loc", help="Re-detect location using your device"):
        st.session_state.pop("search_loc", None)
        st.session_state.pop("detected_user_location", None)
        if hasattr(st, "query_params"):
            st.query_params.pop("geo_checked", None)
            st.query_params.pop("client_zip", None)
            st.query_params.pop("client_city", None)
        st.rerun()

if st.query_params.get("test_geo") == "true":
    with st.expander("📍 **Simulate / Test USA Geolocation (Auto-detect Testing)**", expanded=True):
        st.caption("Change simulated US location to test automatic ZIP code detection across different regions.")
        sim_col1, sim_col2 = st.columns([3, 1])
        with sim_col1:
            sim_options = ["Auto-Detect (Current IP)"] + list(US_SIMULATION_PRESETS.keys())
            current_active = "Auto-Detect (Current IP)"
            if "simulated_ip" in st.session_state:
                for k, v in US_SIMULATION_PRESETS.items():
                    if v == st.session_state["simulated_ip"]:
                        current_active = k
                        break
            chosen_sim = st.selectbox(
                "Select USA location to simulate:",
                sim_options,
                index=sim_options.index(current_active) if current_active in sim_options else 0,
                key="sim_loc_dropdown"
            )
        with sim_col2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Apply Location", key="btn_apply_sim", use_container_width=True):
                if chosen_sim == "Auto-Detect (Current IP)":
                    set_simulated_location(None)
                else:
                    set_simulated_location(chosen_sim)
                st.rerun()

st.markdown("---")

# Live pop-up events: RAM's calendar + hand-verified community events, nearest date first
POPUP_RADIUS_MILES = 150
clean_loc = str(quick_loc).strip() or default_loc
home_lat, home_lon, home_label = geocode_location(clean_loc)
with st.spinner("Checking upcoming free pop-up clinics..."):
    live_events = load_live_data(home_lat, home_lon, include_sites=False)
ram_status = next((s for s in live_events.statuses if s.key == "ram"), None)

matching_events = []
for evt in live_events.events:
    if evt.get("latitude") is None or evt.get("longitude") is None:
        continue
    miles = haversine_distance(home_lat, home_lon, evt["latitude"], evt["longitude"])
    if miles <= POPUP_RADIUS_MILES:
        matching_events.append((evt, miles))

st.subheader("Upcoming free pop-up clinics")
st.markdown("Pop-up clinics give **free care for a day or two**, usually with no insurance, ID or income proof needed. "
            "*Arrive early for a ticket.*")

if matching_events:
    st.markdown(f"**{len(matching_events)} within {POPUP_RADIUS_MILES} miles of {home_label}:**")
    for evt, miles in matching_events[:3]:
        evt_zip = evt.get("zip_code", "")
        when = format_event_dates(evt.get("date_start"), evt.get("date_end"))
        cost_badge = "<span class='badge-free'>FREE</span>" if evt.get("cost_class") == "Free" else ""
        st.markdown(f"""
        <div class="care-card">
            <div style="margin-bottom: 8px;"><span class='badge-event'>📅 {when}</span> {cost_badge}</div>
            <h4 style="margin: 4px 0; color: #0E2A5C;">{evt.get('title')}</h4>
            <div class="card-meta">📍 {evt.get('location_name')}, {evt.get('city')}, {evt.get('state')} {evt_zip} • {miles:.0f} mi away</div>
            <div class="card-meta">🩺 <strong>Services:</strong> {', '.join(evt.get('services', []))}</div>
            <div class="card-meta">⏰ {evt.get('time_details')}</div>
            <div class="source-meta">Source: {evt.get('source_name')} • Checked {format_checked_date(evt.get('last_checked'))}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View event details", key=f"btn_evt_home_{evt.get('id')}", use_container_width=True):
            st.session_state["selected_care_id"] = evt.get("id")
            st.session_state["selected_care_type"] = "event"
            st.session_state["search_loc"] = clean_loc
            st.switch_page("pages/2_📋_Care_Details.py")
elif ram_status is not None and not ram_status.ok:
    st.warning("The pop-up clinic calendar couldn't be reached just now. Please try again in a few minutes.")
else:
    st.info(f"No free pop-up clinics are scheduled within {POPUP_RADIUS_MILES} miles of {home_label} right now.")
    st.caption("This list updates automatically from Remote Area Medical's live calendar. "
               "Tap **Find free care** to see year-round free and low-cost clinics.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; font-size: 0.85rem; color: #64748B; padding: 10px 0;'><span style='color: #0E2A5C; font-weight: 700;'>CareAt</span><span style='color: #0A7C74; font-weight: 700;'>Zero</span> • Free &amp; low-cost care. Know where to go. • Research Triangle Pilot • Version 1.0</div>", unsafe_allow_html=True)



