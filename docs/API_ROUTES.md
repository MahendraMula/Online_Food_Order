# URL Routes Reference - OFO-DBMS

This document lists every URL route in the application, its HTTP methods, required authentication level, and purpose.

---

## Auth Levels

| Symbol | Meaning |
|---|---|
| Public | No login required |
| Login Required | @login_required decorator |
| Staff Only | request.user.is_staff check |

---

## Root Configuration (dbms_project/urls.py)

| Prefix | App |
|---|---|
| / | 
estaurants (storefront) |
| /accounts/ | ccounts (auth & profile) |
| /orders/ | orders (cart, checkout, dashboard) |
| /admin/ | Django Admin |

---

## Storefront & Menu - restaurants/ (mounted at /)

| URL | Name | Method | Auth | Description |
|---|---|---|---|---|
| / | storefront | GET | Public | Main menu page with search, filters, and food cards |
| /review/submit/ | submit_review | POST | Login Required | Submit a star rating + comment for a restaurant/dish |

**Query Parameters for /:**

| Param | Type | Description |
|---|---|---|
| q | string | Search term (filters by dish name) |
| category | string | Category name filter |
| eg | true/false | Veg-only toggle filter |
| sort | price_asc / rating_desc | Sort order |

---

## Authentication & Profile - accounts/ (mounted at /accounts/)

| URL | Name | Method | Auth | Description |
|---|---|---|---|---|
| /accounts/signup/ | signup | GET, POST | Public | Customer registration form |
| /accounts/login/ | login | GET, POST | Public | Session login |
| /accounts/logout/ | logout | POST | Login Required | Session logout, redirects to login |
| /accounts/profile/ | profile | GET, POST | Login Required | View & update customer profile |

---

## Shopping Cart - orders/cart/ (mounted at /orders/)

| URL | Name | Method | Auth | Description |
|---|---|---|---|---|
| /orders/cart/ | cart | GET | Public | View current cart contents |
| /orders/cart/add/<item_id>/ | add_to_cart | POST | Public | Add item to cart |
| /orders/cart/update/<item_id>/ | update_cart | POST | Public | Increment, decrement, or set quantity |
| /orders/cart/remove/<item_id>/ | remove_from_cart | POST | Public | Remove item from cart |
| /orders/cart/clear/ | clear_cart | POST | Public | Empty the entire cart |

**POST body for add_to_cart:**

| Field | Type | Description |
|---|---|---|
| quantity | integer | Units to add (default: 1) |
| 
ext | string | Optional redirect URL after adding |

**POST body for update_cart:**

| Field | Type | Description |
|---|---|---|
| ction | increment / decrement | Quick +1 / -1 adjustment |
| quantity | integer | Override quantity (if action not provided) |

---

## Checkout & Orders (mounted at /orders/)

| URL | Name | Method | Auth | Description |
|---|---|---|---|---|
| /orders/checkout/ | checkout | GET | Login Required | Pre-order review: items, address, payment method |
| /orders/place/ | place_order | POST | Login Required | Finalize order atomically |
| /orders/history/ | order_history | GET | Login Required | Customer order history with visual tracker |
| /orders/receipt/<order_id>/ | order_receipt | GET | Login Required | Printable invoice |
| /orders/cancel/<order_id>/ | cancel_order | POST | Login Required | Cancel order (only if Pending or Placed) |
| /orders/confirm/<order_id>/ | confirm_order | POST | Login Required | Confirm payment |

**POST body for place_order:**

| Field | Type | Validation | Description |
|---|---|---|---|
| payment_mode | COD/UPI/Card | Required | Payment method |
| delivery_address | string | Min 5 chars | Delivery address |
| phone | string | Regex validated | Contact phone |
| special_instructions | string | Optional | Notes for kitchen/driver |

---

## Restaurant Admin Dashboard (mounted at /orders/) - Staff Only

| URL | Name | Method | Auth | Description |
|---|---|---|---|---|
| /orders/dashboard/ | admin_dashboard | GET | Staff Only | Full operations & analytics dashboard |
| /orders/status/<order_id>/ | update_order_status | POST | Staff Only | Advance order status + assign driver |
| /orders/menu/toggle/<item_id>/ | toggle_item_availability | POST | Staff Only | Toggle dish In Stock / Sold Out |
| /orders/drivers/add/ | add_delivery_partner | POST | Staff Only | Onboard a new delivery driver |

**POST body for update_order_status:**

| Field | Type | Description |
|---|---|---|
| status | order status choice | New order status |
| driver_id | integer | Optional - ID of DeliveryPartner to assign |

**POST body for add_delivery_partner:**

| Field | Type | Description |
|---|---|---|
| 
ame | string | Driver full name |
| phone | string | Driver phone number |

---

## Django Admin

| URL | Description |
|---|---|
| /admin/ | Full CRUD admin panel for all models |

Default models registered:
- **accounts**: CustomerProfile
- **restaurants**: Category, Restaurant, MenuItem, Review
- **orders**: Order, OrderItem, Payment, DeliveryPartner, Delivery
