from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User

from restaurants.models import Category, Restaurant, MenuItem
from orders.models import Order, OrderItem, Payment, DeliveryPartner, Delivery
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
        self.assertEqual(order.total_amount, Decimal('13.00'))
        self.assertEqual(order.status, 'Placed')
        self.assertEqual(order.special_instructions, 'Extra ketchup packets please')
        self.assertEqual(order.items.count(), 2)

        # Verify Payment record & standardized Paid status
        payment = Payment.objects.filter(order=order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_mode, 'UPI')
        self.assertEqual(payment.payment_status, 'Paid')
        self.assertEqual(payment.amount, Decimal('13.00'))

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
