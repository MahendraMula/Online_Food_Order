from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

# Centralized delivery configuration defaults
DEFAULT_BASE_DELIVERY_FEE = Decimal('4.00')
DEFAULT_FREE_DELIVERY_THRESHOLD = Decimal('50.00')
DEFAULT_PER_KM_RATE = Decimal('1.00')
DEFAULT_BASE_DISTANCE_KM = Decimal('5.0')
DEFAULT_GST_TAX_RATE = Decimal('0.05')  # 5% GST


def calculate_delivery_fee(subtotal, restaurant=None, delivery_address=None, distance_km=None):
    """
    Centralized dynamic delivery charge calculation.

    Pricing Engine Rules:
    1. If subtotal is zero (empty cart), delivery fee is 0.00.
    2. If subtotal >= FREE_DELIVERY_THRESHOLD (50.00 by default), delivery is FREE (0.00).
    3. Normal orders below threshold incur the BASE_DELIVERY_FEE (4.00 by default).
    4. Distance beyond BASE_DISTANCE_KM (5.0 km) incurs PER_KM_RATE (1.00/km).

    DISTANCE ABSTRACTION & ARCHITECTURE NOTE:
    -----------------------------------------
    Phase 1 Limitation: The current implementation does NOT perform real-time GPS or
    geographical routing calculations. Instead, it provides a clean, deterministic
    distance-input abstraction:
    - Direct parameter: `distance_km` (Decimal or float) can be passed directly.
    - Address tag: `[dist: Xkm]` or `[distance: Xkm]` embedded in delivery addresses.

    Future Provider Extension:
    This pricing function is decoupled from distance resolution. In a future phase,
    an external distance provider (e.g., Google Maps Distance Matrix API, Mapbox, or Leaflet/OSRM)
    can simply calculate the travel distance between `restaurant.address` and `delivery_address`,
    then supply `distance_km=<calculated_distance>` to this function without requiring any changes
    to the fee calculation engine.
    """
    subtotal_dec = Decimal(str(subtotal or '0.00'))
    if subtotal_dec <= Decimal('0.00'):
        return Decimal('0.00')

    free_threshold = getattr(settings, 'OFO_FREE_DELIVERY_THRESHOLD', DEFAULT_FREE_DELIVERY_THRESHOLD)
    base_fee = getattr(settings, 'OFO_BASE_DELIVERY_FEE', DEFAULT_BASE_DELIVERY_FEE)
    per_km_rate = getattr(settings, 'OFO_DELIVERY_PER_KM_RATE', DEFAULT_PER_KM_RATE)
    base_dist = getattr(settings, 'OFO_BASE_DELIVERY_DISTANCE_KM', DEFAULT_BASE_DISTANCE_KM)

    if subtotal_dec >= free_threshold:
        return Decimal('0.00')

    fee = base_fee

    if distance_km is not None:
        dist_dec = Decimal(str(distance_km))
        if dist_dec > base_dist:
            additional_dist = dist_dec - base_dist
            fee += additional_dist * per_km_rate
    elif delivery_address:
        # Deterministic Phase 1 distance-input tag parser
        import re
        match = re.search(r'\[(?:distance|dist):\s*([\d\.]+)km\]', delivery_address, re.IGNORECASE)
        if match:
            try:
                dist_dec = Decimal(match.group(1))
                if dist_dec > base_dist:
                    fee += (dist_dec - base_dist) * per_km_rate
            except Exception:
                pass

    return max(Decimal('0.00'), fee.quantize(Decimal('0.01')))


def calculate_tax(taxable_amount, tax_rate=None):
    """
    Centralized GST / Sales tax calculation.

    Rules:
    1. If taxable_amount <= 0, tax is 0.00.
    2. Tax rate defaults to settings.OFO_GST_TAX_RATE (0.05 / 5% GST assumption).
       NOTE: This 5% rate is the project's configured/default GST rate assumption
       (aligned with standard Indian GST for standalone restaurant services without ITC),
       and can be overridden via `settings.OFO_GST_TAX_RATE`.
    3. Calculates exact tax using Decimal with ROUND_HALF_UP rounding to 2 decimal places.
    4. Guarantees non-negative result.
    """
    amount_dec = Decimal(str(taxable_amount or '0.00'))
    if amount_dec <= Decimal('0.00'):
        return Decimal('0.00')

    rate = tax_rate
    if rate is None:
        rate = getattr(settings, 'OFO_GST_TAX_RATE', DEFAULT_GST_TAX_RATE)
    rate_dec = Decimal(str(rate))

    tax = (amount_dec * rate_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return max(Decimal('0.00'), tax)


def get_gst_rate_percentage(tax_rate=None):
    """Returns human-readable GST percentage string (e.g. '5' for 0.05)."""
    rate = tax_rate
    if rate is None:
        rate = getattr(settings, 'OFO_GST_TAX_RATE', DEFAULT_GST_TAX_RATE)
    return str((Decimal(str(rate)) * Decimal('100')).normalize())

