from django.urls import path
from order import views

urlpatterns = [
    path('orders/', views.order_list_view, name='order-list'),
    path('cart/',views.get_cart, name='cart'),
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('remove-cart-item/', views.remove_to_cart, name='remove-cart-item'),
    path('checkout/<str:cart_id>/', views.checkout_view, name='checkout-view'),
]
