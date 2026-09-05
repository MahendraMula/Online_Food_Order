from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, default='bi-tag')
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Restaurant(models.Model):
    restaurant_name = models.CharField(max_length=255)
    address = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.restaurant_name

class MenuItem(models.Model):
    item_name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_items')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, default='')
    is_veg = models.BooleanField(default=True)
    image_url = models.URLField(blank=True, null=True)
    preparation_time = models.PositiveIntegerField(default=20, help_text="Estimated preparation time in minutes")
    availability = models.BooleanField(default=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')

    def __str__(self):
        return f"{self.item_name} ({self.restaurant.restaurant_name})"

class Review(models.Model):
    RATING_CHOICES = [(i, f"{i} Stars") for i in range(1, 6)]

    customer = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='reviews', db_constraint=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.customer.username} for {self.restaurant.restaurant_name}"