from django.shortcuts import render
from product.models import Car, CarVariants
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, get_object_or_404

# Create your views here.
def car_list_view(request):
    if request.method == 'GET':
        cars = Car.objects.all()
    return render(request, 'product/shop.html', context={'cars':cars})


def car_retrieve_view(request, car_id):

    car = get_object_or_404(Car, id=car_id)
    variants = car.car_variants.all()

    if not variants:
        return render(request, "product/product.html", {"car": car})

    default_variant = variants.first()

    models = list(variants.values_list('car_model', flat=True).distinct())
    engines = list(variants.values_list('car_engine', flat=True).distinct())
    colors  = list(variants.values_list('car_color', flat=True).distinct())

    variant_data = [
        {
            "id": v.id,
            "model": v.car_model,
            "engine": v.car_engine,
            "color": v.car_color,
            "price": float(v.car_price)
        }
        for v in variants
    ]

    return render(request, 'product/product.html', {
        "car": car,
        "models": models,
        "engines": engines,
        "colors": colors,
        "variant_data": json.dumps(variant_data, cls=DjangoJSONEncoder),
        "default_variant": default_variant,
    })

