from django import forms
from .models import ShippingAddress

class ShippingForm(forms.ModelForm):
    full_name = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}), required=True)
    email = forms.EmailField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}), required=True)
    address1 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address 1'}), required=True)
    address2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartament, Suite, etc'}), required=False)
    city = forms.CharField(label='',widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}), required=True)
    state = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}), required=True)
    zipcode = forms.IntegerField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip Code'}), required=True)

    class Meta:
        model = ShippingAddress
        fields = ['full_name', 'email', 'address1', 'address2', 'city', 'state', 'zipcode' ]

class PaymentForm(forms.Form):
    card_name = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name On Card'}), required=True)
    card_number = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Card Number'}), required=True)
    card_exp_date = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expiration Date'}), required=True)
    card_cvv_number = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CVV code'}), required=True)
    card_address1 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Address'}), required=True)
    card_address2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartament, Suite, etc'}), required=False)
    card_city = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing City'}), required=True)
    card_state = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing State'}), required=True)
    card_zipcode = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billin Zipcode'}), required=True)
    card_country = forms.CharField(label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Country'}), required=True)
