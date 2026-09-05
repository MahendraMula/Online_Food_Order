from django.contrib import admin
from .models import Order, OrderItem, Payment, DeliveryPartner, Delivery

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_amount', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    inlines = [OrderItemInline]

admin.site.register(Payment)
admin.site.register(DeliveryPartner)
admin.site.register(Delivery)