from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Customer(User):
    profile_image = models.ImageField(upload_to="customer/", null=True , blank=True)


    def getCartItemCount(self):
        from order.models import CartItems
        return CartItems.objects.filter(cart__customer = self).count()
