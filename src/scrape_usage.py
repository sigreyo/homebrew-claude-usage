#!/usr/bin/env python3
"""
Scrape Claude.ai usage data using cookies from existing browser.
No login required - uses cookies from Chrome/Safari/Firefox.
"""

import json
import re
import sys
from pathlib import Path

import requests

CACHE_FILE = Path.home() / ".config/claude-usage/last_usage.json"

def get_browser_cookies():
    """Try to get claude.ai cookies from installed browsers"""
    try:
        import browser_cookie3
    except ImportError:
        return None

    # Try browsers in order of preference
    browsers = [
        ("Chrome", browser_cookie3.chrome),
        ("Firefox", browser_cookie3.firefox),
        ("Safari", browser_cookie3.safari),
        ("Edge", browser_cookie3.edge),
    ]

    for name, browser_fn in browsers:
        try:
            cookies = browser_fn(domain_name="claude.ai")
            # Check if we got any cookies
            cookie_list = list(cookies)
            if cookie_list:
                print(f"Using cookies from {name}", file=sys.stderr)
                # Recreate the cookie jar (can only iterate once)
                return browser_fn(domain_name="claude.ai")
        except Exception as e:
            continue

    return None

def parse_usage_text(text: str) -> dict | None:
    """Parse usage text like '45.2K / 135K' or '67%'"""
    # Try percentage pattern
    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if pct_match:
        return {"percent": float(pct_match.group(1))}

    # Try "X / Y" pattern
    fraction_match = re.search(r'([\d.]+)\s*([KMB]?)\s*/\s*([\d.]+)\s*([KMB]?)', text, re.IGNORECASE)
    if fraction_match:
        def parse_num(val, suffix):
            num = float(val)
            suffix = suffix.upper()
            if suffix == 'K':
                num *= 1000
            elif suffix == 'M':
                num *= 1_000_000
            elif suffix == 'B':
                num *= 1_000_000_000
            return num

        used = parse_num(fraction_match.group(1), fraction_match.group(2))
        total = parse_num(fraction_match.group(3), fraction_match.group(4))
        return {
            "used": used,
            "total": total,
            "percent": (used / total * 100) if total > 0 else 0
        }

    return None

def scrape_usage() -> dict:
    """Scrape usage from claude.ai using browser cookies"""
    cookies = get_browser_cookies()

    if cookies is None:
        return {"error": "Could not get cookies from any browser. Make sure you're logged into claude.ai in Chrome, Firefox, or Safari."}

    try:
        # Try the API endpoint that the web app uses
        session = requests.Session()
        session.cookies = cookies
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://claude.ai/settings/usage",
        })

        # Get the active org ID from cookies (lastActiveOrg)
        org_id = None
        for cookie in cookies:
            if cookie.name == "lastActiveOrg":
                org_id = cookie.value
                break

        # Fall back to getting from API if cookie not found
        if not org_id:
            org_response = session.get("https://claude.ai/api/organizations")
            if org_response.status_code == 401 or org_response.status_code == 403:
                return {"error": "Not authenticated. Please log into claude.ai in your browser first."}
            if org_response.status_code == 200:
                orgs = org_response.json()
                if orgs and len(orgs) > 0:
                    org_id = orgs[0].get("uuid") or orgs[0].get("id")

        if not org_id:
            return {"error": "Could not determine organization ID"}

        usage_data = {
            "raw_texts": [],
            "session": None,
            "weekly": None,
            "api_data": None,
            "org_id": org_id,
        }

        # Get usage data from the API
        try:
            resp = session.get(f"https://claude.ai/api/organizations/{org_id}/usage")
            if resp.status_code == 200:
                usage_data["api_data"] = resp.json()
                usage_data["api_endpoint"] = f"https://claude.ai/api/organizations/{org_id}/usage"
            elif resp.status_code == 401 or resp.status_code == 403:
                return {"error": "Not authenticated. Please log into claude.ai in your browser."}
        except Exception as e:
            return {"error": f"API error: {e}"}

        # Parse the API data if we got it
        if usage_data.get("api_data"):
            api = usage_data["api_data"]

            # Session usage (5-hour window)
            # Note: utilization is already a percentage (e.g., 4.0 = 4%)
            if api.get("five_hour") and api["five_hour"].get("utilization") is not None:
                usage_data["session"] = {
                    "percent": api["five_hour"]["utilization"],
                    "resets_at": api["five_hour"].get("resets_at"),
                }

            # Weekly usage (7-day) - check various fields
            weekly_fields = ["seven_day", "seven_day_sonnet", "seven_day_opus"]
            for field in weekly_fields:
                if api.get(field) and isinstance(api[field], dict):
                    if api[field].get("utilization") is not None:
                        usage_data["weekly"] = {
                            "percent": api[field]["utilization"],
                            "resets_at": api[field].get("resets_at"),
                            "source": field,
                        }
                        break

            # Clear the garbage regex matches
            usage_data["raw_texts"] = []

        # Cache the result
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(usage_data, indent=2))

        return usage_data

    except Exception as e:
        return {"error": str(e)}

def main():
    result = scrape_usage()
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
