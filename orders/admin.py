from django.contrib import admin
from .models import Order, OrderItem, Payment, DeliveryPartner, Delivery, Coupon

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_type', 'discount_value', 'min_order_value',
        'max_discount_amount', 'is_active', 'valid_from', 'valid_until',
        'times_used', 'max_uses'
    )
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_until')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'subtotal', 'discount_amount', 'delivery_fee', 'tax_amount', 'total_amount', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    inlines = [OrderItemInline]

admin.site.register(Payment)
admin.site.register(DeliveryPartner)
admin.site.register(Delivery)