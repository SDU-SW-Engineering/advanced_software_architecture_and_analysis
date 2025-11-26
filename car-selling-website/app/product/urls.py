from django.urls import path
from product import views

urlpatterns = [
    path("", views.car_list_view, name='car-list'),
    path("product/<str:car_id>/", views.car_retrieve_view, name='car-retrieve-view'),
]
