from django.urls import path
from . import views

app_name = "cart"

urlpatterns =[
    path('', views.cart_summary, name="cart_summary"),
    path('add/', views.cart_add, name="cart_add"),
    path('delete/', views.cart_delete, name="cart_delete"),
    path('update/', views.cart_update, name='cart_update'),
    path('count/', views.cart_count, name="cart_count"),
    path('import/', views.import_cart, name="cart_import"),
    path('import-link/', views.cart_import_link, name="cart_import_link"),
]