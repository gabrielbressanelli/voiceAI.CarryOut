from django.urls import path, include
from . import views

urlpatterns = [
    path('payment_success', views.payment_success, name="payment_success"),
    path('payment_failed', views.payment_failed, name="payment_failed"),
    path('delivery', views.delivery_form, name="delivery_form"),
    path('billing_info', views.billing_info, name='billing_info'),
    path('process_order', views.process_order, name='process_order'),
    path('paypal', include("paypal.standard.ipn.urls")),
    path("pay/create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    path("pay/success/", views.checkout_success, name="checkout_success"),
    path("pay/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("pay/webhook/", views.stripe_webhook, name="stripe_webhook"),
]