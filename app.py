import os
import sqlite3
import uuid

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash
)

from werkzeug.utils import secure_filename


# ==================================================
# APP
# ==================================================

app = Flask(__name__)

app.secret_key = "roxx-secret-key-2026"


# ==================================================
# ADMIN LOGIN
# ==================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "roxx2026"


# ==================================================
# PATHS
# ==================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

IS_VERCEL = bool(
    os.environ.get("VERCEL")
)

if IS_VERCEL:

    DATABASE = "/tmp/roxx.db"

    UPLOAD_FOLDER = "/tmp/roxx_uploads"

else:

    DATABASE = os.path.join(
        BASE_DIR,
        "roxx.db"
    )

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "images",
        "uploads"
    )


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    5 * 1024 * 1024
)


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ==================================================
# ALLOWED IMAGE TYPES
# ==================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower() in ALLOWED_EXTENSIONS
    )


# ==================================================
# DATABASE
# ==================================================

def get_db():

    db = sqlite3.connect(
        DATABASE
    )

    db.row_factory = sqlite3.Row

    return db


def init_db():

    db = get_db()


    # PRODUCTS TABLE

    db.execute("""
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            price REAL NOT NULL,

            category TEXT NOT NULL,

            image TEXT NOT NULL

        )
    """)


    # ORDERS TABLE

    db.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_name TEXT NOT NULL,

            phone TEXT NOT NULL,

            address TEXT NOT NULL,

            payment TEXT NOT NULL,

            total REAL NOT NULL,

            status TEXT NOT NULL DEFAULT 'New',

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

        )
    """)
    # PRODUCT DETAILS MIGRATION

    existing_columns = {
        row[1]
        for row in db.execute(
            "PRAGMA table_info(products)"
        ).fetchall()
    }

    new_columns = {
    "description": "TEXT DEFAULT ''",
    "material": "TEXT DEFAULT ''",
    "fabric_weight": "TEXT DEFAULT ''",
    "fit": "TEXT DEFAULT ''",
    "care": "TEXT DEFAULT ''",
    "shipping_returns": "TEXT DEFAULT ''",
    "back_image": "TEXT DEFAULT ''"
}
    for column, data_type in new_columns.items():

        if column not in existing_columns:

            db.execute(
                f"ALTER TABLE products ADD COLUMN {column} {data_type}"
            )

    # ORDER ITEMS TABLE

    db.execute("""
        CREATE TABLE IF NOT EXISTS order_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id INTEGER NOT NULL,

            product_id INTEGER NOT NULL,

            product_name TEXT NOT NULL,

            size TEXT NOT NULL,

            quantity INTEGER NOT NULL,

            price REAL NOT NULL,

            subtotal REAL NOT NULL,

            FOREIGN KEY(order_id)
                REFERENCES orders(id)

        )
    """)


    # REPLACE OLD PRODUCT CATALOG (RUN ONCE)

   # ==================================================
# PRODUCT CATALOG MIGRATIONS
# ==def init_db():

   # ==================================================
# PRODUCT CATALOG MIGRATIONS
# ==================================================

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS app_migrations (
            migration_key TEXT PRIMARY KEY
        )
    """)

    # ==============================================
    # ORIGINAL CATALOG MIGRATION
    # ==============================================

    migration_key = "roxx_cheetah_catalog_v1"

    migration_done = db.execute(
        "SELECT migration_key FROM app_migrations WHERE migration_key = ?",
        (migration_key,)
    ).fetchone()

    if migration_done is None:

        existing_products = db.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if existing_products == 0:

            original_products = [

                (
                    "CHEETAH HOODIE — BLACK",
                    1000,
                    "Hoodies",
                    "cheetah-hoodie-black.png"
                ),

                (
                    "CHEETAH PANTS — BLACK",
                    1000,
                    "Pants",
                    "cheetah-pants-black.png"
                ),

                (
                    "CHEETAH SET — BLACK",
                    2000,
                    "Sets",
                    "cheetah-set-black.png"
                ),

                (
                    "CHEETAH SET — OFF WHITE",
                    2000,
                    "Sets",
                    "cheetah-set-offwhite.png"
                )

            ]

            db.executemany(
                """
                INSERT INTO products
                (name, price, category, image)
                VALUES (?, ?, ?, ?)
                """,
                original_products
            )

        db.execute(
            "INSERT INTO app_migrations (migration_key) VALUES (?)",
            (migration_key,)
        )

    # ==============================================
    # ADD OFF WHITE PRODUCTS
    # ==============================================

    migration_key = "roxx_offwhite_separate_products_v1"

    migration_done = db.execute(
        "SELECT migration_key FROM app_migrations WHERE migration_key = ?",
        (migration_key,)
    ).fetchone()

    if migration_done is None:

        # Update existing product images to PNG

        db.execute("""
            UPDATE products
            SET image = 'cheetah-hoodie-black.png'
            WHERE name = 'CHEETAH HOODIE — BLACK'
        """)

        db.execute("""
            UPDATE products
            SET image = 'cheetah-pants-black.png'
            WHERE name = 'CHEETAH PANTS — BLACK'
        """)

        db.execute("""
            UPDATE products
            SET image = 'cheetah-set-black.png'
            WHERE name = 'CHEETAH SET — BLACK'
        """)

        db.execute("""
            UPDATE products
            SET image = 'cheetah-set-offwhite.png'
            WHERE name = 'CHEETAH SET — OFF WHITE'
        """)

        new_products = [

            (
                "CHEETAH HOODIE — OFF WHITE",
                1000,
                "Hoodies",
                "cheetah-hoodie-offwhite.png"
            ),

            (
                "CHEETAH PANTS — OFF WHITE",
                1000,
                "Pants",
                "cheetah-pants-offwhite.png"
            )

        ]

        for product in new_products:

            existing = db.execute(
                "SELECT id FROM products WHERE name = ?",
                (product[0],)
            ).fetchone()

            if existing is None:

                db.execute(
                    """
                    INSERT INTO products
                    (name, price, category, image)
                    VALUES (?, ?, ?, ?)
                    """,
                    product
                )

        db.execute(
            "INSERT INTO app_migrations (migration_key) VALUES (?)",
            (migration_key,)
        )

    # ==============================================
    # SAVE AND CLOSE DATABASE
    # ==============================================

    db.commit()
    db.close()
# Initialize database when application starts
init_db()
# ==================================================
# PRODUCT FUNCTIONS
# ==================================================

def get_all_products():

    db = get_db()

    products_rows = db.execute(
        "SELECT * FROM products"
    ).fetchall()

    db.close()

    return [
        dict(product)
        for product in products_rows
    ]


def get_product(product_id):

    db = get_db()

    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    db.close()

    if product:
        return dict(product)

    return None


# ==================================================
# CART
# ==================================================

def get_cart():

    cart = session.get(
        "cart",
        {}
    )

    if not isinstance(
        cart,
        dict
    ):

        cart = {}

    return cart


@app.context_processor
def cart_count():

    cart = get_cart()

    count = 0

    for quantity in cart.values():

        try:

            count += int(
                quantity
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    return {
        "cart_count": count
    }


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    products = get_all_products()

    return render_template(
        "index.html",
        products=products
    )


# ==================================================
# PRODUCTS
# ==================================================

@app.route("/products")
def products_page():

    products = get_all_products()

    return render_template(
        "products.html",
        products=products
    )


# ==================================================
# PRODUCT PAGE
# ==================================================


@app.route("/product/<int:product_id>")
def product_page(product_id):

    product = get_product(product_id)

    if product is None:
        return "Product not found", 404

    # PRODUCT BACK IMAGES

    back_images = {
        "CHEETAH HOODIE — BLACK": "cheetah-hoodie-black-back.png",

        "CHEETAH PANTS — BLACK": "cheetah-pants-black-back.png",

        "CHEETAH HOODIE — OFF WHITE": "cheetah-hoodie-offwhite-back.png",

        "CHEETAH PANTS — OFF WHITE": "cheetah-pants-offwhite-back.png"
    }

    # ASSIGN BACK IMAGE

    if product["name"] in back_images:
        product["back_image"] = back_images[product["name"]]

    return render_template(
        "product.html",
        product=product
    )


# ==================================================
# ADD TO CART
# ==================================================

# ==================================================
# ADD TO CART
# ==================================================

@app.route(
    "/add-to-cart/<int:product_id>"
)
def add_to_cart(product_id):

    product = get_product(
        product_id
    )

    if product is None:

        return (
            "Product not found",
            404
        )

    cart = get_cart()

    size = request.args.get(
        "size"
    )

    if not size:

        return redirect(
            url_for(
                "product_page",
                product_id=product_id
            )
        )

    quantity = request.args.get(
        "quantity",
        1,
        type=int
    )

    if quantity < 1:

        quantity = 1

    cart_key = (
        str(product_id)
        + "_"
        + size
    )

    cart[cart_key] = (
        cart.get(
            cart_key,
            0
        )
        + quantity
    )

    session["cart"] = cart

    return redirect(
        url_for(
            "cart"
        )
    )


# ==================================================
# INCREASE
# ==================================================

@app.route(
    "/increase/<int:product_id>"
)
def increase(product_id):

    cart = get_cart()

    size = request.args.get(
        "size"
    )

    if not size:

        return redirect(
            url_for(
                "cart"
            )
        )

    cart_key = (
        str(product_id)
        + "_"
        + size
    )

    if cart_key in cart:

        cart[cart_key] += 1

    session["cart"] = cart

    return redirect(
        url_for(
            "cart"
        )
    )


# ==================================================
# DECREASE
# ==================================================

@app.route(
    "/decrease/<int:product_id>"
)
def decrease(product_id):

    cart = get_cart()

    size = request.args.get(
        "size"
    )

    if not size:

        return redirect(
            url_for(
                "cart"
            )
        )

    cart_key = (
        str(product_id)
        + "_"
        + size
    )

    if cart_key in cart:

        cart[cart_key] -= 1

        if cart[cart_key] <= 0:

            del cart[cart_key]

    session["cart"] = cart

    return redirect(
        url_for(
            "cart"
        )
    )
# ==================================================
# REMOVE FROM CART
# ==================================================

@app.route(
    "/remove-from-cart/<int:product_id>"
)
def remove_from_cart(product_id):

    cart = get_cart()

    size = request.args.get(
        "size"
    )

    if not size:

        return redirect(
            url_for("cart")
        )

    cart_key = (
        str(product_id)
        + "_"
        + size
    )

    if cart_key in cart:

        del cart[cart_key]

    session["cart"] = cart

    return redirect(
        url_for("cart")
    )


# ==================================================
# CART
# ==================================================

@app.route("/cart")
def cart():

    cart = get_cart()

    cart_products = []

    total = 0

    for cart_key, quantity in cart.items():

        try:

            product_id, size = cart_key.split(
                "_",
                1
            )

            product_id = int(product_id)

            quantity = int(quantity)

        except (
            ValueError,
            TypeError
        ):

            continue

        product = get_product(
            product_id
        )

        if product is None:

            continue

        item = product.copy()

        item["quantity"] = quantity

        item["size"] = size

        item["subtotal"] = (
            product["price"]
            * quantity
        )

        cart_products.append(item)

        total += item["subtotal"]

    return render_template(
        "cart.html",
        cart_products=cart_products,
        total=total
    )


# ==================================================
# CHECKOUT
# ==================================================

@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    cart = get_cart()

    if not cart:

        return redirect(
            url_for("cart")
        )

    # CREATE ORDER

    if request.method == "POST":

        name = (
            request.form.get("name")
            or request.form.get("full_name")
            or request.form.get("fullName")
            or ""
        ).strip()

        phone = (
            request.form.get("phone")
            or request.form.get("phone_number")
            or request.form.get("phoneNumber")
            or ""
        ).strip()

        address = (
            request.form.get("address")
            or ""
        ).strip()

        payment = (
            request.form.get("payment")
            or "Cash on Delivery"
        ).strip()

        if (
            not name
            or not phone
            or not address
        ):

            flash(
                "Please fill in all checkout fields.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

        # ORDER ITEMS

        order_items = []

        total = 0

        for cart_key, quantity in cart.items():

            try:

                product_id, size = cart_key.split(
                    "_",
                    1
                )

                product_id = int(product_id)

                quantity = int(quantity)

            except (
                ValueError,
                TypeError
            ):

                continue

            product = get_product(
                product_id
            )

            if product is None:

                continue

            subtotal = (
                product["price"]
                * quantity
            )

            order_items.append({

                "product_id": product_id,

                "product_name": product["name"],

                "size": size,

                "quantity": quantity,

                "price": product["price"],

                "subtotal": subtotal

            })

            total += subtotal

        if not order_items:

            return redirect(
                url_for("cart")
            )

        # SAVE ORDER

        db = get_db()

        cursor = db.execute(
            """
            INSERT INTO orders
            (
                customer_name,
                phone,
                address,
                payment,
                total,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                address,
                payment,
                total,
                "New"
            )
        )

        order_id = cursor.lastrowid

        # SAVE ORDER ITEMS

        for item in order_items:

            db.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    product_id,
                    product_name,
                    size,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["size"],
                    item["quantity"],
                    item["price"],
                    item["subtotal"]
                )
            )

        db.commit()

        db.close()

        # CLEAR CART

        session["cart"] = {}

        print(
            "NEW ORDER:",
            order_id
        )

        return render_template(
            "success.html"
        )

    # CHECKOUT PAGE

    cart_products = []

    total = 0

    for cart_key, quantity in cart.items():

        try:

            product_id, size = cart_key.split(
                "_",
                1
            )

            product_id = int(product_id)

            quantity = int(quantity)

        except (
            ValueError,
            TypeError
        ):

            continue

        product = get_product(
            product_id
        )

        if product is None:

            continue

        item = product.copy()

        item["quantity"] = quantity

        item["size"] = size

        item["subtotal"] = (
            product["price"]
            * quantity
        )

        cart_products.append(item)

        total += item["subtotal"]

    return render_template(
        "checkout.html",
        cart_products=cart_products,
        total=total
    )


# ==================================================
# ABOUT
# ==================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# ==================================================
# CONTACT
# ==================================================

@app.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if request.method == "POST":

        name = request.form.get(
            "name"
        )

        email = request.form.get(
            "email"
        )

        message = request.form.get(
            "message"
        )

        print(
            "NEW CONTACT MESSAGE"
        )

        print(
            "Name:",
            name
        )

        print(
            "Email:",
            email
        )

        print(
            "Message:",
            message
        )

        return render_template(
            "contact.html",
            sent=True
        )

    return render_template(
        "contact.html"
    )
# ==================================================
# ADMIN LOGIN
# ==================================================

def admin_logged_in():

    return session.get(
        "admin_logged_in",
        False
    )


@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if admin_logged_in():

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Wrong username or password.",
            "error"
        )

    return render_template(
        "admin_login.html"
    )


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin")
def admin_dashboard():

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    # PRODUCTS

    products = get_all_products()

    # ORDERS

    db = get_db()

    orders_rows = db.execute(
        """
        SELECT *
        FROM orders
        ORDER BY id DESC
        """
    ).fetchall()

    orders = []

    for order_row in orders_rows:

        order = dict(order_row)

        items_rows = db.execute(
            """
            SELECT *
            FROM order_items
            WHERE order_id = ?
            ORDER BY id ASC
            """,
            (
                order["id"],
            )
        ).fetchall()

        order["items"] = [
            dict(item)
            for item in items_rows
        ]

        orders.append(order)

    db.close()

    return render_template(
    "admin_dashboard.html",
    products=products,
    orders=orders
)


# ==================================================
# ADMIN ADD PRODUCT
# ==================================================

@app.route(
    "/admin/add-product",
    methods=["POST"]
)
def admin_add_product():

    if not admin_logged_in():
        return redirect(url_for("admin_login"))

    # BASIC INFORMATION

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    price_text = request.form.get("price", "").strip()

    # PRODUCT DETAILS

    description = request.form.get("description", "").strip()
    material = request.form.get("material", "").strip()
    fabric_weight = request.form.get("fabric_weight", "").strip()
    fit = request.form.get("fit", "").strip()
    care = request.form.get("care", "").strip()
    shipping_returns = request.form.get("shipping_returns", "").strip()

    # IMAGES

    image = request.files.get("image")
    back_image_file = request.files.get("back_image")

    # VALIDATION

    if not name or not category or not price_text:
        flash("Please fill in all product fields.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        price = float(price_text)

        if price < 0:
            raise ValueError

    except ValueError:
        flash("Please enter a valid price.", "error")
        return redirect(url_for("admin_dashboard"))

    if image is None or image.filename == "":
        flash("Please choose a front product image.", "error")
        return redirect(url_for("admin_dashboard"))

    if not allowed_file(image.filename):
        flash("Invalid front image format.", "error")
        return redirect(url_for("admin_dashboard"))

    if back_image_file and back_image_file.filename:
        if not allowed_file(back_image_file.filename):
            flash("Invalid back image format.", "error")
            return redirect(url_for("admin_dashboard"))

    # SAVE FRONT IMAGE

    original_name = secure_filename(image.filename)
    extension = original_name.rsplit(".", 1)[1].lower()

    unique_name = uuid.uuid4().hex + "." + extension

    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    image.save(save_path)

    image_path = "uploads/" + unique_name

    # SAVE BACK IMAGE

    back_image_path = ""

    if back_image_file and back_image_file.filename:

        back_original_name = secure_filename(back_image_file.filename)

        back_extension = back_original_name.rsplit(".", 1)[1].lower()

        back_unique_name = uuid.uuid4().hex + "." + back_extension

        back_save_path = os.path.join(
            UPLOAD_FOLDER,
            back_unique_name
        )

        back_image_file.save(back_save_path)

        back_image_path = "uploads/" + back_unique_name

    # DATABASE

    db = get_db()

    db.execute(
        """
        INSERT INTO products
        (
            name,
            price,
            category,
            image,
            description,
            material,
            fabric_weight,
            fit,
            care,
            shipping_returns,
            back_image
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            price,
            category,
            image_path,
            description,
            material,
            fabric_weight,
            fit,
            care,
            shipping_returns,
            back_image_path
        )
    )

    db.commit()
    db.close()

    flash("Product added successfully.", "success")

    return redirect(url_for("admin_dashboard"))
    # BASIC PRODUCT INFORMATION

    name = request.form.get(
        "name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    price_text = request.form.get(
        "price",
        ""
    ).strip()

    # ADDITIONAL PRODUCT DETAILS

    description = request.form.get(
        "description",
        ""
    ).strip()

    material = request.form.get(
        "material",
        ""
    ).strip()

    fabric_weight = request.form.get(
        "fabric_weight",
        ""
    ).strip()

    fit = request.form.get(
        "fit",
        ""
    ).strip()

    care = request.form.get(
        "care",
        ""
    ).strip()

    shipping_returns = request.form.get(
        "shipping_returns",
        ""
    ).strip()

    # PRODUCT IMAGE

    image = request.files.get(
        "image"
    )

    if (
        not name
        or not category
        or not price_text
    ):

        flash(
            "Please fill in all product fields.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    # VALIDATE PRICE

    try:

        price = float(price_text)

        if price < 0:

            raise ValueError

    except ValueError:

        flash(
            "Please enter a valid price.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    # VALIDATE IMAGE

    if (
        image is None
        or image.filename == ""
    ):

        flash(
            "Please choose a product image.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    if not allowed_file(image.filename):

        flash(
            "Only JPG, JPEG, PNG, WEBP and GIF images are allowed.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    # SAVE IMAGE

    original_name = secure_filename(
        image.filename
    )

    extension = original_name.rsplit(
        ".",
        1
    )[1].lower()

    unique_name = (
        uuid.uuid4().hex
        + "."
        + extension
    )

    save_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    image.save(save_path)

    image_path = (
        "uploads/"
        + unique_name
    )

    # SAVE PRODUCT TO DATABASE

    db = get_db()

    db.execute(
        """
        INSERT INTO products
        (
            name,
            price,
            category,
            image,
            description,
            material,
            fabric_weight,
            fit,
            care,
            shipping_returns
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            name,
            price,
            category,
            image_path,
            description,
            material,
            fabric_weight,
            fit,
            care,
            shipping_returns
        )
    )

    db.commit()

    db.close()

    flash(
        "Product added successfully.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )
# ==================================================
# ADMIN DELETE PRODUCT
# ==================================================

@app.route(
    "/admin/delete-product/<int:product_id>",
    methods=["POST"]
)
def admin_delete_product(product_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    product = get_product(product_id)

    if product is None:

        flash(
            "Product not found.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    db = get_db()

    db.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (
            product_id,
        )
    )

    db.commit()

    db.close()

    if product["image"].startswith("uploads/"):

        image_path = os.path.join(
            UPLOAD_FOLDER,
            os.path.basename(product["image"])
        )

        if os.path.exists(image_path):

            try:

                os.remove(image_path)

            except OSError:

                pass

    flash(
        "Product deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# ==================================================
# ADMIN UPDATE ORDER
# ==================================================

@app.route(
    "/admin/update-order/<int:order_id>",
    methods=["POST"]
)
def admin_update_order(order_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    status = request.form.get(
        "status",
        "New"
    ).strip()

    allowed_statuses = {
        "New",
        "Processing",
        "Shipped",
        "Completed",
        "Cancelled"
    }

    if status not in allowed_statuses:

        flash(
            "Invalid order status.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    db = get_db()

    db.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            order_id
        )
    )

    db.commit()

    db.close()

    flash(
        "Order status updated.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# ==================================================
# ADMIN LOGOUT
# ==================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# ==================================================
# RUN LOCAL
# ==================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)