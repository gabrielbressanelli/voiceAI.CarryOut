from MenuOrders.models import Menu
from decimal import Decimal

CART_SESSION_KEY = 'cart'

class Cart():
    def __init__(self, request):
        self.session = request.session
        data = self.session.get(CART_SESSION_KEY)

        # migrate from old key if present (cart = session_key)
        if data is None and "session_key" in self.session and isinstance(self.session["session_key"], dict):
            data = self.session["session_key"]
            self.session[CART_SESSION_KEY] = data
            del self.session["session_key"]
            self.session.modified = True

        if data is None:
            data = {}
            self.session[CART_SESSION_KEY] = data
        
        self.cart = data

    def add(self, item, quantity):
        item_id = str(item.id)
        qty = int(quantity)
        self.cart[item_id] = int(self.cart.get(item_id, 0)) + qty
        self.session.modified = True


    def cart_total(self) -> Decimal:
        if not self.cart:
            return Decimal("0.00")
        
        # Make keys to ints and then map back for lookup
        ids = [int(k) for k in self.cart.keys()]
        menu_map = {str(m.id): m for m in Menu.objects.filter(id__in=ids)}

        total = Decimal("0.00")
        for item_id, qty in self.cart.items():
            m = menu_map.get(item_id)
            if m:
                total += m.price * int(qty)
        return total



    def __len__(self):
        return len(self.cart)

    def get_items(self):
        # Get ids from carts
        ids = list(self.cart.keys())

        # View ids to look up items on database model
        items = Menu.objects.filter(id__in=ids)

        return items

    def get_quants(self):
        quantites = self.cart
        return quantites

    def update(self, item, quantity):
        item_id = str(item)
        qty = max(0, int(quantity))
        if qty == 0:
            self.cart.pop(item_id, None)
        else:
            self.cart[item_id] = qty

        self.session.modified = True

        return self.cart

    def delete(self, item):
        item_id = str(item)

        # Delete from dictionary (cart)
        if item_id in self.cart:
            del self.cart[item_id]
            self.session.modified = True

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.session.modified = True


        
