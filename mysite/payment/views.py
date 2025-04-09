from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ShippingForm

def payment_success(request):
    return render(request, "payment_success.html", {})

def delivery_form(request):
    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your info has been saved")
            return redirect( "payment_success")
    else: 
        form = ShippingForm()

    return render(request, 'delivery.html', {'form':form})
        