from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from restaurants.models import Category, Restaurant, MenuItem
from accounts.models import CustomerProfile
from orders.models import Order, OrderItem, Payment, DeliveryPartner, Delivery, Coupon
from orders.cart import Cart

class OrdersCartAndWorkflowTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='customer1', password='password123')
        self.admin = User.objects.create_superuser(username='superadmin', password='adminpass123', email='admin@test.com')

        self.category = Category.objects.create(name='Fast Food')
        self.restaurant = Restaurant.objects.create(restaurant_name='Snack Shack', address='100 Main St', rating=Decimal('4.5'))
        self.driver = DeliveryPartner.objects.create(name='Rider Dave', phone='+1 555-1234')

        self.item1 = MenuItem.objects.create(
            item_name='Cheese Burger',
            category=self.category,
            restaurant=self.restaurant,
            price=Decimal('5.00'),
            availability=True
        )
        self.item2 = MenuItem.objects.create(
            item_name='French Fries',
            category=self.category,
            restaurant=self.restaurant,
            price=Decimal('3.00'),
            availability=True
        )

    def test_cart_operations(self):
        self.client.post(f'/orders/cart/add/{self.item1.id}/', {'quantity': 2})
        self.client.post(f'/orders/cart/add/{self.item2.id}/', {'quantity': 1})

        resp_cart = self.client.get('/orders/cart/')
        self.assertEqual(resp_cart.status_code, 200)
        self.assertContains(resp_cart, 'Cheese Burger')
        self.assertContains(resp_cart, 'French Fries')

    def test_cart_mutations_reject_get_requests(self):
        """Cart add, update, remove, and clear views must reject GET requests with HTTP 405."""
        resp_add = self.client.get(f'/orders/cart/add/{self.item1.id}/')
        self.assertEqual(resp_add.status_code, 405)

        resp_update = self.client.get(f'/orders/cart/update/{self.item1.id}/')
        self.assertEqual(resp_update.status_code, 405)

        resp_remove = self.client.get(f'/orders/cart/remove/{self.item1.id}/')
        self.assertEqual(resp_remove.status_code, 405)

        resp_clear = self.client.get('/orders/cart/clear/')
        self.assertEqual(resp_clear.status_code, 405)

    def test_multi_item_order_placement_and_receipt(self):
        self.client.force_login(self.user)
        # Add 2 burgers ($10) and 1 fries ($3)
        self.client.post(f'/orders/cart/add/{self.item1.id}/', {'quantity': 2})
        self.client.post(f'/orders/cart/add/{self.item2.id}/', {'quantity': 1})

        # Place Order with instructions
        resp_place = self.client.post('/orders/place/', {
            'payment_mode': 'UPI',
            'phone': '+1 555-7777',
            'delivery_address': '777 Lucky St',
            'special_instructions': 'Extra ketchup packets please'
        }, follow=True)

        self.assertEqual(resp_place.status_code, 200)
        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.subtotal, Decimal('13.00'))
        self.assertEqual(order.delivery_fee, Decimal('4.00'))
        self.assertEqual(order.tax_amount, Decimal('0.65'))
        self.assertEqual(order.total_amount, Decimal('17.65'))
        self.assertEqual(order.status, 'Placed')
        self.assertEqual(order.special_instructions, 'Extra ketchup packets please')
        self.assertEqual(order.items.count(), 2)

        # Verify Payment record & standardized Paid status
        payment = Payment.objects.filter(order=order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_mode, 'UPI')
        self.assertEqual(payment.payment_status, 'Paid')
        self.assertEqual(payment.amount, Decimal('17.65'))

        # Test receipt generation
        resp_receipt = self.client.get(f'/orders/receipt/{order.id}/')
        self.assertEqual(resp_receipt.status_code, 200)
        self.assertContains(resp_receipt, 'INVOICE')
        self.assertContains(resp_receipt, 'Extra ketchup packets please')

    def test_cod_order_payment_status_is_pending(self):
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item1.id}/', {'quantity': 1})

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-8888',
            'delivery_address': '888 Clover Blvd',
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertEqual(order.payment.payment_mode, 'COD')
        self.assertEqual(order.payment.payment_status, 'Pending')

    def test_checkout_input_validation(self):
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item1.id}/', {'quantity': 1})

        # Test invalid payment mode
        resp_invalid_payment = self.client.post('/orders/place/', {
            'payment_mode': 'BitCoin',
            'phone': '+1 555-9999',
            'delivery_address': '123 Valid St',
        }, follow=True)
        self.assertEqual(resp_invalid_payment.status_code, 200)
        self.assertContains(resp_invalid_payment, "Invalid payment method")
        self.assertContains(resp_invalid_payment, "BitCoin")

        # Test invalid phone number
        resp_invalid_phone = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '12',  # Too short
            'delivery_address': '123 Valid St',
        }, follow=True)
        self.assertEqual(resp_invalid_phone.status_code, 200)
        self.assertContains(resp_invalid_phone, 'valid contact phone number')

        # Test invalid/empty address
        resp_invalid_address = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-9999',
            'delivery_address': 'Hi',  # Too short
        }, follow=True)
        self.assertEqual(resp_invalid_address.status_code, 200)
        self.assertContains(resp_invalid_address, 'complete delivery address')

    def test_delivery_status_choices_and_in_progress(self):
        order = Order.objects.create(customer=self.user, status='Placed', total_amount=Decimal('10.00'))
        delivery = Delivery.objects.create(order=order, partner=self.driver, delivery_status='In Progress')
        self.assertEqual(delivery.delivery_status, 'In Progress')

        delivery.delivery_status = 'Picked Up'
        delivery.save()
        self.assertEqual(delivery.delivery_status, 'Picked Up')

        delivery.delivery_status = 'Delivered'
        delivery.save()
        self.assertEqual(delivery.delivery_status, 'Delivered')

    def test_admin_dashboard_and_status_update(self):
        order = Order.objects.create(
            customer=self.user,
            status='Placed',
            total_amount=Decimal('20.00')
        )
        OrderItem.objects.create(order=order, item=self.item1, quantity=4)

        # Login as staff/admin
        self.client.force_login(self.admin)
        resp_dash = self.client.get('/orders/dashboard/')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertContains(resp_dash, 'Restaurant Operations')

        # Update order status to Preparing and assign driver
        resp_status = self.client.post(f'/orders/status/{order.id}/', {
            'status': 'Preparing',
            'driver_id': self.driver.id
        }, follow=True)
        self.assertEqual(resp_status.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Preparing')
        self.assertEqual(order.delivery.partner, self.driver)

    def test_item_stock_toggle_view(self):
        self.client.force_login(self.admin)
        self.assertTrue(self.item1.availability)

        resp_toggle = self.client.post(f'/orders/menu/toggle/{self.item1.id}/', follow=True)
        self.assertEqual(resp_toggle.status_code, 200)
        self.item1.refresh_from_db()
        self.assertFalse(self.item1.availability)

    def test_cancel_order_view_placed_success(self):
        order = Order.objects.create(customer=self.user, status='Placed', total_amount=Decimal('15.00'))
        self.client.force_login(self.user)
        resp = self.client.post(f'/orders/cancel/{order.id}/', follow=True)
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')

    def test_cancel_order_view_in_progress_fails(self):
        order = Order.objects.create(customer=self.user, status='Preparing', total_amount=Decimal('15.00'))
        self.client.force_login(self.user)
        resp = self.client.post(f'/orders/cancel/{order.id}/', follow=True)
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Preparing')
        self.assertContains(resp, 'already in progress')

    def test_confirm_order_view_updates_payment(self):
        order = Order.objects.create(customer=self.user, status='Pending', total_amount=Decimal('15.00'))
        self.client.force_login(self.user)
        resp = self.client.post(f'/orders/confirm/{order.id}/', {'payment_mode': 'Card'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Placed')
        self.assertEqual(order.payment.payment_mode, 'Card')
        self.assertEqual(order.payment.payment_status, 'Paid')

    def test_unauthorized_receipt_view_redirects(self):
        other_user = User.objects.create_user(username='other_customer', password='password123')
        order = Order.objects.create(customer=other_user, status='Placed', total_amount=Decimal('20.00'))
        self.client.force_login(self.user)
        resp = self.client.get(f'/orders/receipt/{order.id}/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'not authorized to view this receipt')

    def test_add_delivery_partner_view(self):
        self.client.force_login(self.admin)
        resp = self.client.post('/orders/drivers/add/', {
            'name': 'Speedy Sam',
            'phone': '+1 555-4321',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(DeliveryPartner.objects.filter(name='Speedy Sam').exists())

    def test_add_delivery_partner_invalid_phone(self):
        self.client.force_login(self.admin)
        resp = self.client.post('/orders/drivers/add/', {
            'name': 'Slow Sam',
            'phone': '12',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'valid contact phone number')

    def test_non_staff_dashboard_access_denied(self):
        self.client.force_login(self.user)
        resp = self.client.get('/orders/dashboard/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Administrator credentials required')


class SingleRestaurantCartValidationTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='diner1', password='password123')
        self.category = Category.objects.create(name='Main Course')

        self.restaurant_a = Restaurant.objects.create(
            restaurant_name='Burger Barn',
            address='123 Burger Way',
            rating=Decimal('4.6')
        )
        self.restaurant_b = Restaurant.objects.create(
            restaurant_name='Sushi Spot',
            address='456 Ocean Ave',
            rating=Decimal('4.9')
        )

        self.item_a1 = MenuItem.objects.create(
            item_name='Classic Burger',
            category=self.category,
            restaurant=self.restaurant_a,
            price=Decimal('8.50'),
            availability=True
        )
        self.item_a2 = MenuItem.objects.create(
            item_name='Crispy Fries',
            category=self.category,
            restaurant=self.restaurant_a,
            price=Decimal('3.50'),
            availability=True
        )
        self.item_b1 = MenuItem.objects.create(
            item_name='Salmon Roll',
            category=self.category,
            restaurant=self.restaurant_b,
            price=Decimal('12.00'),
            availability=True
        )

    def test_empty_cart_can_add_item(self):
        """Rule 1: Empty cart can add any available menu item."""
        resp = self.client.post(f'/orders/cart/add/{self.item_a1.id}/', {'quantity': 1}, follow=True)
        self.assertEqual(resp.status_code, 200)
        session = self.client.session
        self.assertIn(str(self.item_a1.id), session['cart'])
        self.assertEqual(session['cart'][str(self.item_a1.id)], 1)

    def test_add_second_item_from_same_restaurant(self):
        """Rule 2: Adding a second item from the same restaurant is allowed."""
        self.client.post(f'/orders/cart/add/{self.item_a1.id}/', {'quantity': 2})
        self.client.post(f'/orders/cart/add/{self.item_a2.id}/', {'quantity': 1})

        resp_cart = self.client.get('/orders/cart/')
        self.assertEqual(resp_cart.status_code, 200)
        self.assertContains(resp_cart, 'Classic Burger')
        self.assertContains(resp_cart, 'Crispy Fries')
        self.assertContains(resp_cart, 'Burger Barn')

    def test_attempt_to_add_item_from_different_restaurant_rejected(self):
        """Rule 3: Adding item from another restaurant does NOT mix; shows warning and session conflict."""
        self.client.post(f'/orders/cart/add/{self.item_a1.id}/', {'quantity': 1})

        # Attempt to add Sushi Spot item
        resp = self.client.post(f'/orders/cart/add/{self.item_b1.id}/', {'quantity': 2}, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Cart must NOT contain Sushi Spot item
        session = self.client.session
        self.assertNotIn(str(self.item_b1.id), session['cart'])
        self.assertIn(str(self.item_a1.id), session['cart'])

        # User is warned and conflict modal data is recorded
        self.assertContains(resp, 'Burger Barn')
        self.assertContains(resp, 'Replace Cart Items')
        self.assertEqual(session.get('restaurant_conflict')['new_restaurant_name'], 'Sushi Spot')

    def test_clear_cart_and_add_item_from_new_restaurant(self):
        """Rule 4: Clearing cart allows adding items from new restaurant."""
        self.client.post(f'/orders/cart/add/{self.item_a1.id}/', {'quantity': 1})

        # Confirm clear and switch to Restaurant B
        resp = self.client.post(f'/orders/cart/add/{self.item_b1.id}/', {
            'quantity': 3,
            'clear_cart': 'true'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        session = self.client.session
        self.assertNotIn(str(self.item_a1.id), session['cart'])
        self.assertIn(str(self.item_b1.id), session['cart'])
        self.assertEqual(session['cart'][str(self.item_b1.id)], 3)
        self.assertNotIn('restaurant_conflict', session)

    def test_mixed_restaurant_cart_cannot_reach_successful_checkout(self):
        """Rule 5: Defensive integrity check prevents mixed restaurant checkout."""
        self.client.force_login(self.user)

        # Artificially inject mixed restaurant items into session
        session = self.client.session
        session['cart'] = {str(self.item_a1.id): 1, str(self.item_b1.id): 1}
        session.save()

        # Checkout page must reject and redirect to cart
        resp_checkout = self.client.get('/orders/checkout/', follow=True)
        self.assertRedirects(resp_checkout, '/orders/cart/')
        self.assertContains(resp_checkout, 'items from multiple restaurants')

        # Place order endpoint must reject and create NO order
        resp_place = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-4321',
            'delivery_address': '123 Test St'
        }, follow=True)
        self.assertRedirects(resp_place, '/orders/cart/')
        self.assertContains(resp_place, 'items from multiple restaurants')
        self.assertEqual(Order.objects.filter(customer=self.user).count(), 0)

    def test_cart_direct_add_raises_mixed_restaurant_error(self):
        """Rule 6: Low-level Cart.add() enforces single-restaurant constraint."""
        from orders.cart import MixedRestaurantCartError
        session = self.client.session
        session['cart'] = {str(self.item_a1.id): 1}
        session.save()

        request = resp = self.client.get('/orders/cart/').wsgi_request
        cart = Cart(request)
        with self.assertRaises(MixedRestaurantCartError):
            cart.add(item_id=self.item_b1.id, quantity=1)

    def test_dismiss_conflict_view(self):
        """Dismissing the conflict dialog cleans up session without altering cart."""
        self.client.post(f'/orders/cart/add/{self.item_a1.id}/', {'quantity': 1})
        self.client.post(f'/orders/cart/add/{self.item_b1.id}/', {'quantity': 1})

        self.assertIn('restaurant_conflict', self.client.session)
        resp_dismiss = self.client.post('/orders/cart/dismiss-conflict/', follow=True)
        self.assertEqual(resp_dismiss.status_code, 200)
        self.assertNotIn('restaurant_conflict', self.client.session)
        # Cart still has Restaurant A item
        self.assertIn(str(self.item_a1.id), self.client.session['cart'])


class CouponEngineTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='shopper1', password='password123')
        self.category = Category.objects.create(name='Pizzas')
        self.restaurant = Restaurant.objects.create(
            restaurant_name='Napoli Crust',
            address='12 Via Roma',
            rating=Decimal('4.7')
        )
        self.item = MenuItem.objects.create(
            item_name='Large Pepperoni',
            category=self.category,
            restaurant=self.restaurant,
            price=Decimal('20.00'),
            availability=True
        )
        self.now = timezone.now()

        # 1. 20% off coupon, min $15, max cap $10
        self.coupon_pct = Coupon.objects.create(
            code='SAVE20',
            discount_type='PERCENTAGE',
            discount_value=Decimal('20.00'),
            min_order_value=Decimal('15.00'),
            max_discount_amount=Decimal('10.00'),
            is_active=True,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            max_uses=10,
            times_used=0
        )

        # 2. $5 flat coupon, min $10
        self.coupon_flat = Coupon.objects.create(
            code='FLAT5',
            discount_type='FLAT',
            discount_value=Decimal('5.00'),
            min_order_value=Decimal('10.00'),
            is_active=True,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30)
        )

        # 3. Expired coupon
        self.coupon_expired = Coupon.objects.create(
            code='EXPIRED50',
            discount_type='PERCENTAGE',
            discount_value=Decimal('50.00'),
            min_order_value=Decimal('10.00'),
            is_active=True,
            valid_from=self.now - timedelta(days=30),
            valid_until=self.now - timedelta(days=1)
        )

        # 4. Inactive coupon
        self.coupon_inactive = Coupon.objects.create(
            code='INACTIVE',
            discount_type='FLAT',
            discount_value=Decimal('10.00'),
            min_order_value=Decimal('5.00'),
            is_active=False,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30)
        )

        # 5. High minimum order coupon ($100 min)
        self.coupon_high_min = Coupon.objects.create(
            code='BIGSPENDER',
            discount_type='PERCENTAGE',
            discount_value=Decimal('30.00'),
            min_order_value=Decimal('100.00'),
            is_active=True,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30)
        )

        # 6. Flat coupon exceeding subtotal ($50 off)
        self.coupon_super_flat = Coupon.objects.create(
            code='FREEPIZZA',
            discount_type='FLAT',
            discount_value=Decimal('50.00'),
            min_order_value=Decimal('10.00'),
            is_active=True,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30)
        )

    def test_valid_percentage_coupon(self):
        """Rule 1: Valid percentage coupon applies correctly and recalculates subtotal."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20.00
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'SAVE20'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get('coupon_code'), 'SAVE20')
        self.assertContains(resp, 'SAVE20')
        self.assertContains(resp, '-₹4.00')

    def test_valid_flat_coupon(self):
        """Rule 2: Valid flat coupon deducts exact flat amount."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20.00
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'FLAT5'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get('coupon_code'), 'FLAT5')
        self.assertContains(resp, '-₹5.00')

    def test_invalid_coupon_rejected(self):
        """Rule 3: Invalid/non-existent coupon code is rejected with error."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'DOESNOTEXIST'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('coupon_code', self.client.session)
        self.assertContains(resp, 'invalid or does not exist')

    def test_expired_coupon_rejected(self):
        """Rule 4: Expired coupon is rejected."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'EXPIRED50'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('coupon_code', self.client.session)
        self.assertContains(resp, 'has expired')

    def test_inactive_coupon_rejected(self):
        """Rule 5: Inactive coupon is rejected."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'INACTIVE'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('coupon_code', self.client.session)
        self.assertContains(resp, 'is inactive')

    def test_minimum_order_requirement_failure(self):
        """Rule 6: Coupon rejected when order subtotal is below min_order_value."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20 < $100 min
        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'BIGSPENDER'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('coupon_code', self.client.session)
        self.assertContains(resp, 'below the minimum required')

    def test_discount_cannot_exceed_payable_subtotal(self):
        """Rule 7: Discount is capped at subtotal so payable amount never goes negative."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20.00 subtotal
        # FLAT50 gives $50 off on $20 order -> discount should cap at $20.00, payable = $0.00
        disc = self.coupon_super_flat.calculate_discount(Decimal('20.00'))
        self.assertEqual(disc, Decimal('20.00'))

        resp = self.client.post('/orders/coupon/apply/', {'coupon_code': 'FREEPIZZA'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '-₹20.00')

    def test_coupon_applied_to_checkout_and_place_order(self):
        """Rule 8: Coupon discount persists on order, updates times_used, and appears on receipt."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 2})  # $40.00
        self.client.post('/orders/coupon/apply/', {'coupon_code': 'SAVE20'})  # 20% of 40 = $8.00

        # Check checkout view reflects coupon
        resp_checkout = self.client.get('/orders/checkout/')
        self.assertEqual(resp_checkout.status_code, 200)
        self.assertContains(resp_checkout, 'SAVE20')
        self.assertContains(resp_checkout, '-₹8.00')

        # Place order
        resp_place = self.client.post('/orders/place/', {
            'payment_mode': 'UPI',
            'phone': '+1 555-6677',
            'delivery_address': '888 Pizza Lane'
        }, follow=True)
        self.assertEqual(resp_place.status_code, 200)

        # Verify DB order record
        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.subtotal, Decimal('40.00'))
        self.assertEqual(order.coupon, self.coupon_pct)
        self.assertEqual(order.discount_amount, Decimal('8.00'))
        self.assertEqual(order.delivery_fee, Decimal('4.00'))
        self.assertEqual(order.tax_amount, Decimal('1.60'))
        self.assertEqual(order.total_amount, Decimal('37.60'))

        # Verify payment amount matches final total
        self.assertEqual(order.payment.amount, Decimal('37.60'))

        # Verify coupon times_used incremented
        self.coupon_pct.refresh_from_db()
        self.assertEqual(self.coupon_pct.times_used, 1)

        # Verify receipt displays subtotal, discount, delivery fee, and total
        resp_receipt = self.client.get(f'/orders/receipt/{order.id}/')
        self.assertEqual(resp_receipt.status_code, 200)
        self.assertContains(resp_receipt, '₹40.00')
        self.assertContains(resp_receipt, '-₹8.00')
        self.assertContains(resp_receipt, 'SAVE20')
        self.assertContains(resp_receipt, '₹4.00')
        self.assertContains(resp_receipt, '₹1.60')
        self.assertContains(resp_receipt, '₹37.60')

    def test_tampered_client_side_discount_values_are_ignored(self):
        """Rule 9: Client cannot tamper with total_amount or discount in POST request."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20.00
        # Tampered POST with malicious total and discount
        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-1234',
            'delivery_address': '123 Fake St',
            'discount_amount': '19.99',
            'total_amount': '0.01'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        # Server must ignore tampered fields and charge genuine subtotal + delivery fee + tax ($25.00)
        self.assertEqual(order.subtotal, Decimal('20.00'))
        self.assertEqual(order.discount_amount, Decimal('0.00'))
        self.assertEqual(order.delivery_fee, Decimal('4.00'))
        self.assertEqual(order.tax_amount, Decimal('1.00'))
        self.assertEqual(order.total_amount, Decimal('25.00'))
        self.assertEqual(order.payment.amount, Decimal('25.00'))

    def test_existing_orders_without_coupons_continue_to_work(self):
        """Rule 10: Standard checkout without coupon continues to function seamlessly."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})  # $20.00

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-1234',
            'delivery_address': '123 Standard St',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertIsNone(order.coupon)
        self.assertEqual(order.discount_amount, Decimal('0.00'))
        self.assertEqual(order.delivery_fee, Decimal('4.00'))
        self.assertEqual(order.tax_amount, Decimal('1.00'))
        self.assertEqual(order.total_amount, Decimal('25.00'))

    def test_remove_coupon_view(self):
        """Rule 11: Customer can remove an applied coupon from session."""
        self.client.post(f'/orders/cart/add/{self.item.id}/', {'quantity': 1})
        self.client.post('/orders/coupon/apply/', {'coupon_code': 'SAVE20'})
        self.assertEqual(self.client.session.get('coupon_code'), 'SAVE20')

        resp_remove = self.client.post('/orders/coupon/remove/', follow=True)
        self.assertEqual(resp_remove.status_code, 200)
        self.assertNotIn('coupon_code', self.client.session)


class DynamicDeliveryChargeTests(TestCase):
    """
    Automated test suite for Phase 1 Task 3: Dynamic Delivery Charges.
    """
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Main Course")
        self.restaurant = Restaurant.objects.create(
            restaurant_name="Spice Haven",
            address="100 Curry Road",
            rating=Decimal('4.5')
        )
        self.item_cheap = MenuItem.objects.create(
            restaurant=self.restaurant,
            item_name="Naan",
            category=self.category,
            price=Decimal('10.00'),
            availability=True
        )
        self.item_expensive = MenuItem.objects.create(
            restaurant=self.restaurant,
            item_name="Grand Feast Platter",
            category=self.category,
            price=Decimal('60.00'),
            availability=True
        )
        self.user = User.objects.create_user(
            username="delivery_tester",
            email="delivery@test.com",
            password="Password@123"
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone="+1 555-4321",
            address="500 Elm Street [dist: 8.5km]"
        )

    def test_calculate_delivery_fee_base(self):
        """Standard subtotal below $50 and within 5km incurs base fee ($4.00)."""
        from orders.services import calculate_delivery_fee
        fee = calculate_delivery_fee(Decimal('30.00'), distance_km=3.0)
        self.assertEqual(fee, Decimal('4.00'))

    def test_calculate_delivery_fee_free_threshold(self):
        """Subtotal >= $50.00 qualifies for free delivery ($0.00)."""
        from orders.services import calculate_delivery_fee
        fee = calculate_delivery_fee(Decimal('50.00'), distance_km=10.0)
        self.assertEqual(fee, Decimal('0.00'))

        fee2 = calculate_delivery_fee(Decimal('75.50'), distance_km=4.0)
        self.assertEqual(fee2, Decimal('0.00'))

    def test_calculate_delivery_fee_distance_surcharge(self):
        """Subtotal < $50 with distance > 5km incurs $1.00/km beyond 5km."""
        from orders.services import calculate_delivery_fee
        # 8 km: 5km base + 3km extra @ $1.00 = $4.00 + $3.00 = $7.00
        fee = calculate_delivery_fee(Decimal('25.00'), distance_km=8.0)
        self.assertEqual(fee, Decimal('7.00'))

    def test_calculate_delivery_fee_address_tag_parsing(self):
        """Address containing [dist: Xkm] automatically determines distance."""
        from orders.services import calculate_delivery_fee
        # 10 km: base $4.00 + 5km extra @ $1.00 = $9.00
        fee = calculate_delivery_fee(Decimal('20.00'), delivery_address="77 Outer Ring Rd [dist: 10km]")
        self.assertEqual(fee, Decimal('9.00'))

    def test_delivery_fee_displayed_in_checkout(self):
        """Checkout UI displays calculated delivery fee and includes it in total."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_cheap.id}/', {'quantity': 2})  # $20.00

        resp = self.client.get('/orders/checkout/')
        self.assertEqual(resp.status_code, 200)
        # Verify delivery_fee, tax_amount and final total_price are present in context
        self.assertIn('delivery_fee', resp.context)
        self.assertIn('tax_amount', resp.context)
        self.assertIn('total_price', resp.context)
        self.assertEqual(resp.context['subtotal'], Decimal('20.00'))
        self.assertEqual(resp.context['delivery_fee'], Decimal('7.50'))
        self.assertEqual(resp.context['tax_amount'], Decimal('1.00'))
        self.assertEqual(resp.context['total_price'], Decimal('28.50'))

    def test_delivery_fee_persisted_in_database_order(self):
        """Order placement correctly persists delivery_fee in DB and calculates total_amount."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_cheap.id}/', {'quantity': 2})  # $20.00

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-4321',
            'delivery_address': '500 Elm Street [dist: 8.0km]'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertIsNotNone(order)
        # 8 km distance => $4.00 base + 3km extra @ $1 = $7.00
        self.assertEqual(order.delivery_fee, Decimal('7.00'))
        self.assertEqual(order.subtotal, Decimal('20.00'))
        self.assertEqual(order.tax_amount, Decimal('1.00'))
        self.assertEqual(order.total_amount, Decimal('28.00'))
        self.assertEqual(order.payment.amount, Decimal('28.00'))

    def test_free_delivery_persisted_for_qualifying_order(self):
        """Orders >= $50.00 have delivery_fee = $0.00 persisted."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_expensive.id}/', {'quantity': 1})  # $60.00

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-4321',
            'delivery_address': '500 Elm Street [dist: 8.0km]'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertEqual(order.delivery_fee, Decimal('0.00'))
        self.assertEqual(order.subtotal, Decimal('60.00'))
        self.assertEqual(order.tax_amount, Decimal('3.00'))
        self.assertEqual(order.total_amount, Decimal('63.00'))

    def test_tampered_delivery_fee_in_client_request_is_ignored(self):
        """Server ignores any client-submitted delivery_fee or total_amount tampering."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_cheap.id}/', {'quantity': 1})  # $10.00

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-4321',
            'delivery_address': '123 Plain St',
            'delivery_fee': '0.00',  # Tampered to $0
            'total_amount': '1.00'   # Tampered total
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertEqual(order.delivery_fee, Decimal('4.00'))  # Default base fee
        self.assertEqual(order.subtotal, Decimal('10.00'))
        self.assertEqual(order.tax_amount, Decimal('0.50'))
        self.assertEqual(order.total_amount, Decimal('14.50'))

    def test_receipt_displays_delivery_fee_correctly(self):
        """Receipt page renders delivery fee line item accurately."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_cheap.id}/', {'quantity': 1})  # $10.00

        self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-4321',
            'delivery_address': '123 Plain St'
        }, follow=True)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        receipt_resp = self.client.get(f'/orders/receipt/{order.id}/')
        self.assertEqual(receipt_resp.status_code, 200)
        self.assertContains(receipt_resp, "Delivery Charge:")
        self.assertContains(receipt_resp, "₹4.00")


class TaxCalculationTests(TestCase):
    """
    Automated test suite for Phase 1 Task 4: GST / Tax Calculation.
    """
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Dinner Specials")
        self.restaurant = Restaurant.objects.create(
            restaurant_name="Royal Curry Lounge",
            address="45 Palace Road",
            rating=Decimal('4.8')
        )
        self.item_a = MenuItem.objects.create(
            restaurant=self.restaurant,
            item_name="Butter Chicken",
            category=self.category,
            price=Decimal('20.00'),
            availability=True
        )
        self.item_b = MenuItem.objects.create(
            restaurant=self.restaurant,
            item_name="Garlic Naan",
            category=self.category,
            price=Decimal('5.50'),
            availability=True
        )
        self.user = User.objects.create_user(
            username="tax_tester",
            email="taxtester@test.com",
            password="Password@123"
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone="+1 555-9999",
            address="100 Tax Avenue"
        )
        now = timezone.now()
        self.coupon = Coupon.objects.create(
            code="FLAT10",
            discount_type="FLAT",
            discount_value=Decimal('10.00'),
            min_order_value=Decimal('15.00'),
            is_active=True,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=10)
        )

    def test_calculate_tax_standard_rate(self):
        """Rule 1: Tax engine calculates 5% GST on given taxable amount accurately."""
        from orders.services import calculate_tax
        # 5% of $100.00 = $5.00
        tax100 = calculate_tax(Decimal('100.00'))
        self.assertEqual(tax100, Decimal('5.00'))

        # 5% of $20.00 = $1.00
        tax20 = calculate_tax(Decimal('20.00'))
        self.assertEqual(tax20, Decimal('1.00'))

    def test_calculate_tax_rounding_precision(self):
        """Rule 2: Decimal ROUND_HALF_UP rounding handles fractional cents correctly."""
        from orders.services import calculate_tax
        # $12.35 * 0.05 = 0.6175 -> $0.62
        self.assertEqual(calculate_tax(Decimal('12.35')), Decimal('0.62'))
        # $12.30 * 0.05 = 0.6150 -> $0.62 (half up)
        self.assertEqual(calculate_tax(Decimal('12.30')), Decimal('0.62'))
        # $12.25 * 0.05 = 0.6125 -> $0.61
        self.assertEqual(calculate_tax(Decimal('12.25')), Decimal('0.61'))

    def test_calculate_tax_zero_or_negative(self):
        """Rule 3: Zero or negative taxable amount safely yields $0.00 tax."""
        from orders.services import calculate_tax
        self.assertEqual(calculate_tax(Decimal('0.00')), Decimal('0.00'))
        self.assertEqual(calculate_tax(Decimal('-10.00')), Decimal('0.00'))
        self.assertEqual(calculate_tax(None), Decimal('0.00'))

    def test_tax_applied_on_subtotal_after_coupon_discount(self):
        """Rule 4: Tax is computed on net food subtotal (subtotal - coupon discount)."""
        # Subtotal: $20.00 (Butter Chicken) - $10.00 (FLAT10) = $10.00 net
        # 5% of $10.00 = $0.50 tax
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_a.id}/', {'quantity': 1})
        self.client.post('/orders/coupon/apply/', {'coupon_code': 'FLAT10'})

        resp = self.client.get('/orders/checkout/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['subtotal'], Decimal('20.00'))
        self.assertEqual(resp.context['discount_amount'], Decimal('10.00'))
        self.assertEqual(resp.context['tax_amount'], Decimal('0.50'))
        # Delivery fee: $4.00; Grand total: $10.00 net + $4.00 delivery + $0.50 tax = $14.50
        self.assertEqual(resp.context['total_price'], Decimal('14.50'))

    def test_tax_displayed_in_cart_and_checkout_views(self):
        """Rule 5: Cart and Checkout templates receive and render tax details."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_a.id}/', {'quantity': 1})  # $20.00

        # Cart view
        resp_cart = self.client.get('/orders/cart/')
        self.assertEqual(resp_cart.status_code, 200)
        self.assertIn('tax_amount', resp_cart.context)
        self.assertEqual(resp_cart.context['tax_amount'], Decimal('1.00'))
        self.assertContains(resp_cart, "GST / Tax (5%)")
        self.assertContains(resp_cart, "₹1.00")

        # Checkout view
        resp_checkout = self.client.get('/orders/checkout/')
        self.assertEqual(resp_checkout.status_code, 200)
        self.assertIn('tax_amount', resp_checkout.context)
        self.assertEqual(resp_checkout.context['tax_amount'], Decimal('1.00'))
        self.assertContains(resp_checkout, "GST / Tax (5%)")
        self.assertContains(resp_checkout, "₹1.00")

    def test_order_placement_persists_tax_amount(self):
        """Rule 6: Placing an order saves tax_amount to DB and factors into total_amount."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_a.id}/', {'quantity': 1})  # $20.00
        self.client.post(f'/orders/cart/add/{self.item_b.id}/', {'quantity': 1})  # $5.50
        # Subtotal = $25.50; Tax (5%) = 25.50 * 0.05 = 1.275 -> $1.28
        # Delivery fee = $4.00; Total = $25.50 + $4.00 + $1.28 = $30.78

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-9999',
            'delivery_address': '100 Tax Avenue'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.subtotal, Decimal('25.50'))
        self.assertEqual(order.delivery_fee, Decimal('4.00'))
        self.assertEqual(order.tax_amount, Decimal('1.28'))
        self.assertEqual(order.total_amount, Decimal('30.78'))
        self.assertEqual(order.payment.amount, Decimal('30.78'))

    def test_tampered_client_side_tax_ignored(self):
        """Rule 7: Server authoritative calculation ignores tampered client tax values."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_a.id}/', {'quantity': 1})  # $20.00

        resp = self.client.post('/orders/place/', {
            'payment_mode': 'COD',
            'phone': '+1 555-9999',
            'delivery_address': '100 Tax Avenue',
            'tax_amount': '0.00',    # Malicious bypass attempt
            'total_amount': '1.00',  # Malicious price tamper
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        # Genuine 5% tax of $20.00 is $1.00; delivery $4.00; total $25.00
        self.assertEqual(order.tax_amount, Decimal('1.00'))
        self.assertEqual(order.total_amount, Decimal('25.00'))
        self.assertEqual(order.payment.amount, Decimal('25.00'))

    def test_tax_invoice_receipt_displays_tax_line_item(self):
        """Rule 8: Official tax invoice receipt displays GST rate and exact calculated tax."""
        self.client.force_login(self.user)
        self.client.post(f'/orders/cart/add/{self.item_a.id}/', {'quantity': 1})  # $20.00

        self.client.post('/orders/place/', {
            'payment_mode': 'Card',
            'phone': '+1 555-9999',
            'delivery_address': '100 Tax Avenue'
        }, follow=True)

        order = Order.objects.filter(customer=self.user).order_by('-id').first()
        resp_receipt = self.client.get(f'/orders/receipt/{order.id}/')
        self.assertEqual(resp_receipt.status_code, 200)
        self.assertContains(resp_receipt, "GST / Tax (5%):")
        self.assertContains(resp_receipt, "₹1.00")
        self.assertContains(resp_receipt, "₹25.00")




