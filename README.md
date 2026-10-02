# OFO-DBMS
## Online Food Ordering & Delivery System

A production-inspired, full-stack online food ordering and delivery management system built with **Python 3**, **Django 5**, and a **dual SQLite database architecture**. The system demonstrates rigorous relational database design, atomic transaction management, server-side financial calculations, and full customer storefront and restaurant administration workflows.

---

### 1. Project Overview

**OFO-DBMS** simulates a production-grade multi-restaurant food delivery platform (similar to platforms like Swiggy or Zomato). The project addresses the complete lifecycle of online food ordering:

* **Customer Workflow**: Account registration, profile management with delivery addresses, dynamic restaurant and menu item browsing, multi-criteria filtering, single-restaurant cart enforcement, promotional coupon validation, dynamic delivery fee calculations, GST calculation, atomic order placement, live visual milestone tracking, and post-delivery restaurant/dish ratings.
* **Restaurant Operations & Admin Workflow**: A dedicated operations dashboard (`/orders/dashboard/`) providing live business KPI tracking (revenue, active kitchen queue, completed orders, menu inventory), 1-click order workflow progression (*Preparing → Out for Delivery → Delivered → Cancelled*), delivery driver onboarding and assignment, and real-time menu item stock toggling (*In Stock / Sold Out*).

---

### 2. Key Features

#### 👤 Customer Features
* **Authentication & Profile Management**: User registration, session-based login/logout, and auto-provisioned `CustomerProfile` maintaining contact phone numbers and default delivery addresses.
* **Restaurant & Menu Browsing**: Grid-based storefront showcasing restaurants, dish imagery, pricing, preparation times, and vegetarian indicators.
* **Search, Filter & Sort**: Live keyword search across dish names, descriptions, and restaurant titles; category carousel filtering; pure vegetarian toggle; and sorting by price (ascending/descending), preparation time, and restaurant rating.
* **Shopping Cart**: Multi-item session-backed cart supporting quantity adjustments, item removal, and a global live cart count badge in the master navbar.
* **Single-Restaurant Cart Validation**: Defensive validation enforcing that all cart items belong to exactly one restaurant, with modal conflict resolution if a customer attempts to add an item from a different restaurant.
* **Coupon & Promo Code Engine**: Application and removal of promotional codes supporting percentage discounts (with optional maximum discount caps) and flat amount deductions, strictly validated against active date ranges, minimum order values, and global usage limits.
* **Unified Checkout**: Consolidated review of cart items, delivery address, contact phone validation (regex verified), special culinary/delivery instructions, coupon deduction, delivery charge, GST, and payment mode selection (Cash on Delivery, UPI, or Credit/Debit Card).
* **Dynamic Delivery Fee**: Server-side calculation offering free delivery for qualifying orders and transparent distance-based delivery fees.
* **GST / Tax Calculation**: Server-authoritative 5% GST computation on net food subtotal.
* **Order Placement & Atomic Transactions**: Full order placement orchestrated inside `transaction.atomic()` guaranteeing synchronized creation of Order, OrderItems, Payment, and Delivery assignment.
* **Order History & Milestone Tracker**: Order history page with a 4-stage visual progress tracker (*Order Placed → Kitchen Preparing → Out for Delivery → Delivered*), driver contact display, and cancellation options for pending orders.
* **Reviews & Ratings**: Verified customer star ratings (1 to 5 stars) and feedback comments with automated recalculation of restaurant average ratings.
* **Printable Tax Invoices**: Formatted, itemized receipt view (`/orders/receipt/<id>/`) detailing individual dish lines, coupon discounts, delivery fees, GST tax rate, and payment status.

#### 🛡️ Restaurant Admin & Operations Features
* **Executive Dashboard (`/orders/dashboard/`)**: Operational console restricted to staff administrators.
* **Business KPI Metrics**: Live summary cards tracking Total Revenue, Total Orders Placed, Active Kitchen Queue, Delivered Orders, Dishes In Stock, and Registered Customer base.
* **Live Order Queue**: Interactive queue table with one-click status transitions advancing orders through preparation, driver pickup, and final delivery.
* **Driver Onboarding & Assignment**: Delivery driver registration interface and per-order driver assignment dropdown.
* **Menu Stock Control**: Instant toggle button switching dish availability between *In Stock* and *Sold Out*.
* **Coupon & Promotion Management**: Model and admin management for coupon codes, discount types, validity windows, and usage counters.
* **Analytics & Performance Reports**: Top 5 best-selling dishes ranked by cumulative volume, breakdown of payment methods (COD, UPI, Card), and category-level revenue distribution.

---

### 3. Phase 1 Commercial Essentials

The Phase 1 release incorporates four core commercial business requirements:

1. **Single-Restaurant Cart Validation**:
   * Prevents orders containing items from multiple distinct restaurants.
   * Attempting to add an item from a different restaurant alerts the user and offers a conflict resolution prompt to either keep the existing cart or clear it and start fresh with the new restaurant.
   * Backed by low-level defensive checks in `Cart.add()` (`MixedRestaurantCartError`) and an integrity guard in checkout.

2. **Coupon / Promo Code Engine**:
   * Model-driven promotions (`Coupon` model) supporting `PERCENTAGE` discounts (with optional `max_discount_amount` caps) and `FLAT` monetary discounts.
   * Verified against `is_active`, `valid_from`, `valid_until`, `min_order_value`, and `max_uses` vs `times_used`.
   * Row-level locking via `select_for_update()` during checkout to prevent race conditions and over-redemption.

3. **Dynamic Delivery Charges**:
   * Centralized fee engine in `orders/services.py`.
   * Automatically grants **Free Delivery** when net food subtotal reaches or exceeds the threshold.
   * Orders below the threshold incur a flat base fee plus a per-kilometer surcharge for distances beyond the standard delivery radius.

4. **GST / Tax Calculation**:
   * Standard 5% GST calculated on the net food subtotal (after deducting valid coupon discounts).
   * Exact rounding using Python's `Decimal` with `ROUND_HALF_UP` precision to prevent fractional-cent rounding errors.
   * Persisted as a discrete `tax_amount` column on the `Order` model and itemized on the printable tax invoice.

---

### 4. Pricing Formula

All order calculations are computed **authoritatively on the server**:

$$\text{Net Subtotal} = \max(0, \text{Gross Subtotal} - \text{Coupon Discount})$$

$$\text{Delivery Fee} = \begin{cases} ₹0.00 & \text{if } \text{Net Subtotal} \ge ₹50.00 \\ ₹4.00 + \max(0, \text{distance\_km} - 5.0) \times ₹1.00 & \text{if } \text{Net Subtotal} < ₹50.00 \end{cases}$$

$$\text{GST / Tax} = (\text{Net Subtotal} \times 0.05) \quad \text{[rounded to 2 decimal places via ROUND\_HALF\_UP]}$$

$$\text{Final Payable Total} = \text{Net Subtotal} + \text{Delivery Fee} + \text{GST}$$

#### Verified Configuration Defaults (`dbms_project/settings.py`)
* **Currency Symbol**: `₹` (`OFO_CURRENCY_SYMBOL`)
* **Currency Code**: `INR` (`OFO_CURRENCY_CODE`)
* **Configured GST Rate**: `5%` (`0.05` via `OFO_GST_TAX_RATE`)
* **Free Delivery Threshold**: `₹50.00` (`OFO_FREE_DELIVERY_THRESHOLD`)
* **Base Delivery Fee**: `₹4.00` (`OFO_BASE_DELIVERY_FEE`)
* **Standard Delivery Radius**: `5.0 km` (`OFO_BASE_DELIVERY_DISTANCE_KM`)
* **Distance Surcharge Rate**: `₹1.00/km` (`OFO_DELIVERY_PER_KM_RATE`)

---

### 5. Delivery Distance Limitation

The Phase 1 delivery fee engine uses a **deterministic distance abstraction**:

* **Current Implementation**: Distance is evaluated either via an explicit `distance_km` parameter or extracted from an optional delivery address distance tag (e.g., `[dist: 7.5km]` or `[distance: 8km]`). When no distance tag is present, standard local base distance ($\le 5.0\text{ km}$) applies.
* **Real-time GPS / Routing**: The system does **not** yet include live GPS navigation, real-time driver telemetry, or interactive road-network routing.
* **Provider Decoupling**: The pricing function `calculate_delivery_fee()` in `orders/services.py` is fully decoupled from routing implementations. In future phases, an external routing provider (e.g., Google Maps Distance Matrix API or Leaflet/OSRM) can compute real road distances between restaurant and customer coordinates and pass `distance_km` directly into this function without altering the fee engine.

---

### 6. Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Bootstrap 5 Web UI                   │
│   Storefront  │  Cart  │  Checkout  │  Admin Dashboard │
└───────────────────────────▲────────────────────────────┘
                            │ HTTP Request / Response
┌───────────────────────────▼────────────────────────────┐
│                    Django 5 Backend                    │
│   accounts    │   restaurants   │   orders (services)  │
└───────────────────────────▲────────────────────────────┘
                            │ DjangoFrameworkRouter
              ┌─────────────┴─────────────┐
              ▼                           ▼
  ┌───────────────────────┐   ┌───────────────────────┐
  │   food_ordering.db    │   │  django_database.db   │
  │    (App Domain Data)  │   │  (Framework Internals)│
  │ - Categories          │   │ - auth_user           │
  │ - Restaurants         │   │ - sessions            │
  │ - MenuItems & Reviews │   │ - contenttypes        │
  │ - Orders & OrderItems │   │ - admin_log           │
  │ - Coupons & Payments  │   └───────────────────────┘
  │ - Deliveries/Partners │
  └───────────────────────┘
```

#### Dual-Database Setup
* **`food_ordering.db`** (Default DB): Contains all domain-specific application tables (Orders, OrderItems, Coupons, MenuItems, Restaurants, Categories, Deliveries, DeliveryPartners, Payments, Reviews, CustomerProfiles).
* **`django_database.db`** (Framework DB): Houses framework-level Django models (`django.contrib.auth`, `django.contrib.sessions`, `django.contrib.contenttypes`, `django.contrib.admin`).
* **Custom Database Router**: Located in `dbms_project/db_routers.py` (`DjangoFrameworkRouter`), routing database reads, writes, and migrations dynamically based on application labels.

---

### 7. Transaction and Data Integrity

* **Atomic Order Placement**: The entire checkout pipeline in `orders/views.py` runs inside `with transaction.atomic():`. If any operation fails (e.g., payment creation error, database lock issue), all database modifications are rolled back.
* **Server-Side Recalculation**: All monetary values (gross subtotal, coupon discount, delivery fee, GST tax, final total) are recalculated on the server. Client-submitted prices or totals in POST requests are completely ignored.
* **Concurrency Locking with `select_for_update()`**: When redeeming a coupon with usage limits, the coupon record is locked with `Coupon.objects.select_for_update()` inside the atomic block. This eliminates race conditions where simultaneous checkouts could exceed `max_uses`.
* **Referential Integrity**: Order items reference menu items using `on_delete=models.PROTECT`, preventing menu dishes from being deleted while associated with historical orders.

---

### 8. Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Django Templates, HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, JavaScript |
| **Backend Framework** | Python 3.10+, Django 5.x |
| **Database** | SQLite 3 (Dual-database configuration with custom router) |
| **Architecture Pattern** | Model-View-Template (MVT), Service Layer (`orders/services.py`) |
| **Testing** | Django Test Framework / Python `unittest` |
| **Document Generation** | ReportLab 5.x (Printable PDF invoices & status reports) |

---

### 9. Project Structure

```
OFO-DBMS/
├── accounts/                         # User authentication & customer profiles
│   ├── forms.py                      # Registration & profile update forms
│   ├── models.py                     # CustomerProfile (1:1 with User)
│   ├── tests.py                      # Unit tests for accounts app
│   ├── urls.py                       # /accounts/ routes
│   └── views.py                      # Signup, login, logout, profile views
│
├── restaurants/                      # Restaurants, categories, dishes & reviews
│   ├── management/commands/
│   │   └── seed_db.py                # Database seeder (sample data & users)
│   ├── models.py                     # Category, Restaurant, MenuItem, Review
│   ├── tests.py                      # Discovery, filter & review tests
│   ├── urls.py                       # Storefront & review submission routes
│   └── views.py                      # Storefront, search & review views
│
├── orders/                           # Cart, checkout, tracking & dashboard
│   ├── admin.py                      # Django admin configuration for orders
│   ├── cart.py                       # Session-based cart with single-restaurant rule
│   ├── context_processors.py         # Global cart counter & currency symbols
│   ├── models.py                     # Order, OrderItem, Coupon, Payment, Delivery
│   ├── services.py                   # Fee engine: delivery fee & 5% GST calculations
│   ├── tests.py                      # Cart, coupon, delivery, tax & workflow tests
│   ├── urls.py                       # /orders/ routes
│   └── views.py                      # Cart, coupon, checkout, receipt & admin dashboard
│
├── dbms_project/                     # Project configuration
│   ├── db_routers.py                 # DjangoFrameworkRouter (dual-database routing)
│   ├── settings.py                   # Settings, dual DB config, currency & tax vars
│   ├── urls.py                       # Root URL dispatcher
│   ├── wsgi.py / asgi.py
│
├── templates/                        # Bootstrap 5 HTML templates
│   ├── base.html                     # Global base layout (navbar, badge, conflict modal)
│   ├── index.html                    # Storefront dish discovery grid
│   ├── cart.html                     # Shopping cart with coupon & tax breakdown
│   ├── checkout.html                 # Unified checkout & order summary
│   ├── orders.html                   # Customer order history & 4-stage tracker
│   ├── dashboard.html                # Restaurant admin dashboard & queue manager
│   ├── receipt.html                  # Printable itemized tax invoice
│   └── ...                           # Auth templates (login, signup, profile)
│
├── docs/                             # Project documentation
│   ├── API_ROUTES.md                 # Complete HTTP endpoint specifications
│   ├── DATABASE_SCHEMA.md            # Relational database schema reference
│   ├── PROJECT_STATUS_REPORT.md      # Detailed technical evaluation report
│   └── OFO_DBMS_Project_Status_Report.pdf  # Formatted PDF status report
│
├── .env.example                      # Template for environment variables
├── .gitignore                        # Standard exclusions (.env, .venv, *.db)
├── manage.py                         # Django management entry point
├── run_tests.py                      # Custom test runner
└── requirements.txt                  # Python dependencies
```

---

### 10. Installation

#### Prerequisites
* Python 3.10 or higher
* Git

#### Step-by-Step Setup (Windows)

1. **Clone the Repository**:
   ```powershell
   git clone https://github.com/MahendraMula/Online_Food_Order.git
   cd Online_Food_Order
   ```

2. **Create and Activate a Virtual Environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (Optional)**:
   Copy `.env.example` to `.env` if custom configurations (e.g., custom secret keys or ports) are desired:
   ```powershell
   copy .env.example .env
   ```

---

### 11. Database Setup

OFO-DBMS uses a dual-database architecture. Migrations are applied in accordance with the database router rules.

1. **Apply Migrations to Both Databases**:
   ```powershell
   python manage.py migrate --database=django_database
   python manage.py migrate --database=default
   ```
   *(Running `python manage.py migrate` also automatically routes each application's tables to its respective database).*

2. **Seed Sample Data (Recommended)**:
   Pre-populate categories, restaurants, dishes, drivers, demo users, and test orders:
   ```powershell
   python manage.py seed_db
   ```

   **Demo Customer Credentials**:
   * Username: `customer_alice` | Password: `Demo@1234`
   * Username: `customer_bob`   | Password: `Demo@1234`
   * Username: `customer_carol` | Password: `Demo@1234`

3. **Create a Superuser (For Admin Dashboard Access)**:
   ```powershell
   python manage.py createsuperuser
   ```

---

### 12. Verification

Before running the server, verify the integrity of the project:

1. **System Health Check**:
   ```powershell
   python manage.py check
   ```
   *Expected Result: `System check identified no issues (0 silenced).`*

2. **Migration Consistency Check**:
   ```powershell
   python manage.py makemigrations --check
   ```
   *Expected Result: `No changes detected`*

3. **Execute Full Test Suite**:
   ```powershell
   python run_tests.py
   ```
   *or via manage.py:*
   ```powershell
   python manage.py test accounts.tests restaurants.tests orders.tests
   ```
   *Expected Result: `Ran 63 tests ... OK`*

---

### 13. Run the Website

Start the local development server:
```powershell
python manage.py runserver
```

Open your browser and navigate to:
**`http://127.0.0.1:8000/`**

---

### 14. Important URLs

| Endpoint | Name | Access Level | Description |
|---|---|---|---|
| `/` | `storefront` | Public | Storefront menu discovery, search, filter, and dish listings |
| `/accounts/signup/` | `signup` | Public | Customer account registration |
| `/accounts/login/` | `login` | Public | User authentication login |
| `/accounts/logout/` | `logout` | Authenticated | Session logout |
| `/accounts/profile/` | `profile` | Authenticated | Manage customer phone number and delivery address |
| `/orders/cart/` | `cart` | Public | View shopping cart, modify quantities, apply/remove coupons |
| `/orders/coupon/apply/` | `apply_coupon` | Public | POST: Apply promotional discount coupon |
| `/orders/coupon/remove/` | `remove_coupon` | Public | POST: Remove applied coupon from cart session |
| `/orders/checkout/` | `checkout` | Authenticated | Review order breakdown, address, and select payment mode |
| `/orders/place/` | `place_order` | Authenticated | POST: Place order atomically and clear cart |
| `/orders/history/` | `order_history` | Authenticated | Customer order history and 4-stage tracking progress |
| `/orders/receipt/<id>/` | `order_receipt` | Authenticated | Itemized printable tax invoice |
| `/orders/cancel/<id>/` | `cancel_order` | Authenticated | POST: Cancel pending order |
| `/orders/dashboard/` | `admin_dashboard` | Staff Only | Restaurant operations console, order queue, and KPIs |
| `/orders/status/<id>/` | `update_order_status` | Staff Only | POST: Advance order state (*Preparing/Out for Delivery/Delivered*) |
| `/orders/menu/toggle/<id>/` | `toggle_item_availability` | Staff Only | POST: Toggle dish availability (*In Stock / Sold Out*) |
| `/orders/drivers/add/` | `add_delivery_partner` | Staff Only | POST: Onboard a new delivery driver |
| `/admin/` | `admin:index` | Staff Only | Django Admin panel for full relational model CRUD |

---

### 15. Test Results

The test suite runs across all three modular applications (`accounts`, `restaurants`, `orders`):

```text
Ran 63 tests in 30.270s

OK
Destroying test database for alias 'default'...
Destroying test database for alias 'django_database'...
```

#### Test Suite Breakdown (63/63 Passing)
* **`accounts.tests` (16 tests)**:
  * Customer profile auto-creation on user registration.
  * Validation rules for phone numbers (regex) and delivery address minimum length.
  * Password matching validation and error handling on signup.
  * Profile update view permission checks and data persistence.
* **`restaurants.tests` (12 tests)**:
  * Category, Restaurant, and MenuItem model relationships.
  * Storefront filtering by category, search queries, vegetarian toggle, and price sorting.
  * Review creation, login requirements, rating boundary validation (1–5 stars), and automatic recalculation of restaurant average ratings.
  * `seed_db` management command execution and record count verification.
* **`orders.tests` (35 tests)**:
  * **Cart & Lifecycle (8 tests)**: Session mutations, quantity increments/decrements, 405 method guards on mutation endpoints, COD payment statuses, item stock toggling, and multi-item receipt rendering.
  * **Single-Restaurant Cart Validation (7 tests)**: Adding items from same restaurant, rejection of mixed-restaurant items, conflict dismissal, session cleanup, and defensive checkout barriers.
  * **Coupon Engine (11 tests)**: Percentage coupons, flat coupons, invalid/expired/inactive rejections, minimum order subtotal enforcement, global redemption limits, max discount capping, coupon removal, and client-side tamper resistance.
  * **Dynamic Delivery Fee (6 tests)**: Free delivery threshold ($\ge ₹50$), base fee ($₹4$), distance surcharge beyond 5 km, address tag parsing (`[dist: Xkm]`), database persistence, and tamper resistance.
  * **GST / Tax Calculation (8 tests)**: 5% GST computation on net subtotal, Decimal `ROUND_HALF_UP` precision, negative value safety, cart/checkout template rendering, invoice receipt line-item display, and server-side tamper resistance.

---

### 16. Current Limitations / Future Enhancements

The following capabilities are **intentionally not yet implemented** in the Phase 1 milestone and represent planned future enhancements:

* **Real GPS Navigation & Geocoding**: Delivery distance currently uses a deterministic abstraction (`distance_km` parameter or `[dist: Xkm]` address tag). Live road routing (Google Maps Distance Matrix / Mapbox) is planned for a future release.
* **Live Payment Gateway Integration**: Payment options (Card, UPI, COD) currently simulate real-world transactions. Direct integration with payment gateways (Razorpay, Stripe) with webhook verification is not yet implemented.
* **Payment Webhooks & Automated Refunds**: Automatic refunds upon order cancellation are currently handled manually.
* **Transactional Email & SMS**: In-app notifications and printable receipts are supported; automated SMTP/SendGrid emails and Twilio SMS/WhatsApp messages are not yet integrated.
* **Real-Time WebSockets**: Live order tracking and kitchen queue updates currently rely on browser page refreshes rather than persistent WebSocket connections (Django Channels).
* **Decoupled REST / GraphQL APIs**: Views are rendered via server-side Django templates (MVT). Exposing Django REST Framework (DRF) endpoints for mobile or external apps is planned.
* **Production Database Migration**: While dual SQLite handles current workloads, migration to PostgreSQL or MySQL will be required for high-concurrency production deployments.

---

### 📄 License & Attribution

Academic and production prototype developed for educational and demonstration purposes. All rights reserved.
