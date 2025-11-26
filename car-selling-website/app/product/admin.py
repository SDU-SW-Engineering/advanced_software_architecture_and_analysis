from django.contrib import admin
from product.models import Car, CarVariants

# Register your models here.
class CarVariantsInline(admin.StackedInline):
    model = CarVariants

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'description']
    inlines = [CarVariantsInline]
