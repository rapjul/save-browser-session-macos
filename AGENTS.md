# Gemini Context: save-browser-session

This document provides context for the `save-browser-session` project, a Python CLI tool for macOS designed to save open browser tabs to a file.

## Project Overview

`save-browser-session` is a command-line utility built with Python that captures browser tab information (title and URL) from various macOS web browsers and saves it into formatted files like Markdown, HTML, JSON, or CSV.

The core of its functionality relies on executing **JXA (JavaScript for Automation)** and **AppleScript** scripts via `subprocess` to communicate with browser applications. This allows it to fetch a list of all open windows and their corresponding tabs.

### Key Technologies

* **Python 3.10+**: The core programming language.
* **Typer**: Used for creating the command-line interface.
* **Rich**: For creating beautiful and informative terminal UI, including spinners, tables, and formatted text.
* **uv**: For project and dependency management.
* **JXA/AppleScript**: For interacting with macOS applications (browsers).
* **pytest**: For running automated tests.
* **ruff**: For linting and code formatting.

### Architecture

1. **CLI Entrypoint (`main.py`)**: Parses command-line arguments using Typer.
2. **UI Abstraction (`ui.py`)**: Selects between a terminal-based UI (`TerminalUI`) or a native macOS GUI (`GuiUI`) for prompts and notifications. The GUI is used when not in an interactive terminal (e.g., when run from a macOS Shortcut).
3. **Browser Interaction (`browser.py`)**: An abstraction layer with `WebKitBrowser` and `ChromiumBrowser` classes that generate and execute JXA/AppleScript to fetch window and tab data.
4. **Processing & Formatting (`formatter.py`, `processing.py`)**: Cleans up URLs and titles, filters out unwanted tabs, and formats the final output into the desired file format (Markdown, HTML, etc.).

## Building and Running

The project uses `uv` for dependency and environment management.

### Installation

To install dependencies, including development tools like `pytest` and `ruff`:

```bash
uv sync --dev
```

### Running the Application

To run the CLI from the project root:

```bash
uv run save-browser-session [OPTIONS]
```

For example, to save the tabs from the current window only:

```bash
uv run save-browser-session --current
```

### Running Tests

Tests are located in the `tests/` directory and are run using `pytest`:

```bash
uv run pytest
```

## Development Conventions

* **Linting & Formatting**: The project uses `ruff` for code linting. Check for issues with:

    ```bash
    uv run ruff check .
    ```

* **Testing**: Tests are written with `pytest`. The CLI commands are tested using `typer.testing.CliRunner`. New features should be accompanied by tests.

* **Code Style**:
    * The code is written in a modern Python style, using type hints, f-strings, and dataclasses.
    * Browser interaction logic is isolated in the `browser.py` module.
    * User-facing interactions are abstracted in the `ui.py` module.

* **Commits**: Commit messages should be clear and descriptive.
