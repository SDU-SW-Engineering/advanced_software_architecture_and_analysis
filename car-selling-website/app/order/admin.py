from django.contrib import admin
from order.models import Cart, CartItems, Order, OrderItems

# Register your models here.
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer']

@admin.register(CartItems)
class CartItemsAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'car', 'quantity']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id']

@admin.register(OrderItems)
class OrderItemsAdmin(admin.ModelAdmin):
    list_display = ['id']
