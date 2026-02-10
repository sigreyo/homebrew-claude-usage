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
CONFIG_FILE = Path.home() / ".config/claude-usage/config.json"
SCRIPT_DIR = Path(__file__).resolve().parent
SCRAPE_SCRIPT = SCRIPT_DIR / "scrape_usage.py"
if not SCRAPE_SCRIPT.exists():
    SCRAPE_SCRIPT = Path.home() / ".config/claude-usage/scrape_usage.py"

WARN_THRESHOLD = 75  # Percentage


def load_config() -> dict:
    """Load config, creating default if missing."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    config = {"display_org": "auto"}
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    return config


def get_display_org(orgs: list, config: dict) -> dict | None:
    """Determine which org to display in menu bar."""
    if not orgs:
        return None
    display = config.get("display_org", "auto")
    if display != "auto":
        for org in orgs:
            if org["id"] == display:
                return org
    # Auto: pick the org with the highest session usage
    return max(orgs, key=lambda o: (o.get("session") or {}).get("percent", 0))

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

def handle_set_org():
    """Handle --set-org CLI argument to update config."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--set-org":
        org_value = sys.argv[2]
        config = load_config()
        config["display_org"] = org_value
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
        sys.exit(0)


def _migrate_legacy_cache(usage: dict) -> dict:
    """Convert old single-org cache format to multi-org format."""
    if "orgs" in usage:
        return usage
    # Old format had session/weekly at top level
    org_entry = {
        "id": usage.get("org_id", "unknown"),
        "name": "Default",
        "session": usage.get("session"),
        "weekly": usage.get("weekly"),
    }
    return {"orgs": [org_entry], "cached": usage.get("cached")}


def main():
    # Handle config-write action before anything else
    handle_set_org()

    config = load_config()

    # Try to get fresh data
    usage = run_scraper()

    # Fall back to cached data if scraping fails
    if "error" in usage and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text())
            if "error" not in cached:
                usage = cached
                usage["cached"] = True
        except Exception:
            pass

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

    # Migrate legacy single-org cache format if needed
    usage = _migrate_legacy_cache(usage)

    orgs = usage.get("orgs", [])
    cached = usage.get("cached", False)
    display_org = get_display_org(orgs, config)

    state = load_notification_state()

    # Determine menu bar display from the selected org
    session_pct = (display_org.get("session") or {}).get("percent", 0) if display_org else 0
    weekly_pct = (display_org.get("weekly") or {}).get("percent", 0) if display_org else 0
    org_label = display_org["name"] if display_org else "?"

    main_pct = session_pct
    main_color = get_color(main_pct)

    # Check thresholds and notify (for display org)
    if session_pct >= WARN_THRESHOLD and not state.get("notified_session"):
        send_notification("Claude Usage Alert", f"Session usage at {session_pct:.0f}% ({org_label})")
        state["notified_session"] = True
    elif session_pct < WARN_THRESHOLD * 0.8:
        state["notified_session"] = False

    if weekly_pct >= WARN_THRESHOLD and not state.get("notified_weekly"):
        send_notification("Claude Usage Alert", f"Weekly usage at {weekly_pct:.0f}% ({org_label})")
        state["notified_weekly"] = True
    elif weekly_pct < WARN_THRESHOLD * 0.8:
        state["notified_weekly"] = False

    state["last_session_pct"] = session_pct
    save_notification_state(state)

    # --- SwiftBar output ---
    sficon = get_icon(main_pct)
    cached_indicator = " (cached)" if cached else ""
    short_label = f" ({org_label})" if len(orgs) > 1 else ""
    print(f"{main_pct:.0f}%{short_label}{cached_indicator} | sfSymbol={sficon} sfColor={main_color} color={main_color}")
    print("---")

    # Per-org sections
    this_script = str(Path(__file__).resolve())
    for org in orgs:
        o_session = (org.get("session") or {}).get("percent", 0)
        o_weekly = (org.get("weekly") or {}).get("percent", 0)
        print(f"{org['name']} | size=14")
        print(f"  Session: {get_bar(o_session)} {o_session:.1f}% | font=Menlo color={get_color(o_session)}")
        if (org.get("session") or {}).get("resets_at"):
            print(f"  Resets: {org['session']['resets_at']} | font=Menlo size=11 color=gray")
        print(f"  Weekly:  {get_bar(o_weekly)} {o_weekly:.1f}% | font=Menlo color={get_color(o_weekly)}")
        if (org.get("weekly") or {}).get("resets_at"):
            print(f"  Resets: {org['weekly']['resets_at']} | font=Menlo size=11 color=gray")
        print("---")

    # Org switching submenu
    current_display = config.get("display_org", "auto")
    is_auto = current_display == "auto"
    auto_check = "✓ " if is_auto else ""
    print("Display Org | size=12")
    print(f"--{auto_check}Auto (highest) | terminal=false refresh=true bash={sys.executable} param1={this_script} param2=--set-org param3=auto")
    for org in orgs:
        check = "✓ " if current_display == org["id"] else ""
        print(f"--{check}{org['name']} | terminal=false refresh=true bash={sys.executable} param1={this_script} param2=--set-org param3={org['id']}")
    print("---")

    print("Refresh | refresh=true")
    print("---")
    print("Open Claude Settings | href=https://claude.ai/settings/usage")
    print("Re-login | terminal=true bash=claude-usage-login")

if __name__ == "__main__":
    main()
