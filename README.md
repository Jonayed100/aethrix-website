# Project Aethrix website

The full website for **Project Aethrix**, founded by **Jonayed Hossain**. It covers the public site with the red 3D design, live demo projects, project bookings, a private **founder dashboard** and a **client dashboard**, all backed by a database.

Built with **Python + Django**, **PostgreSQL** (SQLite on your laptop), **Three.js** for the 3D, and ready to deploy on **Render**.

---

## What's inside

| Part | Who sees it | What it does |
|---|---|---|
| Public website | Everyone | 3D hero with your name, 3 services (Web development, Application development, AI chatbot), demo projects, founder section, booking form |
| Booking system | Clients | Booking saved in the database, email alert to you, confirmation email to the client |
| **Client dashboard** `/dashboard/` | Each client, with email + password | Their own orders only: 3D "block-by-block" progress, active and completed orders, stage tracker, price, due date, delivery link, messages with you |
| **Founder dashboard** (secret address) | **Only you**, with email + password | 3D bookings chart, stats, all orders, update status/price/progress, message clients, give clients dashboard access, manage demo projects, client list, CSV export |
| Backup admin (secret address) | Only you | Django's built-in admin, for rare fixes |
| Accounts | Clients | Sign up, verify email, log in, forgot password, change password |
| Security | — | Founder pages show "page not found" to everyone else, login rate limits, spam trap on bookings, HTTPS-only cookies, CSRF protection |
| Tests | — | 49 automated tests (`python manage.py test`) |

### Who can open what

| | Visitor | Client | Founder (you) |
|---|---|---|---|
| Website, booking form | ✅ | ✅ | ✅ |
| Client dashboard | ❌ asked to log in | ✅ own orders only | ➜ sent to founder dashboard |
| Founder dashboard | ❌ asked to log in | ❌ "page not found" | ✅ |
| Backup admin | ❌ | ❌ | ✅ |

The website only links to **Client login**. Nothing on the site links to the founder dashboard; you open it from your saved address.

---

## What you need

| Thing | Why | Cost |
|---|---|---|
| **Python 3.12+** | Runs the website | Free · python.org |
| **VS Code** + Python extension | Editing and running | Free |
| **Git** + **GitHub account** | Stores your code; Render deploys from it | Free |
| **Database** | SQLite file on your laptop (automatic). **PostgreSQL** on the live site | Free to start |
| **Render account** | Hosts the website and the database | Free plan to start |
| **Brevo account** | Sends emails (bookings, verification, password links) from the live site | Free plan |
| **Domain name** (optional) | e.g. `projectaethrix.com` | Yearly fee |

---

## 1. Run it on your computer

Open the `aethrix-website` folder in VS Code, then **Terminal → New Terminal**.

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

**Mac / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Now open the new `.env` file and set your founder password:
```
FOUNDER_EMAIL=projectaethrix@gmail.com
FOUNDER_PASSWORD=pick-a-long-strong-password
```

Then:
```
python manage.py migrate
python manage.py ensure_founder
python manage.py runserver
```

| Open | What |
|---|---|
| http://127.0.0.1:8000 | The website |
| http://127.0.0.1:8000/login/ | Client login |
| http://127.0.0.1:8000/founder/login/ | **Your founder login** (email + password from `.env`) |
| http://127.0.0.1:8000/admin/ | Backup admin |

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
> In VS Code press **Ctrl+Shift+P → Python: Select Interpreter → .venv**. Then **F5** starts the site.

**Updating from the earlier version?** Just run `python manage.py migrate` again. Your existing bookings and projects stay.

Locally, emails (verification links, password links, booking alerts) are **printed in the terminal** instead of sent. Copy links from there while testing.

---

## 2. The founder dashboard

Log in at **/founder/login/** (or your secret `FOUNDER_URL`).

- **Overview:** a 3D chart of bookings for the last 6 months (hover a column), new bookings waiting, active projects, completed projects, your open pipeline in taka, the latest bookings and client messages.
- **Orders:**
  - Filter by New / Active / Completed / Declined, search by name, email or reference, and download a CSV.
  - Open an order to set its **status**, **project name**, **quoted price**, **progress %** (slider), **due date** and **delivery link**, and add private notes.
  - Tick **Email the client** to send them a summary of the changes. Every change also appears in the client's dashboard timeline.
  - Send messages to the client; their replies show up here and in your email.
- **Give client dashboard access:**
  - On any order, click **Give client dashboard access**.
  - If the client has no account, one is created and they get an email to set a password. Then they log in with email + password and see the order.
- **Demo projects:** add, edit, hide/show and delete the projects on the website. No code needed.
- **Clients:** every client account, their orders, whether their email is verified, and when they last signed in.
- **Account:** change your password.

## 3. The client dashboard

Clients get in by:
1. **Signing up** at `/signup/` (the booking confirmation email and thank-you page link there with their email filled in), then clicking the verification link in their email, **or**
2. Getting **dashboard access** from you on an order.

Inside, they see only their own orders:
- A 3D build where blocks drop into place up to the project's progress, with a big progress %.
- A stage tracker: Received → Call → Building → Delivered.
- Separate **Active** and **Completed** tabs.
- Price, due date, and the **live link** when the project is delivered.
- The message thread with you, and the **Account** page to change their details and password.

Bookings made with the same email before the client signed up appear once they verify their email. Bookings made while logged in go straight into their dashboard.

---

## 4. Where the database is

- **On your laptop:** the file `db.sqlite3` in the project folder.
- **On Render:** a PostgreSQL database named `aethrix-db`, connected automatically.

Tables you'll care about: bookings/orders, order messages, demo projects, user accounts and profiles. You manage all of it from the founder dashboard.

---

## 5. Turn on real emails (Brevo)

Render's free plan blocks normal email (SMTP) ports, so the site sends email through Brevo's web API.

1. Create a free account at **brevo.com** with `projectaethrix@gmail.com`.
2. Add `projectaethrix@gmail.com` as a sender in Brevo and verify it from the email Brevo sends you.
3. Create an API key in Brevo and copy it.
4. Put it in `BREVO_API_KEY` (in `.env` locally, or in Render's Environment tab).

Clients need working emails to verify their account and to set or reset passwords, so do this before you share the site.

Tip: emails sent "from" a Gmail address can land in spam. Once you own a domain, verify it in Brevo and change `DEFAULT_FROM_EMAIL` to something like `hello@projectaethrix.com`.

---

## 6. Put it online (GitHub + Render)

**a. Push to GitHub**
```bash
git init
git add .
git commit -m "Project Aethrix website"
git update-index --chmod=+x build.sh
git commit -m "Make build script runnable"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/aethrix-website.git
git push -u origin main
```

**b. Deploy on Render**
1. Render dashboard → **New → Blueprint** → choose your repo. Render reads `render.yaml` and creates the **website** and the **PostgreSQL database**.
2. Fill in the empty values:
   - `SITE_URL` → `https://project-aethrix.onrender.com` (your Render address)
   - `FOUNDER_URL` → a secret address for your dashboard, e.g. `aethrix-hq-7392/`
   - `ADMIN_URL` → another secret address, e.g. `aethrix-backup-4810/`
   - `FOUNDER_EMAIL` → `projectaethrix@gmail.com`
   - `FOUNDER_PASSWORD` → a long, strong password
   - `BREVO_API_KEY` → from step 5
3. Click **Apply**. When it says **Live**, your founder login is at `https://your-site/aethrix-hq-7392/login/`. Bookmark it.

Every `git push` redeploys the site. Changing `FOUNDER_PASSWORD` later does **not** change your password; use the Account page in the dashboard for that.

**Good to know about free plans**
- **The site sleeps:** a free Render website sleeps after about 15 minutes without visitors, and the next visit takes up to a minute.
- **The database is deleted after 30 days:** Render's free PostgreSQL is deleted 30 days after it's created. Before then, upgrade it, or create a free database at **neon.tech** and paste its connection string into `DATABASE_URL`. Bookings and client accounts live there, so don't skip this.

---

## 7. Your own domain (optional)

1. Buy a domain and add it in Render → your web service → **Settings → Custom Domains**.
2. Set in Render's Environment tab:
   - `ALLOWED_HOSTS` → `projectaethrix.com,www.projectaethrix.com`
   - `CSRF_TRUSTED_ORIGINS` → `https://projectaethrix.com,https://www.projectaethrix.com`
   - `SITE_URL` → `https://projectaethrix.com`

---

## Where to change things

| To change | Edit |
|---|---|
| Home page text | `templates/home.html` |
| Colours, fonts | `static/css/site.css` (tokens at the top: `--red`, `--bone`, …) |
| Dashboard look | `static/css/dash.css` |
| Home 3D (robot cube, particles) | `static/js/site.js` |
| Dashboard 3D (bookings chart, block build, login cube) | `static/js/dash3d.js` |
| Founder dashboard pages | `templates/founder/`, logic in `founder/views.py` |
| Client dashboard pages | `templates/portal/`, logic in `portal/views.py` |
| Login and sign-up pages | `templates/accounts/`, logic in `accounts/views.py` |
| Email wording | `studio/emails.py` and `templates/emails/` |
| Booking form fields | `studio/forms.py` and `studio/models.py` |

After changing anything in a `models.py`, run `python manage.py makemigrations` then `python manage.py migrate`.

---

## Project structure

```
aethrix-website/
├── config/      Settings and main URLs
├── studio/      Public site: demo projects, bookings/orders, messages, emails
├── accounts/    Email + password logins, sign-up, email verification, password reset
├── portal/      Client dashboard
├── founder/     Founder dashboard (founder only)
├── templates/   Pages and emails
├── static/      CSS, JavaScript, three.js
├── build.sh     What Render runs on each deploy
└── render.yaml  Render Blueprint (website + database)
```

## Useful commands

```bash
python manage.py runserver        # start the site locally
python manage.py test             # run all 49 tests
python manage.py ensure_founder   # create the founder login from .env
python manage.py check --deploy   # security check before going live
```

## Troubleshooting

- **`SECRET_KEY is not set`:** you have no `.env` file. Copy `.env.example` to `.env`.
- **"Email or password is wrong" on founder login:** run `python manage.py ensure_founder` after setting `FOUNDER_EMAIL` and `FOUNDER_PASSWORD` in `.env`.
- **"Too many tries":** 8 wrong logins lock that connection for 15 minutes.
- **Clients don't get verification or password emails:** check `BREVO_API_KEY` and that the sender is verified in Brevo. Locally, the links are in the terminal.
- **Live site shows "Bad Request (400)":** add your domain to `ALLOWED_HOSTS`.
- **"CSRF verification failed" on your domain:** add `https://yourdomain` to `CSRF_TRUSTED_ORIGINS`.
