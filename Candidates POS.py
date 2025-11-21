# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.
import tkinter as tk
from tkinter import messagebox, font as tkfont
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import qrcode
import os
import shutil
import json
import traceback

# Google Sheets imports
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ----------------- Configuration files -----------------
SHEETS_ID_FILE = "sheetsid.txt"
SERVICE_ACCOUNT_FILE = "service_account.json"

TICKET_FOLDER = "Tickets"
CONFIG_FOLDER = "config"
DATE_TRACK_FILE = os.path.join(CONFIG_FOLDER, "last_ticket_date.txt")

os.makedirs(CONFIG_FOLDER, exist_ok=True)
os.makedirs(TICKET_FOLDER, exist_ok=True)

# ----------------- Utilities -----------------
def pick_preferred_font(root):
    preferred_fonts = ["Montserrat", "Aptos", "Segoe UI", "Helvetica", "Arial"]
    try:
        available = list(tkfont.families(root))
        for f in preferred_fonts:
            if f in available:
                return f
    except Exception:
        pass
    return "TkDefaultFont"

def register_pdf_font():
    possible_fonts = [
        ("Montserrat", "C:\\Windows\\Fonts\\Montserrat-Regular.ttf"),
        ("Aptos", "C:\\Windows\\Fonts\\Aptos.ttf"),
    ]
    for name, path in possible_fonts:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                pass
    return "Helvetica"

def read_sheet_id():
    if not os.path.exists(SHEETS_ID_FILE):
        raise FileNotFoundError(f"{SHEETS_ID_FILE} not found. Create it with your Google Sheet ID.")
    with open(SHEETS_ID_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

# ----------------- Google Sheets Handler -----------------
class SheetsHandler:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self):
        self.sheet_id = read_sheet_id()
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"{SERVICE_ACCOUNT_FILE} not found. Place your service account JSON file in the project folder.")
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
        self.service = build("sheets", "v4", credentials=creds)
        self.spreadsheet = None
        # load spreadsheet metadata
        self._load_spreadsheet()

    def _load_spreadsheet(self):
        try:
            self.spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
        except HttpError as e:
            raise RuntimeError(f"Error loading spreadsheet: {e}")

    def sheet_exists(self, title):
        sheets = self.spreadsheet.get("sheets", [])
        for s in sheets:
            props = s.get("properties", {})
            if props.get("title") == title:
                return True
        return False

    def create_daily_sheet_if_missing(self, title):
        # refresh metadata
        self._load_spreadsheet()
        if self.sheet_exists(title):
            return
        requests = [
            {"addSheet": {"properties": {"title": title, "gridProperties": {"rowCount": 1000, "columnCount": 10}}}}
        ]
        try:
            body = {"requests": requests}
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()
            # set header row
            header = [["Date", "Day", "Time", "Candidate Name", "Contact Number", "Entry No"]]
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"'{title}'!A1:F1",
                valueInputOption="USER_ENTERED",
                body={"values": header}
            ).execute()
            # reload metadata
            self._load_spreadsheet()
        except HttpError as e:
            raise RuntimeError(f"Error creating daily sheet: {e}")

    def get_today_rows(self, title):
        try:
            res = self.service.spreadsheets().values().get(spreadsheetId=self.sheet_id, range=f"'{title}'!A:F").execute()
            return res.get("values", [])
        except HttpError:
            return []

    def append_row(self, title, row_values):
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=f"'{title}'!A:F",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_values]}
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Error appending row: {e}")

    def clear_daily_rows(self, title):
        try:
            # clear from row 2 onwards (keep header)
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=f"'{title}'!A2:F"
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Error clearing sheet: {e}")

    def get_last_ticket_number(self, title, today_date_str):
        rows = self.get_today_rows(title)
        # first row is header; check rows starting from index 1
        if not rows or len(rows) <= 1:
            return 0
        count = 0
        for r in rows[1:]:
            # A column is Date
            if len(r) >= 1 and r[0] == today_date_str:
                count += 1
        return count

# ----------------- Main App -----------------
class InterviewCandidatePOS:
    def __init__(self, root):
        self.root = root
        self.root.title("KTech Candidate POS")
        self.set_window_size(420, 480)

        self.bg_color = "#121217"
        self.fg_color = "#E0E6F1"
        self.accent_color = "#00FFFF"
        self.button_bg = "#1F1F2B"
        self.button_hover_bg = "#00CED1"
        self.entry_bg = "#1E1E2F"
        self.entry_fg = "#E0E6F1"
        self.root.configure(bg=self.bg_color)

        self.font_family = pick_preferred_font(root)
        self.pdf_font = register_pdf_font()

        self.today = datetime.now().strftime("%Y-%m-%d")
        # Sheets handler (lazy init; errors shown as messagebox)
        try:
            self.sheets = SheetsHandler()
        except Exception as e:
            messagebox.showerror("Sheets Init Error", f"Could not initialize Google Sheets:\n{e}")
            raise

        # ensure daily sheet exists
        try:
            self.sheet_name = self.today  # daily sheet title
            self.sheets.create_daily_sheet_if_missing(self.sheet_name)
        except Exception as e:
            messagebox.showerror("Sheets Error", f"Error ensuring daily sheet:\n{e}")
            raise

        # ticket counter logic
        self.check_and_reset_daily()

        # GUI setup
        self.main_frame = tk.Frame(root, bg=self.bg_color)
        self.main_frame.pack(fill='both', expand=True)
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=0)
        self.main_frame.columnconfigure(0, weight=1)

        self.input_frame = tk.Frame(self.main_frame, bg=self.bg_color, padx=20, pady=20)
        self.input_frame.grid(row=0, column=0, sticky='nsew')

        self.button_frame = tk.Frame(self.main_frame, bg=self.bg_color, padx=20, pady=10)
        self.button_frame.grid(row=1, column=0, sticky='ew')

        for i in range(6):
            self.input_frame.rowconfigure(i, weight=0)
        self.input_frame.columnconfigure(0, weight=0)
        self.input_frame.columnconfigure(1, weight=1)

        self.title_label = tk.Label(
            self.input_frame,
            text="🎓 KTech Interview Candidate POS",
            font=(self.font_family, 18, "bold"),
            bg=self.bg_color, fg=self.accent_color
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 25))

        self.name_label = tk.Label(
            self.input_frame, text="Candidate Name:",
            bg=self.bg_color, fg=self.fg_color, font=(self.font_family, 12)
        )
        self.name_label.grid(row=1, column=0, sticky='w', pady=5)
        self.name_entry = tk.Entry(
            self.input_frame, bg=self.entry_bg, fg=self.entry_fg,
            insertbackground=self.accent_color, font=(self.font_family, 12),
            relief="flat", highlightthickness=2,
            highlightbackground="#2F2F3F", highlightcolor=self.accent_color
        )
        self.name_entry.grid(row=1, column=1, sticky='ew', pady=5)

        self.contact_label = tk.Label(
            self.input_frame, text="Contact Number:",
            bg=self.bg_color, fg=self.fg_color, font=(self.font_family, 12)
        )
        self.contact_label.grid(row=2, column=0, sticky='w', pady=5)
        self.contact_number_entry = tk.Entry(
            self.input_frame, bg=self.entry_bg, fg=self.entry_fg,
            insertbackground=self.accent_color, font=(self.font_family, 12),
            relief="flat", highlightthickness=2,
            highlightbackground="#2F2F3F", highlightcolor=self.accent_color
        )
        self.contact_number_entry.grid(row=2, column=1, sticky='ew', pady=5)

        self.ticket_label = tk.Label(
            self.input_frame, text=f"Entry No: {getattr(self, 'ticket_number', 0)}",
            font=(self.font_family, 22, "bold"), fg=self.accent_color, bg=self.bg_color
        )
        self.ticket_label.grid(row=4, column=0, columnspan=2, pady=20)

        self.btn_generate = tk.Button(
            self.button_frame, text="Generate Entry Pass",
            font=(self.font_family, 14, "bold"),
            bg=self.button_bg, fg=self.accent_color,
            activebackground=self.button_hover_bg, activeforeground="#121217",
            relief="flat", command=self.generate_ticket, cursor="hand2"
        )
        self.btn_generate.pack(fill='x', pady=8)
        self.add_hover_effect(self.btn_generate, self.button_bg, self.button_hover_bg, self.accent_color, "#121217")

        self.btn_reset = tk.Button(
            self.button_frame, text="Reset Counter",
            font=(self.font_family, 12, "bold"),
            bg="#8B0000", fg="white",
            activebackground="#B22222", activeforeground="#f0f0f0",
            relief="flat", command=self.reset_counter, cursor="hand2"
        )
        self.btn_reset.pack(fill='x')
        self.add_hover_effect(self.btn_reset, "#8B0000", "#B22222", "white", "#f0f0f0")

    def add_hover_effect(self, widget, bg_normal, bg_hover, fg_normal, fg_hover):
        def on_enter(e):
            widget['background'] = bg_hover
            widget['foreground'] = fg_hover
            try:
                widget['font'] = (self.font_family, widget['font'][1], "bold")
            except Exception:
                pass
        def on_leave(e):
            widget['background'] = bg_normal
            widget['foreground'] = fg_normal
            try:
                widget['font'] = (self.font_family, widget['font'][1])
            except Exception:
                pass
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def set_window_size(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(400, 450)

    def check_and_reset_daily(self):
        # determine today's ticket number from Sheets
        try:
            if not os.path.exists(DATE_TRACK_FILE):
                with open(DATE_TRACK_FILE, 'w', encoding='utf-8') as f:
                    f.write(self.today)
                self.sheets.create_daily_sheet_if_missing(self.sheet_name)
                self.ticket_number = 0
            else:
                with open(DATE_TRACK_FILE, 'r', encoding='utf-8') as f:
                    last_date = f.read().strip()
                if last_date != self.today:
                    # new day: reset counter and clear today's sheet rows if exist
                    self.ticket_number = 0
                    with open(DATE_TRACK_FILE, 'w', encoding='utf-8') as f:
                        f.write(self.today)
                    try:
                        # ensure sheet exists then clear it
                        self.sheets.create_daily_sheet_if_missing(self.sheet_name)
                        self.sheets.clear_daily_rows(self.sheet_name)
                    except Exception as e:
                        messagebox.showwarning("Sheets Warning", f"Could not clear daily sheet: {e}")
                else:
                    # same day: read count from sheet
                    try:
                        self.sheets.create_daily_sheet_if_missing(self.sheet_name)
                        self.ticket_number = self.sheets.get_last_ticket_number(self.sheet_name, self.today)
                    except Exception as e:
                        messagebox.showwarning("Sheets Warning", f"Could not read ticket number from sheet: {e}")
                        self.ticket_number = 0
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Error during daily check: {e}\n{traceback.format_exc()}")
            self.ticket_number = 0

    def generate_ticket(self):
        name = self.name_entry.get().strip()
        contact_number = self.contact_number_entry.get().strip()
        if not name:
            messagebox.showwarning("Input Required", "Please enter the candidate's name.")
            return
        if not contact_number:
            messagebox.showwarning("Input Required", "Please enter the contact number.")
            return

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        day = now.strftime("%A")
        time_str = now.strftime("%H:%M:%S")
        file_time = now.strftime("%H-%M-%S")

        # increment and update label
        self.ticket_number += 1
        self.ticket_label.config(text=f"Entry No: {self.ticket_number}")

        # append to Google Sheets (A-F)
        try:
            self.sheets.append_row(self.sheet_name, [date, day, time_str, name, contact_number, str(self.ticket_number)])
        except Exception as e:
            messagebox.showerror("Sheets Error", f"Could not write to Google Sheets:\n{e}")
            # rollback ticket number visually (optional)
            self.ticket_number -= 1
            self.ticket_label.config(text=f"Entry No: {self.ticket_number}")
            return

        # create folder for today and save local PDF token
        folder_name = os.path.join(TICKET_FOLDER, f"{date} - Entries")
        os.makedirs(folder_name, exist_ok=True)

        safe_name = name.replace(" ", "_")
        pdf_filename = f"Entry_{self.ticket_number}_{safe_name}_{file_time}.pdf"
        pdf_path = os.path.join(folder_name, pdf_filename)

        try:
            self.create_ticket_pdf(pdf_path, name, contact_number, self.ticket_number, date, day, time_str)
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not create PDF:\n{e}")
            # PDF failure doesn't remove sheet row — you can implement cleanup if desired
            return

        # clear inputs
        self.name_entry.delete(0, tk.END)
        self.contact_number_entry.delete(0, tk.END)

        messagebox.showinfo("Success", f"Entry No {self.ticket_number} generated for {name}.")
        if messagebox.askyesno("Print Entry Pass", "Do you want to print the pass now?"):
            try:
                os.startfile(pdf_path, "print")
            except Exception as e:
                messagebox.showerror("Printing Error", f"Could not print ticket: {e}")

    def create_ticket_pdf(self, filepath, name, contact_number, entry_no, date, day, time_str):
        width = 8 * cm
        height = 8 * cm
        c = canvas.Canvas(filepath, pagesize=(width, height))
        qr_text = f"Entry No: {entry_no}\nName: {name}\nContact: {contact_number}\nDate: {date} ({day})\nTime: {time_str}"
        qr_img = qrcode.make(qr_text)
        qr_temp = "temp_qr.png"
        qr_img.save(qr_temp)

        c.setFont(self.pdf_font, 16)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(width / 2, height - 30, "KTech")

        c.setFont(self.pdf_font, 10)
        c.drawCentredString(width / 2, height - 50, f"{date} ({day}) | {time_str}")

        c.setFont(self.pdf_font, 10)
        c.drawString(20, height - 80, f"Name: {name}")
        c.drawString(20, height - 110, f"Number: {contact_number}")
        c.drawString(20, height - 140, f"Entry No: {entry_no}")

        c.drawImage(qr_temp, width - 90, 20, width=70, height=70)

        c.setFont(self.pdf_font, 8)
        c.drawCentredString(width / 2, 10, "Scan for interview info")

        c.showPage()
        c.save()
        os.remove(qr_temp)

    def reset_counter(self):
        if not messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the entry number?"):
            return

        # reset counter variable and label
        self.ticket_number = 0
        self.ticket_label.config(text="Entry No: 0")

        # reset date tracker file
        try:
            with open(DATE_TRACK_FILE, 'w', encoding='utf-8') as f:
                f.write(self.today)
        except Exception as e:
            messagebox.showwarning("File Warning", f"Could not update date tracking file: {e}")

        # clear today's sheet rows
        try:
            self.sheets.clear_daily_rows(self.sheet_name)
            messagebox.showinfo("Reset", "Daily entries cleared.")
        except Exception as e:
            messagebox.showerror("Sheets Error", f"Could not clear daily sheet:\n{e}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.configure(bg="#121217")
        app = InterviewCandidatePOS(root)
        root.mainloop()
    except Exception as e:
        # if initialization failed, show error on console
        print("Fatal error:", e)
        traceback.print_exc()
