from .cart import Cart

def cart_context(request):
    """
    Exposes cart statistics globally to all templates for the navbar badge.
    """
    try:
        cart = Cart(request)
        return {
            'cart_total_items': cart.get_total_count(),
            'cart_total_price': cart.get_total_price(),
        }
    except Exception:
        return {
            'cart_total_items': 0,
            'cart_total_price': 0,
        }
