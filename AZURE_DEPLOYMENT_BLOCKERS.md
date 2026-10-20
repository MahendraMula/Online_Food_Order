# OFO-DBMS — Azure Deployment Blockers & Remediation Plan

**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect & Security Auditor  
**Scope:** Actionable register of deployment defects, architectural limitations, and missing cloud settings required before Azure App Service production deployment.

---

## 1. Summary of Identified Deployment Blockers

| Blocker ID | Category | Severity | Description | Impact on Azure |
|---|---|---|---|---|
| **BLK-01** | CI/CD & Assets | **HIGH** | `images/` directory excluded by `.gitignore:42` | Deployed site in Azure will have no dish or restaurant photos (HTTP 404). |
| **BLK-02** | Security & Networking | **HIGH** | Missing `SECURE_PROXY_SSL_HEADER` in `settings.py` | Azure SSL termination proxy will trigger an infinite 301 redirect loop (`ERR_TOO_MANY_REDIRECTS`). |
| **BLK-03** | Security & CSRF | **HIGH** | Missing `CSRF_TRUSTED_ORIGINS` in `settings.py` | All HTTPS POST requests on `*.azurewebsites.net` (login, cart, checkout) fail with HTTP 403. |
| **BLK-04** | Database & Persistence | **MEDIUM** | Hardcoded database paths to `BASE_DIR` | Deploying new zip archives can overwrite or reset SQLite databases in `wwwroot`. |
| **BLK-05** | Cloud Architecture | **CRITICAL CONSTRAINT** | Multi-instance SQLite file-locking limitation | Scale Out > 1 causes database lock crashes and data corruption. App Service must be pinned to 1 instance. |
| **BLK-06** | Cloud Provisioning | **PREREQUISITE** | Missing Azure App Settings & GitHub Secrets | GitHub Actions cannot deploy without `AZURE_WEBAPP_PUBLISH_PROFILE`. |

---

## 2. Detailed Technical Breakdown & Proposed Diffs

### BLK-01: Dish Imagery Excluded by `.gitignore`
- **Root Cause:** Line 42 of `.gitignore` contains `/images/`. Git check-ignore confirms `images/menu/bacon_cheeseburger.jpg` and all 20 catalog images are ignored.
- **Azure Impact:** When GitHub Actions checks out code, `images/` is omitted. The generated `release.zip` contains no dish images.
- **Proposed Safe Fix:** Update `.gitignore` to track static catalog images while continuing to ignore temporary or generated files:
  ```gitignore
  # --- Media / User Uploads ---
  /images/*
  !/images/menu/
  !/images/restaurants/
  !/images/categories/
  /media/
  ```
  Then track the catalog images with `git add images/`.

---

### BLK-02: Missing `SECURE_PROXY_SSL_HEADER` (Infinite Redirect Loop)
- **Root Cause:** In `dbms_project/settings.py:96`, `SECURE_SSL_REDIRECT = True` is active when `DEBUG=False`. Azure App Service terminates SSL at its front-end load balancer and forwards plain HTTP to Gunicorn on port 8000 with header `X-Forwarded-Proto: https`.
- **Azure Impact:** Django checks `request.is_secure()`. Since Gunicorn receives plain HTTP, Django believes the connection is insecure and issues a `301 Moved Permanently` to `https://...`. The browser loops endlessly (`ERR_TOO_MANY_REDIRECTS`).
- **Proposed Safe Fix:** Add `SECURE_PROXY_SSL_HEADER` to `dbms_project/settings.py`:
  ```python
  # Inform Django to trust Azure App Service reverse proxy SSL termination
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  ```

---

### BLK-03: Missing `CSRF_TRUSTED_ORIGINS` (HTTP 403 Forbidden)
- **Root Cause:** Django 4.0+ enforces that for HTTPS POST requests, the request's `Origin` or `Referer` must match an entry in `CSRF_TRUSTED_ORIGINS`. `settings.py` does not configure this variable.
- **Azure Impact:** When customers submit registration, login, add-to-cart, or checkout forms on `https://<your-app>.azurewebsites.net`, Django rejects the request with `403 Forbidden: CSRF verification failed`.
- **Proposed Safe Fix:** In `dbms_project/settings.py`, parse `CSRF_TRUSTED_ORIGINS` from environment variables with intelligent fallback for Azure:
  ```python
  raw_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
  if raw_csrf_origins:
      CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_csrf_origins.split(',') if o.strip()]
  else:
      CSRF_TRUSTED_ORIGINS = [
          f"https://{h}" for h in ALLOWED_HOSTS if h not in ('*', '127.0.0.1', 'localhost', 'testserver')
      ]
  ```

---

### BLK-04: Database Path Decoupling (`OFO_DATA_DIR`)
- **Root Cause:** `settings.py:65,69` hardcodes `BASE_DIR / 'food_ordering.db'`. In Azure App Service, `BASE_DIR` is `/home/site/wwwroot`. During a new zip deployment, Azure extracts files into this directory. If SQLite databases reside directly in the deployment directory, there is a risk of data loss on destructive redeployments.
- **Azure Impact:** Existing database records could be overwritten or reset during fresh code releases.
- **Proposed Safe Fix:** Make the database directory configurable via `OFO_DATA_DIR` with an automatic directory creation guard:
  ```python
  DATA_DIR = Path(os.environ.get('OFO_DATA_DIR', BASE_DIR))
  DATA_DIR.mkdir(parents=True, exist_ok=True)

  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': DATA_DIR / 'food_ordering.db',
      },
      'django_database': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': DATA_DIR / 'django_database.db',
      }
  }
  ```
  On Azure App Service, set `OFO_DATA_DIR = /home/data` (a persistent directory outside the ephemeral code deployment root).

---

### BLK-05: Multi-Instance SQLite Concurrency & Scaling Constraint
- **Architectural Analysis:**
  - SQLite uses POSIX advisory file locks. Azure App Service `/home` is backed by CIFS/SMB storage. Over network storage, POSIX locks are unreliable and prone to deadlocks.
  - If the App Service Plan scales to $\ge 2$ instances, multiple instances writing to the same SQLite file will trigger `sqlite3.OperationalError: database is locked` or data corruption.
- **Mandatory Operational Rule:**
  - The App Service Plan must be configured with **Scale Out = 1 instance** and **Always On = Enabled**.
  - Horizontal scaling is strictly prohibited with SQLite. If scaling out is required in the future, migrate to Azure Database for PostgreSQL Flexible Server as scheduled in Roadmap Phase 3D.

---

### BLK-06: Azure Cloud & GitHub Secrets Pre-Requisites
Before triggering an automated deployment via `.github/workflows/deploy-azure.yml`, the following external credentials must be established:

1. **GitHub Repository Secrets & Variables:**
   - Secret: `AZURE_WEBAPP_PUBLISH_PROFILE` (Exported XML publish profile from Azure Portal > Web App > Get publish profile).
   - Variable: `AZURE_WEBAPP_NAME` (e.g., `ofo-dbms-app`).
2. **Azure App Service Application Settings:**
   - `DJANGO_SECRET_KEY`: Long, random 50+ character string.
   - `DJANGO_DEBUG`: `False`
   - `DJANGO_ALLOWED_HOSTS`: `<your-app-name>.azurewebsites.net`
   - `DJANGO_CSRF_TRUSTED_ORIGINS`: `https://<your-app-name>.azurewebsites.net`
   - `OFO_DATA_DIR`: `/home/data`
   - `WEBSITES_PORT`: `8000`
