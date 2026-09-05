from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from restaurants.models import Category, Restaurant, MenuItem, Review
from orders.models import Order, OrderItem, Payment, DeliveryPartner

class RestaurantModelAndDiscoveryTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.cat_pizza = Category.objects.create(name='Pizzas', icon='bi-pie-chart-fill')
        self.cat_burger = Category.objects.create(name='Burgers', icon='bi-egg-fried')

        self.rest1 = Restaurant.objects.create(restaurant_name='Luigi Pizzeria', address='12 Roma St', rating=Decimal('4.8'))
        self.rest2 = Restaurant.objects.create(restaurant_name='Burger House', address='44 Market St', rating=Decimal('4.2'))

        self.item_pizza = MenuItem.objects.create(
            item_name='Margherita Pizza',
            category=self.cat_pizza,
            restaurant=self.rest1,
            price=Decimal('12.00'),
            description='Classic cheese and tomato pizza',
            is_veg=True,
            preparation_time=15,
            availability=True
        )

        self.item_burger = MenuItem.objects.create(
            item_name='Bacon Beef Burger',
            category=self.cat_burger,
            restaurant=self.rest2,
            price=Decimal('10.00'),
            description='Juicy beef patty with crispy bacon',
            is_veg=False,
            preparation_time=20,
            availability=True
        )

    def test_category_and_menuitem_creation(self):
        self.assertEqual(str(self.cat_pizza), 'Pizzas')
        self.assertEqual(str(self.item_pizza), f"Margherita Pizza ({self.rest1.restaurant_name})")

    def test_storefront_view_all_items(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Margherita Pizza')
        self.assertContains(resp, 'Bacon Beef Burger')

    def test_storefront_search_by_name(self):
        resp = self.client.get('/?q=Margherita')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Margherita Pizza')
        self.assertNotContains(resp, 'Bacon Beef Burger')

    def test_storefront_category_filter(self):
        resp = self.client.get(f'/?category={self.cat_burger.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Bacon Beef Burger')
        self.assertNotContains(resp, 'Margherita Pizza')

    def test_storefront_veg_filter(self):
        resp = self.client.get('/?veg=1')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Margherita Pizza')
        self.assertNotContains(resp, 'Bacon Beef Burger')

    def test_storefront_sort_price_asc(self):
        resp = self.client.get('/?sort=price_asc')
        self.assertEqual(resp.status_code, 200)
        items = list(resp.context['menu_items'])
        self.assertEqual(items[0], self.item_burger)  # 10.00 < 12.00
        self.assertEqual(items[1], self.item_pizza)


class ReviewSystemTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='reviewer', password='reviewpass123')
        self.cat = Category.objects.create(name='Italian')
        self.rest = Restaurant.objects.create(restaurant_name='Roma Bistro', address='5 Via Roma', rating=Decimal('4.0'))
        self.item = MenuItem.objects.create(
            item_name='Spaghetti Carbonara',
            category=self.cat,
            restaurant=self.rest,
            price=Decimal('11.00'),
            availability=True
        )

    def test_review_model_creation(self):
        review = Review.objects.create(
            customer=self.user,
            restaurant=self.rest,
            menu_item=self.item,
            rating=4,
            comment='Very good flavour!'
        )
        self.assertEqual(review.rating, 4)
        self.assertIn('Roma Bistro', str(review))
        self.assertIn('reviewer', str(review))

    def test_submit_review_view_updates_restaurant_rating(self):
        self.client.force_login(self.user)
        initial_rating = self.rest.rating

        resp = self.client.post('/review/submit/', {
            'restaurant_id': self.rest.id,
            'menu_item_id': self.item.id,
            'rating': 5,
            'comment': 'Best Italian in town!'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Review should be in DB
        self.assertTrue(Review.objects.filter(customer=self.user, restaurant=self.rest, rating=5).exists())

        # Restaurant rating should update
        self.rest.refresh_from_db()
        self.assertNotEqual(self.rest.rating, initial_rating)
        self.assertEqual(self.rest.rating, Decimal('5.0'))

    def test_submit_review_invalid_rating(self):
        self.client.force_login(self.user)
        resp = self.client.post('/review/submit/', {
            'restaurant_id': self.rest.id,
            'rating': 'invalid_stars',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid rating value provided')

        # Test out of range rating
        resp2 = self.client.post('/review/submit/', {
            'restaurant_id': self.rest.id,
            'rating': 10,
        }, follow=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'Rating must be an integer between 1 and 5 stars')

    def test_review_requires_login(self):
        resp = self.client.post('/review/submit/', {
            'restaurant_id': self.rest.id,
            'rating': 5,
        })
        # Should redirect to login
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_review_rejects_get(self):
        self.client.force_login(self.user)
        resp = self.client.get('/review/submit/')
        self.assertEqual(resp.status_code, 405)


class SeedCommandTests(TestCase):
    databases = '__all__'

    def test_seed_db_management_command(self):
        """Tests that the seed_db command creates all expected records."""
        from django.core.management import call_command
        call_command('seed_db', verbosity=0)

        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Restaurant.objects.count(), 5)
        self.assertEqual(MenuItem.objects.count(), 15)
        self.assertEqual(DeliveryPartner.objects.count(), 3)
        self.assertEqual(Order.objects.count(), 4)

        # Demo users should be created
        self.assertTrue(User.objects.filter(username='customer_alice').exists())
        self.assertTrue(User.objects.filter(username='customer_bob').exists())
        self.assertTrue(User.objects.filter(username='customer_carol').exists())
