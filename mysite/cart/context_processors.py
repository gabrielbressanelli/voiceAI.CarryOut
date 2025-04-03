from .cart import Cart

# Create processor so cart works on every page of the website
def cart(request):
    # return default data from the Cart
    return {'cart': Cart(request)}