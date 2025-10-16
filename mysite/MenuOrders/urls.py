from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:menu_id>/modifiers/", views.menu_modifiers, name="menu_modifiers")
    
]