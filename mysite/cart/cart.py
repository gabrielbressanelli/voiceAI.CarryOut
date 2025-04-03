from MenuOrders.models import Menu

class Cart():
    def __init__(self, request):
        self.session = request.session

        # Get current session key if it exists
        cart = self.session.get('session_key')

        # Create a new one if it does not find one
        if 'session_key' not in request.session:
            cart = self.session['session_key'] = {}

        #cart available everywhere
        self.cart = cart

    def add(self, item, quantity):
        item_id = str(item.id)
        item_qty = str(quantity)

        # Logic
        if item_id in self.cart:
            pass
        else:
            #self.cart[item_id] = {'price:' : str(item.price)}
            self.cart[item_id] = int(item_qty)

        self.session.modified = True

    def cart_total(self):
        # get item ids
        item_ids = self.cart.keys()
        #Look up keys in database
        items = Menu.objects.filter(id__in=item_ids)
        #Get quantities
        quantities = self.cart
        # Start counting at 0
        total = 0

        for key, value in quantities.items():
            #Converting string to int for math 
            key= int(key)
            for item in items: 
                if item.id == key: 
                    total = total + (item.price * value)
        return total


    def __len__(self):
        return len(self.cart)

    def get_items(self):
        # Get ids from carts
        item_ids = self.cart.keys()

        # View ids to look up items on database model
        items = Menu.objects.filter(id__in=item_ids)

        return items

    def get_quants(self):
        quantites = self.cart
        return quantites

    def update(self, item, quantity):
        item_id = str(item)
        item_qty = int(quantity)

        # Get Cart
        our_cart = self.cart

        #Update dictionary (cart)
        our_cart[item_id] = item_qty

        self.session.modified = True

        thing = self.cart

        return thing

    def delete(self, item):
        item_id = str(item)

        # Delete from dictionary (cart)
        if item_id in self.cart:
            del self.cart[item_id]

        self.session.modified = True


        
