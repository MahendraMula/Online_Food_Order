"""
Custom Django management command: seed_db
Usage: python manage.py seed_db [--clear]

Populates the database with a rich realistic dataset for demo/development purposes.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import CustomerProfile
from restaurants.models import Category, Restaurant, MenuItem, Review
from orders.models import Order, OrderItem, Payment, DeliveryPartner, Delivery


CATEGORIES = [
    {'name': 'Burgers', 'icon': 'bi-egg-fried', 'description': 'Juicy beef and veggie burgers'},
    {'name': 'Pizzas', 'icon': 'bi-pie-chart-fill', 'description': 'Thin-crust and deep-dish pizzas'},
    {'name': 'Sushi', 'icon': 'bi-water', 'description': 'Fresh nigiri, rolls, and sashimi'},
    {'name': 'Indian', 'icon': 'bi-fire', 'description': 'Rich curries, biryani, and tandoor items'},
    {'name': 'Desserts', 'icon': 'bi-cake2-fill', 'description': 'Cakes, ice cream, and sweet bites'},
    {'name': 'Beverages', 'icon': 'bi-cup-straw', 'description': 'Refreshing drinks and smoothies'},
]

RESTAURANTS = [
    {'name': 'The Burger Lab', 'address': '12 Market Street, Downtown', 'rating': Decimal('4.7'), 'image_url': '/images/restaurants/the_burger_lab.jpg'},
    {'name': 'Luigi Pizzeria', 'address': '44 Roma Avenue, Little Italy', 'rating': Decimal('4.8'), 'image_url': '/images/restaurants/luigi_pizzeria.jpg'},
    {'name': 'Tokyo Bites', 'address': '7 Sakura Lane, Japantown', 'rating': Decimal('4.9'), 'image_url': '/images/restaurants/tokyo_bites.jpg'},
    {'name': 'Spice Garden', 'address': '21 Curry Mile, East Side', 'rating': Decimal('4.6'), 'image_url': '/images/restaurants/spice_garden.jpg'},
    {'name': 'Sweet Endings', 'address': '5 Dessert Drive, West End', 'rating': Decimal('4.5'), 'image_url': '/images/restaurants/sweet_endings.jpg'},
]

MENU_ITEMS = [
    # Burgers
    {'name': 'Smash Burger', 'cat': 'Burgers', 'rest': 'The Burger Lab', 'price': Decimal('9.99'), 'is_veg': False, 'prep': 12, 'desc': 'Double smash patty with cheddar and pickles', 'image_url': '/images/menu/smash_burger.jpg'},
    {'name': 'Veggie Bliss Burger', 'cat': 'Burgers', 'rest': 'The Burger Lab', 'price': Decimal('8.49'), 'is_veg': True, 'prep': 10, 'desc': 'Black bean patty with avocado and lettuce', 'image_url': '/images/menu/veggie_bliss_burger.jpg'},
    {'name': 'Bacon Cheeseburger', 'cat': 'Burgers', 'rest': 'The Burger Lab', 'price': Decimal('11.99'), 'is_veg': False, 'prep': 14, 'desc': 'Crispy bacon, cheddar, caramelized onions', 'image_url': '/images/menu/bacon_cheeseburger.jpg'},
    # Pizzas
    {'name': 'Margherita Pizza', 'cat': 'Pizzas', 'rest': 'Luigi Pizzeria', 'price': Decimal('12.00'), 'is_veg': True, 'prep': 15, 'desc': 'Classic tomato sauce, mozzarella, fresh basil', 'image_url': '/images/menu/margherita_pizza.jpg'},
    {'name': 'Pepperoni Supreme', 'cat': 'Pizzas', 'rest': 'Luigi Pizzeria', 'price': Decimal('14.50'), 'is_veg': False, 'prep': 18, 'desc': 'Double pepperoni with extra cheese blend', 'image_url': '/images/menu/pepperoni_supreme.jpg'},
    {'name': 'BBQ Chicken Pizza', 'cat': 'Pizzas', 'rest': 'Luigi Pizzeria', 'price': Decimal('15.00'), 'is_veg': False, 'prep': 20, 'desc': 'Smoky BBQ sauce, grilled chicken, red onion', 'image_url': '/images/menu/bbq_chicken_pizza.jpg'},
    # Sushi
    {'name': 'Dragon Roll', 'cat': 'Sushi', 'rest': 'Tokyo Bites', 'price': Decimal('16.00'), 'is_veg': False, 'prep': 20, 'desc': 'Shrimp tempura topped with avocado and eel sauce', 'image_url': '/images/menu/dragon_roll.jpg'},
    {'name': 'Spicy Tuna Roll', 'cat': 'Sushi', 'rest': 'Tokyo Bites', 'price': Decimal('13.50'), 'is_veg': False, 'prep': 15, 'desc': 'Fresh tuna, spicy mayo, cucumber', 'image_url': '/images/menu/spicy_tuna_roll.jpg'},
    {'name': 'Veggie Avocado Roll', 'cat': 'Sushi', 'rest': 'Tokyo Bites', 'price': Decimal('10.00'), 'is_veg': True, 'prep': 12, 'desc': 'Creamy avocado, cucumber, pickled radish', 'image_url': '/images/menu/veggie_avocado_roll.jpg'},
    # Indian
    {'name': 'Butter Chicken', 'cat': 'Indian', 'rest': 'Spice Garden', 'price': Decimal('13.00'), 'is_veg': False, 'prep': 25, 'desc': 'Tender chicken in rich tomato cream sauce', 'image_url': '/images/menu/butter_chicken.jpg'},
    {'name': 'Paneer Tikka Masala', 'cat': 'Indian', 'rest': 'Spice Garden', 'price': Decimal('12.00'), 'is_veg': True, 'prep': 22, 'desc': 'Grilled paneer in spiced tomato gravy', 'image_url': '/images/menu/paneer_tikka_masala.jpg'},
    {'name': 'Lamb Biryani', 'cat': 'Indian', 'rest': 'Spice Garden', 'price': Decimal('16.00'), 'is_veg': False, 'prep': 30, 'desc': 'Fragrant basmati rice layered with spiced lamb', 'image_url': '/images/menu/lamb_biryani.jpg'},
    # Desserts
    {'name': 'Chocolate Lava Cake', 'cat': 'Desserts', 'rest': 'Sweet Endings', 'price': Decimal('6.50'), 'is_veg': True, 'prep': 10, 'desc': 'Warm dark chocolate cake with molten center', 'image_url': '/images/menu/chocolate_lava_cake.jpg'},
    {'name': 'Mango Sorbet', 'cat': 'Desserts', 'rest': 'Sweet Endings', 'price': Decimal('5.00'), 'is_veg': True, 'prep': 5, 'desc': 'Refreshing tropical mango sorbet, 2 scoops', 'image_url': '/images/menu/mango_sorbet.jpg'},
    {'name': 'New York Cheesecake', 'cat': 'Desserts', 'rest': 'Sweet Endings', 'price': Decimal('7.00'), 'is_veg': True, 'prep': 5, 'desc': 'Classic dense and creamy NY-style cheesecake', 'image_url': '/images/menu/new_york_cheesecake.jpg'},
]

DELIVERY_PARTNERS = [
    {'name': 'Alex Johnson', 'phone': '+1 555-1001'},
    {'name': 'Maria Garcia', 'phone': '+1 555-2002'},
    {'name': 'David Kim', 'phone': '+1 555-3003'},
]


class Command(BaseCommand):
    help = 'Seeds the database with realistic demo data for restaurants, menus, users, and orders.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing seed data before seeding.',
        )

    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)

        def log(msg, style=None):
            if verbosity > 0:
                if style:
                    self.stdout.write(style(msg))
                else:
                    self.stdout.write(msg)

        if options['clear']:
            log('Clearing existing data...', self.style.WARNING)
            Review.objects.all().delete()
            OrderItem.objects.all().delete()
            Payment.objects.all().delete()
            Delivery.objects.all().delete()
            Order.objects.all().delete()
            MenuItem.objects.all().delete()
            Category.objects.all().delete()
            Restaurant.objects.all().delete()
            DeliveryPartner.objects.all().delete()
            CustomerProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            log('All data cleared.', self.style.WARNING)

        log('Seeding categories...')
        cat_map = {}
        for c in CATEGORIES:
            obj, _ = Category.objects.get_or_create(name=c['name'], defaults={'icon': c['icon'], 'description': c['description']})
            cat_map[c['name']] = obj

        log('Seeding restaurants...')
        rest_map = {}
        for r in RESTAURANTS:
            obj, _ = Restaurant.objects.get_or_create(restaurant_name=r['name'], defaults={'address': r['address'], 'rating': r['rating'], 'image_url': r['image_url']})
            rest_map[r['name']] = obj

        log('Seeding menu items...')
        item_map = {}
        for item in MENU_ITEMS:
            cat_obj = cat_map.get(item['cat'])
            rest_obj = rest_map.get(item['rest'])
            if not cat_obj or not rest_obj:
                continue
            obj, _ = MenuItem.objects.get_or_create(
                item_name=item['name'],
                restaurant=rest_obj,
                defaults={
                    'category': cat_obj,
                    'price': item['price'],
                    'is_veg': item['is_veg'],
                    'preparation_time': item['prep'],
                    'description': item['desc'],
                    'image_url': item['image_url'],
                    'availability': True,
                }
            )
            item_map[item['name']] = obj

        log('Seeding delivery partners...')
        driver_map = {}
        for d in DELIVERY_PARTNERS:
            obj, _ = DeliveryPartner.objects.get_or_create(name=d['name'], defaults={'phone': d['phone']})
            driver_map[d['name']] = obj

        log('Seeding demo customer users...')
        demo_users = []
        customers_data = [
            {'username': 'customer_alice', 'email': 'alice@demo.com', 'first_name': 'Alice', 'last_name': 'Walker', 'phone': '+1 555-4001', 'address': '101 Maple St'},
            {'username': 'customer_bob', 'email': 'bob@demo.com', 'first_name': 'Bob', 'last_name': 'Smith', 'phone': '+1 555-4002', 'address': '202 Oak Ave'},
            {'username': 'customer_carol', 'email': 'carol@demo.com', 'first_name': 'Carol', 'last_name': 'Jones', 'phone': '+1 555-4003', 'address': '303 Pine Blvd'},
        ]
        for cd in customers_data:
            user, created = User.objects.get_or_create(username=cd['username'], defaults={
                'email': cd['email'], 'first_name': cd['first_name'], 'last_name': cd['last_name']
            })
            if created:
                user.set_password('Demo@1234')
                user.save()
            CustomerProfile.objects.get_or_create(user=user, defaults={'phone': cd['phone'], 'address': cd['address']})
            demo_users.append(user)

        log('Seeding sample orders...')
        sample_orders = [
            {
                'customer': demo_users[0],
                'items': [('Smash Burger', 2), ('Chocolate Lava Cake', 1)],
                'status': 'Delivered',
                'payment_mode': 'UPI',
                'driver': driver_map['Alex Johnson'],
                'instructions': 'Extra pickles on the burger please',
            },
            {
                'customer': demo_users[1],
                'items': [('Margherita Pizza', 1), ('Mango Sorbet', 2)],
                'status': 'Out for Delivery',
                'payment_mode': 'Card',
                'driver': driver_map['Maria Garcia'],
                'instructions': '',
            },
            {
                'customer': demo_users[2],
                'items': [('Butter Chicken', 1), ('Lamb Biryani', 1)],
                'status': 'Preparing',
                'payment_mode': 'COD',
                'driver': None,
                'instructions': 'Less spicy please',
            },
            {
                'customer': demo_users[0],
                'items': [('Dragon Roll', 2), ('Spicy Tuna Roll', 1)],
                'status': 'Placed',
                'payment_mode': 'UPI',
                'driver': None,
                'instructions': 'Soy sauce on the side',
            },
        ]

        for od in sample_orders:
            total = sum(
                item_map[name].price * qty
                for name, qty in od['items']
                if name in item_map
            )
            order = Order.objects.create(
                customer=od['customer'],
                status=od['status'],
                total_amount=total,
                special_instructions=od['instructions']
            )
            for name, qty in od['items']:
                if name in item_map:
                    OrderItem.objects.create(order=order, item=item_map[name], quantity=qty)
            # Payment record
            Payment.objects.create(
                order=order,
                payment_mode=od['payment_mode'],
                amount=total,
                payment_status='Paid' if od['payment_mode'] != 'COD' else 'Pending'
            )
            # Delivery record if driver assigned
            if od['driver']:
                del_status = 'Delivered' if od['status'] == 'Delivered' else ('Picked Up' if od['status'] == 'Out for Delivery' else 'In Progress')
                Delivery.objects.get_or_create(
                    order=order,
                    defaults={'partner': od['driver'], 'delivery_status': del_status}
                )

        # Seed some reviews for delivered orders
        log('Seeding reviews...')
        delivered_orders = Order.objects.filter(status='Delivered')
        for dord in delivered_orders:
            first_item = dord.items.first()
            if first_item:
                Review.objects.get_or_create(
                    customer=dord.customer,
                    restaurant=first_item.item.restaurant,
                    defaults={
                        'menu_item': first_item.item,
                        'rating': 5,
                        'comment': 'Absolutely fantastic! Fast delivery and delicious food!'
                    }
                )

        log(
            '\n[OK] Seed completed successfully!'
            f'\n   Categories: {Category.objects.count()}'
            f'\n   Restaurants: {Restaurant.objects.count()}'
            f'\n   Menu Items: {MenuItem.objects.count()}'
            f'\n   Delivery Partners: {DeliveryPartner.objects.count()}'
            f'\n   Demo Users: {len(demo_users)}'
            f'\n   Orders: {Order.objects.count()}'
            f'\n   Reviews: {Review.objects.count()}'
            '\n\nDemo customer credentials:'
            '\n   Username: customer_alice | Password: Demo@1234'
            '\n   Username: customer_bob   | Password: Demo@1234'
            '\n   Username: customer_carol | Password: Demo@1234',
            self.style.SUCCESS
        )
