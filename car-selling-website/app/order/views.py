from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from account.models import Customer
from order.models import Cart,CartItems, Order, OrderItems
from product.models import Car
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

@login_required(login_url="/accounts/login/")
def get_cart(request):
    cart = None
    try:
        cart = Cart.objects.get(customer = request.user.customer)        
    except Exception as e:
        print(e)

    return render( request,'order/cart.html', context = {'cart' : cart})





@login_required(login_url="/account/login/")
def add_to_cart(request):
    try:
        customer = Customer.objects.get(user_ptr=request.user.id)
        car = request.GET.get('car_id')
        car_model = request.GET.get('car_model')
        car_engine = request.GET.get('car_engine')
        car_color = request.GET.get('car_color')
        car_price = request.GET.get('car_price')
        print("car", car)
        cart , _ = Cart.objects.get_or_create(customer = customer)
        cart_item , _  = CartItems.objects.get_or_create(cart = cart ,
                                                          car = Car.objects.get(id = car), car_model=car_model, car_engine=car_engine, car_color=car_color, car_price=car_price)
        print(cart_item)
        cart_item.quantity += 1
        cart_item.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    
    except Exception as e:
        messages.error(request, 'Invalid car ID')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required(login_url="/accounts/login/")
def remove_to_cart(request):
    try:
        customer = Customer.objects.get(user_ptr=request.user.id)
        car = request.GET.get('car_id')

        cart , _ = Cart.objects.get_or_create(customer = customer)
        cart_item   = CartItems.objects.filter(cart = cart , car = Car.objects.get(id = car))
        quantity = request.GET.get('quantity')

        if cart_item.exists():
            cart_item = cart_item[0]

            if quantity:
                cart_item.quantity = int(quantity)
            else:
                cart_item.quantity -= 1

            if cart_item.quantity <= 0:
                cart_item.delete()
            else:
                cart_item.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    
    except Exception as e:
        print(e)
        messages.error(request, 'Invalid Product ID')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required(login_url="/accounts/login/")
def checkout_view(request, cart_id):
    cart = Cart.objects.get(id=cart_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        cart.convertToOrder(
            name=name,
            email=email,
            phone=phone,
            address=address
        )
        cart.is_order = True
        cart.cart_items.all().delete()
        cart.save()

        return redirect('order-list')

    return render(request, 'order/checkout.html', {'cart': cart})

def order_list_view(request):
    if request.method == 'GET':
        customer = Customer.objects.get(user_ptr=request.user.id)
        orders = Order.objects.filter(customer=customer).order_by('-created_at')
        print("orders", orders)
        order_items = OrderItems.objects.filter(order__in=orders)
        print("order_items", order_items)
        return render(request, 'order/orders.html', context={'orders':orders, 'order_items':order_items})

