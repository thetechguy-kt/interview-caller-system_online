# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.
import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from datetime import datetime
import traceback

# --- Constants / Config ---
SHEETS_ID_FILE = "sheetsid.txt"
SERVICE_ACCOUNT_FILE = "service_account.json"
STATE_FILE = "queue_state.json"
COUNTER_NAME = "Room 1"  # Change per instance if needed

# UI Colors (dark theme)
BG_COLOR = "#121212"
FG_COLOR = "#00FFFF"
BUTTON_BG = "#1E1E1E"
BUTTON_FG = "#00FFFF"
DISABLED_BG = "#333333"
DISABLED_FG = "#555555"
RED_COLOR = "#FF5555"
GREEN_COLOR = "#55FF55"

# Ensure state file exists
if not os.path.exists(STATE_FILE):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"called_tokens": []}, f)

# --- Utility: pick preferred font ---
def pick_preferred_font():
    preferred_fonts = ["Montserrat", "Aptos", "Segoe UI", "Helvetica", "Arial"]
    try:
        available = list(tkfont.families())
        for f in preferred_fonts:
            if f in available:
                return f
    except Exception:
        pass
    return "TkDefaultFont"

# --- Sheets reader (read-only) ---
class SheetsReader:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(self):
        self.sheet_id = self._read_sheet_id()
        self._validate_service_account()
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
        self.service = build("sheets", "v4", credentials=creds)

    def _read_sheet_id(self):
        if not os.path.exists(SHEETS_ID_FILE):
            raise FileNotFoundError(f"{SHEETS_ID_FILE} not found. Create it and put the spreadsheet ID inside.")
        with open(SHEETS_ID_FILE, "r", encoding="utf-8") as f:
            sid = f.read().strip()
        if not sid:
            raise ValueError(f"{SHEETS_ID_FILE} is empty. Paste the spreadsheet ID inside.")
        return sid

    def _validate_service_account(self):
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"{SERVICE_ACCOUNT_FILE} not found. Place your service account JSON file in the project folder.")

    def fetch_today_rows(self, sheet_name=None):
        """
        Fetch values from the spreadsheet.
        Returns a list of rows (each row is a list of cell values).
        By default reads from the first sheet range A:F for convenience.
        If sheet_name provided, queries that tab: '{sheet_name}'!A:F
        """
        if sheet_name:
            range_name = f"'{sheet_name}'!A:F"
        else:
            range_name = "Sheet1!A:F"
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.sheet_id, range=range_name).execute()
            values = result.get("values", [])
            return values
        except HttpError as e:
            # Bubble up a clearer message
            raise RuntimeError(f"Google Sheets API error: {e}")

# --- Main App ---
class TokenCallerApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{COUNTER_NAME} Control Panel")
        self.master.geometry("420x320")
        self.master.configure(bg=BG_COLOR)

        self.font_family = pick_preferred_font()

        heading = tk.Label(master, text=COUNTER_NAME, font=(self.font_family, 18, "bold"),
                           bg=BG_COLOR, fg=FG_COLOR)
        heading.pack(pady=6)

        # Data
        self.token_data = []       # list of dicts: {"token","name","date","time"}
        self.current_token = None
        self.counter_closed = False

        # Sheets reader (init; show error if missing)
        try:
            self.sheets = SheetsReader()
        except Exception as e:
            messagebox.showerror("Sheets Init Error", f"Could not initialize Google Sheets reader:\n{e}")
            # show stack on console for debugging, but allow app to open (it will have no tokens)
            print(traceback.format_exc())
            self.sheets = None

        # Display window (separate)
        self.display_window = tk.Toplevel(master)
        self.display_window.title(f"{COUNTER_NAME} Display")
        self.display_window.geometry("360x220")
        self.display_window.protocol("WM_DELETE_WINDOW", self.on_display_close)
        self.display_window.configure(bg=BG_COLOR)

        self.display_heading = tk.Label(self.display_window, text="KTech",
                                        font=(self.font_family, 20, "bold"), fg=FG_COLOR, bg=BG_COLOR)
        self.display_heading.pack(pady=(10, 4))

        self.counter_heading = tk.Label(self.display_window, text=COUNTER_NAME,
                                        font=(self.font_family, 14, "bold"), fg=FG_COLOR, bg=BG_COLOR)
        self.counter_heading.pack(pady=(0, 8))

        self.display_label = tk.Label(self.display_window, text="Waiting...",
                                      font=(self.font_family, 26, "bold"), fg=FG_COLOR, bg=BG_COLOR)
        self.display_label.pack(expand=True)

        # Control buttons
        btn_style = {"font": (self.font_family, 14, "bold"),
                     "bg": BUTTON_BG, "fg": BUTTON_FG,
                     "activebackground": "#00AAAA", "activeforeground": "#000000",
                     "bd": 0, "relief": "flat"}

        self.call_button = tk.Button(master, text="Call Next", command=self.call_next, **btn_style)
        self.call_button.pack(pady=6, fill='x', padx=12)

        btn_style_sm = {"font": (self.font_family, 12, "bold"),
                        "bg": BUTTON_BG, "fg": BUTTON_FG,
                        "activebackground": "#00AAAA", "activeforeground": "#000000",
                        "bd": 0, "relief": "flat"}

        self.recall_button = tk.Button(master, text="Recall", command=self.recall, **btn_style_sm)
        self.recall_button.pack(pady=4, fill='x', padx=12)

        self.waiting_button = tk.Button(master, text="Waiting", command=self.set_waiting, **btn_style_sm)
        self.waiting_button.pack(pady=4, fill='x', padx=12)

        self.close_button = tk.Button(master, text="Close Room", fg="white", bg=RED_COLOR,
                                      command=self.close_counter, font=(self.font_family, 12, "bold"))
        self.close_button.pack(pady=6, fill='x', padx=12)

        self.open_button = tk.Button(master, text="Open Room", fg="white", bg=GREEN_COLOR,
                                     command=self.open_counter, font=(self.font_family, 12, "bold"))
        self.open_button.pack(pady=(0,8), fill='x', padx=12)

        self.token_label = tk.Label(master, text="Token: -\nName: -", font=(self.font_family, 14, "bold"),
                                    fg=FG_COLOR, bg=BG_COLOR, justify="left")
        self.token_label.pack(pady=6)

        # initial load
        self.refresh_interval_ms = 3000
        self.load_tokens_from_sheets()
        self.refresh_loop()

    def on_display_close(self):
        messagebox.showinfo("Info", "Display window cannot be closed separately.")

    def load_tokens_from_sheets(self):
        """
        Loads token rows for today from the Google Sheet into self.token_data.
        Expected sheet columns (A-F): Date | Day | Time | Candidate Name | Contact Number | Entry No
        """
        self.token_data = []
        if not self.sheets:
            # Sheets reader not initialized
            return

        # Use today's sheet tab name (YYYY-MM-DD). If that tab doesn't exist, try the default first sheet range.
        today_tab = datetime.now().strftime("%Y-%m-%d")
        rows = []
        # Try reading the daily tab first (common setup where each day is a tab)
        try:
            rows = self.sheets.fetch_today_rows(sheet_name=today_tab)
        except Exception as e_tab:
            # If daily tab doesn't exist or error, fallback to default A:F of first sheet
            try:
                rows = self.sheets.fetch_today_rows(sheet_name=None)
            except Exception as e_default:
                # Could not read any sheet; show warning once in console
                print("Sheets read error:", e_tab, e_default)
                return

        if not rows or len(rows) <= 1:
            # no data or only header
            return

        today = datetime.now().strftime("%Y-%m-%d")
        # rows[0] is header; iterate from rows[1:]
        for r in rows[1:]:
            # ensure row has at least 6 columns safely
            # A: Date (index 0), D: Name (3), F: Entry No (5), C: Time (2)
            if len(r) >= 6:
                date_val = r[0]
                try:
                    if date_val == today:
                        token = r[5]
                        name = r[3]
                        time_val = r[2] if len(r) > 2 else ""
                        self.token_data.append({
                            "token": token,
                            "name": name,
                            "date": date_val,
                            "time": time_val
                        })
                except Exception:
                    # ignore row if malformed
                    continue
            else:
                # row too short — try best-effort mapping if indices exist
                if len(r) >= 1 and r[0] == today:
                    token = r[5] if len(r) > 5 else (r[-1] if len(r) > 0 else "")
                    name = r[3] if len(r) > 3 else ""
                    time_val = r[2] if len(r) > 2 else ""
                    self.token_data.append({
                        "token": token,
                        "name": name,
                        "date": r[0],
                        "time": time_val
                    })

    def refresh_loop(self):
        # reload tokens (only if room is open)
        if not self.counter_closed:
            try:
                self.load_tokens_from_sheets()
            except Exception as e:
                print("Error loading tokens:", e)
        # schedule next refresh
        self.master.after(self.refresh_interval_ms, self.refresh_loop)

    def call_next(self):
        if self.counter_closed:
            messagebox.showwarning("Room Closed", "This room is closed.")
            return

        # load local state
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {"called_tokens": []}

        called_tokens = [item.get("token") for item in state.get("called_tokens", [])]

        # pick next token not in called_tokens
        next_token = None
        for t in self.token_data:
            if t.get("token") and t.get("token") not in called_tokens:
                next_token = t
                break

        if next_token:
            self.current_token = next_token
            # append to local state
            state.setdefault("called_tokens", []).append({
                "token": next_token.get("token"),
                "name": next_token.get("name"),
                "counter": COUNTER_NAME,
                "time": next_token.get("time"),
                "called_at": datetime.now().isoformat()
            })
            try:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            except Exception as e:
                messagebox.showwarning("Write Error", f"Could not update local state file:\n{e}")

            # update UI/display
            self.update_display(next_token)
        else:
            messagebox.showinfo("Info", "No more tokens to call.")

    def recall(self):
        if self.counter_closed:
            messagebox.showwarning("Room Closed", "This room is closed.")
            return

        if self.current_token:
            self.update_display(self.current_token)
        else:
            messagebox.showinfo("Info", "No token to recall.")

    def set_waiting(self):
        if self.counter_closed:
            messagebox.showwarning("Room Closed", "This room is closed.")
            return

        self.current_token = None
        self.token_label.config(text="Waiting", fg=FG_COLOR)
        self.display_label.config(text="Waiting", fg=FG_COLOR, font=(self.font_family, 24, "bold"))

    def update_display(self, token_info):
        token_text = f"Token: {token_info.get('token')}\nName: {token_info.get('name')}"
        self.token_label.config(text=token_text, fg=FG_COLOR)
        self.display_label.config(text=f"Token {token_info.get('token')}\n{token_info.get('name')}",
                                  fg=FG_COLOR, font=(self.font_family, 24, "bold"))

    def close_counter(self):
        if not messagebox.askyesno("Close Room", "Are you sure you want to close this interview room?"):
            return
        self.counter_closed = True
        self.call_button.config(state='disabled', bg=DISABLED_BG, fg=DISABLED_FG)
        self.recall_button.config(state='disabled', bg=DISABLED_BG, fg=DISABLED_FG)
        self.waiting_button.config(state='disabled', bg=DISABLED_BG, fg=DISABLED_FG)
        self.close_button.config(state='disabled', bg=DISABLED_BG, fg=DISABLED_FG)

        self.display_label.config(text="Room Closed", fg=RED_COLOR, font=(self.font_family, 28, "bold"))
        self.token_label.config(text="Room Closed", fg=RED_COLOR)

    def open_counter(self):
        if not self.counter_closed:
            messagebox.showinfo("Info", "Room is already open.")
            return
        self.counter_closed = False
        self.call_button.config(state='normal', bg=BUTTON_BG, fg=BUTTON_FG)
        self.recall_button.config(state='normal', bg=BUTTON_BG, fg=BUTTON_FG)
        self.waiting_button.config(state='normal', bg=BUTTON_BG, fg=BUTTON_FG)
        self.close_button.config(state='normal', bg=RED_COLOR, fg="white")

        self.current_token = None
        self.token_label.config(text="Waiting", fg=FG_COLOR)
        self.display_label.config(text="Waiting", fg=FG_COLOR, font=(self.font_family, 24, "bold"))

# --- Run app ---
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = TokenCallerApp(root)
        root.mainloop()
    except Exception as e:
        print("Fatal error starting app:", e)
        traceback.print_exc()
