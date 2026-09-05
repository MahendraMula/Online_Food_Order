import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from restaurants.models import MenuItem, Category, Restaurant
from .models import Order, OrderItem, Payment, Delivery, DeliveryPartner
from .cart import Cart


@require_POST
def add_to_cart_view(request, item_id):
    """
    Adds an item to the session-based shopping cart.
    """
    menu_item = get_object_or_404(MenuItem, id=item_id, availability=True)
    cart = Cart(request)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity <= 0:
        quantity = 1

    cart.add(item_id=menu_item.id, quantity=quantity)
    messages.success(request, f"Added {quantity}x '{menu_item.item_name}' to your cart!")

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


def cart_view(request):
    """
    Renders the dedicated shopping cart page.
    """
    cart = Cart(request)
    items = cart.get_items()
    total_price = cart.get_total_price()
    delivery_fee = Decimal('0.00')

    context = {
        'cart_items': items,
        'subtotal': total_price,
        'delivery_fee': delivery_fee,
        'grand_total': total_price + delivery_fee,
        'is_empty': len(items) == 0,
    }
    return render(request, 'cart.html', context)


@login_required
def checkout_view(request):
    """
    Step before placing the order: Review all cart items, address, and payment method.
    """
    cart = Cart(request)
    items = cart.get_items()

    if not items:
        messages.warning(request, "Your shopping cart is empty. Please add dishes before checking out.")
        return redirect('storefront')

    total_price = cart.get_total_price()
    profile = getattr(request.user, 'profile', None)

    context = {
        'cart_items': items,
        'total_price': total_price,
        'profile': profile,
    }
    return render(request, 'checkout.html', context)


@login_required
@require_POST
def place_order_view(request):
    """
    Finalizes the transaction from the shopping cart items atomically.
    """
    cart = Cart(request)
    items = cart.get_items()

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect('storefront')

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
    profile = getattr(request.user, 'profile', None)
    if profile:
        profile.address = delivery_address
        profile.phone = phone
        profile.save()

    total_amount = cart.get_total_price()

    with transaction.atomic():
        # 1. Create Order
        order = Order.objects.create(
            customer=request.user,
            status='Placed',
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

        # 5. Clear the cart
        cart.clear()

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
        ).exclude(order__status='Cancelled').aggregate(
            total=Sum('order__total_amount')
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
def update_order_status_view(request, order_id):
    """
    Staff action to advance order workflow and assign delivery drivers.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        driver_id = request.POST.get('driver_id')

        with transaction.atomic():
            if new_status:
                order.status = new_status
                order.save()

            # Handle Delivery Record
            delivery, _ = Delivery.objects.get_or_create(order=order)
            if driver_id:
                try:
                    driver = DeliveryPartner.objects.get(id=driver_id)
                    delivery.partner = driver
                except DeliveryPartner.DoesNotExist:
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
def toggle_item_availability_view(request, item_id):
    """
    Staff quick action to toggle menu dish stock availability.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    item = get_object_or_404(MenuItem, id=item_id)
    if request.method == 'POST':
        item.availability = not item.availability
        item.save()
        status_text = "In Stock" if item.availability else "Out of Stock"
        messages.info(request, f"'{item.item_name}' is now marked as {status_text}.")

    return redirect('admin_dashboard')


@login_required
def add_delivery_partner_view(request):
    """
    Staff action to onboard a new delivery driver.
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('storefront')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if name and phone:
            DeliveryPartner.objects.create(name=name, phone=phone)
            messages.success(request, f"Driver '{name}' added successfully.")
        else:
            messages.error(request, "Please provide valid name and phone number.")

    return redirect('admin_dashboard')


@login_required
def order_receipt_view(request, order_id):
    """
    Renders a printable tax invoice / receipt for an order.
    """
    order = get_object_or_404(Order.objects.select_related('payment', 'delivery__partner').prefetch_related('customer', 'items__item__restaurant'), id=order_id)

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

    context = {
        'order': order,
        'items_with_totals': items_with_totals,
        'restaurant_name': order.items.first().item.restaurant.restaurant_name if order.items.exists() else 'Food Express Partner',
    }
    return render(request, 'receipt.html', context)