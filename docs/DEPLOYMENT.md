# PlacementHub (Campus AI) - Render Production Deployment Guide

This guide provides step-by-step instructions for deploying **PlacementHub** to **Render** using the free tier (Python Web Service + Render Managed PostgreSQL).

---

## 📋 Architecture Overview

- **Web Server**: Gunicorn WSGI HTTP Server (`gunicorn placementhub_project.wsgi:application`)
- **Framework**: Django 5.2 (running on Python 3.11)
- **Database**: Render Managed PostgreSQL (`psycopg2-binary` + `dj-database-url`)
- **Static Assets**: WhiteNoise (`CompressedManifestStaticFilesStorage`)
- **Settings Module**: `placementhub_project.settings.prod`

---

## ⚠️ Important Limitation: Ephemeral Media Files on Render Free Tier

> [!WARNING]
> **Uploaded Resumes & Ephemeral Filesystem**:
> Render's free tier uses an **ephemeral disk**. Files uploaded at runtime (such as student resumes uploaded to `media/resumes/` or company logos in `media/company_logos/`) **will NOT persist across deploys, service restarts, or daily spin-downs**.
>
> - **For Academic Demo & Evaluation**: This is fully functional and acceptable. Uploaded resumes will parse in real-time, extract skills, and compute match scores immediately during an active evaluation session.
> - **For Commercial / Production Long-term Use**: Configure cloud object storage such as **AWS S3**, **Cloudflare R2**, or **Supabase Storage** using `django-storages`.

---

## 🚀 Option A: Automated Blueprint Deployment (`render.yaml`)

The repository includes a ready-to-use [`render.yaml`](../render.yaml) blueprint that automatically provisions both the PostgreSQL database and the Web Service.

1. Sign in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **Blueprints** in the top navigation.
3. Click **New Blueprint Instance**.
4. Connect your GitHub repository (`https://github.com/DeepakC637/Campus-AI`).
5. Render will automatically parse `render.yaml` and prompt you to create:
   - `placementhub-postgres` (PostgreSQL Database)
   - `placementhub` (Web Service)
6. Click **Apply**. Render will automatically provision the database and start the initial build.

---

## 🛠️ Option B: Manual Dashboard Deployment (Step-by-Step)

If you prefer setting up the services manually via the Render dashboard, follow these exact steps:

### Step 1: Create the Render PostgreSQL Database

1. In the Render Dashboard, click **New +** $\rightarrow$ **PostgreSQL**.
2. Configure the database instance:
   - **Name**: `placementhub-postgres`
   - **Database**: `placementhub`
   - **User**: `placementhub_user`
   - **Region**: Choose the region closest to you (e.g., `Oregon (US West)` or `Frankfurt (EU)`)
   - **PostgreSQL Version**: `16` (or default)
   - **Plan**: `Free`
3. Click **Create Database**.
4. Wait for status to show **Available**.
5. Scroll down to **Connections** and copy the **Internal Database URL** (e.g., `postgres://placementhub_user:password@dpg-...-a/placementhub`).

---

### Step 2: Create the Render Web Service

1. In the Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
2. Connect your GitHub repository: `DeepakC637/Campus-AI`.
3. Fill in the service configuration:
   - **Name**: `placementhub`
   - **Region**: Select the **same region** as your database.
   - **Branch**: `main`
   - **Root Directory**: *(leave blank — repository root)*
   - **Runtime**: `Python`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**:
     ```bash
     gunicorn placementhub_project.wsgi:application
     ```
   - **Plan**: `Free`

---

### Step 3: Configure Environment Variables

Scroll down to the **Environment Variables** section and add the following keys:

| Key | Value | Description |
| :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | `placementhub_project.settings.prod` | Activates production security and database settings |
| `SECRET_KEY` | *(Generate a random 50+ char string)* | Production Django cryptographic signing key |
| `ALLOWED_HOSTS` | `.onrender.com` | Allows your Render domain (e.g. `placementhub.onrender.com`) |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 1)* | Connects Django to Render PostgreSQL |
| `PYTHON_VERSION` | `3.11.9` | Ensures compatible Python runtime version |
| `WEB_CONCURRENCY` | `2` | Optimizes Gunicorn worker count for 512 MB RAM |

> [!TIP]
> You can generate a secure secret key locally with:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(50))"
> ```

4. Click **Create Web Service**.

---

### Step 4: First Build & Deployment

Render will pull your code, install all dependencies from `requirements.txt`, run `collectstatic`, and execute database migrations.

Monitor the **Logs** tab in Render. Look for:
```text
==> Generating container image from build. This may take a few minutes...
==> Uploading build...
==> Build successful 🎉
==> Deploying...
==> Starting service with 'gunicorn placementhub_project.wsgi:application'
[INFO] Starting gunicorn 27.0.1
[INFO] Listening at: http://0.0.0.0:10000
==> Your service is live 🚀
```

---

## 📦 Step 5: Post-Deployment Data Initialization

Once the service is live, seed the initial skills taxonomy and demo data into the production PostgreSQL database.

1. In your Render Web Service dashboard, click **Shell** in the left menu.
2. In the interactive terminal, run the following commands:

### 1. Seed Common Skill Taxonomy
```bash
python manage.py seed_skills
```
*Populates 60 standardized technical skills (Python, React, AWS, Docker, PostgreSQL, etc.) into the database.*

### 2. Seed Realistic Placement Data (Optional, Recommended for Demo)
```bash
python manage.py seed_real_data
```
*Seeds top tech companies (Google Cloud, Microsoft, AWS, Razorpay, CRED), active job postings, verified student profiles, real AI compatibility scores, and scheduled interviews.*

### 3. Create Superuser (Admin) Account
```bash
python manage.py createsuperuser
```
Follow the interactive prompts to set your admin email and password.

---

## 🔒 Production Security Verification

The production settings (`placementhub_project/settings/prod.py`) enforce the following security controls:

- `DEBUG = False` (Prevents leaking stack traces or sensitive environment variables)
- `SECURE_SSL_REDIRECT = True` (Forces all traffic to HTTPS)
- `SESSION_COOKIE_SECURE = True` (Session cookies transmitted only over HTTPS)
- `CSRF_COOKIE_SECURE = True` (CSRF tokens transmitted only over HTTPS)
- `CSRF_TRUSTED_ORIGINS` (Automatically configured for `https://*.onrender.com`)
- `X_FRAME_OPTIONS = 'DENY'` (Guards against Clickjacking attacks)
- `SECURE_CONTENT_TYPE_NOSNIFF = True` (Prevents MIME-type sniffing)
- `WhiteNoise` compression & cache-busting manifest enabled.

---

## 🔍 Troubleshooting

### 1. `DisallowedHost` Error (HTTP 400)
- **Cause**: The incoming host header does not match `ALLOWED_HOSTS`.
- **Fix**: In your Render Web Service Environment Variables, verify that `ALLOWED_HOSTS` includes `.onrender.com` or your exact domain (e.g. `placementhub.onrender.com`).

### 2. Static Files Not Loading (CSS/JS 404s)
- **Cause**: `collectstatic` failed during build.
- **Fix**: Check the build logs to confirm `python manage.py collectstatic --noinput` ran successfully and WhiteNoise is active in `MIDDLEWARE`.

### 3. Out of Memory (OOM) Errors on Free Tier
- **Cause**: Gunicorn spawned too many workers exceeding Render's 512 MB free tier memory.
- **Fix**: Ensure `WEB_CONCURRENCY=2` is set in environment variables.

### 4. Database Connection Refused
- **Cause**: Using the External Database URL instead of the Internal Database URL.
- **Fix**: Within Render, services communicating with Render Postgres should use the **Internal Database URL** for lower latency and zero egress cost.
