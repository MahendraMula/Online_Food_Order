from decimal import Decimal
from restaurants.models import MenuItem

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, item_id, quantity=1, override_quantity=False):
        """
        Add a menu item to the cart or update its quantity.
        """
        item_id_str = str(item_id)
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
        self.session['cart'] = {}
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
