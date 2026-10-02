from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from restaurants.models import MenuItem

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage Discount'),
        ('FLAT', 'Flat Amount Discount'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=6, decimal_places=2, help_text="Percentage (e.g. 10.00) or Flat Amount (e.g. 5.00)")
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'), help_text="Minimum subtotal required to apply this coupon")
    max_discount_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Optional max cap for percentage discounts")
    is_active = models.BooleanField(default=True, help_text="Whether this coupon is currently active")
    valid_from = models.DateTimeField(help_text="Start date and time of coupon validity")
    valid_until = models.DateTimeField(help_text="Expiry date and time of coupon validity")
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Max times this coupon can be redeemed across all orders")
    times_used = models.PositiveIntegerField(default=0, help_text="Number of times this coupon has been successfully redeemed")

    class Meta:
        ordering = ['-valid_until']

    def __str__(self):
        if self.discount_type == 'PERCENTAGE':
            return f"{self.code} ({self.discount_value}% off)"
        from django.conf import settings
        currency = getattr(settings, 'OFO_CURRENCY_SYMBOL', '₹')
        return f"{self.code} ({currency}{self.discount_value} off)"

    def is_valid_for_subtotal(self, subtotal):
        """
        Validates coupon against current time, active status, usage limits, and minimum subtotal.
        Returns (is_valid: bool, error_message: str).
        """
        now = timezone.now()

        if not self.is_active:
            return False, f"Coupon '{self.code}' is inactive."

        if now < self.valid_from:
            return False, f"Coupon '{self.code}' is not yet valid (starts {self.valid_from.strftime('%b %d, %Y')})."

        if now > self.valid_until:
            return False, f"Coupon '{self.code}' has expired on {self.valid_until.strftime('%b %d, %Y')}."

        if self.max_uses is not None and self.times_used >= self.max_uses:
            return False, f"Coupon '{self.code}' has reached its maximum redemption limit."

        subtotal_dec = Decimal(str(subtotal))
        if subtotal_dec < self.min_order_value:
            from django.conf import settings
            currency = getattr(settings, 'OFO_CURRENCY_SYMBOL', '₹')
            return False, f"Order subtotal ({currency}{subtotal_dec:.2f}) is below the minimum required ({currency}{self.min_order_value:.2f}) for '{self.code}'."

        return True, ""

    def calculate_discount(self, subtotal):
        """
        Calculates the exact discount for a given subtotal.
        Guarantees discount never exceeds subtotal or results in negative payable amount.
        """
        subtotal_dec = Decimal(str(subtotal))
        is_valid, _ = self.is_valid_for_subtotal(subtotal_dec)
        if not is_valid:
            return Decimal('0.00')

        if self.discount_type == 'PERCENTAGE':
            disc = (subtotal_dec * self.discount_value) / Decimal('100.00')
            if self.max_discount_amount is not None and disc > self.max_discount_amount:
                disc = self.max_discount_amount
        elif self.discount_type == 'FLAT':
            disc = self.discount_value
        else:
            disc = Decimal('0.00')

        # Never exceed subtotal and never negative
        if disc > subtotal_dec:
            disc = subtotal_dec
        if disc < Decimal('0.00'):
            disc = Decimal('0.00')

        return disc.quantize(Decimal('0.01'))


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
    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
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