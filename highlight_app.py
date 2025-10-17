import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import logging
from typing import List, Dict, Any, Optional

# New modular imports
from config import load_api_keys
from exceptions import APIAuthenticationError, APINotAvailableError
from clients.twitter_client import TwitterClient
from clients.youtube_client import YouTubeClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)




class HighlightSearcher:
    """Handles searching across different platforms using injected client objects"""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        self.clients: Dict[str, Any] = clients or {}
        self.last_error: Optional[Exception] = None

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Aggregate search results from all available platforms"""
        results: List[Dict[str, Any]] = []
        self.last_error = None  # Reset last error before starting a new search

        # Search each client
        for name, client in self.clients.items():
            try:
                client_results = client.search(query, max_results)
                print(f"Found {len(client_results)} {name} results")
                results.extend(client_results)
            except Exception as e:
                self.last_error = e
                print(f"{name} search error: {e}")

        return self._sort_results(results)

    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort results by score and date"""
        return sorted(
            results,
            key=lambda x: (x.get("score", 0), x.get("upload_date", "")),
            reverse=True,
        )


class HighlightApp(tk.Tk):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.title("Basketball Highlights Aggregator")
        self.geometry("1000x600")

        # Load API keys and create clients
        self.clients = self._initialize_clients()
        self.searcher = HighlightSearcher(self.clients)

        self._create_widgets()

    def _initialize_clients(self) -> Dict[str, Any]:
        """Initialize API clients with error handling"""
        clients: Dict[str, Any] = {}

        try:
            # Load API keys
            api_keys = load_api_keys()
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            logger.error(f"Failed to load API keys: {e}")
            # Show error on startup if keys are missing
            self.after(0, lambda e=e: messagebox.showerror(
                "Configuration Error",
                f"Failed to load API configuration: {e}\nPlease check your .env file."
            ))
            return clients  # Return empty dict, search will handle no clients

        # Create clients (catch exceptions if API unavailable)
        if api_keys.twitter_api_key and api_keys.twitter_api_secret and api_keys.twitter_access_token and api_keys.twitter_access_token_secret:
            try:
                clients["twitter"] = TwitterClient(
                    api_key=api_keys.twitter_api_key,
                    api_secret=api_keys.twitter_api_secret,
                    access_token=api_keys.twitter_access_token,
                    access_token_secret=api_keys.twitter_access_token_secret,
                )
                logger.debug("Twitter client initialized successfully")
            except (APINotAvailableError, APIAuthenticationError) as exc:
                logger.warning(f"Twitter client initialization failed: {exc}")

        if api_keys.youtube_key:
            try:
                clients["youtube"] = YouTubeClient(api_key=api_keys.youtube_key)
                logger.debug("YouTube client initialized successfully")
            except (APINotAvailableError, APIAuthenticationError) as exc:
                logger.warning(f"YouTube client initialization failed: {exc}")

        return clients

    def _create_widgets(self):
        """Create and arrange GUI elements"""
        # Search frame
        search_frame = ttk.Frame(self, padding="5")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        # Add status label
        self.status_label = ttk.Label(search_frame, text="Ready to search")
        self.status_label.pack(side=tk.RIGHT)

        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind("<Return>", lambda _: self.start_search())

        # Make sure entry is enabled and focused
        self.search_entry.config(state="normal")
        self.search_entry.focus_set()

        self.search_button = ttk.Button(
            search_frame, text="Search", command=self.start_search
        )
        self.search_button.pack(side=tk.LEFT)

        # Results tree
        self.tree = ttk.Treeview(
            self, columns=("Platform", "Title", "Date", "URL"), show="headings"
        )
        self.tree.heading("Platform", text="Platform")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Date", text="Upload Date")
        self.tree.heading("URL", text="URL")

        # Column widths
        self.tree.column("Platform", width=100)
        self.tree.column("Title", width=400)
        self.tree.column("Date", width=150)
        self.tree.column("URL", width=300)

        # Scrollbar
        from typing import Any
        def on_scrollbar(*args: Any) -> None:
            self.tree.yview(*args)  # type: ignore
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=on_scrollbar)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # Bind double-click
        self.tree.bind("<Double-1>", self.on_item_double_click)

    def start_search(self):
        """Start search in a separate thread"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Required", "Please enter search keywords.")
            self.search_entry.focus_set()  # Return focus to search entry
            return

        self.search_button.configure(state="disabled")
        self.search_entry.configure(state="disabled")  # Disable entry during search
        self.status_label.configure(text="Searching...")
        self.tree.delete(*self.tree.get_children())

        threading.Thread(target=self._run_search, args=(query,), daemon=True).start()


    def _run_search(self, query: str):
        """Execute search and update results"""
        try:
            results = self.searcher.search(query)
            if not results:
                # Check if the last error was due to access level
                if self.searcher.last_error and "access level" in str(self.searcher.last_error):
                    self.after(0, lambda: messagebox.showerror(
                        "Access Level Error",
                        "Your Twitter API access level does not allow this operation. Please apply for elevated access."
                    ))
                elif self.searcher.last_error:
                    self.after(0, lambda: messagebox.showerror(
                        "Search Error", f"Search failed: {self.searcher.last_error}"
                    ))
                else:
                    self.after(0, lambda: messagebox.showinfo(
                        "No Results",
                        "No highlights found. Please try different keywords."
                    ))
            else:
                self.after(0, self._update_results, results)
        except Exception as e:
            self.after(0, self._show_error, str(e))
        finally:
            self.after(0, lambda: self.search_button.configure(state="normal"))
            self.after(0, lambda: self.search_entry.configure(state="normal"))
            self.after(0, lambda: self.status_label.configure(text="Ready"))
            self.after(0, lambda: self.search_entry.focus_set())

    def _update_results(self, results: List[Dict[str, Any]]):
        """Update the results tree with search results"""
        for result in results:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    result.get("platform", ""),
                    result.get("title", ""),
                    result.get("upload_date", ""),
                    result.get("url", ""),
                ),
            )

    def _show_error(self, message: str):
        """Show error message"""
        messagebox.showerror("Error", f"Search failed: {message}")
    def on_item_double_click(self, _: object):
        """Handle double-click on result"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item)["values"]
            url = values[3] if len(values) > 3 else values[2]
            webbrowser.open_new_tab(url)


def main():
    app = HighlightApp()
    app.mainloop()


if __name__ == "__main__":
    main()
    # Add your main application logic here
    print("Highlight App is running")
