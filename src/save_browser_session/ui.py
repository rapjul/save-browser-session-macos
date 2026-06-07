import subprocess
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum, auto
from typing import Any, ContextManager, List, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table


class UserAction(Enum):
    SAVE = auto()
    VIEW = auto()


class UserScope(Enum):
    ALL = auto()
    CURRENT = auto()


# Abstract Base Class
class UserInterface(ABC):
    @abstractmethod
    def status(self, msg: str):
        pass

    @abstractmethod
    def print_line(self, msg: str = ""):
        pass

    @abstractmethod
    def confirm_fix_broken(self, count: int) -> bool:
        pass

    @abstractmethod
    def notify_success(self, count: int, file_path: Optional[str] = None):
        pass

    @abstractmethod
    def ask_session_name(self) -> str:
        pass

    @abstractmethod
    def ask_session_name_with_suggestions(self, suggestions: List[Any]) -> str:
        """
        Ask for session name with intelligent suggestions.

        Parameters:
            suggestions: List of SessionNameSuggestion objects sorted by confidence

        Returns:
            Selected or custom session name
        """
        pass

    @abstractmethod
    def show_summary(self, windows: List[Any]):
        pass

    @abstractmethod
    def confirm(self, question: str) -> bool:
        pass

    @abstractmethod
    def ask_action(self) -> UserAction:
        """
        Ask for the action to perform.
        """
        pass

    @abstractmethod
    def ask_scope(self) -> UserScope:
        """
        Ask for the scope of the action.
        """
        pass

    @abstractmethod
    def display_tabs(self, windows: List[Any]):
        """
        Display tabs in a pretty format.
        """
        pass

    @abstractmethod
    def spinner(self, msg: str) -> ContextManager[Any]:
        pass


class TerminalUI(UserInterface):
    def __init__(self):
        self.console = Console()
        self._status = None

    def print_line(self, msg: str = ""):
        self.console.print(msg)

    def status(self, msg: str):
        # Rich status context manager usage is usually: with console.status(): ...
        # But for an interface method, we might just print or yield.
        # Simpler for this script: Just print styled status or return a context manager wrapper?
        # Let's return a context manager or just print.
        # Actually, best pattern is to let main control the context block.
        # But here we want UI abstraction.
        # We'll use a simple print for now to avoid complex context passing in ABC.
        self.console.print(f"[bold blue]ℹ {msg}[/bold blue]")

    def confirm_fix_broken(self, count: int) -> bool:
        self.console.print(
            f"[bold yellow]⚠️  Found {count} broken tabs (Untitled, Loading, etc).[/bold yellow]"
        )
        return Confirm.ask("Would you like to try to activate/reload them to fix?")

    def confirm(self, question: str) -> bool:
        return Confirm.ask(question)

    def ask_action(self) -> UserAction:
        choices = ["s", "v"]
        choice = Prompt.ask(
            "What would you like to do? ([purple][[bold]S[/bold]]ave to File[/purple] / [green][[bold]v[/bold]]iew Only[/green])",
            choices=choices,
            default="s",
            show_choices=False,
            show_default=False,
        )
        if choice.lower() == "v":
            return UserAction.VIEW
        return UserAction.SAVE

    def ask_scope(self) -> UserScope:
        choices = ["a", "c"]
        choice = Prompt.ask(
            "Select target ([magenta][[bold]A[/bold]]ll Windows[/magenta] / [yellow][[bold]c[/bold]]urrent Window[/yellow])",
            choices=choices,
            default="a",
            show_choices=False,
            show_default=False,
        )
        if choice.lower() == "a":
            return UserScope.ALL
        return UserScope.CURRENT

    def display_tabs(self, windows: List[Any]):
        import pyperclip
        from rich.tree import Tree

        root = Tree("[bold cyan]Browser Session[/bold cyan]")

        full_text = ""

        for win in windows:
            w_node = root.add(
                f"[bold yellow]Window {win.id}[/bold yellow] ({len(win.tabs)} tabs)"
            )
            win_text = f"Window {win.id}:\n"
            for tab in win.tabs:
                w_node.add(f"[green]{tab.title}[/green] [dim]({tab.url})[/dim]")
                win_text += f"- {tab.title} ({tab.url})\n"
            full_text += win_text + "\n"

        self.console.print(root)
        self.console.print("")

        if Confirm.ask("Copy to Clipboard?", default=True):
            pyperclip.copy(full_text)
            self.console.print("[bold green]✔ Copied![/bold green]")

    def notify_success(self, count: int, file_path: Optional[str] = None):
        msg = f"[bold green]✔ Checked {count} tabs successfully.[/bold green]"
        if file_path:
            msg += f"\n📁 Saved to: [underline]'{file_path}'[/underline]"
        else:
            msg += "\n📋 Copied to Clipboard."
        self.console.print(msg)

    def ask_session_name(self) -> str:
        return Prompt.ask("Enter a Session Name (optional)", default="")

    def ask_session_name_with_suggestions(self, suggestions: List[Any]) -> str:
        """Terminal version with Rich interactive selection."""
        from rich.table import Table

        if not suggestions:
            # Fallback to simple prompt
            return Prompt.ask("Enter a Session Name (optional)", default="")

        # Display suggestions in a table
        self.console.print("\n[bold cyan]💡 Suggested Session Names:[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="yellow", width=12)
        table.add_column("Conf", justify="right", style="green", width=6)
        table.add_column("Reasoning", style="dim")

        for idx, suggestion in enumerate(suggestions, 1):
            confidence_pct = f"{suggestion.confidence * 100:.0f}%"

            # Different icons for different categories
            category_icon = {
                "history": "🕒",
                "domain": "🌐",
                "keyword": "🔤",
                "pattern": "🧩",
                "github": "💻",
            }.get(suggestion.category, "•")

            table.add_row(
                str(idx),
                suggestion.name,
                f"{category_icon} {suggestion.category}",
                confidence_pct,
                suggestion.reasoning,
            )

        self.console.print(table)

        self.console.print(
            f"\n[dim]Enter number (1-{len(suggestions)}) to select, "
            "or type a custom name:[/dim]"
        )

        choice = Prompt.ask("Session name", default="1")

        # Try to parse as number
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                return suggestions[idx].name
        except ValueError:
            pass

        # Return custom input or default to first suggestion
        return choice if choice and choice != "1" else suggestions[0].name

    def show_summary(self, windows: List[Any]):
        table = Table(title="Browser Session Summary")
        table.add_column("Window", style="cyan")
        table.add_column("Tabs", style="magenta")
        table.add_column("First Tab Title", style="green")

        for w in windows:
            first_title = w.tabs[0].title if w.tabs else "[Empty]"
            if len(first_title) > 50:
                first_title = first_title[:47] + "..."
            table.add_row(f"Window {w.id}", str(len(w.tabs)), first_title)

        self.console.print(table)

    def spinner(self, msg: str) -> ContextManager[Any]:
        return self.console.status(msg)


class GuiUI(UserInterface):
    def _run_osascript(self, script: str) -> str:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        return result.stdout.strip()

    def status(self, msg: str):
        # Notifications for status updates might be too noisy.
        pass

    def print_line(self, msg: str = ""):
        pass

    def confirm_fix_broken(self, count: int) -> bool:
        script = f"""
        display dialog "Found {count} broken tabs. Attempt to fix?" buttons {{"cancel", "Fix"}} default button "Fix" with icon caution
        return button returned of result
        """
        try:
            res = self._run_osascript(script)
            return res == "Fix"
        except Exception:
            return False

    def confirm(self, question: str) -> bool:
        script = f"""
        display dialog "{question}" buttons {{"No", "Yes"}} default button "Yes"
        return button returned of result
        """
        try:
            res = self._run_osascript(script)
            return res == "Yes"
        except Exception:
            return False

    def ask_action(self) -> UserAction:
        script = """
        display dialog "Choose action:" buttons {"View Only", "Save to File"} default button "Save to File" with title "Browser Session"
        return button returned of result
        """
        try:
            res = self._run_osascript(script)
            if res == "View Only":
                return UserAction.VIEW
            return UserAction.SAVE
        except Exception:
            return UserAction.SAVE

    def ask_scope(self) -> UserScope:
        script = """
        display dialog "Select scope:" buttons {"Current Window", "All Windows"} default button "All Windows" with title "Browser Session"
        return button returned of result
        """
        try:
            res = self._run_osascript(script)
            if res == "All Windows":
                return UserScope.ALL
            return UserScope.CURRENT
        except Exception:
            return UserScope.ALL

    def display_tabs(self, windows: List[Any]):
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            self._run_osascript(
                'display dialog "Python Tkinter is not installed. Please install it to use the GUI view." buttons {"OK"} default button "OK" with icon stop'
            )
            return

        import pyperclip

        root = tk.Tk()
        root.title("Browser Session View")
        root.geometry("800x600")

        # Configure styles
        style = ttk.Style()
        style.configure("Treeview", font=("Helvetica", 12), rowheight=25)
        style.configure("Treeview.Heading", font=("Helvetica", 13, "bold"))

        # Create Treeview
        tree = ttk.Treeview(root, columns=("url"), show="tree")
        tree.heading("#0", text="Title/Window", anchor=tk.W)
        tree.heading(
            "url", text="URL", anchor=tk.W
        )  # Hidden column if just tree? No, let's just do hierarchical title

        # Actually, let's just use tree structure: Window -> Tab
        # We can put URL in a column or just in text
        # Let's try 2 columns: Title, URL
        tree = ttk.Treeview(root, columns=("url"), show="tree headings")
        tree.heading("#0", text="Title")
        tree.heading("url", text="URL")
        tree.column("#0", width=400)
        tree.column("url", width=400)

        # Scrollbar
        scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        full_text = ""

        for win in windows:
            w_id = tree.insert(
                "", "end", text=f"Window {win.id} ({len(win.tabs)} tabs)", open=True
            )
            win_text = f"Window {win.id}:\n"
            for tab in win.tabs:
                tree.insert(w_id, "end", text=tab.title, values=(tab.url,))
                win_text += f"- {tab.title} ({tab.url})\n"
            full_text += win_text + "\n"

        def copy_all():
            pyperclip.copy(full_text)
            status_label.config(text="Copied to clipboard!")
            root.after(2000, lambda: status_label.config(text=""))

        # Buttons frame
        btn_frame = ttk.Frame(root)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        copy_btn = ttk.Button(btn_frame, text="Copy All", command=copy_all)
        copy_btn.pack(side=tk.LEFT)

        close_btn = ttk.Button(btn_frame, text="Close", command=root.destroy)
        close_btn.pack(side=tk.RIGHT)

        status_label = ttk.Label(btn_frame, text="", foreground="green")
        status_label.pack(side=tk.LEFT, padx=10)

        # Bring to front
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(lambda: root.attributes("-topmost", False))

        root.mainloop()

    def notify_success(self, count: int, file_path: Optional[str] = None):
        subtitle = "Copied to Clipboard"
        if file_path:
            subtitle = "Saved to file"  # Path might be too long for subtitle

        script = f'''
        display notification "{count} tabs processed" with title "Browser Session Saved" subtitle "{subtitle}"
        '''
        self._run_osascript(script)

    def ask_session_name(self) -> str:
        script = """
        display dialog "Enter Session Name (optional):" default answer "" buttons {"OK"} default button "OK" with title "Save Browser Session"
        text returned of result
        """
        return self._run_osascript(script)

    def ask_session_name_with_suggestions(self, suggestions: List[Any]) -> str:
        """GUI version using AppleScript dropdown."""
        if not suggestions:
            return self.ask_session_name()  # Fallback

        # Create list of choices for dropdown
        choices = [s.name for s in suggestions[:5]]  # Limit to 5
        choices_str = '", "'.join(choices)

        script = f"""
        set choices to {{"{choices_str}"}}
        choose from list choices with prompt "Select a session name or cancel to enter custom:" ¬
            default items {{item 1 of choices}} with title "Save Browser Session"
        """

        result = self._run_osascript(script)

        # If user cancelled, show text input
        if result == "false" or not result:
            return self.ask_session_name()

        return result

    def show_summary(self, windows: List[Any]):
        # Maybe skip summary in GUI mode or show a simple dialog?
        pass

    @contextmanager
    def spinner(self, msg: str):
        # GUI doesn't have a spinner, so we just yield
        yield


def get_ui(force_gui: bool = False) -> UserInterface:
    import sys

    # If not TTY or forced, use GUI
    if force_gui or not sys.stdout.isatty():
        return GuiUI()
    return TerminalUI()
