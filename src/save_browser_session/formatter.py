import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from typing import Literal
from urllib.parse import unquote

from .browser import Browser, Tab, Window
from .processing import clean_title, clean_url, is_broken_tab, should_skip


@dataclass
class SessionResult:
    content: str
    total_tabs: int
    total_windows: int
    extension: str


def generate_json(
    browser: Browser,
    windows: list[Window],
    session_name: str,
    timestamp: datetime,
) -> str:
    data = {
        "metadata": {
            "browser": browser.name,
            "session_name": session_name,
            "timestamp": timestamp.isoformat(),
            "windows_count": len(windows),
            "tabs_count": sum(len(w.tabs) for w in windows),
        },
        "windows": [
            {
                "id": i + 1,
                "tabs": [{"title": t.title, "url": t.url} for t in w.tabs],
            }
            for i, w in enumerate(windows)
        ],
    }
    return json.dumps(data, indent=2)


def generate_csv(
    browser: Browser,
    windows: list[Window],
    session_name: str,
    timestamp: datetime,
) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Window ID", "Tab ID", "Title", "URL", "Session", "Timestamp"])

    date_str = timestamp.isoformat()
    for i, w in enumerate(windows):
        for j, t in enumerate(w.tabs):
            writer.writerow([i + 1, j + 1, t.title, t.url, session_name, date_str])

    return output.getvalue()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }}
        input#search {{ width: 100%; padding: 10px; font-size: 16px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
        .controls {{ margin-bottom: 20px; display: flex; gap: 10px; }}
        button {{ padding: 8px 16px; font-size: 14px; cursor: pointer; background-color: #f1f1f1; border: 1px solid #ccc; border-radius: 4px; }}
        button:hover {{ background-color: #e1e1e1; }}
        .window {{ margin-bottom: 30px; border: 1px solid #eee; border-radius: 8px; padding: 15px; }}
        h1 {{ font-size: 24px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        h2 {{ font-size: 18px; color: #555; margin-top: 0; border-bottom: 1px solid #f5f5f5; padding-bottom: 5px; }}
        ul {{ list-style-type: none; padding: 0; margin: 0; }}
        li {{ padding: 8px 0; border-bottom: 1px solid #f9f9f9; display: flex; flex-direction: column; }}
        li:last-child {{ border-bottom: none; }}
        li a {{ text-decoration: none; color: #0366d6; font-weight: 500; }}
        li a:hover {{ text-decoration: underline; }}
        .url {{ color: #6a737d; font-size: 12px; margin-top: 2px; word-break: break-all; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <h1>{header}</h1>

    <input type="text" id="search" placeholder="Search tabs...">

    <div class="controls">
        <button id="copyAll">Copy All URLs</button>
        <button id="copyFiltered" class="hidden">Copy Filtered URLs</button>
    </div>

    <div id="content">
        {body}
    </div>

    <script>
        const searchInput = document.getElementById('search');
        const items = document.querySelectorAll('li');
        const copyAllBtn = document.getElementById('copyAll');
        const copyFilteredBtn = document.getElementById('copyFiltered');

        // Search
        searchInput.addEventListener('input', (e) => {{
            const term = e.target.value.toLowerCase();
            let hasFilter = term.length > 0;

            items.forEach(item => {{
                const text = item.textContent.toLowerCase();
                // Simple search in title and URL
                if (text.includes(term)) {{
                    item.classList.remove('hidden');
                }} else {{
                    item.classList.add('hidden');
                }}
            }});

            if (hasFilter) {{
                copyFilteredBtn.classList.remove('hidden');
            }} else {{
                copyFilteredBtn.classList.add('hidden');
            }}
        }});

        // Copy Logic
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert('Copied to clipboard!');
            }}).catch(err => {{
                console.error('Failed to copy: ', err);
                alert('Failed to copy to clipboard.');
            }});
        }}

        function getUrls(onlyVisible) {{
            const urls = [];
            items.forEach(item => {{
                if (onlyVisible && item.classList.contains('hidden')) {{
                    return;
                }}
                // Find the url span or anchor
                const urlSpan = item.querySelector('.url');
                if (urlSpan) {{
                    urls.push(urlSpan.textContent);
                }}
            }});
            return urls.join('\\n');
        }}

        copyAllBtn.addEventListener('click', () => {{
            copyToClipboard(getUrls(false));
        }});

        copyFilteredBtn.addEventListener('click', () => {{
            copyToClipboard(getUrls(true));
        }});
    </script>
</body>
</html>
"""


def generate_html(
    browser: Browser,
    windows: list[Window],
    session_name: str,
    timestamp: datetime,
) -> str:
    date_str = timestamp.strftime("%Y-%m-%d %H:%M")
    header_text = html.escape(f"{browser.name} Session | {session_name} [{date_str}]")

    body_html = ""
    for i, w in enumerate(windows):
        body_html += (
            f'<div class="window"><h2>Window {i + 1} ({len(w.tabs)} tabs)</h2><ul>'
        )
        for t in w.tabs:
            # Escape title and URL for HTML safety (prevents XSS/broken HTML)
            # but preserves brackets [ ] as desired by user
            title = html.escape(t.title or t.url)
            url_display = html.escape(t.url)
            url_href = html.escape(t.url, quote=True)

            body_html += f'<li><a href="{url_href}" target="_blank">{title}</a><span class="url">{url_display}</span></li>'
        body_html += "</ul></div>"

    return HTML_TEMPLATE.format(title=header_text, header=header_text, body=body_html)


def generate_formatted_content(
    browser: Browser,
    windows: list[Window],
    session_name: str,
    include_empty: bool,
    save_all: bool,
    timestamp: datetime,
    format_type: Literal["markdown", "json", "csv", "html"],
) -> SessionResult:
    # Pre-process filtering (common logic)
    filtered_windows: list[Window] = []
    total_tabs = 0

    for win in windows:
        valid_tabs: list[Tab] = []
        for tab in win.tabs:
            if not include_empty and should_skip(tab.title, tab.url):
                continue

            # Clean
            clean_t = clean_title(tab.title)
            clean_u = clean_url(tab.url)

            if is_broken_tab(tab.title, tab.url):
                clean_t = "⚠️ " + (clean_t or "Broken")

            if not clean_t:
                clean_t = clean_u

            valid_tabs.append(Tab(clean_t, clean_u))

        if valid_tabs:
            filtered_windows.append(Window(win.id, valid_tabs))
            total_tabs += len(valid_tabs)

    total_windows = len(filtered_windows)

    if format_type == "json":
        content = generate_json(browser, filtered_windows, session_name, timestamp)
        ext = ".json"
    elif format_type == "csv":
        content = generate_csv(browser, filtered_windows, session_name, timestamp)
        ext = ".csv"
    elif format_type == "html":
        content = generate_html(browser, filtered_windows, session_name, timestamp)
        ext = ".html"
    else:
        # Markdown (Default logic)
        date_str = timestamp.strftime("%Y-%m-%d %H:%M")
        scope = "Session" if save_all else "Window"
        header = f"# {browser.name} {scope} [{date_str}]"
        if session_name and session_name != "Autosaved":
            header = f"# {browser.name} Tabs | {session_name} [{date_str}]"

        body = ""
        for i, win in enumerate(filtered_windows):
            body += f"\n\n## Window {i + 1} ({len(win.tabs)} Tabs)\n\n"
            count_digits = len(str(len(win.tabs)))

            max_width = count_digits + 1

            for idx, vt in enumerate(win.tabs):
                # Left-align the number + dot, padded with spaces to the right
                num_str = f"{idx + 1}."
                padded_num = f"{num_str:<{max_width}}"

                if vt.title == vt.url or vt.title == unquote(vt.url):
                    body += f"{padded_num} <{vt.url}>\n"
                else:
                    safe_title = vt.title.replace("[", "&#91;").replace("]", "&#93;")
                    body += f"{padded_num} [{safe_title}]({vt.url})\n"

        if save_all:
            content = (
                f"{header}\n\n"
                f"**Total Number of Windows: {total_windows}**\n"
                f"**Total Number of Tabs: {total_tabs}**\n"
                f"{body}"
            )
        else:
            content = f"{header}\n\n{body}"
        ext = ".md"

    return SessionResult(
        content=content,
        total_tabs=total_tabs,
        total_windows=total_windows,
        extension=ext,
    )
