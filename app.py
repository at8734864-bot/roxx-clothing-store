from flask import Flask, render_template, redirect, url_for, session, request

app = Flask(__name__)
app.secret_key = "roxx-secret-key"


# =========================
# PRODUCTS
# =========================

products = [
    {
        "id": 1,
        "name": "Classic Black T-Shirt",
        "price": 299,
        "category": "T-Shirts",
        "image": "tshirt.jpg"
    },
    {
        "id": 2,
        "name": "Oversized Hoodie",
        "price": 699,
        "category": "Hoodies",
        "image": "hoodie.jpg"
    },
    {
        "id": 3,
        "name": "Blue Jeans",
        "price": 799,
        "category": "Jeans",
        "image": "jeans.jpg"
    },
    {
        "id": 4,
        "name": "Street Jacket",
        "price": 999,
        "category": "Jackets",
        "image": "jacket.jpg"
    }
]


# =========================
# CART HELPER
# =========================

def get_cart():

    cart = session.get("cart", {})

    if not isinstance(cart, dict):
        cart = {}

    return cart


# =========================
# CART COUNT
# =========================

@app.context_processor
def cart_count():

    cart = get_cart()

    count = sum(cart.values())

    return {
        "cart_count": count
    }


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html",
        products=products
    )


# =========================
# PRODUCTS
# =========================

@app.route("/products")
def products_page():

    return render_template(
        "products.html",
        products=products
    )


# =========================
# PRODUCT DETAILS
# =========================

@app.route("/product/<int:product_id>")
def product_page(product_id):

    product = next(
        (p for p in products if p["id"] == product_id),
        None
    )

    if product is None:
        return "Product not found", 404

    return render_template(
        "product.html",
        product=product
    )


# =========================
# ADD TO CART
# =========================

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):

    cart = get_cart()

    size = request.args.get("size")

    if not size:
        return redirect(
            url_for(
                "product_page",
                product_id=product_id
            )
        )

    # GET QUANTITY

    quantity = request.args.get(
        "quantity",
        1,
        type=int
    )

    if quantity < 1:
        quantity = 1

    product_id = str(product_id)

    cart_key = product_id + "_" + size

    # ADD SELECTED QUANTITY

    cart[cart_key] = cart.get(
        cart_key,
        0
    ) + quantity

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# INCREASE
# =========================

@app.route("/increase/<int:product_id>")
def increase(product_id):

    cart = get_cart()

    size = request.args.get("size")

    if not size:
        return redirect(url_for("cart"))

    product_id = str(product_id)

    cart_key = product_id + "_" + size

    if cart_key in cart:
        cart[cart_key] += 1

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# DECREASE
# =========================

@app.route("/decrease/<int:product_id>")
def decrease(product_id):

    cart = get_cart()

    size = request.args.get("size")

    if not size:
        return redirect(url_for("cart"))

    product_id = str(product_id)

    cart_key = product_id + "_" + size

    if cart_key in cart:

        cart[cart_key] -= 1

        if cart[cart_key] <= 0:
            del cart[cart_key]

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# REMOVE
# =========================

@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):

    cart = get_cart()

    size = request.args.get("size")

    if not size:
        return redirect(url_for("cart"))

    product_id = str(product_id)

    cart_key = product_id + "_" + size

    if cart_key in cart:
        del cart[cart_key]

    session["cart"] = cart

    return redirect(url_for("cart"))


# =========================
# CART PAGE
# =========================

@app.route("/cart")
def cart():

    cart = get_cart()

    cart_products = []

    total = 0

    for cart_key, quantity in cart.items():

        try:
            product_id, size = cart_key.split("_", 1)

            product_id = int(product_id)
            quantity = int(quantity)

        except (ValueError, TypeError):
            continue

        product = next(
            (
                p for p in products
                if p["id"] == product_id
            ),
            None
        )

        if product is None:
            continue

        item = product.copy()

        item["quantity"] = quantity
        item["size"] = size
        item["subtotal"] = product["price"] * quantity

        cart_products.append(item)

        total += item["subtotal"]

    return render_template(
        "cart.html",
        cart_products=cart_products,
        total=total
    )


# =========================
# CHECKOUT
# =========================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = get_cart()

    if not cart:
        return redirect(url_for("cart"))

    # PLACE ORDER

    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")
        address = request.form.get("address")
        payment = request.form.get("payment")

        print("NEW ORDER")
        print("Name:", name)
        print("Phone:", phone)
        print("Address:", address)
        print("Payment:", payment)

        session["cart"] = {}

        return render_template("success.html")

    # ORDER SUMMARY

    cart_products = []

    total = 0

    for cart_key, quantity in cart.items():

        try:
            product_id, size = cart_key.split("_", 1)

            product_id = int(product_id)
            quantity = int(quantity)

        except (ValueError, TypeError):
            continue

        product = next(
            (
                p for p in products
                if p["id"] == product_id
            ),
            None
        )

        if product is None:
            continue

        item = product.copy()

        item["quantity"] = quantity
        item["size"] = size
        item["subtotal"] = product["price"] * quantity

        cart_products.append(item)

        total += item["subtotal"]

    return render_template(
        "checkout.html",
        cart_products=cart_products,
        total=total
    )


# =========================
# ABOUT
# =========================

@app.route("/about")
def about():

    return render_template("about.html")


# =========================
# CONTACT
# =========================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        print("NEW CONTACT MESSAGE")
        print("Name:", name)
        print("Email:", email)
        print("Message:", message)

        return render_template(
            "contact.html",
            sent=True
        )

    return render_template("contact.html")


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    app.run(debug=True)