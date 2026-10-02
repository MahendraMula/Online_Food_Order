from decimal import Decimal
from restaurants.models import MenuItem

class MixedRestaurantCartError(ValueError):
    """Raised when an item from a different restaurant is added to the cart without clearing."""
    pass

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def get_restaurant_id(self):
        """
        Returns the restaurant ID of the items currently in the cart,
        or None if the cart is empty.
        """
        item_ids = [int(k) for k, qty in self.cart.items() if qty > 0]
        if not item_ids:
            return None
        restaurant_ids = list(
            MenuItem.objects.filter(id__in=item_ids)
            .values_list('restaurant_id', flat=True)
            .distinct()
        )
        if restaurant_ids:
            return restaurant_ids[0]
        return None

    def get_restaurant(self):
        """
        Returns the Restaurant model instance of the items currently in the cart,
        or None if the cart is empty.
        """
        restaurant_id = self.get_restaurant_id()
        if restaurant_id:
            try:
                from restaurants.models import Restaurant
                return Restaurant.objects.get(id=restaurant_id)
            except Exception:
                return None
        return None

    def is_single_restaurant(self):
        """
        Returns True if all items in the cart belong to at most one restaurant.
        """
        item_ids = [int(k) for k, qty in self.cart.items() if qty > 0]
        if not item_ids:
            return True
        restaurant_count = (
            MenuItem.objects.filter(id__in=item_ids)
            .values('restaurant_id')
            .distinct()
            .count()
        )
        return restaurant_count <= 1

    def add(self, item_id, quantity=1, override_quantity=False, clear_conflicting=False):
        """
        Add a menu item to the cart or update its quantity.
        Enforces single-restaurant constraint unless clear_conflicting is True.
        """
        item_id_int = int(item_id)
        item_id_str = str(item_id)

        if clear_conflicting:
            self.cart.clear()
            self.cart[item_id_str] = 0
        else:
            existing_restaurant_id = self.get_restaurant_id()
            if existing_restaurant_id is not None and item_id_str not in self.cart:
                menu_item = MenuItem.objects.filter(id=item_id_int).first()
                if menu_item and menu_item.restaurant_id != existing_restaurant_id:
                    raise MixedRestaurantCartError(
                        f"Cart contains items from restaurant #{existing_restaurant_id}. "
                        f"Cannot add item from restaurant #{menu_item.restaurant_id}."
                    )

        if item_id_str not in self.cart:
            self.cart[item_id_str] = 0
        
        if override_quantity:
            self.cart[item_id_str] = quantity
        else:
            self.cart[item_id_str] += quantity

        if self.cart[item_id_str] <= 0:
            self.remove(item_id)
        else:
            self.save()

    def remove(self, item_id):
        """
        Remove a menu item from the cart.
        """
        item_id_str = str(item_id)
        if item_id_str in self.cart:
            del self.cart[item_id_str]
            self.save()

    def clear(self):
        """
        Remove all items from the cart session.
        """
        self.cart.clear()
        self.session['cart'] = self.cart
        self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        """
        Iterate over the items in the cart and fetch MenuItem models from DB.
        """
        item_ids = [int(k) for k in self.cart.keys() if self.cart[k] > 0]
        menu_items = MenuItem.objects.filter(id__in=item_ids, availability=True).select_related('restaurant', 'category')
        menu_item_map = {item.id: item for item in menu_items}

        for item_id_str, quantity in list(self.cart.items()):
            try:
                item_id = int(item_id_str)
            except ValueError:
                continue

            if item_id in menu_item_map and quantity > 0:
                item = menu_item_map[item_id]
                total_price = item.price * quantity
                yield {
                    'item': item,
                    'quantity': quantity,
                    'unit_price': item.price,
                    'total_price': total_price,
                }

    def get_items(self):
        return list(self.__iter__())

    def get_total_price(self):
        return sum(entry['total_price'] for entry in self.__iter__())

    def get_total_count(self):
        return sum(qty for qty in self.cart.values() if qty > 0)
