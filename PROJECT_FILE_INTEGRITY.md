# OFO-DBMS — Project File Integrity & Dependency Audit

**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect & Backend Security Engineer  
**Scope:** Static Analysis, AST Validation, Import Graph Inspection, Template Syntax & Link Validation, Model & Database Relationship Verification.

---

## 1. System Architecture & Dependency Graph

```mermaid
graph TD
    subgraph Browser ["Frontend Client (Bootstrap 5.3 + Dark Theme + CDN)"]
        UI_Home["Storefront (index.html)"]
        UI_Cart["Cart (cart.html)"]
        UI_Checkout["Checkout (checkout.html)"]
        UI_History["Order Tracking (orders.html)"]
        UI_Admin["Operations Console (dashboard.html)"]
        UI_Invoice["Tax Invoice (receipt.html)"]
    end

    subgraph DjangoApps ["Django Core Applications"]
        accounts["accounts app (Auth, Profile, Forms)"]
        restaurants["restaurants app (Storefront, Menu, Reviews)"]
        orders["orders app (Cart, Checkout, Pricing Services, Dashboard)"]
        dbms_project["dbms_project (Settings, Root URLs, DB Router)"]
    end

    subgraph Services ["Authoritative Backend Services"]
        CartEngine["orders.cart.Cart"]
        DeliveryEngine["orders.services.calculate_delivery_fee"]
        TaxEngine["orders.services.calculate_tax"]
        CouponEngine["orders.models.Coupon (select_for_update)"]
    end

    subgraph Router ["DjangoFrameworkRouter (dbms_project/db_routers.py)"]
        RouteLogic{"app_label in {auth, contenttypes, sessions, admin}?"}
    end

    subgraph Databases ["Dual SQLite Relational Storage"]
        DB_Framework[("django_database.db\nauth_user, sessions, admin_log")]
        DB_Domain[("food_ordering.db\nrestaurants, menu, orders, payments, deliveries")]
    end

    Browser -->|HTTP Requests| dbms_project
    dbms_project --> accounts
    dbms_project --> restaurants
    dbms_project --> orders

    orders --> CartEngine
    orders --> DeliveryEngine
    orders --> TaxEngine
    orders --> CouponEngine

    accounts --> RouteLogic
    restaurants --> RouteLogic
    orders --> RouteLogic

    RouteLogic -->|Yes| DB_Framework
    RouteLogic -->|No (Domain)| DB_Domain
```

---

## 2. Integrity Verification Findings Table

| Finding ID | Source File | Referenced Target | Problem Description | Severity | Verifiable Evidence | Recommended Fix |
|---|---|---|---|---|---|---|
| **INT-01** | `dbms_project/settings.py` | `food_ordering.db`, `django_database.db` | Dual database SQLite files cannot enforce cross-database Foreign Key constraints at SQL engine level | **Medium** | `accounts/models.py:5`, `orders/models.py:107`, `restaurants/models.py:42` specify `db_constraint=False` and `on_delete=DO_NOTHING`. Cross-table SQL `JOIN` fails if attempted. | Maintain current defensive code design: always use `prefetch_related('customer')` rather than `select_related('customer')`. In Phase 3D, migrate to a single PostgreSQL database with schemas. |
| **INT-02** | Root Directory | `db.sqlite3` | Orphaned, 0-byte database file in project root. Ignored by active `DATABASES` configuration. | **Low** | File size is 0 bytes; active databases are `food_ordering.db` (237 KB) and `django_database.db` (131 KB). | Delete or archive `db.sqlite3` to prevent developer confusion during manual database inspections. |
| **INT-03** | `requirements.txt` | Production Server & Static Handler | Missing WSGI server (`gunicorn`/`uvicorn`) and static file engine (`whitenoise`) required for Azure cloud deployment | **High** | `requirements.txt` only lists `django` and `Pillow`. `settings.py` disables static file serving when `DEBUG=False`. | Add `gunicorn>=22.0.0` and `whitenoise>=6.6.0` to `requirements.txt`. Configure WhiteNoise middleware in `MIDDLEWARE`. |
| **INT-04** | `static/` | Static Asset Directory | `static/` directory is completely empty; frontend relies 100% on external CDNs (Bootstrap, Icons, Fonts) | **Low** | `Get-ChildItem -Force static` returns 0 items. `base.html` loads all assets from `cdn.jsdelivr.net`. | Vendorize critical CSS/JS locally into `static/` for offline resilience, intranet compatibility, and deterministic loading times. |
| **INT-05** | `dbms_project/settings.py` | Environment Variables | `SECRET_KEY` falls back to hardcoded insecure development key if `DJANGO_SECRET_KEY` is unset | **Medium** | `settings.py:7`: fallback string `'django-insecure-ofo-dbms-strong-development-fallback-key-2026-production-ready'`. | When `DEBUG=False`, raise a `django.core.exceptions.ImproperlyConfigured` exception if `DJANGO_SECRET_KEY` is not explicitly set in production. |
| **INT-06** | `orders/services.py` | External Geocoding / Routing API | Distance calculation uses deterministic address parsing tags (`[dist: Xkm]`) rather than live GPS / Maps API | **Low** (Documented) | `orders/services.py:59`: `re.search(r'\[(?:distance|dist):\s*([\d\.]+)km\]', delivery_address)`. No live map routing provider connected. | Decoupled architecture is already in place. In Phase 3B, connect Google Maps Distance Matrix API or Leaflet/OSRM to feed `distance_km` dynamically. |
| **INT-07** | `orders/views.py` | Payment Gateways | Non-COD orders automatically set `Payment.payment_status = 'Paid'` without third-party gateway verification | **Low** (Documented) | `orders/views.py:401`: `payment_status='Paid' if payment_mode != 'COD' else 'Pending'`. No webhook or gateway integration. | In Phase 2A, integrate Razorpay or Stripe checkout with signature verification and webhook handlers. |
| **INT-08** | Project Root | Azure Deployment Configs | No `Dockerfile`, Azure App Service deployment workflow, or container spec exists | **Medium** | Workspace search for `*docker*`, `*azure*`, `*deploy*` reveals 0 configuration files. | Add `Dockerfile`, `.dockerignore`, and an Azure deployment GitHub Actions workflow (`deploy-azure.yml`). |

---

## 3. Subsystem-by-Subsystem Integrity Analysis

### A. Python Module Imports & AST
- **Evaluation:** Inspected all 18 Python source files in `dbms_project/`, `accounts/`, `restaurants/`, and `orders/`.
- **Integrity Status:** **VERIFIED (0 errors)**.
- **Findings:**
  - All internal module imports (`from .models import ...`, `from .cart import ...`, `from .services import ...`) resolve to existing classes and functions.
  - Zero circular import loops detected.
  - Installed app configurations (`accounts.apps.AccountsConfig`, `restaurants.apps.RestaurantsConfig`, `orders.apps.OrdersConfig`) properly declared in `settings.INSTALLED_APPS`.

---

### B. Django URL Routing & Reverse Resolution
- **Evaluation:** Analyzed root URL dispatcher (`dbms_project/urls.py`) and application URL configurations (`accounts/urls.py`, `restaurants/urls.py`, `orders/urls.py`).
- **Integrity Status:** **VERIFIED (0 errors)**.
- **Registered Route Count:** 92 total named routes (including Django Admin and Auth defaults).
- **Reverse Lookup Verification:**
  - Every URL referenced across all HTML templates was parsed via Django's URL resolver.
  - **Result:** **0 broken `{% url %}` references**. All views resolve cleanly with exact matching parameters (e.g. `add_to_cart item.id`, `order_receipt order.id`).

---

### C. Template System & Presentation Tier
- **Templates Audited (10):**
  1. `base.html` (Master layout, responsive navbar, flash message alerts, restaurant conflict modal, dark theme styling)
  2. `index.html` (Storefront, multi-filter chips, dish grid, category carousel)
  3. `cart.html` (Session cart, line item table, coupon input, financial subtotal/tax/delivery breakdown)
  4. `checkout.html` (Consolidated review, delivery address, phone input, payment mode selection, atomic place order form)
  5. `orders.html` (Customer order history, 4-step progress tracker, driver contact badge, cancel trigger)
  6. `dashboard.html` (Restaurant operations console, live kitchen queue, KPI metric cards, driver assignment, menu stock toggles)
  7. `receipt.html` (Printable tax invoice, GST itemization, discount details, payment status)
  8. `login.html` (Customer/staff session authentication form)
  9. `signup.html` (Registration form with phone and address validation)
  10. `profile.html` (Customer profile view, order statistics, address updater)
- **Integrity Status:** **VERIFIED (0 errors)**.
- **Findings:**
  - All `{% extends 'base.html' %}` tags resolve cleanly.
  - Zero missing `{% include %}` references.
  - All CSRF tokens (`{% csrf_token %}`) are present on every mutating form (cart, checkout, status, login, signup, reviews).

---

### D. Static Assets & Media Management
- **Static Assets:**
  - The local `static/` folder is empty.
  - All styles and fonts are currently loaded via CDN (`Bootstrap 5.3.3`, `Bootstrap Icons 1.11.3`, `Google Fonts Plus Jakarta Sans`).
  - Dark theme variables and custom UI card styles are defined inline within `templates/base.html` `<style>` blocks.
- **Media Assets:**
  - Local disk directory `images/` contains 15 dish images in `images/menu/` and 5 restaurant banner images in `images/restaurants/`.
  - Configured in `settings.py`: `MEDIA_URL = '/images/'`, `MEDIA_ROOT = os.path.join(BASE_DIR, 'images')`.
  - In development (`DEBUG=True`), served via `django.conf.urls.static.static()`.
  - **Azure Production Warning:** In production (`DEBUG=False`), Django does not serve media or static files natively. Integration with WhiteNoise or Azure Blob Storage (`django-storages[azure]`) is mandatory prior to deployment.

---

### E. Relational Schema & Dual-Database Router
- **Router:** `dbms_project.db_routers.DjangoFrameworkRouter`.
- **Routing Rules:**
  - `route_app_labels = {'auth', 'contenttypes', 'sessions', 'admin'}` ➔ Routed exclusively to `django_database.db`.
  - All other application models (`accounts`, `restaurants`, `orders`) ➔ Routed to `food_ordering.db` (`default`).
- **Physical Table Alignment:**
  - `food_ordering.db` (13 tables): Contains only domain tables (`accounts_customerprofile`, `restaurants_*`, `orders_*`).
  - `django_database.db` (11 tables): Contains only framework tables (`auth_user`, `django_session`, `django_admin_log`, `django_content_type`, `auth_*`).
- **Cross-Database Foreign Keys:**
  - SQLite cannot enforce cross-file foreign key constraints.
  - Handled safely across models: `CustomerProfile.user`, `Review.customer`, and `Order.customer` declare `db_constraint=False` and `on_delete=models.DO_NOTHING`.
  - Queryset integrity: Views strictly utilize `prefetch_related('customer')` instead of `select_related('customer')` to avoid cross-database SQL `JOIN` failure.

---

### F. Migration Consistency
- **Evaluation:** Inspected migration trees across `accounts` (3), `restaurants` (5), `orders` (9), and Django internal apps.
- **Integrity Status:** **VERIFIED (0 errors)**.
- `makemigrations --check --dry-run` reports **"No changes detected"**. All model fields match physical tables.
