"""
Find screen: a Search button next to the ZIP box, a message when results change,
a summary line that names every active choice, and Reset filters.
"""
from test_mobile_ui import run_page


def toasts(at):
    return " ".join(t.value for t in at.toast)


def summary(at):
    return next(m.value for m in at.markdown if " within " in m.value and " mi of " in m.value)


def test_search_button_next_to_zip_box():
    at = run_page("find", search_loc="27601")
    assert at.button(key="find_search_btn").label == "Search"
    assert toasts(at) == ""  # no message on first open


def test_new_zip_and_search_updates_results_and_says_so():
    at = run_page("find", search_loc="27601")
    at.text_input(key="find_care_loc_input").input("27514")
    at.button(key="find_search_btn").click().run()
    assert not at.exception
    assert "Results updated" in toasts(at)
    assert "Chapel Hill" in summary(at)


def test_changing_a_filter_says_results_updated():
    at = run_page("find", search_loc="27601")
    at.selectbox(key="find_cost").select("Free Only ($0 Fee)").run()
    assert "Results updated" in toasts(at)
    assert "Free only" in summary(at) and "within 35 mi" in summary(at)


def test_reset_filters_goes_back_to_defaults():
    at = run_page("find", search_loc="27601")
    at.selectbox(key="find_cost").select("Free Only ($0 Fee)").run()
    at.slider(key="find_dist").set_value(10).run()
    at.button(key="find_reset_btn").click().run()
    assert at.selectbox(key="find_cost").value == "All Low-Cost & Free"
    assert at.slider(key="find_dist").value == 35
