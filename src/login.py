#!/usr/bin/env python3
"""
One-time login script to save Claude.ai session.
Run this once to authenticate, then the usage monitor will use the saved session.
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from pathlib import Path

USER_DATA_DIR = Path.home() / ".config/claude-usage/browser-data"

def main():
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Opening browser for Claude.ai login...")
    print("Please log in, then close the browser window when done.")
    print()

    with sync_playwright() as p:
        # Launch with persistent context to save cookies/session
        # Use Chrome channel and stealth to bypass Cloudflare
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,  # Need visible browser for login
            channel="chrome",  # Use system Chrome instead of bundled Chromium
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.new_page()
        stealth = Stealth(navigator_platform_override="MacIntel")
        stealth.apply_stealth_sync(page)  # Apply stealth to bypass bot detection
        page.goto("https://claude.ai/settings/usage")

        print("Waiting for you to log in...")
        print("The browser will stay open - close it manually when you're logged in and can see the usage page.")

        # Wait for the browser to close (user closes it manually after login)
        try:
            context.pages[0].wait_for_event("close", timeout=300000)  # 5 min timeout
        except:
            pass

        context.close()

    print()
    print("Session saved! You can now run the usage monitor.")

if __name__ == "__main__":
    main()
