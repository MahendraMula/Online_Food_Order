import re
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Sum

from .forms import CustomerSignupForm
from .models import CustomerProfile

def signup_view(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            CustomerProfile.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            login(request, user)
            messages.success(request, f"Welcome to Food Express, {user.username}! Your account is ready.")
            return redirect('/')
    else:
        form = CustomerSignupForm()
    return render(request, 'signup.html', {'form': form})


@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        if phone and not re.match(r'^\+?[\d\s\-()]{7,20}$', phone):
            messages.error(request, "Please enter a valid phone number (at least 7 digits).")
            return redirect('profile')

        if address and len(address) < 5:
            messages.error(request, "Address must be at least 5 characters long.")
            return redirect('profile')

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()

        profile.phone = phone
        profile.address = address
        profile.save()

        messages.success(request, "Your profile and delivery preferences were updated successfully.")
        return redirect('profile')

    total_orders = request.user.orders.count()
    total_spent = request.user.orders.exclude(status='Cancelled').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    active_orders = request.user.orders.filter(status__in=['Pending', 'Placed', 'Preparing', 'Out for Delivery']).count()

    context = {
        'profile': profile,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'active_orders': active_orders,
    }
    return render(request, 'profile.html', context)