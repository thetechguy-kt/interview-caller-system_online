# <b>Interview Queue Caller System - Online</b>
[![Documentation](https://img.shields.io/badge/Documentation-available-brightgreen)](./README.md)
[![License: GNU](https://img.shields.io/badge/License-GNU%20v3.0-yellow.svg)](./LICENSE)
![Platforms](https://img.shields.io/badge/Platform-Windows-blue)
[![Python](https://img.shields.io/badge/Python-3.11-orange?logo=python)](https://www.python.org/)

<i>An Online Interview Queue Caller System built with Python and Tkinter.</i>
### <i>This project is licensed under the GNU General Public License v3.0 — see the LICENSE file for details.</i>

This is a multi-part application designed to streamline candidate flow management during interviews or walk-in assessments. It automates token generation, queue control, and live displays for interview counters. Built with Python and Tkinter, the system uses Google Sheets for online candidate records and JSON files for local queue handling to ensure fast and reliable performance.

To get the Offline Version of this application or system, please have a look at this repository: [Click Here](https://github.com/thetechguy-kt/interview-caller-system)

### One-Time ChangeLog ###
21th November 2025:
  - The Pre-Release 1 is uploaded in the Main Repository.
  - Any Queries can be sent to my E-Mail ID: [thetechguy34@outlook.com](mailto:thetechguy34@outlook.com)

For the full ChangeLog: [Click Here](https://github.com/thetechguy-kt/interview-caller-system_online/blob/main/Changelog.md)

# ✔️ Preparatory Steps

## 📄 Steps for `sheetsid.txt`
### 1. Create or Open the File:
-  Create a plain text file named sheetsid.txt in your project folder.
### 2. Get the Google Sheets ID:
-  Open your Google Sheets document in the browser.
-  Copy the ID from the URL. It’s the long string between /d/ and /edit in the URL. Example: `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit#gid=0`
### 3. Paste the ID:
-  Paste only the ID string inside sheetsid.txt and save the file.

## 📄 Steps for `service_account.json`
### 1. Create a Google Cloud Project:
-  Go to Google Cloud Consoleand create a new project or use an existing one.
### 2. Enable Google Sheets API:
-  In the project dashboard, navigate to APIs & Services > Library, search for Google Sheets API, and enable it.
### 3. Create a Service Account:
-  Go to APIs & Services > Credentials.
-  Click Create Credentials > Service account.
-  Fill in a name and description, then create.
### 4. Generate Service Account Key:
-  After creating the service account, go to its details and select Keys tab.
-  Click Add Key > Create new key.
-  Choose JSON and download the key file.
### 5. Save the JSON File:
-  Rename the downloaded file to service_account.json and place it in your project folder.
### 6. Share the Google Sheet with the Service Account:
-  Open your Google Sheet.
-  Share it with the service account’s email address (found inside the JSON file under client_email) and give it Editor permissions.

## 📄 1. Candidate Token Generator App - `Candidate POS.py (With Packaged .exe File for Windows)`
This is the front-desk application where a staff member logs each candidate as they arrive. It:
- Allows entry of candidate name and contact number
- Automatically assigns and displays a daily token number
- Saves each entry directly into an online Google Sheet
- Generates a printable PDF ticket for the candidate with QR code and interview info
- Resets the token count every day automatically
- Stores token data organized by date in the Google Sheet
- Tracks date and token state via a local JSON file

> <b> Ideal for reception or registration desk staff to quickly log and print token slips while keeping all data synchronized online. </b>

## 🖥️ 2. Interview Room Control Panel - `Interview Room 1.py, Interview Room 2.py (With Packaged .exe File for Windows for both the Python Files)`
This app runs inside each interview room and allows the interviewer or assistant to call the next candidate. Each instance represents one counter/room and includes:
- A main control window (Example, for Room 1)  
- A pop-up display window visible to candidates  
- A Call Next button that selects the next available token  
- Recall, Waiting, Open/Close Room controls  
- Updates a central file `queue_state.json` with the list of called tokens  
- Only reads from the Google Sheet (does not write to it)

> <b> Multiple rooms can run their own instances (Room 1, Room 2, and more), all coordinating via the shared `queue_state.json`. </b>

## 📺 3. Central Display Board - `Central Display.py (With Packaged .exe File for Windows)`
- The current token number and candidate name  
- The room number where the candidate should go  
- A clean layout suitable for large screens or TV monitors  
- Pulls data from:
  - `queue_state.json` → Called token data (updated by Room apps)  
  - Google Sheet → Candidate names and details  

> <b> This app is read-only and does not modify any files. Place it in the same folder as the shared `.json` and data source for live updates. </b>

## 🗂️ 4. Record Viewer App - `Record Viewer.py`

This utility app is designed for admins or HR staff to monitor, review, or audit the list of registered or interviewed candidates. It:

- Loads and displays the contents of `candidate_list.xlsx` as a live-updating HTML table  
- Uses a lightweight Flask web server with server-side Excel rendering (no Excel or GUI libraries needed)  
- Supports large datasets by rendering directly from the Excel file on the server  
- Auto-refreshes every 3 seconds to reflect new candidate entries via automatic page reload  
- Is fully read-only — it does not modify the Excel file  

> <b>This app is especially helpful during busy interview sessions for non-technical users who need a live, automatically refreshing web view of which candidates have registered and when. It’s also ideal for verifying past entries, performing audit checks, or sharing the list easily across multiple devices — all without opening Excel manually.</b>

# 📁 File Overview

| File/Folder                      | App/File Name             | Description                                                                                  |
|:--------------------------------|:-------------------------|:---------------------------------------------------------------------------------------------|
| `Candidate POS.py`               | Token Generator App       | Registers candidates, assigns daily token numbers, and generates printable PDF tickets with QR codes. |
| `Interview Room 1/2.py` | Interview Room Controller | Calls the next candidate, updates `queue_state.json`, and displays the token info in-room.   |
| `Central Display.py`             | Central Display Board     | Displays currently called tokens and assigned rooms in real-time for waiting candidates.    |
| `Record Viewer.py`               | Live Record Viewer App    | Shows and auto-refreshes the full list of registered candidates from `candidate_list.xlsx`. |
| `candidate_list.xlsx`            | Excel File - Candidate List | Stores all logged candidate details including name, contact, time, and assigned token.      |
| `sheetsid.txt`           | Sheets ID Config       | Contains the Google Sheets document ID used for the app.|
| `service_account.json`   | Service Account Config | Google service account credentials JSON for API access. |
| `queue_state.json`               | JSON File - Queue State   | Maintains the live state of called tokens and their assigned interview rooms.                |
| `config/last_ticket_date.txt`   | Text File - Last Ticket Date | Tracks the last active date for auto-resetting token numbers each day.                      |
| `Tickets/YYYY-MM-DD - Tickets/` | PDF Tickets and Excel Logs| Daily folder containing all generated PDF tickets plus a copy of the daily Excel log (`candidate_list_YYYY-MM-DD.xlsx`). |

<b> Note: 
  - Place all files in a single folder. Also include `dip_config/notify.wav`, which plays a sound and highlights the name when a new candidate is called from Room 1, 2, etc. You can     change the sound path in the Python File. Compile using PyInstaller or similar to create a `.exe File`.
  - `.exe Files` can be accessed from by Clicking Here: [Drive Share Folder](https://drive.google.com/drive/folders/1Ee10FsXgDbHq5aOWEoz9DiuQcTJltwUP?usp=drive_link)
</b>
