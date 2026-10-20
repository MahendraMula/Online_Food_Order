# OFO-DBMS — Project Phase Status Matrix & Verification Report

**Date:** October 20, 2026  
**Auditor:** Senior Software Architect, QA & Security Auditor  
**Scope:** Phase-by-phase implementation verification against source code, runtime tests, database contents, and Git history.

---

## 1. Executive Summary & Phase Status Summary

| Phase | Phase Name & Scope | Established Status | Tests Passed | Completion % | Blocking Issues |
|---|---|---|---|---|---|
| **Phase 1** | **Foundation & Dual-Database Relational Schema** | **COMPLETE AND VERIFIED** | 20 / 20 | 100% | None |
| **Phase 2** | **Core Commerce, Ordering & Phase 1 Essentials** | **COMPLETE AND VERIFIED** | 43 / 43 | 100% (Prototype Scope) | None for local prototype; payments simulated |
| **Phase 3** | **Testing, Security & Transaction Stabilization** | **COMPLETE AND VERIFIED** | 63 / 63 | 100% | None |
| **Phase 4** | **Cloud Deployment & Azure Operations** | **PENDING** | 0 / 0 | 15% (Settings scaffolded) | Missing Gunicorn, WhiteNoise, Dockerfile, Azure configs |
| **Roadmap Phase 2** | **Live Payment Gateways & Automated Notifications** | **PENDING** | N/A | 0% (Planned Roadmap) | Awaiting Razorpay/Stripe & Twilio/SMTP integration |
| **Roadmap Phase 3** | **WebSockets, Live GPS Mapping & Mobile REST API** | **PENDING** | N/A | 0% (Planned Roadmap) | Awaiting Django Channels, Leaflet/Maps, DRF |

---

## 2. Phase 1 — Foundation and Database Design

### Status: **COMPLETE AND VERIFIED**

#### A. Scope & Objectives
Establish project workspace, modular Django structure (`accounts`, `restaurants`, `orders`, `dbms_project`), dual-database architecture (`food_ordering.db` + `django_database.db`), custom framework router (`DjangoFrameworkRouter`), database seeder, and core relational entity schema.

#### B. Feature-by-Feature Verification Table

| Feature / Component | Status | Verified Evidence | Notes |
|---|---|---|---|
| **Django Application Structure** | COMPLETE AND VERIFIED | `settings.INSTALLED_APPS` lines 18-22 | `accounts`, `restaurants`, `orders`, `dbms_project` modularly registered. |
| **Dual-Database Configuration** | COMPLETE AND VERIFIED | `settings.py:56-65`, physical files on disk | `food_ordering.db` (237 KB) and `django_database.db` (131 KB) configured. |
| **Database Router** | COMPLETE AND VERIFIED | `dbms_project/db_routers.py` lines 1-39 | `DjangoFrameworkRouter` routes auth/sessions/admin to `django_database` and domain models to `default`. |
| **Relational Domain Models** | COMPLETE AND VERIFIED | `restaurants/models.py`, `orders/models.py`, `accounts/models.py` | 10 models: `CustomerProfile`, `Category`, `Restaurant`, `MenuItem`, `Review`, `Order`, `OrderItem`, `Payment`, `DeliveryPartner`, `Delivery`. |
| **Cross-Database Foreign Keys** | COMPLETE AND VERIFIED | `models.py: db_constraint=False`, `on_delete=DO_NOTHING` | Defensive schema prevents SQLite cross-file constraint crashes. Views use `prefetch_related()`. |
| **Migration Consistency** | COMPLETE AND VERIFIED | `manage.py showmigrations`, `makemigrations --check --dry-run` | Zero unapplied migrations; zero model schema drift. |
| **Database Seeder** | COMPLETE AND VERIFIED | `restaurants/management/commands/seed_db.py` | Seeds 6 categories, 5 restaurants, 15 dishes, 3 drivers, sample orders, reviews, and 3 demo customers. |

#### C. Outstanding Requirements / Risks
- Unused 0-byte `db.sqlite3` file in workspace root (minor cleanup item).
- Multi-user concurrency limitations of SQLite in high-traffic production (Phase 3D roadmap item).

---

## 3. Phase 2 — Core Application Implementation & Commercial Essentials

### Status: **COMPLETE AND VERIFIED** (Prototype Scope)

#### A. Scope & Objectives
Implement end-to-end customer and administrative journeys: user registration and profile management, menu discovery and multi-parameter filtering, session shopping cart, single-restaurant cart validation, coupon discount engine, dynamic delivery charge calculation, 5% GST computation, atomic order checkout, live order tracking, customer reviews, and kitchen operations console.

#### B. Feature-by-Feature Verification Table

| Feature / Component | Status | Verified Evidence | Notes |
|---|---|---|---|
| **User Registration & Profile** | COMPLETE AND VERIFIED | `accounts/views.py:13-30`, `accounts/forms.py` | Validates regex phone, minimum address length; creates User + CustomerProfile. |
| **Storefront & Menu Discovery** | COMPLETE AND VERIFIED | `restaurants/views.py:9-74`, `templates/index.html` | Keyword search (`q`), category chips, pure veg toggle (`veg=1`), 4-way sorting. |
| **Session Shopping Cart** | COMPLETE AND VERIFIED | `orders/cart.py`, `templates/cart.html` | Persistent session cart; add, update quantity, remove, clear, live navbar badge. |
| **Single-Restaurant Cart Validation** | COMPLETE AND VERIFIED | `orders/cart.py:74-82`, `orders/views.py:37-77` | Intercepts dishes from different restaurants, renders conflict modal to keep or clear cart. |
| **Coupon & Discount Engine** | COMPLETE AND VERIFIED | `orders/models.py:Coupon`, `orders/views.py:162-205` | Percentage and Flat discounts; validates active status, validity window, min order value, max uses; locked via `select_for_update()`. |
| **Dynamic Delivery Charges** | COMPLETE AND VERIFIED | `orders/services.py:calculate_delivery_fee()` | Free delivery above $50.00; base fee $4.00; $1.00/km excess surcharge beyond 5 km (parsed via address tag `[dist: Xkm]`). |
| **GST / Tax Calculation** | COMPLETE AND VERIFIED | `orders/services.py:calculate_tax()` | 5% GST on net food subtotal with `ROUND_HALF_UP` Decimal rounding precision. |
| **Atomic Order Placement** | COMPLETE AND VERIFIED | `orders/views.py:place_order_view()`, `transaction.atomic` | Creates Order, OrderItems, Payment, and Delivery atomically. |
| **Order History & Progress Tracking** | COMPLETE AND VERIFIED | `orders/views.py:421-430`, `templates/orders.html` | 4-stage visual tracker: Placed → Preparing → Out for Delivery → Delivered. |
| **Customer Review & Ratings** | COMPLETE AND VERIFIED | `restaurants/views.py:76-119` | 1–5 star rating submission, auto-updates `Restaurant.rating` average. |
| **Operations Dashboard** | COMPLETE AND VERIFIED | `orders/views.py:490-559`, `templates/dashboard.html` | Staff-only console (`is_staff` guarded): KPI cards, live order queue, driver assignment, stock toggles. |
| **Printable Tax Invoices** | COMPLETE AND VERIFIED | `orders/views.py:651-682`, `templates/receipt.html` | Itemized invoice detailing dishes, coupon discount, delivery fee, GST, and total. |

#### C. Documented Scope Limitations (Prototype vs. Full Production)
1. **Payment Gateways:** Credit Card and UPI payments are currently simulated; non-COD orders transition immediately to `Paid` status. Full integration with live payment gateways (Razorpay/Stripe) is planned for Roadmap Phase 2.
2. **Delivery Distance:** Uses address tag parsing (`[dist: Xkm]`) rather than live GPS / Google Maps Distance Matrix API. Real-time mapping is planned for Roadmap Phase 3.

---

## 4. Phase 3 — Testing, Integration, Security, and Stabilization

### Status: **COMPLETE AND VERIFIED**

#### A. Scope & Objectives
Full test coverage of all business modules, view authorization checks, input validation, CSRF protection, transaction isolation, financial tampering prevention, and CI/CD validation.

#### B. Verification Evidence
- **Automated Test Suite:** 63/63 tests passing across `accounts` (8), `restaurants` (12), and `orders` (43) in 62.3 seconds.
- **Input Sanitization & Validation:** Regex phone validation (`^\+?[\d\s\-()]{7,20}$`) and minimum 5-character address validation enforced in forms and checkout views.
- **Financial Tampering Protection:** Client-submitted `total_amount`, `discount_amount`, and `delivery_fee` are ignored; all financial calculations are re-computed authoritatively on the server.
- **Authorization Boundaries:**
  - `/orders/dashboard/`, `/orders/status/`, `/orders/menu/toggle/`, and `/orders/drivers/add/` strictly require `request.user.is_staff`.
  - `/orders/receipt/<id>/` verifies that `request.user` is either staff or the owner who placed the order.
  - `/orders/cancel/<id>/` verifies that `order.customer == request.user`.
- **CSRF Protection:** All mutating endpoints require `POST` (`@require_POST`) and validate Django CSRF tokens.
- **Continuous Integration:** `.github/workflows/django-ci.yml` runs tests on every push/PR across Python 3.10, 3.11, and 3.12.

---

## 5. Phase 4 — Cloud Deployment and Operations

### Status: **PENDING (15% Complete — Pre-Deployment Configuration Only)**

#### A. Current Implementation State
- Production settings scaffolding exists in `dbms_project/settings.py` (HSTS, SSL redirect, secure cookies when `DEBUG=False`).
- Environment variable loading configured via `.env.example` (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`).

#### B. Missing Components & Blockers for Azure Deployment
1. **WSGI Web Server:** Neither `gunicorn` nor `uvicorn` is present in `requirements.txt`. Azure App Service Linux requires Gunicorn to serve Django WSGI.
2. **Static & Media Asset Handler:** `whitenoise` is not installed, and Azure Blob Storage integration (`django-storages[azure]`) is not configured. When `DEBUG=False`, static files and dish images will fail with HTTP 404.
3. **Containerization / Deployment Manifests:** No `Dockerfile`, `docker-compose.yml`, or Azure GitHub Actions workflow (`deploy-azure.yml`) exists in the repository.
4. **Production Secret Enforcement:** `settings.py` falls back to an insecure development key if `DJANGO_SECRET_KEY` is not provided. An explicit startup check must reject default keys when `DEBUG=False`.

---

## 6. Roadmap Phases (Future Commercial Enhancements)

### Roadmap Phase 2: Cashless Payments & Notifications (Status: PENDING)
- Integrate Razorpay / Stripe checkout modal with client SDK.
- Add server-side webhook listener with cryptographic signature verification (`/orders/webhooks/razorpay/`).
- Automated order refund handling on customer cancellation.
- SendGrid / SMTP transactional email confirmations with attached PDF receipt.
- Twilio SMS / WhatsApp dispatch alerts.

### Roadmap Phase 3: Real-Time & Mobility (Status: PENDING)
- Live WebSockets via Django Channels or Server-Sent Events (SSE) for driver tracking and kitchen alerts.
- Interactive Leaflet / Google Maps showing live courier location and estimated ETA.
- Django REST Framework (DRF) / Ninja API endpoints (`/api/v1/`) to decouple mobile frontends.
- Migration from dual SQLite files to production PostgreSQL with segregated schemas.
