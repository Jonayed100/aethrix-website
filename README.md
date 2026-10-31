# Project Aethrix website

The full website for **Project Aethrix**, founded by **Jonayed Hossain** (*Ideas into Intelligence*). It covers the public site with the red 3D design, demo projects with their own details pages, client **sign up / log in**, a **client dashboard** where clients order projects, a private **admin dashboard** for your team and a private **founder dashboard** that sees everything, all backed by a database.

Built with **Python + Django**, **PostgreSQL** (SQLite on your laptop), **Three.js** for the 3D, and ready to deploy on **Render**.

---

## What's inside

| Part | Who sees it | What it does |
|---|---|---|
| Public website | Everyone | 3D hero with your name, **Log in / Sign up** buttons, 3 services, demo projects (each with a details page and live link), founder section, "Start your project" |
| Accounts | Clients | Sign up with full name, email, phone number and password; log in; forgot password; change password |
| **Client dashboard** `/dashboard/` | Each client | **New order** (project name + project details), their own orders only, 3D progress, stage tracker, price, due date, delivery link, messages with the team |
| **Admin dashboard** (secret address) | Your admins + you | Receives every order (Incoming / Pending / Completed), updates status, progress, price and dates, notifies the client by email, messages clients |
| **Founder dashboard** (secret address) | **Only you** | Everything admins have, plus money totals, every client's dashboard, the Team page (add/block admins), demo projects editor and CSV export |
| Backup admin (secret address) | Only you | Django's built-in admin, for rare fixes |
| Security | — | Private dashboards show "page not found" to everyone else, login rate limits, order rate limits, HTTPS-only cookies, CSRF protection |
| Tests | — | 77 automated tests (`python manage.py test`) |

### Who can open what

| | Visitor | Client | Admin | Founder (you) |
|---|---|---|---|---|
| Website, demo projects | ✅ | ✅ | ✅ | ✅ |
| Client dashboard, New order | ❌ asked to log in | ✅ own orders only | ➜ sent to admin dashboard | ➜ sent to founder dashboard |
| Admin dashboard | ❌ asked to log in | ❌ "page not found" | ✅ | ✅ |
| Founder dashboard | ❌ asked to log in | ❌ "page not found" | ❌ "page not found" | ✅ |
| Backup admin | ❌ | ❌ | ❌ | ✅ |

The website only shows **Log in** and **Sign up** (for clients). A signed-in client sees **My dashboard** and **Log out**. The founder and admins always see the website like a visitor: nothing on the site links to the admin or founder dashboards; they live at secret addresses. The website's Log in is for clients only.

**Founder login:** `projectaethrix@gmail.com` with the password you chose. It is set once by `accounts/migrations/0002_founder_login.py` (only the encrypted form is stored). Change it any time on the founder dashboard's Account page.

---

## What you need

| Thing | Why | Cost |
|---|---|---|
| **Python 3.12+** | Runs the website | Free · python.org |
| **VS Code** + Python extension | Editing and running | Free |
| **Git** + **GitHub account** | Stores your code; Render deploys from it | Free |
| **Database** | SQLite file on your laptop (automatic). **PostgreSQL** on the live site | Free to start |
| **Render account** | Hosts the website and the database | Free plan to start |
| **Brevo account** | Sends emails (new orders, updates, password links) from the live site | Free plan |
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
| http://127.0.0.1:8000/signup/ | Client sign up |
| http://127.0.0.1:8000/login/ | Client log in |
| http://127.0.0.1:8000/founder/login/ | **Your founder login** (email + password from `.env`) |
| http://127.0.0.1:8000/aethrix-team-5180/login/ | Admin dashboard login (for admins you create on the Team page) |
| http://127.0.0.1:8000/admin/ | Backup admin |

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
> In VS Code press **Ctrl+Shift+P → Python: Select Interpreter → .venv**. Then **F5** starts the site.

**Updating from the earlier version?** Just run `python manage.py migrate` again. Your existing orders and projects stay, and the Floodlit and Banglish (BE) demo projects are added.

Locally, emails (new-order alerts, updates, password links) are **printed in the terminal** instead of sent. Copy links from there while testing.

---

## 2. How an order flows

1. A client clicks **Sign up** on the website and enters full name, email, phone number and password.
2. In their dashboard they click **New order**, type the **project name** and **project details**, pick the service, budget and timeline, and press **Place order**.
3. The order is saved in the database. You and every active admin get an email, and it appears under **Orders → Incoming** in both dashboards.
4. You or an admin open it, change the status (Contacted → Call confirmed → In progress → Completed), move the progress slider, set price and due date, and tick **Email the client**. The client sees every change in their dashboard.
5. When it's **Completed**, add the delivery link. It moves to the client's Completed tab with a "live project" button.

## 3. The founder dashboard (only you)

Log in at **/founder/login/** (or your secret `FOUNDER_URL`).

- **Overview:** 3D chart of orders for the last 6 months, incoming, pending and completed counts, earnings and open pipeline in taka, latest orders and client messages.
- **Orders:** tabs **All / Incoming / Pending / Completed / Declined**, search, CSV download. Open an order to update it and message the client.
- **Clients:** every client with phone number and order counts. **View dashboard** shows that client's dashboard exactly as they see it.
- **Team (admins):** create admin accounts (name, email, phone, password) and copy the admin dashboard link to send them. Click **Manage** on any admin to edit their details, give them a new password, block or unblock them, or remove them.
- **Demo projects:** add, edit, hide and delete projects. Each one has a details page on the website with description, features, roadmap and closing text. Write one feature per line; `Name — text` makes the name bold.
- **Admin dashboard ↗** (bottom of the menu): open the admin dashboard yourself.
- **Account:** change your password and see your private addresses.

## 4. The admin dashboard (your team)

Admins log in at **/aethrix-team-5180/login/** (change it with the `ADMIN_PANEL_URL` setting) with the email and password you set on the Team page. They see **Overview**, **Orders** and **Account**: they receive orders, update them, notify clients and send messages. They can't see money totals, the client list, demo projects or the Team page.

## 5. The client dashboard

- **New order:** project name, service, project details, budget, timeline. Their name, email and phone are added from their account.
- **My orders:** a 3D build where blocks drop into place up to the project's progress, a stage tracker (Received → Call → Building → Delivered), Active and Completed tabs, price, due date and the live link when delivered.
- **Messages** with the team on each order, and an **Account** page to change their details and password.

---

## 6. Where the database is

- **On your laptop:** the file `db.sqlite3` in the project folder.
- **On Render:** a PostgreSQL database named `aethrix-db`, connected automatically.

Tables you'll care about: orders, order messages, demo projects, user accounts (clients, admins, founder) and profiles (phone numbers). You manage all of it from the dashboards.

---

## 7. Turn on real emails (Brevo)

Render's free plan blocks normal email (SMTP) ports, so the site sends email through Brevo's web API.

1. Create a free account at **brevo.com** with `projectaethrix@gmail.com`.
2. Add `projectaethrix@gmail.com` as a sender in Brevo and verify it from the email Brevo sends you.
3. Create an API key in Brevo and copy it.
4. Put it in `BREVO_API_KEY` (in `.env` locally, or in Render's Environment tab).

Until you do this, everything still works and is saved in the database, but no emails go out (new-order alerts, update emails, "forgot password" links).

Tip: emails sent "from" a Gmail address can land in spam. Once you own a domain, verify it in Brevo and change `DEFAULT_FROM_EMAIL` to something like `hello@projectaethrix.com`.

---

## 8. Put it online (GitHub + Render)

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
   - `ADMIN_PANEL_URL` (optional) → the admin dashboard address. Without it, it is `aethrix-team-5180/`
   - `ADMIN_URL` → another secret address, e.g. `aethrix-backup-4810/`
   - `FOUNDER_EMAIL` → `projectaethrix@gmail.com`
   - `FOUNDER_PASSWORD` → a long, strong password
   - `BREVO_API_KEY` → from step 5
3. Click **Apply**. When it says **Live**, your founder login is at `https://your-site/aethrix-hq-7392/login/` and the admin login at `https://your-site/aethrix-team-5180/login/`. Bookmark them.

Every `git push` redeploys the site. Changing `FOUNDER_PASSWORD` later does **not** change your password; use the Account page in the dashboard for that.

**Good to know about free plans**
- **The site sleeps:** a free Render website sleeps after about 15 minutes without visitors, and the next visit takes up to a minute.
- **The database is deleted after 30 days:** Render's free PostgreSQL is deleted 30 days after it's created. Before then, upgrade it, or create a free database at **neon.tech** and paste its connection string into `DATABASE_URL`. Orders and client accounts live there, so don't skip this.

---

## 9. Your own domain (optional)

1. Buy a domain and add it in Render → your web service → **Settings → Custom Domains**.
2. Set in Render's Environment tab:
   - `ALLOWED_HOSTS` → `projectaethrix.com,www.projectaethrix.com`
   - `CSRF_TRUSTED_ORIGINS` → `https://projectaethrix.com,https://www.projectaethrix.com`
   - `SITE_URL` → `https://projectaethrix.com`

---

## Where to change things

| To change | Edit |
|---|---|
| Home page text | `templates/home.html` (top bar: `templates/_site_nav.html`) |
| Demo project details page | `templates/project_detail.html` (content: founder dashboard → Demo projects) |
| Colours, fonts | `static/css/site.css` (tokens at the top: `--red`, `--bone`, …) |
| Dashboard look | `static/css/dash.css` |
| Home 3D (robot cube, particles) | `static/js/site.js` |
| Dashboard 3D (orders chart, block build, login cube) | `static/js/dash3d.js` |
| Founder + admin dashboard pages | `templates/founder/`, logic in `founder/views.py` |
| Client dashboard pages | `templates/portal/`, logic in `portal/views.py` |
| New order form fields | `portal/forms.py` |
| Login and sign-up pages | `templates/accounts/`, logic in `accounts/views.py` |
| Email wording | `studio/emails.py` and `templates/emails/` |

After changing anything in a `models.py`, run `python manage.py makemigrations` then `python manage.py migrate`.

---

## Project structure

```
aethrix-website/
├── config/      Settings and main URLs
├── studio/      Public site, demo project pages, orders, messages, emails
├── accounts/    Sign-up, log in, roles (client / admin / founder), password reset
├── portal/      Client dashboard + New order
├── founder/     Founder dashboard (urls.py) and admin dashboard (admin_urls.py)
├── templates/   Pages and emails
├── static/      CSS, JavaScript, three.js
├── build.sh     What Render runs on each deploy
└── render.yaml  Render Blueprint (website + database)
```

## Useful commands

```bash
python manage.py runserver        # start the site locally
python manage.py test             # run all 77 tests
python manage.py ensure_founder   # create the founder login from .env
python manage.py check --deploy   # security check before going live
```

## Troubleshooting

- **`SECRET_KEY is not set`:** you have no `.env` file. Copy `.env.example` to `.env`.
- **"Email or password is wrong" on founder login:** run `python manage.py ensure_founder` after setting `FOUNDER_EMAIL` and `FOUNDER_PASSWORD` in `.env`.
- **"Too many tries":** 8 wrong logins lock that connection for 15 minutes.
- **An admin sees "page not found":** they must use the admin login link (Team page), not the founder link. Check they aren't blocked.
- **Clients don't get emails:** check `BREVO_API_KEY` and that the sender is verified in Brevo. Locally, the links are in the terminal.
- **Live site shows "Bad Request (400)":** add your domain to `ALLOWED_HOSTS`.
- **"CSRF verification failed" on your domain:** add `https://yourdomain` to `CSRF_TRUSTED_ORIGINS`.
