"""
Collects live records from every source for the Find and Home screens.

- All sources are fetched at the same time, and results are kept for 6 hours
  (a failed fetch is retried after 5 minutes), so searches stay fast and the
  official sites aren't hit on every tap.
- Each source reports whether it worked, how many records it returned and when
  it was fetched; the About screen shows this.
- If a source is down, the others still work. Only if every clinic source is
  down does the app fall back to its saved directory (data/seed_data.py), and it
  says so on screen.
- Pop-up events = RAM's live calendar + the hand-verified community events in the
  saved directory (dental buses, county vans etc. that publish no feed), each shown
  only until its end date.
"""
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from live import hrsa, nc_safety_net, ram_events, samhsa
from live.common import SourceUnavailable, fetched_at
from utils.dates import today, today_str

CACHE_SECONDS = 6 * 60 * 60
RETRY_SECONDS = 5 * 60


@dataclass
class SourceStatus:
    key: str
    name: str
    provides: str
    url: str
    ok: bool = False
    count: int = 0
    checked: str = ""
    error: str = ""


@dataclass
class LiveData:
    sites: List[dict] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)
    statuses: List[SourceStatus] = field(default_factory=list)
    using_saved_directory: bool = False


SOURCES = {
    "hrsa": ("HRSA health centers", "Medical care (sliding scale)", hrsa.SOURCE_URL),
    "nc_safety_net": ("NC DHHS Safety Net list", "Free clinics, dental clinics, health departments", nc_safety_net.SOURCE_URL),
    "samhsa": ("SAMHSA FindTreatment.gov", "Mental health & substance use care near you", samhsa.SOURCE_URL),
    "ram": ("Remote Area Medical (RAM)", "Free pop-up clinics: dental, vision, medical", ram_events.SOURCE_URL),
}

_cache: Dict[Tuple, Tuple[float, object]] = {}
_lock = threading.Lock()


def _cached(key: Tuple, loader: Callable[[], List[dict]]) -> Tuple[List[dict], Optional[str], str]:
    """(records, error, fetched_time) for one source, from the cache when still fresh."""
    now = time.time()
    with _lock:
        hit = _cache.get(key)
    if hit and now < hit[0]:
        return hit[1]
    try:
        result = (loader(), None, fetched_at())
        expires = now + CACHE_SECONDS
    except SourceUnavailable as e:
        result = ([], str(e), fetched_at())
        expires = now + RETRY_SECONDS
    except Exception as e:  # an unexpected bug in one source must not break the app
        result = ([], f"Unexpected error: {e}", fetched_at())
        expires = now + RETRY_SECONDS
    with _lock:
        _cache[key] = (expires, result)
    return result


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _dedupe_key(site: dict) -> str:
    name = re.sub(r"[^a-z0-9]", "", (site.get("name") or "").lower())
    return f"{name}|{site.get('zip_code', '')}"


def load_live_data(lat: float, lon: float, include_sites: bool = True) -> LiveData:
    """
    Live sites and upcoming events around (lat, lon), plus each source's status.
    include_sites=False loads only the pop-up events (used by the Home screen).
    """
    day = today()
    samhsa_key = ("samhsa", round(lat, 1), round(lon, 1))  # ~7-mile grid so nearby searches share results
    jobs = {"ram": (("ram", day.isoformat()), lambda: ram_events.fetch(day))}
    if include_sites:
        jobs.update({
            "hrsa": (("hrsa", "NC"), lambda: hrsa.fetch("NC")),
            "nc_safety_net": (("nc_safety_net",), nc_safety_net.fetch),
            "samhsa": (samhsa_key, lambda: samhsa.fetch(lat, lon)),
        })
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {k: pool.submit(_cached, key, loader) for k, (key, loader) in jobs.items()}
        results = {k: f.result() for k, f in futures.items()}

    data = LiveData()
    seen = set()
    for key in ("hrsa", "nc_safety_net", "samhsa", "ram"):
        if key not in results:
            continue
        records, error, checked = results[key]
        name, provides, url = SOURCES[key]
        data.statuses.append(SourceStatus(key, name, provides, url, ok=error is None,
                                          count=len(records), checked=checked, error=error or ""))
        if key == "ram":
            data.events.extend(records)
            continue
        for site in records:  # the same clinic can appear in more than one list; keep the first
            k = _dedupe_key(site)
            if k not in seen:
                seen.add(k)
                data.sites.append(site)

    # Hand-verified community events (dental buses, county vans...) that publish no feed
    try:
        from database.db import get_all_events, get_all_sites
        community = get_all_events(include_expired=False, current_date_str=today_str())
        for e in community:
            e["source_name"] = f"{e.get('source_name') or 'CareAtZero community list'} (manually verified)"
        data.events.extend(community)
        if include_sites and not any(s.ok for s in data.statuses if s.key != "ram"):
            # every clinic source is down: show the saved directory, clearly labeled
            data.using_saved_directory = True
            for s in get_all_sites():
                s["source_name"] = f"{s.get('source_name') or 'Saved directory'} (saved copy)"
                data.sites.append(s)
    except Exception:
        pass

    data.events.sort(key=lambda e: e.get("date_start") or "")
    return data


def find_record(record_id: str, lat: float, lon: float) -> Optional[dict]:
    """Look up one record by id (for the Detail screen), live data first, then the saved directory."""
    data = load_live_data(lat, lon)
    for rec in data.sites + data.events:
        if rec.get("id") == record_id:
            return rec
    try:
        from database.db import get_event_by_id, get_site_by_id
        return get_site_by_id(record_id) or get_event_by_id(record_id)
    except Exception:
        return None
