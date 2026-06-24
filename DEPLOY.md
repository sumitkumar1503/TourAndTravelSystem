# Deploying TravelBot to PythonAnywhere

A step-by-step guide to host your Django project on
**PythonAnywhere** (free tier works). After completing these steps your
project will be live at:

```
https://<your-username>.pythonanywhere.com
```

---

## 1. Create a PythonAnywhere account

1. Go to <https://www.pythonanywhere.com>
2. Sign up for a **Beginner (free) account**.
3. After signup, you'll land on the dashboard.

> Free tier gives you: 1 web app, 512 MB storage, SQLite, custom subdomain
> `username.pythonanywhere.com`. That is enough for this project.

---

## 2. Open a Bash console

1. From the dashboard, click the **Consoles** tab.
2. Click **Bash** under "Start a new console".

You should now see a Linux shell.

---

## 3. Clone the GitHub repository

In the bash console:

```bash
cd ~
git clone https://github.com/sumitkumar1503/TourAndTravelSystem.git
cd TourAndTravelSystem
```

Verify the files are there:

```bash
ls
# manage.py  accounts  booking  chatbot  dashboard  templates  static  reports …
```

---

## 4. Create a virtual environment

PythonAnywhere supports Python 3.10. Create a fresh venv:

```bash
mkvirtualenv --python=/usr/bin/python3.10 travelbot
```

This activates the new venv automatically (`(travelbot)` appears in
your prompt). To activate it later: `workon travelbot`.

---

## 5. Install dependencies

```bash
cd ~/TourAndTravelSystem
pip install -r requirements.txt
```

Wait for installation to finish (~2 minutes).

---

## 6. Configure Django settings for production

Open `travel_chatbot/settings.py` in the **Files** tab of PythonAnywhere
(or use `nano` in the console) and change these lines:

```python
DEBUG = False
ALLOWED_HOSTS = ['<your-username>.pythonanywhere.com']
```

Replace `<your-username>` with your PythonAnywhere username (e.g. `sumitkumar1503`).

The rest of the settings (database, static files, etc.) are already
production-ready.

---

## 7. Run migrations and seed data

Back in the bash console:

```bash
cd ~/TourAndTravelSystem
python manage.py migrate
python manage.py seed_data
python manage.py collectstatic --noinput
```

The last command gathers all CSS/JS into a `staticfiles/` folder that
the web server will serve directly.

---

## 8. Configure the Web app

1. Click the **Web** tab in the top menu.
2. Click **Add a new web app**.
3. Click **Next** (your domain will be your username's subdomain).
4. Choose **Manual configuration** (NOT the Django option — we have our
   own project layout).
5. Choose **Python 3.10**.
6. Click **Next** to create the app.

You'll now see the Web app configuration page.

---

## 9. Set virtualenv & source code paths

On the Web tab, fill these fields:

| Field              | Value                                                  |
|--------------------|--------------------------------------------------------|
| **Source code**    | `/home/<your-username>/TourAndTravelSystem`            |
| **Working dir.**   | `/home/<your-username>/TourAndTravelSystem`            |
| **Virtualenv**     | `/home/<your-username>/.virtualenvs/travelbot`       |

---

## 10. Edit the WSGI file

On the same Web tab, scroll to **Code → WSGI configuration file** and
click the link. It opens an editor with default content. Replace it
entirely with:

```python
import os
import sys

# Path to your project root
project_home = '/home/<your-username>/TourAndTravelSystem'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'travel_chatbot.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace `<your-username>` with your actual username. **Save** the file.

---

## 11. Map static and media files

On the Web tab, scroll down to **Static files**. Add two rows:

| URL        | Directory                                                          |
|------------|--------------------------------------------------------------------|
| `/static/` | `/home/<your-username>/TourAndTravelSystem/staticfiles`            |
| `/media/`  | `/home/<your-username>/TourAndTravelSystem/media`                  |

---

## 12. Reload and visit your site

Click the big green **Reload** button at the top of the Web tab.

Then visit: `https://<your-username>.pythonanywhere.com`

You should see TravelBot live!

---

## 13. Demo accounts (created by `seed_data`)

| Role  | Username | Password    |
|-------|----------|-------------|
| Admin | `admin`  | `admin123`  |
| User  | `demo`   | `demo12345` |

> Login as `admin` to access the admin dashboard at `/dashboard/`.

---

## Troubleshooting

### "DisallowedHost" error
You forgot to add your domain to `ALLOWED_HOSTS` in `settings.py`. Edit
the file and reload the web app.

### CSS / JS missing
You didn't run `python manage.py collectstatic`, or the static-file
mapping in Step 11 is wrong. Re-run collectstatic, double-check the
paths, then reload.

### Server error 500
Check the error log: Web tab → **Log files → Error log**. The most
common reason is a missing dependency (run `pip install -r requirements.txt`
again in the venv) or a typo in the WSGI file.

### Updating after a code change

```bash
workon travelbot
cd ~/TourAndTravelSystem
git pull
pip install -r requirements.txt              # if dependencies changed
python manage.py migrate                     # if models changed
python manage.py collectstatic --noinput     # if static files changed
```

Then click **Reload** on the Web tab.

---

## Performance tips (optional)

- **Disable the chatbot's NLTK auto-downloads in production.** PythonAnywhere
  free tier has restricted outbound internet. The chatbot already
  gracefully degrades to regex parsing if NLTK data isn't available.
- **Use WhiteNoise** for static-file compression (already standard in
  Django; not strictly needed because PythonAnywhere serves static
  files natively via the mapping in Step 11).
- For more traffic, upgrade to a paid plan (£5/month) for more CPU
  seconds and a custom domain.
