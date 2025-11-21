# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.
import tkinter as tk
from tkinter import ttk
import json
import os
import platform
from datetime import datetime

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# Windows sound
if platform.system() == "Windows":
    import winsound

STATE_FILE = "queue_state.json"
SHEET_ID_FILE = "sheetsid.txt"
SERVICE_JSON = "service_account.json"

REFRESH_INTERVAL = 3000  # ms

# Theme colors
BG_COLOR = "#1e1e1e"
FG_COLOR = "#e0e0e0"
HEADER_BG_COLOR = "#004080"
SELECT_BG_COLOR = "#3399ff"
ROW_COLOR_1 = "#1e1e1e"
ROW_COLOR_2 = "#2a2a2a"
SELECT_FG_COLOR = "#ffffff"

class CentralDisplayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KTech Central Display")
        self.root.configure(bg=BG_COLOR)
        self.root.attributes('-fullscreen', True)

        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<f>", self.enter_fullscreen)
        self.root.bind("<F>", self.enter_fullscreen)

        tk.Label(root, text="🎓 KTech Interview",
                 font=("Arial", 36, "bold"),
                 fg=FG_COLOR, bg=BG_COLOR).pack(pady=(20, 5))

        tk.Button(
            root, text="🔲 Fullscreen (F)", font=("Arial", 10),
            command=self.enter_fullscreen,
            bg=HEADER_BG_COLOR, fg="white"
        ).pack(anchor="ne", padx=20, pady=(5, 0))

        self.time_label = tk.Label(root, text="", font=("Arial", 22, "bold"),
                                   bg=BG_COLOR, fg=FG_COLOR)
        self.time_label.pack()

        # Table
        columns = ("Token", "Name", "Room")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=15)
        self.tree.heading("Token", text="Token No")
        self.tree.heading("Name", text="Candidate Name")
        self.tree.heading("Room", text="Room")

        self.tree.column("Token", anchor="center", width=300)
        self.tree.column("Name", anchor="center", width=500)
        self.tree.column("Room", anchor="center", width=300)
        self.tree.pack(pady=40, expand=True, fill='both')

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview", background=BG_COLOR, foreground=FG_COLOR,
                        fieldbackground=BG_COLOR, font=("Arial", 18), rowheight=50)
        style.configure("Treeview.Heading", font=("Arial", 26, "bold"),
                        background=HEADER_BG_COLOR, foreground="white")
        style.map('Treeview', background=[('selected', SELECT_BG_COLOR)],
                  foreground=[('selected', SELECT_FG_COLOR)])

        self.tree.tag_configure('oddrow', background=ROW_COLOR_1)
        self.tree.tag_configure('evenrow', background=ROW_COLOR_2)
        self.tree.tag_configure('blink', background=SELECT_BG_COLOR, foreground=SELECT_FG_COLOR)

        self.previous_data = {}

        # Load Google Sheets once
        self.sheet = self.connect_to_sheets()

        self.update_time()
        self.refresh_data()

    def connect_to_sheets(self):
        try:
            if not os.path.exists(SHEET_ID_FILE) or not os.path.exists(SERVICE_JSON):
                print("Sheets disabled (missing file).")
                return None

            with open(SHEET_ID_FILE, "r") as f:
                sheet_id = f.read().strip()

            scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file(SERVICE_JSON, scopes=scope)
            client = gspread.authorize(creds)

            today = datetime.now().strftime("%d-%m-%Y")
            sheet = client.open_by_key(sheet_id).worksheet(today)

            print("Google Sheets connected.")
            return sheet

        except Exception as e:
            print("Sheets connection failed:", e)
            return None

    def get_name_from_sheet(self, token):
        """Reads candidate name from Google Sheet"""
        if self.sheet is None:
            return None

        try:
            records = self.sheet.get_all_records()
            for row in records:
                if str(row.get("Token")).strip() == str(token).strip():
                    return row.get("Name", "Unknown")
        except:
            return None

        return None

    def exit_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', False)

    def enter_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', True)

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        self.time_label.config(text=now)
        self.root.after(1000, self.update_time)

    def refresh_data(self):
        self.tree.delete(*self.tree.get_children())
        latest_data = {}

        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                state = json.load(f)

            latest_per_counter = {}
            for item in state.get("called_tokens", []):
                latest_per_counter[item["counter"]] = item

            sorted_items = sorted(
                latest_per_counter.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )

            for i, (counter, entry) in enumerate(sorted_items):
                token = entry["token"]

                # Try Google Sheets → fallback to JSON name
                name = self.get_name_from_sheet(token) or entry["name"]

                latest_data[counter] = token
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'

                row_id = self.tree.insert("", "end",
                                          values=(token, name, counter),
                                          tags=(tag,))

                if counter not in self.previous_data or self.previous_data[counter] != token:
                    self.blink_row(row_id, 0)
                    self.play_sound()

        self.previous_data = latest_data
        self.root.after(REFRESH_INTERVAL, self.refresh_data)

    def blink_row(self, row_id, count):
        if count < 6:
            tags = self.tree.item(row_id, "tags")

            normal_bg = ROW_COLOR_1 if 'oddrow' in tags else ROW_COLOR_2

            color = SELECT_BG_COLOR if count % 2 == 0 else normal_bg
            self.tree.tag_configure("blink", background=color)

            new_tags = [t for t in tags if t not in ('oddrow', 'evenrow')]
            new_tags.append("blink")
            self.tree.item(row_id, tags=new_tags)

            self.root.after(500, lambda: self.blink_row(row_id, count + 1))
        else:
            tags = self.tree.item(row_id, "tags")
            new_tags = [t for t in tags if t != "blink"]

            index = self.tree.index(row_id)
            new_tags.append('evenrow' if index % 2 == 0 else 'oddrow')
            self.tree.item(row_id, tags=new_tags)

    def play_sound(self):
        if platform.system() == "Windows" and os.path.exists("dip_config/notify.wav"):
            winsound.PlaySound("dip_config/notify.wav",
                               winsound.SND_FILENAME | winsound.SND_ASYNC)

if __name__ == "__main__":
    root = tk.Tk()
    app = CentralDisplayApp(root)
    root.mainloop()
