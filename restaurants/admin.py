from django.contrib import admin
from .models import Category, Restaurant, MenuItem, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'description')
    search_fields = ('name',)

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('restaurant_name', 'rating', 'address')
    search_fields = ('restaurant_name', 'address')

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'category', 'price', 'restaurant', 'is_veg', 'preparation_time', 'availability')
    list_filter = ('category', 'is_veg', 'availability', 'restaurant')
    search_fields = ('item_name', 'description', 'restaurant__restaurant_name')
    list_editable = ('availability', 'price')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'menu_item', 'rating', 'created_at')
    list_filter = ('rating', 'restaurant', 'created_at')
    search_fields = ('customer__username', 'restaurant__restaurant_name', 'comment')