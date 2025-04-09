from django.urls import path
from . import views

urlpatterns = [
    path('payment_success', views.payment_success, name="payment_success"),
    path('delivery', views.delivery_form, name="delivery_form") 
]