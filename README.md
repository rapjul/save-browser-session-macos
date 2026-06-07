# Save Browser Session

A robust Python CLI tool for macOS to save your open browser tabs into a formatted Markdown file. It serves as a modern replacement for complex AppleScript/JXA scripts.

## Features

- **Multi-Browser Support**: Works with Safari, Google Chrome, Microsoft Edge, Arc, Orion, Brave, Vivaldi, and more.
- **Smart Cleaning**: Automatically removes tracking parameters, fixes messy titles, and cleans up URLs.
- **Broken Tab Fixer**: Detects "Loading..." or "Untitled" tabs and offers to reload/fix them before saving.
- **Rich CLI**: Beautiful terminal interface with status spinners and tables.
- **Headless Mode**: Automatic GUI dialog fallback (via native macOS dialogs) when running from Shortcuts or Keyboard Maestro.

## Installation

Install the package directly from PyPI using `uv`:

```bash
uv tool install save-browser-session
```

Or run it directly without installing:

```bash
uv tool run save-browser-session
```

### Development Installation

If you are developing or running from the source repository:

```bash
uv tool install .
```

Or, clone and run it directly from the source directory:

```bash
git clone https://github.com/rapjul/save-browser-session-macos
cd save-browser-session-macos
uv run save-browser-session
```

## Usage

### Basic Usage

Save all tabs from the frontmost browser:

```bash
save-browser-session --all 
```

This will copy the result to your clipboard and save a Markdown file to the current working directory (configurable in source).

### Options

| Flag | Description |
| :--- | :--- |
| `--current`, `-c` | Save only the **current window** (ignores other windows). |
| `--autosave` | Run in silent mode. Saves to `.../Browser Sessions/Autosaved`. Perfect for cron jobs. |
| `--include-empty` | Include tabs that are normally skipped (e.g. "Start Page"). |
| `--browser <Name>` | Force specific browser (e.g. "Google Chrome"). |
| `--gui` | Force GUI dialogs even when running in a terminal. |

### Examples

**Save only current window:**

```bash
save-browser-session --current
```

**Run silently in background (Autosave):**

```bash
save-browser-session --autosave
```

### Browser-Specific Commands

To target any of the other supported macOS browsers explicitly, use the `--browser` (or `-b`) flag:

- **Safari**:

    ```bash
    save-browser-session --browser "Safari"
    ```

- **Google Chrome**:

    ```bash
    save-browser-session --browser "Google Chrome"
    ```

    > [!NOTE]
    > You can also use `--browser Chrome` as a shortcut for "Google Chrome".

- **Microsoft Edge**:

    ```bash
    save-browser-session --browser "Microsoft Edge"
    ```

    > [!NOTE]
    > You can also use `--browser Edge` as a shortcut for "Microsoft Edge".

- **Brave Browser**:

    ```bash
    save-browser-session --browser "Brave Browser"
    ```

- **Arc**:

    ```bash
    save-browser-session --browser "Arc"
    ```

- **Orion**:

    ```bash
    save-browser-session --browser "Orion"
    ```

- **Vivaldi**:

    ```bash
    save-browser-session --browser "Vivaldi"
    ```

- **Chromium**:

    ```bash
    save-browser-session --browser "Chromium"
    ```

- **Opera**:

    ```bash
    save-browser-session --browser "Opera"
    ```

### Firefox - No Support

> [!WARNING]
> **Firefox is not supported.**
> Unlike Safari and Chromium-based browsers, Firefox lacks native support for macOS AppleScript or JavaScript for Automation (JXA) dictionaries. As a result, external tools cannot programmatically query Firefox for active window and tab information (titles/URLs). You can track this long-standing limitation on Mozilla's Bugzilla: [Bug 125419 - Add AppleScript support to Firefox](https://bugzilla.mozilla.org/show_bug.cgi?id=125419).

### Open Saved Files

You can automatically open the saved Markdown file in your favorite editor:

```bash
# Open in a specific app (e.g., TextEdit)
save-browser-session --open-with TextEdit

# Open in VS Code
save-browser-session --open-with "Visual Studio Code"

# Open in Antigravity
save-browser-session --open-with "Antigravity"

# Use a custom application name
save-browser-session --custom-open-with "Sublime Text"

# Use a custom application name
save-browser-session --custom-open-with "Zed"
```

## Publishing to PyPI

This package is built and published using `uv`:

1. **Build the package**:

    ```bash
    uv build
    ```

    This generates source distribution (`.tar.gz`) and wheel (`.whl`) archives in the `dist/` directory.

2. **Publish to PyPI**:
    Make sure you have your PyPI API token set in the `UV_PUBLISH_TOKEN` environment variable, then run:

    ```bash
    uv publish
    ```
