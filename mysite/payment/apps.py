from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payment'

    # Adding paypal ipn
    def ready(self):
        import payment.hooks
