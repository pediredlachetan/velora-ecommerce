from django.db import models
from django.conf import settings

# Create your models here.

class Product(models.Model):
    name=models.CharField(max_length=100)
    description=models.TextField()
    category=models.CharField(max_length=100, default='General')
    price=models.DecimalField(max_digits=10, decimal_places=2)
    stock=models.PositiveBigIntegerField(default=0)
    image=models.ImageField(upload_to='products/', blank=True, null=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders',
    null=True,
    blank=True,
)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=10)
    address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20,choices=[('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'),('cancelled', 'Cancelled'),], default='pending',)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order by {self.full_name} - {self.created_at}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True
    )
    product_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.price * self.quantity

    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"



class ProductReview(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'],
                name='unique_product_review_per_user'
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name='product_review_rating_1_to_5'
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.product.name} ({self.rating}/5)'

