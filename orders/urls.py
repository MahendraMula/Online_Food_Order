from django.urls import path
from . import views

urlpatterns = [
    # Customer Cart & Checkout Routes
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_view, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),
    path('cart/dismiss-conflict/', views.clear_cart_conflict_view, name='clear_cart_conflict'),
    path('coupon/apply/', views.apply_coupon_view, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon_view, name='remove_coupon'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('place/', views.place_order_view, name='place_order'),
    path('history/', views.order_history_view, name='order_history'),
    path('receipt/<int:order_id>/', views.order_receipt_view, name='order_receipt'),
    path('cancel/<int:order_id>/', views.cancel_order_view, name='cancel_order'),
    path('confirm/<int:order_id>/', views.confirm_order_view, name='confirm_order'),

    # Dedicated Restaurant Operations & Admin Routes
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('status/<int:order_id>/', views.update_order_status_view, name='update_order_status'),
    path('menu/toggle/<int:item_id>/', views.toggle_item_availability_view, name='toggle_item_availability'),
    path('drivers/add/', views.add_delivery_partner_view, name='add_delivery_partner'),
]