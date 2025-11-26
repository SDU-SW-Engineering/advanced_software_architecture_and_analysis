from django.db import models
from account.models import Customer
from product.models import Car
from django.db.models import Sum,F

# Create your models here.
class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_cart")
    is_order = models.BooleanField(default=False)

    def getCartTotal(self):
        total = self.cart_items.aggregate(
            total = Sum(F('car_price') * F('quantity'))
        )['total']
        return total or 0
    
    def convertToOrder(self, name, email, phone, address):
            order = Order.objects.create(
                cart = self,
                customer = self.customer,
                name=name,
                email=email,
                phone=phone,
                address=address,
                total = self.getCartTotal()
            )
            for cart_item in self.cart_items.all():
                OrderItems.objects.create(
                    order = order,
                    car = cart_item.car,
                    quantity = cart_item.quantity,
                    car_model = cart_item.car_model,
                    car_engine = cart_item.car_engine,
                    car_color = cart_item.car_color,
                    car_price = cart_item.car_price
                )

class CartItems(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    car = models.ForeignKey(Car, null=True, on_delete=models.SET_NULL)
    car_model = models.CharField(max_length=100, null=True, blank=True)
    car_engine = models.CharField(max_length=100, null=True, blank=True)
    car_color = models.CharField(max_length=100, null=True, blank=True)
    car_price = models.IntegerField(default=0)
    quantity = models.IntegerField(default=0)


    def getCartItemTotal(self):
        return self.car_price * self.quantity 

class Order(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_order")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=50, choices=(('Accepted', 'Accepted'), ('Scheduled', 'Scheduled'), ('In Progress', 'In Progress'), ('Completed', 'Completed'),), default='Accepted')
    email = models.EmailField()
    phone = models.CharField(max_length=100)
    address = models.TextField()
    total = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItems(models.Model):
    order = models.ForeignKey(Order , on_delete=models.CASCADE, related_name="order_items")
    car = models.ForeignKey(Car, null=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField(default=0)
    car_model = models.CharField(max_length=100, null=True, blank=True)
    car_engine = models.CharField(max_length=100, null=True, blank=True)
    car_color = models.CharField(max_length=100, null=True, blank=True)
    car_price = models.FloatField()

    def getBase64Image(self):
        image_path = f"http://127.0.0.1:8000/{self.car.image}"
        print(image_path)


