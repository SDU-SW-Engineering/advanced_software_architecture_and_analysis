from django.db import models

# Create your models here.
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Car(BaseModel):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='car_image/', null=True, blank=True)

class CarVariants(BaseModel):
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='car_variants'
    )
    car_model = models.CharField(max_length=100)
    car_engine = models.CharField(max_length=100)
    car_color = models.CharField(max_length=100)
    car_price = models.CharField(max_length=100)

