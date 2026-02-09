#!/usr/bin/env python3
"""
Claude.ai Usage Monitor for SwiftBar
Scrapes usage from claude.ai and displays in macOS menu bar
Refresh interval: 5 minutes (configured in filename)
"""

import json
import subprocess
import sys
from pathlib import Path

CACHE_FILE = Path.home() / ".config/claude-usage/last_usage.json"
STATE_FILE = Path.home() / ".config/claude-usage/notification_state.json"
SCRAPE_SCRIPT = Path(__file__).resolve().parent / "scrape_usage.py"

WARN_THRESHOLD = 75  # Percentage

def send_notification(title: str, message: str):
    """Send macOS notification"""
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ], capture_output=True)

def load_notification_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"notified_session": False, "notified_weekly": False, "last_session_pct": 0}

def save_notification_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))

def get_bar(percent: float, width: int = 10) -> str:
    """Create a text-based progress bar"""
    # Use round to show at least 1 block when > 0%
    filled = round(percent / 100 * width)
    if percent > 0 and filled == 0:
        filled = 1  # Show at least one block if there's any usage
    empty = width - filled
    return "█" * filled + "░" * empty

def get_color(percent: float) -> str:
    """Get color based on usage percentage - bright colors for visibility"""
    if percent >= 90:
        return "#FF3B30"  # Bright red
    elif percent >= 75:
        return "#FF9500"  # Bright orange
    elif percent >= 50:
        return "#FFCC00"  # Bright yellow
    return "#30D158"  # Bright green

def get_icon(percent: float) -> str:
    """Get SF Symbol icon based on usage percentage"""
    # Using SF Symbols for better visibility
    if percent >= 90:
        return "gauge.with.dots.needle.100percent"
    elif percent >= 75:
        return "gauge.with.dots.needle.67percent"
    elif percent >= 50:
        return "gauge.with.dots.needle.50percent"
    elif percent >= 25:
        return "gauge.with.dots.needle.33percent"
    return "gauge.with.dots.needle.0percent"

def run_scraper() -> dict:
    """Run the scraper script and return results"""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRAPE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr or "Scraper failed"}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout"}
    except Exception as e:
        return {"error": str(e)}

def main():
    # Try to get fresh data
    usage = run_scraper()

    # Fall back to cached data if scraping fails
    if "error" in usage and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text())
            if "error" not in cached:
                usage = cached
                usage["cached"] = True
        except:
            pass

    state = load_notification_state()

    # Handle errors
    if "error" in usage:
        error_msg = usage["error"]
        if "Not logged in" in error_msg or "login.py" in error_msg:
            print("🔑 Login | color=orange")
            print("---")
            print("Not logged in to Claude.ai | color=red")
            print("Run: claude-usage-login | color=gray font=Menlo size=11")
        elif "expired" in error_msg.lower():
            print("🔑 Expired | color=orange")
            print("---")
            print("Session expired | color=red")
            print("Run: claude-usage-login | color=gray font=Menlo size=11")
        else:
            print("⚠️ Error | color=red")
            print("---")
            print(f"Error: {error_msg} | color=red")
        print("---")
        print("Refresh | refresh=true")
        return

    # Extract percentages
    session_pct = 0
    weekly_pct = 0

    if usage.get("session") and "percent" in usage["session"]:
        session_pct = usage["session"]["percent"]

    if usage.get("weekly") and "percent" in usage["weekly"]:
        weekly_pct = usage["weekly"]["percent"]

    # Always show session % in the menu bar
    main_pct = session_pct
    main_color = get_color(main_pct)

    # Check thresholds and notify
    if session_pct >= WARN_THRESHOLD and not state.get("notified_session"):
        send_notification("Claude Usage Alert", f"Session usage at {session_pct:.0f}%")
        state["notified_session"] = True
    elif session_pct < WARN_THRESHOLD * 0.8:
        state["notified_session"] = False

    if weekly_pct >= WARN_THRESHOLD and not state.get("notified_weekly"):
        send_notification("Claude Usage Alert", f"Weekly usage at {weekly_pct:.0f}%")
        state["notified_weekly"] = True
    elif weekly_pct < WARN_THRESHOLD * 0.8:
        state["notified_weekly"] = False

    state["last_session_pct"] = session_pct
    save_notification_state(state)

    # SwiftBar output - use SF Symbol for menu bar
    sficon = get_icon(main_pct)
    cached_indicator = " (cached)" if usage.get("cached") else ""
    print(f"{main_pct:.0f}%{cached_indicator} | sfSymbol={sficon} sfColor={main_color} color={main_color}")
    print("---")

    # Session usage (5-hour window)
    print("Session (5-hour) | size=14")
    print(f"{get_bar(session_pct)} {session_pct:.1f}% | font=Menlo color={get_color(session_pct)}")
    if usage.get("session", {}).get("resets_at"):
        print(f"Resets: {usage['session']['resets_at']} | font=Menlo size=11 color=gray")
    print("---")

    # Weekly usage (7-day)
    print("Weekly (7-day) | size=14")
    if usage.get("weekly"):
        print(f"{get_bar(weekly_pct)} {weekly_pct:.1f}% | font=Menlo color={get_color(weekly_pct)}")
        if usage["weekly"].get("resets_at"):
            print(f"Resets: {usage['weekly']['resets_at']} | font=Menlo size=11 color=gray")
    else:
        print(f"{get_bar(0)} No data | font=Menlo color=gray")
    print("---")

    # Show API data status
    if usage.get("api_data"):
        print("API Status: Connected | color=green size=11")
    else:
        print("API Status: No data | color=orange size=11")
    print("---")

    print("Refresh | refresh=true")
    print("---")
    print("Open Claude Settings | href=https://claude.ai/settings/usage")
    print("Re-login | terminal=true bash=claude-usage-login")

if __name__ == "__main__":
    main()
