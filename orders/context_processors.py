from django.conf import settings
from .cart import Cart

def cart_context(request):
    """
    Exposes cart statistics and configured project currency globally to all templates.
    """
    currency_symbol = getattr(settings, 'OFO_CURRENCY_SYMBOL', '₹')
    currency_code = getattr(settings, 'OFO_CURRENCY_CODE', 'INR')
    try:
        cart = Cart(request)
        return {
            'cart_total_items': cart.get_total_count(),
            'cart_total_price': cart.get_total_price(),
            'currency_symbol': currency_symbol,
            'currency_code': currency_code,
        }
    except Exception:
        return {
            'cart_total_items': 0,
            'cart_total_price': 0,
            'currency_symbol': currency_symbol,
            'currency_code': currency_code,
        }
