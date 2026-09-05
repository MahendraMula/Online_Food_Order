from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Avg
from .models import Restaurant, MenuItem, Category, Review

def storefront_view(request):
    """
    Storefront menu view with multi-parameter search, category filtering,
    dietary preference toggling, and sorting.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    veg_filter = request.GET.get('veg', '').strip()
    restaurant_id = request.GET.get('restaurant', '').strip()
    sort_by = request.GET.get('sort', '').strip()

    # Base queryset: only available dishes, pre-fetching foreign keys
    menu_items = MenuItem.objects.filter(availability=True).select_related('restaurant', 'category')

    # Keyword Search (Dish name, description, or restaurant name)
    if query:
        menu_items = menu_items.filter(
            Q(item_name__icontains=query) |
            Q(description__icontains=query) |
            Q(restaurant__restaurant_name__icontains=query)
        )

    # Category Filter
    if category_id:
        menu_items = menu_items.filter(category_id=category_id)

    # Dietary Preference (1 for Veg, 0 for Non-Veg)
    if veg_filter == '1':
        menu_items = menu_items.filter(is_veg=True)
    elif veg_filter == '0':
        menu_items = menu_items.filter(is_veg=False)

    # Restaurant Filter
    if restaurant_id:
        menu_items = menu_items.filter(restaurant_id=restaurant_id)

    # Sorting
    if sort_by == 'price_asc':
        menu_items = menu_items.order_by('price')
    elif sort_by == 'price_desc':
        menu_items = menu_items.order_by('-price')
    elif sort_by == 'prep_time':
        menu_items = menu_items.order_by('preparation_time')
    elif sort_by == 'rating':
        menu_items = menu_items.order_by('-restaurant__rating')
    else:
        menu_items = menu_items.order_by('id')

    categories = Category.objects.all()
    restaurants = Restaurant.objects.all()
    recent_reviews = Review.objects.select_related('restaurant').prefetch_related('customer')[:4]

    context = {
        'menu_items': menu_items,
        'categories': categories,
        'restaurants': restaurants,
        'recent_reviews': recent_reviews,
        'query': query,
        'selected_category': category_id,
        'selected_veg': veg_filter,
        'selected_restaurant': restaurant_id,
        'selected_sort': sort_by,
        'total_count': menu_items.count(),
    }
    return render(request, 'index.html', context)


@login_required
@require_POST
def submit_review_view(request):
    """
    Submits a rating and customer review for a restaurant/dish and updates restaurant aggregate rating.
    """
    restaurant_id = request.POST.get('restaurant_id')
    raw_rating = request.POST.get('rating', '5')
    comment = request.POST.get('comment', '').strip()
    menu_item_id = request.POST.get('menu_item_id')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'order_history'

    # Rating validation
    try:
        rating = int(raw_rating)
        if rating < 1 or rating > 5:
            messages.error(request, "Rating must be an integer between 1 and 5 stars.")
            return redirect(next_url)
    except (ValueError, TypeError):
        messages.error(request, "Invalid rating value provided.")
        return redirect(next_url)

    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    menu_item = None
    if menu_item_id:
        menu_item = MenuItem.objects.filter(id=menu_item_id, restaurant=restaurant).first()

    Review.objects.create(
        customer=request.user,
        restaurant=restaurant,
        menu_item=menu_item,
        rating=rating,
        comment=comment
    )

    # Recalculate average restaurant rating
    avg_rating = restaurant.reviews.aggregate(avg=Avg('rating'))['avg']
    if avg_rating is not None:
        restaurant.rating = round(Decimal(str(avg_rating)), 1)
        restaurant.save()

    messages.success(request, f"⭐ Thank you! Your {rating}-star review for '{restaurant.restaurant_name}' was submitted.")
    return redirect(next_url)