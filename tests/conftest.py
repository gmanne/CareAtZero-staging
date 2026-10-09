"""
Shared test setup.

Several tests use the sample pop-up events in data/seed_data.py, which are dated
September 2026. Pinning "today" to 2026-09-16 keeps those tests about the app's
logic, not about what today's date happens to be. The app itself uses the real
date (see utils/dates.py).
"""
import os

os.environ.setdefault("CAREATZERO_TODAY", "2026-09-16")
