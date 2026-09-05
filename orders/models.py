from django.db import models
from django.contrib.auth.models import User
from restaurants.models import MenuItem

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Placed', 'Placed'),
        ('Preparing', 'Preparing'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    customer = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, related_name='orders', db_constraint=False)
    special_instructions = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.item.item_name}"

class Payment(models.Model):
    MODES = [('COD', 'Cash on Delivery'), ('Card', 'Card'), ('UPI', 'UPI')]
    STATUS = [('Pending', 'Pending'), ('Paid', 'Paid'), ('Failed', 'Failed')]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_mode = models.CharField(max_length=50, choices=MODES)
    payment_status = models.CharField(max_length=50, choices=STATUS, default='Pending')

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order.id}"

# --- DECLARE THIS FIRST SO DELIVERY CAN REFERENCE IT CLEANLY ---
class DeliveryPartner(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Delivery(models.Model):
    STATUS = [
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Picked Up', 'Picked Up'),
        ('Delivered', 'Delivered'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    partner = models.ForeignKey(DeliveryPartner, on_delete=models.SET_NULL, null=True, related_name='deliveries')
    delivery_status = models.CharField(max_length=50, choices=STATUS, default='Assigned')
    delivery_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.id}"