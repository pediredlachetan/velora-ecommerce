from django.contrib import admin
from .models import Product, Order, OrderItem, ProductReview

# Register your models here.



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'email',
        'phone',
        'total_amount',
        'status',
        'created_at',
    )

    search_fields = ('full_name', 'email', 'phone')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_name', 'price', 'quantity')
    search_fields = ('product_name',)

admin.site.register(Product)

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')
    ordering = ('-created_at',)