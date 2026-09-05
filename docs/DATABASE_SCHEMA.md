# Database Schema — OFO-DBMS

This document provides a complete reference for the relational database schema used in the OFO-DBMS project.

---

## Architecture Overview

The project uses a **dual-database architecture**:

| Database File | Purpose | Managed By |
|---|---|---|
| food_ordering.db | All application data (Orders, Menus, Users, etc.) | App models |
| django_database.db | Django framework internals (sessions, admin, content types) | DjangoFrameworkRouter |

The router (dbms_project/db_routers.py) automatically directs reads/writes for django.contrib.* models to django_database and all app models to default.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    AUTH_USER {
        int id PK
        varchar username
        varchar email
        varchar password
        bool is_staff
        bool is_active
    }

    CUSTOMER_PROFILE {
        int id PK
        int user_id FK
        varchar phone
        text address
    }

    CATEGORY {
        int id PK
        varchar name
        varchar icon
        text description
    }

    RESTAURANT {
        int id PK
        varchar restaurant_name
        text address
        decimal rating
        url image_url
    }

    MENU_ITEM {
        int id PK
        int category_id FK
        int restaurant_id FK
        varchar item_name
        decimal price
        text description
        bool is_veg
        url image_url
        int preparation_time
        bool availability
    }

    REVIEW {
        int id PK
        int customer_id FK
        int restaurant_id FK
        int menu_item_id FK
        int rating
        text comment
        datetime created_at
    }

    ORDER {
        int id PK
        int customer_id FK
        datetime order_date
        varchar status
        decimal total_amount
        text special_instructions
    }

    ORDER_ITEM {
        int id PK
        int order_id FK
        int item_id FK
        int quantity
    }

    PAYMENT {
        int id PK
        int order_id FK
        decimal amount
        varchar payment_mode
        varchar payment_status
    }

    DELIVERY_PARTNER {
        int id PK
        varchar name
        varchar phone
    }

    DELIVERY {
        int id PK
        int order_id FK
        int partner_id FK
        varchar delivery_status
        datetime delivery_time
    }

    AUTH_USER ||--|| CUSTOMER_PROFILE : "has profile"
    AUTH_USER ||--o{ ORDER : "places"
    AUTH_USER ||--o{ REVIEW : "writes"
    CATEGORY ||--o{ MENU_ITEM : "classifies"
    RESTAURANT ||--o{ MENU_ITEM : "offers"
    RESTAURANT ||--o{ REVIEW : "receives"
    MENU_ITEM ||--o{ ORDER_ITEM : "ordered in"
    MENU_ITEM ||--o{ REVIEW : "rated in"
    ORDER ||--|{ ORDER_ITEM : "contains"
    ORDER ||--|| PAYMENT : "paid via"
    ORDER ||--|| DELIVERY : "fulfilled via"
    DELIVERY_PARTNER ||--o{ DELIVERY : "delivers"
``

---

## Table Reference

### accounts_customerprofile
Extends Django's built-in auth_user with customer-specific fields.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| user_id | INTEGER | FK → auth_user, OneToOne | Associated user account |
| phone | VARCHAR(15) | NOT NULL | Customer phone number |
| address | TEXT | NOT NULL | Default delivery address |

---

### restaurants_category
Food categories for grouping menu items.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Category name (e.g., "Pizzas & Pasta") |
| icon | VARCHAR(50) | default='bi-tag' | Bootstrap Icons class name |
| description | TEXT | blank | Optional description |

---

### restaurants_restaurant
Partner restaurant information.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| estaurant_name | VARCHAR(255) | NOT NULL | Restaurant display name |
| address | TEXT | NOT NULL | Physical address |
| ating | DECIMAL(3,1) | default=4.5 | Restaurant rating |
| image_url | URL | nullable | Banner/logo image URL |

---

### restaurants_menuitem
Individual food dishes available for ordering.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| category_id | INTEGER | FK → category, nullable | Food category |
| estaurant_id | INTEGER | FK → restaurant, CASCADE | Owning restaurant |
| item_name | VARCHAR(255) | NOT NULL | Dish name |
| price | DECIMAL(6,2) | NOT NULL | Price per unit |
| description | TEXT | blank | Dish description |
| is_veg | BOOLEAN | default=True | Vegetarian flag |
| image_url | URL | nullable | Dish image URL |
| preparation_time | INTEGER | default=20 | Prep time in minutes |
| availability | BOOLEAN | default=True | In stock flag |

---

### restaurants_review
Customer reviews for restaurants and/or menu items.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| customer_id | INTEGER | FK → auth_user | Reviewer |
| estaurant_id | INTEGER | FK → restaurant, CASCADE | Reviewed restaurant |
| menu_item_id | INTEGER | FK → menuitem, nullable | Specific dish reviewed |
| ating | INTEGER | 1–5 choices | Star rating |
| comment | TEXT | blank | Review text |
| created_at | DATETIME | auto_now_add | Review timestamp |

---

### orders_order
A single customer order (can contain multiple items).

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| customer_id | INTEGER | FK → auth_user | Customer who placed the order |
| order_date | DATETIME | auto_now_add | When the order was placed |
| status | VARCHAR(50) | choices | Order status |
| total_amount | DECIMAL(8,2) | NOT NULL | Total order value |
| special_instructions | TEXT | blank | Customer's delivery notes |

**Status Choices:** Pending → Placed → Preparing → Out for Delivery → Delivered / Cancelled

---

### orders_orderitem
Individual line items within an order.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| order_id | INTEGER | FK → order, CASCADE | Parent order |
| item_id | INTEGER | FK → menuitem, PROTECT | Ordered dish |
| quantity | INTEGER | default=1 | Number of units |

---

### orders_payment
Payment record linked 1-to-1 with an order.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| order_id | INTEGER | FK → order, CASCADE, OneToOne | Associated order |
| amount | DECIMAL(8,2) | NOT NULL | Amount paid |
| payment_mode | VARCHAR(50) | choices | COD / Card / UPI |
| payment_status | VARCHAR(50) | choices, default=Pending | Pending / Paid / Failed |

---

### orders_deliverypartner
Registered delivery drivers.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| name | VARCHAR(255) | NOT NULL | Driver's full name |
| phone | VARCHAR(15) | NOT NULL | Driver's contact number |

---

### orders_delivery
Delivery record tracking assignment and status.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK, Auto | Primary key |
| order_id | INTEGER | FK → order, CASCADE, OneToOne | Associated order |
| partner_id | INTEGER | FK → deliverypartner, SET_NULL | Assigned driver |
| delivery_status | VARCHAR(50) | choices, default=Assigned | Assigned / In Progress / Picked Up / Delivered |
| delivery_time | DATETIME | nullable | Timestamp of delivery completion |

---

## Key Design Decisions

1. **Dual-database setup** separates concern: app data vs Django internals. This prevents Django's session/admin tables from cluttering the main business database.

2. **db_constraint=False** on CustomerProfile.user and Order.customer allows the SQLite databases to operate independently without cross-database foreign key constraints (SQLite limitation).

3. **ORDER_ITEM quantity** acts as the line-item multiplier. Total for a line = quantity × item.price.

4. **PAYMENT.payment_status** is set to Paid immediately for UPI/Card at checkout, but Pending for COD — auto-upgraded to Paid when admin marks order as Delivered.

5. **MENU_ITEM uses PROTECT** on delete to prevent accidental deletion of dishes that are referenced in historical orders.
