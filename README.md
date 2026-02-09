# Claude Usage Monitor (Homebrew Tap)

SwiftBar plugin that monitors your Claude.ai usage and displays session/weekly percentages in the macOS menu bar.

## Install

```bash
brew tap sigreyo/claude-usage
brew install claude-usage
```

## Setup

```bash
# Install SwiftBar if you don't have it
brew install --cask swiftbar
```

Open SwiftBar — when prompted for a Plugin Folder, pick any folder (e.g. `~/Library/Application Support/SwiftBar`).

```bash
# Run one-time setup (symlinks plugin into your SwiftBar folder)
claude-usage-setup
```

Make sure you're logged into claude.ai in your browser (Chrome/Firefox/Safari). The usage monitor will appear in your menu bar, refreshing every 5 minutes.

If cookies can't be read from your browser, run `claude-usage-login` as a fallback.

## Commands

| Command | Description |
|---|---|
| `claude-usage-setup` | One-time setup: symlink plugin into SwiftBar |
| `claude-usage-login` | Fallback: open browser to authenticate if cookies can't be read |
| `claude-usage-scrape` | Manually trigger a usage scrape |

## How It Works

The plugin scrapes your Claude.ai usage data using browser cookies and displays:

- **Session usage** (5-hour window) - shown in the menu bar
- **Weekly usage** (7-day window) - shown in the dropdown

Color-coded indicators:
- Green: < 50%
- Yellow: 50-74%
- Orange: 75-89%
- Red: 90%+

Desktop notifications are sent when usage exceeds 75%.

## Data Storage

All user data is stored in `~/.config/claude-usage/`:
- `last_usage.json` - cached usage data
- `notification_state.json` - notification tracking
- `browser-data/` - browser profile (only if claude-usage-login was used)

## Uninstall

```bash
brew uninstall claude-usage
brew untap sigreyo/claude-usage
# Optionally remove user data:
rm -rf ~/.config/claude-usage
```

## License

MIT
