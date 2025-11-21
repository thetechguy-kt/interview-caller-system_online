# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.
from flask import Flask, render_template_string
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ------------------------------------------------------
# READ SHEET ID FROM FILE
# ------------------------------------------------------
with open("sheetsid.txt", "r") as f:
    SHEET_ID = f.read().strip()

# ------------------------------------------------------
# GOOGLE SHEETS AUTH
# ------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)
app = Flask(__name__)

# ------------------------------------------------------
# FETCH DATA FROM GOOGLE SHEETS
# ------------------------------------------------------
def sheet_to_html():
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.sheet1  # first worksheet (you can change this)
        data = ws.get_all_values()

        if not data:
            return "<p style='color:#ffdede'>No data found.</p>"

        # Build table HTML
        header = data[0]
        rows = data[1:]

        html = '<table class="candidate-table" role="table">'
        html += "<thead><tr>"
        for col in header:
            html += f"<th scope='col'>{col}</th>"
        html += "</tr></thead>"

        html += "<tbody>"
        for i, row in enumerate(rows):
            row_class = "even" if i % 2 == 0 else "odd"
            html += f"<tr class='{row_class}'>"

            for j, cell in enumerate(row):
                cell_val = cell if cell else ""
                if j == 3:  # highlight NAME column
                    html += f"<td class='name-cell'>{cell_val}</td>"
                else:
                    html += f"<td>{cell_val}</td>"

            html += "</tr>"
        html += "</tbody></table>"
        return html

    except Exception as e:
        return f"<p style='color:#ffdede'>Error loading sheet:<br>{e}</p>"

# ------------------------------------------------------
# ROUTE
# ------------------------------------------------------
@app.route('/')
def index():
    table_html = sheet_to_html()
    now = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>KTech Candidate Record Viewer</title>

<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap" rel="stylesheet">

<style>
  :root{{
    --bg:#0f1214;
    --panel:#15171a;
    --muted:#bfc8cc;
    --title:#00e5ff;
    --subtitle:#00bfa5;
    --accent:#0a84a6;
    --row-odd:#121416;
    --row-even:#1a1c1e;
    --name-highlight:rgba(0,191,165,0.08);
    --border:rgba(255,255,255,0.04);
  }}
  html,body {{
    margin:0;background:var(--bg);color:var(--muted);
    font-family:"Montserrat", Aptos, Segoe UI, Roboto, sans-serif;
  }}
  .container {{
    max-width:1200px;margin:32px auto;padding:28px;
    background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01));
    border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.6);
    border:1px solid var(--border);
  }}
  h1 {{color:var(--title);margin:0;font-size:28px;font-weight:800;}}
  .time {{color:var(--subtitle);font-weight:800;font-size:16px;}}
  .candidate-table {{
    width:100%;border-collapse:collapse;border-radius:12px;overflow:hidden;
  }}
  .candidate-table thead th {{
    padding:14px 16px;background:rgba(255,255,255,0.03);
    color:var(--title);font-size:16px;font-weight:700;
  }}
  .candidate-table tbody td {{
    padding:12px 16px;font-size:14px;white-space:nowrap;
  }}
  .odd {{background:var(--row-odd);}}
  .even {{background:var(--row-even);}}
  .name-cell {{
    background:var(--name-highlight);
    border-radius:4px;padding:10px 14px;
  }}
</style>

<script>
  setTimeout(() => {{ location.reload(); }}, 3000);
</script>
</head>
<body>
  <div class="container">
    <header style="display:flex;justify-content:space-between;align-items:center;">
      <h1>🎓 KTech Candidate Records</h1>
      <div>
        <div class="time">{now}</div>
      </div>
    </header>

    <main>{table_html}</main>

    <div class="footer" style="margin-top:16px;color:#555;">
      Data Source: <strong style="color:var(--title)">Google Sheets</strong> • Auto-refresh 3s
    </div>
  </div>
</body>
</html>
'''
    return render_template_string(page)

# ------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
