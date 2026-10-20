# OFO-DBMS — Automated Test & System Verification Results

**Date of Execution:** October 20, 2026  
**Auditor:** Senior Software Architect, QA & Security Auditor  
**Repository:** OFO-DBMS (Online Food Ordering System)  
**Execution Environment:** Windows (x64), Virtual Environment (`.venv`)  
**Python Runtime:** Python 3.14.5  
**Django Version:** 5.2.17  
**Database Engines:** Dual SQLite3 (`food_ordering.db` [default] and `django_database.db` [django_database])

---

## 1. Automated Command Execution Log

| # | Command Executed | Directory | Exit Code | Result Status | Purpose / Description |
|---|---|---|---|---|---|
| 1 | `.\.venv\Scripts\python.exe -V` | Workspace root | 0 | PASSED | Verify local Python runtime version (`Python 3.14.5`) |
| 2 | `.\.venv\Scripts\python.exe -m django --version` | Workspace root | 0 | PASSED | Verify Django framework version (`5.2.17`) |
| 3 | `.\.venv\Scripts\python.exe manage.py check` | Workspace root | 0 | PASSED | Django full system check (`0 issues, 0 silenced`) |
| 4 | `.\.venv\Scripts\python.exe manage.py check --database default` | Workspace root | 0 | PASSED | System check against primary domain database alias |
| 5 | `.\.venv\Scripts\python.exe manage.py check --database django_database` | Workspace root | 0 | PASSED | System check against framework database alias |
| 6 | `.\.venv\Scripts\python.exe manage.py showmigrations` | Workspace root | 0 | PASSED | Migration history check across all installed apps |
| 7 | `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` | Workspace root | 0 | PASSED | Detect unapplied/uncommitted model schema drifts (`No changes detected`) |
| 8 | `.\.venv\Scripts\python.exe run_tests.py` | Workspace root | 0 | PASSED | Full unit and integration test suite execution (`63/63 passed in 62.345s`) |
| 9 | `git status --short` | Workspace root | 0 | PASSED | Working tree status check (`Clean, branch main`) |
| 10 | `git fetch --dry-run` | Workspace root | 0 | PASSED | Remote synchronization alignment check with `origin/main` |
| 11 | `.\.venv\Scripts\pip.exe list` | Workspace root | 0 | PASSED | Inspect installed dependencies and packaging state |
| 12 | `check_templates.py` (Custom AST validator) | Scratch | 0 | PASSED | Validate all 10 templates, inheritance, and 92 reverse URL names |

---

## 2. Test Suite Breakdown by Application

```
----------------------------------------------------------------------
Ran 63 tests in 62.345s

OK
Destroying test database for alias 'default' ('file:memorydb_default?mode=memory&cache=shared')...
Destroying test database for alias 'django_database' ('file:memorydb_django_database?mode=memory&cache=shared')...
```

### A. `accounts` App (8 Tests — 100% Passing)

*Test Class: `accounts.tests.AccountsModelAndFormTests`*

| # | Test Name | Target Unit | Verification Objective | Result |
|---|---|---|---|---|
| 1 | `test_customer_profile_creation` | Model | Profile creation linked 1:1 to User with address and phone | **PASS** |
| 2 | `test_signup_form_valid` | Form | Valid registration credentials produce clean form | **PASS** |
| 3 | `test_signup_form_invalid_phone` | Form | Non-phone strings and short numbers are rejected | **PASS** |
| 4 | `test_signup_form_invalid_address` | Form | Addresses under 5 characters are rejected | **PASS** |
| 5 | `test_signup_form_password_mismatch` | Form | Form rejects mismatched password confirmation | **PASS** |
| 6 | `test_signup_view_creates_user_and_profile` | View / Flow | HTTP POST creates User, CustomerProfile, logs in session | **PASS** |
| 7 | `test_profile_view_requires_login` | Security | Unauthenticated requests to `/accounts/profile/` redirect to login | **PASS** |
| 8 | `test_profile_view_updates_data` | View | Authenticated POST updates user fields and profile delivery address | **PASS** |

---

### B. `restaurants` App (12 Tests — 100% Passing)

*Test Class: `restaurants.tests.RestaurantModelAndDiscoveryTests` (6 Tests)*

| # | Test Name | Target Unit | Verification Objective | Result |
|---|---|---|---|---|
| 9 | `test_category_and_menuitem_creation` | Model | Creation of Categories and MenuItems linked to Restaurant | **PASS** |
| 10 | `test_storefront_view_all_items` | View | Storefront renders list of all available menu items | **PASS** |
| 11 | `test_storefront_search_by_name` | Queryset | Search query filters items by dish name and restaurant name | **PASS** |
| 12 | `test_storefront_category_filter` | Queryset | Category ID query parameter isolates matching category dishes | **PASS** |
| 13 | `test_storefront_veg_filter` | Queryset | Toggle filter (`veg=1`) isolates pure vegetarian items | **PASS** |
| 14 | `test_storefront_sort_price_asc` | Queryset | Sorting parameter `sort=price_asc` orders dishes correctly | **PASS** |

*Test Class: `restaurants.tests.ReviewSystemTests` (5 Tests)*

| # | Test Name | Target Unit | Verification Objective | Result |
|---|---|---|---|---|
| 15 | `test_review_model_creation` | Model | Customer review record linked to restaurant and user | **PASS** |
| 16 | `test_review_requires_login` | Security | Unauthenticated POST to `/review/submit/` redirects to login | **PASS** |
| 17 | `test_review_rejects_get` | HTTP Method | GET request to review endpoint is rejected (HTTP 405) | **PASS** |
| 18 | `test_submit_review_invalid_rating` | Validation | Ratings outside 1–5 range are rejected with user error message | **PASS** |
| 19 | `test_submit_review_view_updates_restaurant_rating` | Aggregation | Submitting review dynamically recalculates Restaurant.rating | **PASS** |

*Test Class: `restaurants.tests.SeedCommandTests` (1 Test)*

| # | Test Name | Target Unit | Verification Objective | Result |
|---|---|---|---|---|
| 20 | `test_seed_db_management_command` | CLI Tool | `manage.py seed_db` populates categories, dishes, partners, users | **PASS** |

---

### C. `orders` App (43 Tests — 100% Passing)

#### 1. Single-Restaurant Cart Validation (`orders.tests.SingleRestaurantCartValidationTests` — 6 Tests)

| # | Test Name | Rule Verified | Result |
|---|---|---|---|
| 21 | `test_empty_cart_can_add_item` | Empty cart accepts any valid menu dish | **PASS** |
| 22 | `test_add_second_item_from_same_restaurant` | Adding another dish from same restaurant succeeds | **PASS** |
| 23 | `test_attempt_to_add_item_from_different_restaurant_rejected` | Adding dish from different restaurant sets conflict session and warning | **PASS** |
| 24 | `test_clear_cart_and_add_item_from_new_restaurant` | `clear_cart=True` flag empties old restaurant cart and adds new dish | **PASS** |
| 25 | `test_dismiss_conflict_view` | Dismissing conflict popup clears session warning without modifying cart | **PASS** |
| 26 | `test_cart_direct_add_raises_mixed_restaurant_error` | Low-level `Cart.add()` throws `MixedRestaurantCartError` exception | **PASS** |
| 27 | `test_mixed_restaurant_cart_cannot_reach_successful_checkout` | Defensive checkout check blocks mixed restaurant orders | **PASS** |

#### 2. Promotional Coupon Engine (`orders.tests.CouponEngineTests` — 11 Tests)

| # | Test Name | Rule Verified | Result |
|---|---|---|---|
| 28 | `test_valid_percentage_coupon` | Correct percentage deduction computed against subtotal | **PASS** |
| 29 | `test_valid_flat_coupon` | Exact flat currency discount deducted | **PASS** |
| 30 | `test_invalid_coupon_rejected` | Non-existent coupon code is rejected with descriptive error | **PASS** |
| 31 | `test_expired_coupon_rejected` | Coupon past `valid_until` is rejected | **PASS** |
| 32 | `test_inactive_coupon_rejected` | Coupon with `is_active=False` is rejected | **PASS** |
| 33 | `test_minimum_order_requirement_failure` | Subtotal below `min_order_value` prevents redemption | **PASS** |
| 34 | `test_discount_cannot_exceed_payable_subtotal` | Discount amount capped at 100% of subtotal; payable never negative | **PASS** |
| 35 | `test_coupon_applied_to_checkout_and_place_order` | Checkout persists discount, increments `times_used`, prints on invoice | **PASS** |
| 36 | `test_tampered_client_side_discount_values_are_ignored` | Client-submitted discount/total forms ignored in favor of server math | **PASS** |
| 37 | `test_existing_orders_without_coupons_continue_to_work` | Standard orders without coupons calculate and persist seamlessly | **PASS** |
| 38 | `test_remove_coupon_view` | Removing coupon from session resets checkout totals to full amount | **PASS** |

#### 3. Dynamic Delivery Fee Engine (`orders.tests.DynamicDeliveryChargeTests` — 8 Tests)

| # | Test Name | Rule Verified | Result |
|---|---|---|---|
| 39 | `test_calculate_delivery_fee_base` | Standard subtotal < $50 within 5km incurs base fee ($4.00) | **PASS** |
| 40 | `test_calculate_delivery_fee_free_threshold` | Subtotal >= $50.00 qualifies for free delivery ($0.00 fee) | **PASS** |
| 41 | `test_calculate_delivery_fee_distance_surcharge` | Subtotal < $50 at > 5km incurs base + $1.00/km excess surcharge | **PASS** |
| 42 | `test_calculate_delivery_fee_address_tag_parsing` | Address string `[dist: 8.5km]` parsed automatically by fee engine | **PASS** |
| 43 | `test_delivery_fee_displayed_in_checkout` | Checkout view renders delivery fee and factors into payable total | **PASS** |
| 44 | `test_delivery_fee_persisted_in_database_order` | Order placement persists `delivery_fee` column in database | **PASS** |
| 45 | `test_free_delivery_persisted_for_qualifying_order` | Order >= $50 records `delivery_fee = 0.00` in database | **PASS** |
| 46 | `test_receipt_displays_delivery_fee_correctly` | Invoice receipt view items and renders exact delivery fee | **PASS** |
| 47 | `test_tampered_delivery_fee_in_client_request_is_ignored` | Client attempting to inject `delivery_fee=0` is overridden by server | **PASS** |

#### 4. GST & Tax Calculation Engine (`orders.tests.TaxCalculationTests` — 8 Tests)

| # | Test Name | Rule Verified | Result |
|---|---|---|---|
| 48 | `test_calculate_tax_standard_rate` | Tax engine calculates 5% GST on given taxable amount | **PASS** |
| 49 | `test_calculate_tax_rounding_precision` | Fractional cent rounding adheres to `ROUND_HALF_UP` Decimal standard | **PASS** |
| 50 | `test_calculate_tax_zero_or_negative` | Zero or negative taxable inputs safely produce $0.00 tax | **PASS** |
| 51 | `test_tax_applied_on_subtotal_after_coupon_discount` | GST computed exclusively on net food subtotal (after promo deduction) | **PASS** |
| 52 | `test_tax_displayed_in_cart_and_checkout_views` | Cart and checkout templates receive and render tax details | **PASS** |
| 53 | `test_order_placement_persists_tax_amount` | Placing order persists `tax_amount` column on Order record | **PASS** |
| 54 | `test_tampered_client_side_tax_ignored` | Client attempting to alter tax in POST request is overridden by server | **PASS** |
| 55 | `test_tax_invoice_receipt_displays_tax_line_item` | Tax invoice receipt renders GST rate percentage and exact tax | **PASS** |

#### 5. Cart Operations & Workflow Lifecycle (`orders.tests.OrdersCartAndWorkflowTests` — 10 Tests)

| # | Test Name | Rule Verified | Result |
|---|---|---|---|
| 56 | `test_cart_operations` | Add, update quantity, remove, and subtotal calculation | **PASS** |
| 57 | `test_cart_mutations_reject_get_requests` | Cart add, update, remove, and clear reject GET requests (HTTP 405) | **PASS** |
| 58 | `test_multi_item_order_placement_and_receipt` | Atomic multi-item order placement, payment, and receipt generation | **PASS** |
| 59 | `test_checkout_input_validation` | Checkout rejects invalid phone numbers and addresses < 5 chars | **PASS** |
| 60 | `test_cod_order_payment_status_is_pending` | COD order payment status defaults to 'Pending' | **PASS** |
| 61 | `test_admin_dashboard_and_status_update` | Staff access to `/orders/dashboard/` and 1-click status transitions | **PASS** |
| 62 | `test_item_stock_toggle_view` | Staff 1-click toggle switches `MenuItem.availability` | **PASS** |
| 63 | `test_delivery_status_choices_and_in_progress` | Delivery workflow progresses through Assigned -> In Progress -> Delivered | **PASS** |

---

## 3. Database State Precautions & Test Isolation

- **Test Database Isolation:** All tests run against temporary in-memory SQLite instances (`file:memorydb_default?mode=memory&cache=shared` and `file:memorydb_django_database?mode=memory&cache=shared`).
- **Physical Databases:** The physical production prototype databases (`food_ordering.db` and `django_database.db`) were **not** modified, altered, or truncated during the test runs.
- **Seeder Verification:** Running `run_tests.py` also runs the seeder verification test which provisions a clean demo state in the test memory database and validates demo accounts (`customer_alice`, `customer_bob`, `customer_carol`).

---

## 4. Test Suite Conclusion

- **Total Test Cases:** 63
- **Passed:** 63 (100.0%)
- **Failed:** 0
- **Errors:** 0
- **Skipped:** 0
- **Overall Quality Grade:** **A+ (Excellent functional stability and regression safety)**
