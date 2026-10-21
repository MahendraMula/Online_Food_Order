import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from restaurants.models import MenuItem, Category, Restaurant
from accounts.models import CustomerProfile
from .models import Order, OrderItem, Payment, Delivery, DeliveryPartner, Coupon
from .cart import Cart, MixedRestaurantCartError
from .services import calculate_delivery_fee, calculate_tax, get_gst_rate_percentage


@require_POST
def add_to_cart_view(request, item_id):
    """
    Adds an item to the session-based shopping cart with single-restaurant validation.
    """
    menu_item = get_object_or_404(MenuItem, id=item_id, availability=True)
    cart = Cart(request)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity <= 0:
        quantity = 1

    clear_cart_flag = request.POST.get('clear_cart') in ('true', '1', 'yes', True)
    existing_restaurant = cart.get_restaurant()

    if existing_restaurant and existing_restaurant.id != menu_item.restaurant_id and not clear_cart_flag:
        # Restaurant conflict: Cart already contains items from a different restaurant
        request.session['restaurant_conflict'] = {
            'current_restaurant_name': existing_restaurant.restaurant_name,
            'new_restaurant_name': menu_item.restaurant.restaurant_name,
            'item_id': menu_item.id,
            'item_name': menu_item.item_name,
            'quantity': quantity,
        }
        request.session.modified = True
        messages.warning(
            request,
            f"Your cart already contains dishes from '{existing_restaurant.restaurant_name}'. "
            f"You can only order from one restaurant at a time. Clear your cart to order from '{menu_item.restaurant.restaurant_name}'."
        )
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'storefront'
        return redirect(next_url)

    if clear_cart_flag:
        cart.clear()
        cart.add(item_id=menu_item.id, quantity=quantity, clear_conflicting=True)
        request.session.pop('restaurant_conflict', None)
        request.session.modified = True
        messages.warning(
            request,
            f"Your previous cart was cleared. Added {quantity}x '{menu_item.item_name}' from '{menu_item.restaurant.restaurant_name}'."
        )
    else:
        try:
            cart.add(item_id=menu_item.id, quantity=quantity)
            request.session.pop('restaurant_conflict', None)
            request.session.modified = True
            messages.success(request, f"Added {quantity}x '{menu_item.item_name}' to your cart!")
        except MixedRestaurantCartError:
            messages.error(
                request,
                f"Cart contains dishes from another restaurant. Please clear your cart first."
            )

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'storefront'
    return redirect(next_url)


@require_POST
def clear_cart_conflict_view(request):
    """
    Dismisses the restaurant conflict dialog without changing the cart.
    """
    request.session.pop('restaurant_conflict', None)
    request.session.modified = True
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'storefront'
    return redirect(next_url)


@require_POST
def update_cart_view(request, item_id):
    """
    Updates the quantity of a specific item in the cart.
    """
    cart = Cart(request)
    action = request.POST.get('action')

    if action == 'increment':
        cart.add(item_id=item_id, quantity=1)
    elif action == 'decrement':
        cart.add(item_id=item_id, quantity=-1)
    else:
        try:
            quantity = int(request.POST.get('quantity', 1))
            cart.add(item_id=item_id, quantity=quantity, override_quantity=True)
        except (ValueError, TypeError):
            pass

    return redirect('cart')


@require_POST
def remove_from_cart_view(request, item_id):
    """
    Removes an item completely from the cart.
    """
    cart = Cart(request)
    cart.remove(item_id=item_id)
    messages.info(request, "Item removed from cart.")
    return redirect('cart')


@require_POST
def clear_cart_view(request):
    """
    Clears all items in the cart.
    """
    cart = Cart(request)
    cart.clear()
    messages.info(request, "Your shopping cart has been cleared.")
    return redirect('cart')


def get_cart_coupon_data(request, subtotal):
    """
    Validates and calculates coupon discount from session for given subtotal.
    Returns: (coupon_instance_or_None, discount_amount: Decimal, status_message: str)
    """
    coupon_code = request.session.get('coupon_code')
    if not coupon_code:
        return None, Decimal('0.00'), ""

    try:
        coupon = Coupon.objects.get(code__iexact=coupon_code)
    except Coupon.DoesNotExist:
        request.session.pop('coupon_code', None)
        request.session.modified = True
        return None, Decimal('0.00'), "The previously applied coupon no longer exists."

    is_valid, msg = coupon.is_valid_for_subtotal(subtotal)
    if not is_valid:
        request.session.pop('coupon_code', None)
        request.session.modified = True
        return None, Decimal('0.00'), msg

    discount = coupon.calculate_discount(subtotal)
    return coupon, discount, ""


@require_POST
def apply_coupon_view(request):
    """
    Validates and attaches a promo code to the session.
    """
    code = request.POST.get('coupon_code', '').strip().upper()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cart'

    if not code:
        messages.error(request, "Please enter a coupon code.")
        return redirect(next_url)

    cart = Cart(request)
    subtotal = cart.get_total_price()

    if subtotal <= Decimal('0.00'):
        messages.error(request, "Please add items to your cart before applying a coupon.")
        return redirect(next_url)

    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        messages.error(request, f"Coupon code '{code}' is invalid or does not exist.")
        return redirect(next_url)

    is_valid, error_msg = coupon.is_valid_for_subtotal(subtotal)
    if not is_valid:
        messages.error(request, error_msg)
        return redirect(next_url)

    request.session['coupon_code'] = coupon.code
    request.session.modified = True
    discount = coupon.calculate_discount(subtotal)
    from django.conf import settings
    currency = getattr(settings, 'OFO_CURRENCY_SYMBOL', '₹')
    messages.success(request, f"Promo code '{coupon.code}' applied! Saved {currency}{discount:.2f}.")
    return redirect(next_url)


@require_POST
def remove_coupon_view(request):
    """
    Removes currently applied coupon from the user's session.
    """
    code = request.session.pop('coupon_code', None)
    request.session.modified = True
    if code:
        messages.info(request, f"Coupon '{code}' removed.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cart'
    return redirect(next_url)


def cart_view(request):
    """
    Renders the dedicated shopping cart page with coupon summary and dynamic delivery fee.
    """
    cart = Cart(request)
    items = cart.get_items()
    subtotal = cart.get_total_price()
    restaurant = cart.get_restaurant()

    coupon, discount_amount, coupon_msg = get_cart_coupon_data(request, subtotal)
    if coupon_msg and not coupon:
        messages.warning(request, coupon_msg)

    net_subtotal = max(Decimal('0.00'), subtotal - discount_amount)
    delivery_fee = calculate_delivery_fee(subtotal=net_subtotal, restaurant=restaurant)
    tax_amount = calculate_tax(taxable_amount=net_subtotal)
    grand_total = net_subtotal + delivery_fee + tax_amount
    gst_rate_pct = get_gst_rate_percentage()

    context = {
        'cart_items': items,
        'restaurant': restaurant,
        'subtotal': subtotal,
        'coupon': coupon,
        'discount_amount': discount_amount,
        'delivery_fee': delivery_fee,
        'tax_amount': tax_amount,
        'gst_rate_pct': gst_rate_pct,
        'grand_total': grand_total,
        'is_empty': len(items) == 0,
    }
    return render(request, 'cart.html', context)


@login_required
def checkout_view(request):
    """
    Step before placing the order: Review cart items, promo code, delivery, and payment.
    """
    cart = Cart(request)
    items = cart.get_items()

    if not items:
        messages.warning(request, "Your shopping cart is empty. Please add dishes before checking out.")
        return redirect('storefront')

    if not cart.is_single_restaurant():
        messages.error(
            request,
            "Your cart contains items from multiple restaurants. Please clear your cart or remove conflicting items before checking out."
        )
        return redirect('cart')

    subtotal = cart.get_total_price()
    profile = getattr(request.user, 'profile', None)
    restaurant = cart.get_restaurant()

    coupon, discount_amount, coupon_msg = get_cart_coupon_data(request, subtotal)
    if coupon_msg and not coupon:
        messages.warning(request, coupon_msg)

    net_subtotal = max(Decimal('0.00'), subtotal - discount_amount)
    delivery_address = profile.address if profile else None
    delivery_fee = calculate_delivery_fee(subtotal=net_subtotal, restaurant=restaurant, delivery_address=delivery_address)
    tax_amount = calculate_tax(taxable_amount=net_subtotal)
    total_price = net_subtotal + delivery_fee + tax_amount
    gst_rate_pct = get_gst_rate_percentage()

    context = {
        'cart_items': items,
        'restaurant': restaurant,
        'subtotal': subtotal,
        'coupon': coupon,
        'discount_amount': discount_amount,
        'delivery_fee': delivery_fee,
        'tax_amount': tax_amount,
        'gst_rate_pct': gst_rate_pct,
        'total_price': total_price,
        'profile': profile,
    }
    return render(request, 'checkout.html', context)


@login_required
@require_POST
def place_order_view(request):
    """
    Finalizes the transaction from the shopping cart items atomically with server-side coupon and delivery fee validation.
    """
    cart = Cart(request)
    items = cart.get_items()

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect('storefront')

    if not cart.is_single_restaurant():
        messages.error(
            request,
            "Cannot place order: your cart contains items from multiple restaurants. An order must be from a single restaurant."
        )
        return redirect('cart')

    payment_mode = request.POST.get('payment_mode', 'COD').strip()
    delivery_address = request.POST.get('delivery_address', '').strip()
    phone = request.POST.get('phone', '').strip()
    special_instructions = request.POST.get('special_instructions', '').strip()

    # Input Validation
    valid_payment_modes = {mode[0] for mode in Payment.MODES}
    if payment_mode not in valid_payment_modes:
        messages.error(request, f"Invalid payment method '{payment_mode}'. Please choose COD, UPI, or Card.")
        return redirect('checkout')

    if not phone or not re.match(r'^\+?[\d\s\-()]{7,20}$', phone):
        messages.error(request, "Please provide a valid contact phone number (at least 7 digits).")
        return redirect('checkout')

    if not delivery_address or len(delivery_address) < 5:
        messages.error(request, "Please provide a complete delivery address (at least 5 characters).")
        return redirect('checkout')

    # Update profile address/phone if provided
    CustomerProfile.objects.update_or_create(
        user=request.user,
        defaults={
            'address': delivery_address,
            'phone': phone,
        }
    )

    # Server-side authoritative calculation
    subtotal = cart.get_total_price()
    restaurant = cart.get_restaurant()

    with transaction.atomic():
        # Coupon validation and locking
        coupon_code = request.session.get('coupon_code')
        applied_coupon = None
        discount_amount = Decimal('0.00')

        if coupon_code:
            try:
                locked_coupon = Coupon.objects.select_for_update().get(code__iexact=coupon_code)
                is_valid, err_msg = locked_coupon.is_valid_for_subtotal(subtotal)
                if is_valid:
                    discount_amount = locked_coupon.calculate_discount(subtotal)
                    locked_coupon.times_used += 1
                    locked_coupon.save()
                    applied_coupon = locked_coupon
                else:
                    messages.warning(request, f"Coupon '{coupon_code}' could not be applied: {err_msg}")
            except Coupon.DoesNotExist:
                messages.warning(request, f"Coupon '{coupon_code}' is no longer valid.")

        net_subtotal = max(Decimal('0.00'), subtotal - discount_amount)
        delivery_fee = calculate_delivery_fee(
            subtotal=net_subtotal,
            restaurant=restaurant,
            delivery_address=delivery_address
        )
        tax_amount = calculate_tax(taxable_amount=net_subtotal)
        total_amount = net_subtotal + delivery_fee + tax_amount

        # 1. Create Order
        order = Order.objects.create(
            customer=request.user,
            status='Placed',
            subtotal=subtotal,
            coupon=applied_coupon,
            discount_amount=discount_amount,
            delivery_fee=delivery_fee,
            tax_amount=tax_amount,
            total_amount=total_amount,
            special_instructions=special_instructions
        )

        # 2. Create OrderItems
        for entry in items:
            OrderItem.objects.create(
                order=order,
                item=entry['item'],
                quantity=entry['quantity']
            )

        # 3. Create Payment
        Payment.objects.create(
            order=order,
            amount=total_amount,
            payment_mode=payment_mode,
            payment_status='Paid' if payment_mode != 'COD' else 'Pending'
        )

        # 4. Assign Delivery Partner & Delivery record
        default_partner = DeliveryPartner.objects.first()
        Delivery.objects.create(
            order=order,
            partner=default_partner,
            delivery_status='Assigned'
        )

        # 5. Clear the cart and coupon session
        cart.clear()
        request.session.pop('coupon_code', None)
        request.session.modified = True

    messages.success(request, f"🎉 Order #{order.id} placed successfully! Track its status below.")
    return redirect('order_history')


@login_required
def order_history_view(request):
    """
    Displays the customer's order history with progressive status tracker.
    """
    orders = Order.objects.filter(customer=request.user).prefetch_related(
        'items__item__restaurant', 'payment', 'delivery__partner'
    ).order_by('-order_date')

    return render(request, 'orders.html', {'orders': orders})


@login_required
@require_POST
def cancel_order_view(request, order_id):
    """
    Cancels an order if it is in Pending or Placed status.
    """
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if order.status in ['Pending', 'Placed']:
        order.status = 'Cancelled'
        order.save()
        messages.info(request, f"Order #{order.id} has been cancelled.")
    else:
        messages.error(request, f"Cannot cancel order #{order.id} as it is already in progress ({order.status}).")

    return redirect('order_history')


@login_required
@require_POST
def confirm_order_view(request, order_id):
    """
    Re-confirms payment or moves a pending order to Placed.
    """
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    payment_mode = request.POST.get('payment_mode', 'COD').strip()

    valid_payment_modes = {mode[0] for mode in Payment.MODES}
    if payment_mode not in valid_payment_modes:
        messages.error(request, "Invalid payment method selected.")
        return redirect('order_history')

    with transaction.atomic():
        order.status = 'Placed'
        order.save()

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'amount': order.total_amount,
                'payment_mode': payment_mode,
                'payment_status': 'Paid' if payment_mode != 'COD' else 'Pending'
            }
        )
        if not created:
            payment.payment_mode = payment_mode
            payment.payment_status = 'Paid' if payment_mode != 'COD' else 'Pending'
            payment.save()

    messages.success(request, f"Payment confirmed for Order #{order.id}.")
    return redirect('order_history')


# ---------------------------------------------------------------------------
#  DEDICATED RESTAURANT OPERATIONS & ADMIN DASHBOARD
# ---------------------------------------------------------------------------

@login_required
def admin_dashboard_view(request):
    """
    Executive & Operational Dashboard for Restaurant Administrators.
    """
    if not request.user.is_staff:
        messages.error(request, "Access restricted: Administrator credentials required.")
        return redirect('storefront')

    # KPI Metrics
    total_revenue = Order.objects.exclude(status='Cancelled').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_orders = Order.objects.count()
    active_orders_count = Order.objects.filter(status__in=['Pending', 'Placed', 'Preparing', 'Out for Delivery']).count()
    delivered_orders_count = Order.objects.filter(status='Delivered').count()
    cancelled_orders_count = Order.objects.filter(status='Cancelled').count()
    
    total_dishes = MenuItem.objects.count()
    available_dishes = MenuItem.objects.filter(availability=True).count()
    total_customers = User.objects.filter(is_staff=False).count()

    # Data lists
    orders = Order.objects.all().select_related('payment', 'delivery__partner').prefetch_related('customer', 'items__item__restaurant').order_by('-order_date')
    menu_items = MenuItem.objects.all().select_related('restaurant', 'category').order_by('restaurant', 'item_name')
    drivers = DeliveryPartner.objects.all()

    # Top Selling Dishes (by quantity ordered)
    top_selling_dishes = MenuItem.objects.annotate(
        total_sold=Sum('orderitem__quantity', filter=~Q(orderitem__order__status='Cancelled'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]

    # Payment Mode Statistics
    payment_stats = Payment.objects.values('payment_mode').annotate(
        total_amount=Sum('amount'),
        tx_count=Count('id')
    ).order_by('-total_amount')

    # Category Sales Breakdown
    category_sales = []
    for cat in Category.objects.all():
        cat_rev = OrderItem.objects.filter(
            item__category=cat
        ).exclude(order__status='Cancelled').annotate(
            line_total=F('quantity') * F('item__price')
        ).aggregate(
            total=Sum('line_total')
        )['total'] or Decimal('0.00')
        category_sales.append({
            'name': cat.name,
            'icon': cat.icon,
            'dish_count': cat.menu_items.count(),
            'revenue': cat_rev
        })

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'active_orders_count': active_orders_count,
        'delivered_orders_count': delivered_orders_count,
        'cancelled_orders_count': cancelled_orders_count,
        'total_dishes': total_dishes,
        'available_dishes': available_dishes,
        'total_customers': total_customers,
        'orders': orders,
        'menu_items': menu_items,
        'drivers': drivers,
        'top_selling_dishes': top_selling_dishes,
        'payment_stats': payment_stats,
        'category_sales': category_sales,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_POST
def update_order_status_view(request, order_id):
    """
    Staff action to advance order workflow and assign delivery drivers.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    driver_id = request.POST.get('driver_id')

    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
    with transaction.atomic():
        if new_status and new_status in valid_statuses:
            order.status = new_status
            order.save()

        # Handle Delivery Record
        delivery, _ = Delivery.objects.get_or_create(order=order)
        if driver_id:
            try:
                driver = DeliveryPartner.objects.get(id=int(driver_id))
                delivery.partner = driver
            except (DeliveryPartner.DoesNotExist, ValueError, TypeError):
                pass

        if new_status == 'Out for Delivery':
            delivery.delivery_status = 'Picked Up'
        elif new_status == 'Delivered':
            delivery.delivery_status = 'Delivered'
            delivery.delivery_time = timezone.now()
            # Mark payment as Paid if completed
            if hasattr(order, 'payment'):
                order.payment.payment_status = 'Paid'
                order.payment.save()
        elif new_status == 'Preparing':
            delivery.delivery_status = 'Assigned'

        delivery.save()

    messages.success(request, f"Updated Order #{order.id} status to '{order.status}'.")
    return redirect('admin_dashboard')


@login_required
@require_POST
def toggle_item_availability_view(request, item_id):
    """
    Staff quick action to toggle menu dish stock availability.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    item = get_object_or_404(MenuItem, id=item_id)
    item.availability = not item.availability
    item.save()
    status_text = "In Stock" if item.availability else "Out of Stock"
    messages.info(request, f"'{item.item_name}' is now marked as {status_text}.")
    return redirect('admin_dashboard')


@login_required
@require_POST
def add_delivery_partner_view(request):
    """
    Staff action to onboard a new delivery driver.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()

    if not name:
        messages.error(request, "Please provide a valid delivery partner name.")
        return redirect('admin_dashboard')

    if not phone or not re.match(r'^\+?[\d\s\-()]{7,20}$', phone):
        messages.error(request, "Please provide a valid contact phone number (at least 7 digits).")
        return redirect('admin_dashboard')

    DeliveryPartner.objects.create(name=name, phone=phone)
    messages.success(request, f"Driver '{name}' added successfully.")
    return redirect('admin_dashboard')


@login_required
def order_receipt_view(request, order_id):
    """
    Renders a printable tax invoice / receipt for an order.
    """
    order = get_object_or_404(Order.objects.select_related('payment', 'delivery__partner', 'coupon').prefetch_related('customer', 'items__item__restaurant'), id=order_id)

    # Security check: User must be staff or the customer who placed the order
    if not request.user.is_staff and order.customer != request.user:
        messages.error(request, "You are not authorized to view this receipt.")
        return redirect('order_history')

    items_with_totals = []
    for oi in order.items.all():
        line_total = oi.quantity * oi.item.price
        items_with_totals.append({
            'item': oi.item,
            'quantity': oi.quantity,
            'unit_price': oi.item.price,
            'line_total': line_total
        })

    calculated_subtotal = sum(item['line_total'] for item in items_with_totals)
    order_subtotal = order.subtotal if order.subtotal > Decimal('0.00') else calculated_subtotal

    context = {
        'order': order,
        'order_subtotal': order_subtotal,
        'items_with_totals': items_with_totals,
        'restaurant_name': order.items.first().item.restaurant.restaurant_name if order.items.exists() else 'Food Express Partner',
        'gst_rate_pct': get_gst_rate_percentage(),
    }
    return render(request, 'receipt.html', context)