# HuntMyHead v0.1

A local-first career dashboard. It stores your career profile, projects, evidence files, discovered jobs, application drafts and outreach drafts on your laptop.

## Quick start (Windows 10/11)

1. Install **Python 3.12 (64-bit)** from https://www.python.org/downloads/ and enable **Add Python to PATH**. The launcher intentionally selects Python 3.12 rather than an untested newer interpreter.
2. Extract this folder somewhere writable, e.g. `C:\CareerOS`.
3. Double-click `START_CAREEROS.bat`.
4. Wait for dependencies to install. Your browser opens at **http://127.0.0.1:8765**.
5. Keep the terminal window open while using CareerOS. Close it to stop the server.

The first launch needs an internet connection to install Python packages. The app itself binds only to `127.0.0.1` and is not exposed to your network.

## Included in v0.1

- Dashboard and local SQLite database.
- Seeded career profile and editable salary, location, role-family and briefing preferences.
- Project Studio with starter entries for work, ventures and initiatives; add/edit projects and upload PDF, DOCX, PPTX, TXT, Markdown and source-code files.
- Text extraction from supported document types.
- Job discovery from configured public Greenhouse and Lever boards.
- Manual job URL import, deduplication, keyword/role/location/recency scoring.
- Application draft queue and explicit approval recording.
- Founder outreach draft queue and approval recording.
- Local event log and daily briefing endpoint.
- Windows Task Scheduler installer for 9:00 AM IST discovery.

## Configure job sources

Open **Sources** in the app. Add the public board token for each company:

- Greenhouse: `https://boards.greenhouse.io/<token>` → token is `<token>`.
- Lever: `https://jobs.lever.co/<token>` → token is `<token>`.

Then select **Run job discovery**. The first sample `example` rows are placeholders and are skipped. Add real board tokens to receive results. Use the company’s public careers page to confirm the role is still open.

This release does not perform universal web search and does not scrape LinkedIn. Add jobs manually using their URLs, or use permitted alerts/exports and connectors. Do not bypass login, CAPTCHA, rate limits or site terms.

## Daily 9:00 AM IST task

After the first successful launch and source setup, open PowerShell in the extracted folder and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\install_scheduler.ps1
```

Windows Task Scheduler runs discovery at 9:00 AM using the local machine timezone. Ensure Windows is configured to India Standard Time and the laptop is powered on. The run log is `data/daily_run.log`. The API/dashboard does not have to be open for the scheduled discovery task.

## Approval and submission safety

- Preparing an application does not submit it.
- Approving an application records your explicit decision but does **not** click the employer's final submit button in v0.1. Open the original posting, complete any required declarations/OTP/CAPTCHA, submit yourself, then record a confirmation note in CareerOS.
- Outreach approval records your decision but does **not** send email in v0.1. Copy the draft, verify recipient and send it yourself.
- Never enter false qualifications, employment dates, salary history or eligibility declarations.

This is intentional: no application or email is marked submitted/sent without evidence of the action.

## Data and backups

All data lives under `data/`:

- `careeros.db`: SQLite database.
- `uploads/`: uploaded project documents.
- `daily_run.log`: scheduler log.

Back up the entire `data` folder. Do not commit it to GitHub. The `.gitignore` excludes it.

## API

Interactive API documentation: http://127.0.0.1:8765/docs
Health: http://127.0.0.1:8765/api/health

## Known v0.1 limitations

- No LinkedIn scraping, universal job-board search, Gmail integration, automatic email sending, or unattended employer-site form submission.
- Greenhouse/Lever board tokens must be configured by you. Search coverage depends on the configured boards.
- Scoring is a transparent first-pass heuristic, not an AI hiring prediction. Review eligibility, seniority, location, salary and job freshness manually.
- Local LLM/Ollama integration, robust resume generation, founder discovery and richer interview knowledge extraction are planned next increments.
- Public recruiter portfolio is not deployed in this package; it should be a separate sanitized site, not a public view of this private database.

## Development

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.app
```

Python 3.12 is the supported Windows runtime for this release. This is an initial runnable MVP; verify connectors and back up data before relying on it for a live search.
