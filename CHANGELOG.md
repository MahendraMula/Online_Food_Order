# Changelog

All notable changes to **OFO-DBMS** will be documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

> Changes that are in development but not yet released.

---

## [1.0.0] — 2026-09-05

### ?? Initial Release

#### Added

**Authentication & Profiles**
- User registration with automatic CustomerProfile creation (phone, address)
- Session-based login and logout using Django's built-in auth
- Profile update page for editing phone number and delivery address

**Menu & Storefront**
- Dynamic storefront with food card grid layout (Bootstrap 5)
- Category-based menu organization: Burgers & Wraps, Pizzas & Pasta, Asian Bowls, Beverages, Desserts
- Live AJAX-style search bar filtering menu items by name
- Category carousel chips for quick filtering
- ?? Pure Veg / ?? Non-Veg toggle filter
- Price (Low ? High) and Rating (High ? Low) sorting options
- Menu item cards with dish image, description, price, prep time, and veg/non-veg badge

**Shopping Cart**
- Session-based persistent cart (no login required)
- Add, update quantity (increment/decrement), remove, and clear cart actions
- Real-time subtotal calculations
- Live cart item counter in the navbar (via context processor)

**Order & Checkout**
- Unified checkout page showing all cart items, delivery address, and payment selection
- Three payment modes: Cash on Delivery (COD), UPI Transfer, Credit/Debit Card
- Input validation for phone number (regex) and delivery address length
- Atomic transaction for order creation: Order ? OrderItems ? Payment ? Delivery
- Profile address auto-update on successful checkout

**Order Tracking**
- Customer order history page with all past orders
- 4-step visual milestone tracker: *Order Placed ? Kitchen Preparing ? Out for Delivery ? Delivered*
- Assigned delivery driver name and contact shown on tracking card
- Cancel order functionality (for Pending/Placed orders)
- Printable order receipt/invoice page

**Restaurant Admin Dashboard** (/orders/dashboard/)
- KPI metric cards: Total Revenue, Total Orders, Active Queue, Delivered, Menu Stock, Customers
- Live orders queue table with 1-click status progression
- Driver assignment dropdown per order
- Menu stock manager: toggle In Stock / Sold Out per dish
- Driver onboarding form
- Top 5 best-selling dishes (by quantity)
- Payment mode breakdown (COD / UPI / Card totals)
- Category revenue statistics

**Database Architecture**
- Dual-database setup: ood_ordering.db (app data) + django_database.db (framework internals)
- Custom DjangoFrameworkRouter to route Django internals to separate database
- Full relational schema: CustomerProfile, Category, Restaurant, MenuItem, Review, Order, OrderItem, Payment, DeliveryPartner, Delivery

**Testing**
- Unit tests for ccounts, estaurants, and orders apps
- Custom un_tests.py test runner

**Project Config**
- Environment variable support for SECRET_KEY, DEBUG, ALLOWED_HOSTS, SSL settings
- Production-ready security settings (HSTS, SSL redirect, secure cookies) when DEBUG=False
- Django Admin panel with full CRUD on all models

---

[Unreleased]: https://github.com/YOUR_USERNAME/OFO-DBMS/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/YOUR_USERNAME/OFO-DBMS/releases/tag/v1.0.0
