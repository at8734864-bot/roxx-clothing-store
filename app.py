import os
import re
import requests

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash
)


# ==================================================
# APP CONFIGURATION
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "roxx-local-development-key-change-before-deploy"
)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ==================================================
# SHOPIFY CONFIGURATION
# ==================================================

SHOPIFY_STORE_DOMAIN = os.environ.get(
    "SHOPIFY_STORE_DOMAIN",
    ""
).strip()

SHOPIFY_API_VERSION = os.environ.get(
    "SHOPIFY_API_VERSION",
    "2026-10"
).strip()

SHOPIFY_STOREFRONT_ACCESS_TOKEN = os.environ.get(
    "SHOPIFY_STOREFRONT_ACCESS_TOKEN",
    ""
).strip()


def shopify_is_configured():

    return all([
        SHOPIFY_STORE_DOMAIN,
        SHOPIFY_API_VERSION,
        SHOPIFY_STOREFRONT_ACCESS_TOKEN
    ])


def shopify_endpoint():

    domain = SHOPIFY_STORE_DOMAIN.replace(
        "https://",
        ""
    ).replace(
        "http://",
        ""
    ).strip("/")

    return (
        f"https://{domain}/api/"
        f"{SHOPIFY_API_VERSION}/graphql.json"
    )


# ==================================================
# SHOPIFY GRAPHQL CLIENT
# ==================================================

def shopify_request(query, variables=None):

    if not shopify_is_configured():

        raise RuntimeError(
            "Shopify environment variables are missing."
        )

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Storefront-Access-Token":
            SHOPIFY_STOREFRONT_ACCESS_TOKEN
    }

    response = requests.post(
        shopify_endpoint(),
        headers=headers,
        json={
            "query": query,
            "variables": variables or {}
        },
        timeout=25
    )

    response.raise_for_status()

    result = response.json()

    if result.get("errors"):

        messages = [
            error.get("message", "Unknown Shopify error")
            for error in result["errors"]
        ]

        raise RuntimeError(
            "Shopify GraphQL error: "
            + " | ".join(messages)
        )

    return result.get("data", {})


# ==================================================
# PRODUCT QUERIES
# ==================================================

PRODUCTS_QUERY = """
query RoxxProducts {

    products(first: 100) {

        edges {

            node {

                id
                handle
                title
                description
                descriptionHtml
                productType
                vendor
                availableForSale

                featuredImage {
                    url
                    altText
                }

                images(first: 10) {

                    edges {

                        node {
                            url
                            altText
                        }

                    }

                }

                priceRange {

                    minVariantPrice {
                        amount
                        currencyCode
                    }

                }

                variants(first: 100) {

                    edges {

                        node {

                            id
                            title
                            availableForSale

                            selectedOptions {
                                name
                                value
                            }

                            price {
                                amount
                                currencyCode
                            }

                            image {
                                url
                                altText
                            }

                        }

                    }

                }

            }

        }

    }

}
"""


PRODUCT_QUERY = """
query RoxxSingleProduct($id: ID!) {

    product(id: $id) {

        id
        handle
        title
        description
        descriptionHtml
        productType
        vendor
        availableForSale

        featuredImage {
            url
            altText
        }

        images(first: 10) {

            edges {

                node {
                    url
                    altText
                }

            }

        }

        priceRange {

            minVariantPrice {
                amount
                currencyCode
            }

        }

        variants(first: 100) {

            edges {

                node {

                    id
                    title
                    availableForSale

                    selectedOptions {
                        name
                        value
                    }

                    price {
                        amount
                        currencyCode
                    }

                    image {
                        url
                        altText
                    }

                }

            }

        }

    }

}
"""


# ==================================================
# PRODUCT CONVERSION
# ==================================================

def numeric_shopify_id(gid):

    if not gid:
        return 0

    match = re.search(
        r"/(\d+)$",
        gid
    )

    return int(match.group(1)) if match else 0


def convert_shopify_product(node):

    if not node:
        return None

    images = [
        edge["node"]
        for edge in node.get(
            "images",
            {}
        ).get(
            "edges",
            []
        )
    ]

    variants = [
        edge["node"]
        for edge in node.get(
            "variants",
            {}
        ).get(
            "edges",
            []
        )
    ]

    featured_image = node.get(
        "featuredImage"
    ) or {}

    price_info = node.get(
        "priceRange",
        {}
    ).get(
        "minVariantPrice",
        {}
    )

    product_id = numeric_shopify_id(
        node.get("id")
    )

    converted_variants = []

    for variant in variants:

        selected_options = variant.get(
            "selectedOptions",
            []
        )

        size = ""

        for option in selected_options:

            if option.get("name", "").lower() in (
                "size",
                "sizes"
            ):

                size = option.get("value", "")

        variant_price = variant.get(
            "price",
            {}
        )

        converted_variants.append({

            "id": variant.get("id"),

            "numeric_id": numeric_shopify_id(
                variant.get("id")
            ),

            "title": variant.get("title"),

            "size": size,

            "available": variant.get(
                "availableForSale",
                False
            ),

            "price": float(
                variant_price.get("amount", 0)
            ),

            "currency": variant_price.get(
                "currencyCode",
                "EGP"
            ),

            "selected_options": selected_options

        })

    image_url = featured_image.get(
        "url",
        ""
    )

    if not image_url and images:

        image_url = images[0].get(
            "url",
            ""
        )

    back_image = ""

    if len(images) > 1:

        back_image = images[1].get(
            "url",
            ""
        )

    product = {

        "id": product_id,

        "shopify_id": node.get("id"),

        "handle": node.get("handle"),

        "name": node.get("title", ""),

        "title": node.get("title", ""),

        "description": node.get(
            "description",
            ""
        ),

        "description_html": node.get(
            "descriptionHtml",
            ""
        ),

        "category": node.get(
            "productType",
            "ROXX ORIGINALS"
        ),

        "vendor": node.get(
            "vendor",
            "ROXX"
        ),

        "price": float(
            price_info.get("amount", 0)
        ),

        "currency": price_info.get(
            "currencyCode",
            "EGP"
        ),

        "image": image_url,

        "back_image": back_image,

        "images": [
            image.get("url", "")
            for image in images
        ],

        "available": node.get(
            "availableForSale",
            False
        ),

        "variants": converted_variants,

        "sizes": [
            variant["size"]
            for variant in converted_variants
            if variant["size"]
        ]

    }

    return product


# ==================================================
# GET ALL PRODUCTS
# ==================================================

def get_all_products():

    data = shopify_request(
        PRODUCTS_QUERY
    )

    edges = data.get(
        "products",
        {}
    ).get(
        "edges",
        []
    )

    products = []

    for edge in edges:

        product = convert_shopify_product(
            edge.get("node")
        )

        if product:

            products.append(product)

    return products


# ==================================================
# GET ONE PRODUCT
# ==================================================

def get_product(product_id):

    try:

        product_id = int(product_id)

    except (
        ValueError,
        TypeError
    ):

        return None

    products = get_all_products()

    for product in products:

        if product["id"] == product_id:

            return product

    return None


# ==================================================
# CART GRAPHQL
# ==================================================

CART_FIELDS = """
id
checkoutUrl
totalQuantity

cost {
    subtotalAmount {
        amount
        currencyCode
    }

    totalAmount {
        amount
        currencyCode
    }
}

lines(first: 100) {

    edges {

        node {

            id
            quantity

            merchandise {

                ... on ProductVariant {

                    id
                    title

                    selectedOptions {
                        name
                        value
                    }

                    price {
                        amount
                        currencyCode
                    }

                    image {
                        url
                        altText
                    }

                    product {

                        id
                        title
                        handle

                        featuredImage {
                            url
                            altText
                        }

                    }

                }

            }

        }

    }

}
"""


CART_QUERY = f"""
query RoxxCart($id: ID!) {{

    cart(id: $id) {{

        {CART_FIELDS}

    }}

}}
"""


CART_CREATE_MUTATION = f"""
mutation RoxxCreateCart($input: CartInput!) {{

    cartCreate(input: $input) {{

        cart {{

            {CART_FIELDS}

        }}

        userErrors {{
            field
            message
        }}

    }}

}}
"""


CART_ADD_MUTATION = f"""
mutation RoxxAddToCart(
    $cartId: ID!,
    $lines: [CartLineInput!]!
) {{

    cartLinesAdd(
        cartId: $cartId,
        lines: $lines
    ) {{

        cart {{

            {CART_FIELDS}

        }}

        userErrors {{
            field
            message
        }}

    }}

}}
"""


CART_UPDATE_MUTATION = f"""
mutation RoxxUpdateCart(
    $cartId: ID!,
    $lines: [CartLineUpdateInput!]!
) {{

    cartLinesUpdate(
        cartId: $cartId,
        lines: $lines
    ) {{

        cart {{

            {CART_FIELDS}

        }}

        userErrors {{
            field
            message
        }}

    }}

}}
"""


CART_REMOVE_MUTATION = f"""
mutation RoxxRemoveCart(
    $cartId: ID!,
    $lineIds: [ID!]!
) {{

    cartLinesRemove(
        cartId: $cartId,
        lineIds: $lineIds
    ) {{

        cart {{

            {CART_FIELDS}

        }}

        userErrors {{
            field
            message
        }}

    }}

}}
"""


# ==================================================
# CART HELPERS
# ==================================================

def get_cart_id():

    return session.get(
        "shopify_cart_id"
    )


def save_cart_id(cart_id):

    session["shopify_cart_id"] = cart_id


def clear_shopify_cart():

    session.pop(
        "shopify_cart_id",
        None
    )


def get_shopify_cart():

    cart_id = get_cart_id()

    if not cart_id:

        return None

    data = shopify_request(
        CART_QUERY,
        {
            "id": cart_id
        }
    )

    return data.get("cart")


def get_cart_lines(cart):

    if not cart:

        return []

    return [
        edge["node"]
        for edge in cart.get(
            "lines",
            {}
        ).get(
            "edges",
            []
        )
    ]


def check_user_errors(payload):

    errors = payload.get(
        "userErrors",
        []
    )

    if errors:

        message = " | ".join(
            error.get(
                "message",
                "Shopify cart error"
            )
            for error in errors
        )

        raise RuntimeError(message)


def add_shopify_variant(
    variant_id,
    quantity
):

    quantity = max(
        1,
        min(int(quantity), 20)
    )

    cart_id = get_cart_id()

    line = {
        "merchandiseId": variant_id,
        "quantity": quantity
    }

    if cart_id:

        try:

            data = shopify_request(
                CART_ADD_MUTATION,
                {
                    "cartId": cart_id,
                    "lines": [line]
                }
            )

            payload = data.get(
                "cartLinesAdd",
                {}
            )

            check_user_errors(payload)

            cart = payload.get("cart")

            if cart:

                save_cart_id(
                    cart["id"]
                )

                return cart

        except Exception:

            clear_shopify_cart()

    data = shopify_request(
        CART_CREATE_MUTATION,
        {
            "input": {
                "lines": [line]
            }
        }
    )

    payload = data.get(
        "cartCreate",
        {}
    )

    check_user_errors(payload)

    cart = payload.get("cart")

    if not cart:

        raise RuntimeError(
            "Shopify did not return a cart."
        )

    save_cart_id(
        cart["id"]
    )

    return cart


# ==================================================
# CART DISPLAY CONVERSION
# ==================================================

def build_cart_products(cart):

    cart_products = []

    if not cart:

        return cart_products

    for line in get_cart_lines(cart):

        merchandise = line.get(
            "merchandise",
            {}
        )

        product = merchandise.get(
            "product",
            {}
        )

        image = merchandise.get(
            "image"
        ) or product.get(
            "featuredImage"
        ) or {}

        selected_options = merchandise.get(
            "selectedOptions",
            []
        )

        size = ""

        for option in selected_options:

            if option.get("name", "").lower() in (
                "size",
                "sizes"
            ):

                size = option.get(
                    "value",
                    ""
                )

        price = float(
            merchandise.get(
                "price",
                {}
            ).get(
                "amount",
                0
            )
        )

        quantity = int(
            line.get("quantity", 1)
        )

        cart_products.append({

            "id": numeric_shopify_id(
                product.get("id")
            ),

            "product_id": numeric_shopify_id(
                product.get("id")
            ),

            "shopify_id": product.get("id"),

            "variant_id": merchandise.get("id"),

            "line_id": line.get("id"),

            "name": product.get(
                "title",
                ""
            ),

            "title": product.get(
                "title",
                ""
            ),

            "image": image.get(
                "url",
                ""
            ),

            "price": price,

           "currency": merchandise.get(
    "price",
    {}
).get(
    "currencyCode",
    "EGP"
),

"currencyCode": merchandise.get(
    "price",
    {}
).get(
    "currencyCode",
    "EGP"
),

            "size": size,

            "quantity": quantity,

            "subtotal": price * quantity

        })

    return cart_products


# ==================================================
# GLOBAL CART COUNT
# ==================================================

@app.context_processor
def cart_count():

    try:

        cart = get_shopify_cart()

        count = int(
            cart.get(
                "totalQuantity",
                0
            )
        ) if cart else 0

    except Exception:

        count = 0

    return {
        "cart_count": count
    }


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    try:

        products = get_all_products()

    except Exception as error:

        print(
            "SHOPIFY HOME ERROR:",
            str(error)
        )

        products = []

        flash(
            "Unable to load products. Please try again.",
            "error"
        )

    return render_template(
        "index.html",
        products=products
    )


# ==================================================
# PRODUCTS
# ==================================================

@app.route("/products")
def products_page():

    try:

        products = get_all_products()

    except Exception as error:

        print(
            "SHOPIFY PRODUCTS ERROR:",
            str(error)
        )

        products = []

        flash(
            "Unable to load products.",
            "error"
        )

    return render_template(
        "products.html",
        products=products
    )


# ==================================================
# PRODUCT PAGE
# ==================================================

@app.route("/product/<int:product_id>")
def product_page(product_id):

    try:

        product = get_product(
            product_id
        )

        if not product:

            return "Product not found", 404

        all_products = get_all_products()

        related_products = [
            item
            for item in all_products
            if item["id"] != product_id
        ][:4]

        return render_template(
            "product.html",
            product=product,
            related_products=related_products
        )

    except Exception as error:

        print(
            "SHOPIFY PRODUCT PAGE ERROR:",
            str(error)
        )

        return (
            "Unable to load this product.",
            500
        )


# ==================================================
# ADD TO CART
# ==================================================

@app.route(
    "/add-to-cart/<int:product_id>",
    methods=["GET", "POST"]
)
def add_to_cart(product_id):

    try:

        product = get_product(
            product_id
        )

        if not product:

            return "Product not found", 404

        variant_id = (
            request.values.get("variant_id")
            or ""
        ).strip()

        size = (
            request.values.get("size")
            or ""
        ).strip()

        quantity = request.values.get(
            "quantity",
            1,
            type=int
        )

        quantity = max(
            1,
            min(quantity or 1, 20)
        )

        selected_variant = None

        if variant_id:

            for variant in product["variants"]:

                if variant["id"] == variant_id:

                    selected_variant = variant

                    break

        elif size:

            for variant in product["variants"]:

                if variant["size"].lower() == size.lower():

                    selected_variant = variant

                    break

        if not selected_variant:

            flash(
                "Please select an available size.",
                "error"
            )

            return redirect(
                url_for(
                    "product_page",
                    product_id=product_id
                )
            )

        if not selected_variant["available"]:

            flash(
                "This size is currently unavailable.",
                "error"
            )

            return redirect(
                url_for(
                    "product_page",
                    product_id=product_id
                )
            )

        add_shopify_variant(
            selected_variant["id"],
            quantity
        )

        return redirect(
            url_for("cart")
        )

    except Exception as error:

        print(
            "SHOPIFY ADD TO CART ERROR:",
            str(error)
        )

        flash(
            "Unable to add this item. Please try again.",
            "error"
        )

        return redirect(
            url_for(
                "product_page",
                product_id=product_id
            )
        )


# ==================================================
# UPDATE CART QUANTITY
# ==================================================

def update_cart_line(
    line_id,
    new_quantity
):

    cart_id = get_cart_id()

    if not cart_id:

        return

    if new_quantity <= 0:

        data = shopify_request(
            CART_REMOVE_MUTATION,
            {
                "cartId": cart_id,
                "lineIds": [line_id]
            }
        )

        payload = data.get(
            "cartLinesRemove",
            {}
        )

    else:

        data = shopify_request(
            CART_UPDATE_MUTATION,
            {
                "cartId": cart_id,
                "lines": [{
                    "id": line_id,
                    "quantity": min(
                        int(new_quantity),
                        20
                    )
                }]
            }
        )

        payload = data.get(
            "cartLinesUpdate",
            {}
        )

    check_user_errors(payload)

    if not payload.get("cart"):

        clear_shopify_cart()


# ==================================================
# INCREASE
# ==================================================

@app.route("/increase/<int:product_id>")
def increase(product_id):

    size = request.args.get(
        "size",
        ""
    )

    line_id = request.args.get(
        "line_id",
        ""
    )

    try:

        cart = get_shopify_cart()

        for line in get_cart_lines(cart):

            merchandise = line.get(
                "merchandise",
                {}
            )

            product = merchandise.get(
                "product",
                {}
            )

            current_product_id = numeric_shopify_id(
                product.get("id")
            )

            selected_size = ""

            for option in merchandise.get(
                "selectedOptions",
                []
            ):

                if option.get("name", "").lower() in (
                    "size",
                    "sizes"
                ):

                    selected_size = option.get(
                        "value",
                        ""
                    )

            if line_id:

                matches = line["id"] == line_id

            else:

                matches = (
                    current_product_id == product_id
                    and selected_size == size
                )

            if matches:

                update_cart_line(
                    line["id"],
                    int(line["quantity"]) + 1
                )

                break

    except Exception as error:

        print(
            "CART INCREASE ERROR:",
            str(error)
        )

        flash(
            "Unable to update cart.",
            "error"
        )

    return redirect(
        url_for("cart")
    )


# ==================================================
# DECREASE
# ==================================================

@app.route("/decrease/<int:product_id>")
def decrease(product_id):

    size = request.args.get(
        "size",
        ""
    )

    line_id = request.args.get(
        "line_id",
        ""
    )

    try:

        cart = get_shopify_cart()

        for line in get_cart_lines(cart):

            merchandise = line.get(
                "merchandise",
                {}
            )

            product = merchandise.get(
                "product",
                {}
            )

            current_product_id = numeric_shopify_id(
                product.get("id")
            )

            selected_size = ""

            for option in merchandise.get(
                "selectedOptions",
                []
            ):

                if option.get("name", "").lower() in (
                    "size",
                    "sizes"
                ):

                    selected_size = option.get(
                        "value",
                        ""
                    )

            if line_id:

                matches = line["id"] == line_id

            else:

                matches = (
                    current_product_id == product_id
                    and selected_size == size
                )

            if matches:

                update_cart_line(
                    line["id"],
                    int(line["quantity"]) - 1
                )

                break

    except Exception as error:

        print(
            "CART DECREASE ERROR:",
            str(error)
        )

        flash(
            "Unable to update cart.",
            "error"
        )

    return redirect(
        url_for("cart")
    )


# ==================================================
# UPDATE CART
# ==================================================

@app.route("/update-cart", methods=["POST"])
def update_cart():

    line_id = request.form.get(
        "line_id",
        ""
    ).strip()

    quantity = request.form.get(
        "quantity",
        type=int
    )

    if not line_id or quantity is None:
        flash("Invalid cart update.", "error")
        return redirect(url_for("cart"))

    try:

        cart = get_shopify_cart()

        if not cart:
            return redirect(url_for("cart"))

        # Verify that this line belongs to the current cart
        valid_line = any(
            line.get("id") == line_id
            for line in get_cart_lines(cart)
        )

        if not valid_line:
            flash("Cart item not found.", "error")
            return redirect(url_for("cart"))

        quantity = max(1, min(quantity, 20))

        update_cart_line(
            line_id,
            quantity
        )

        flash("Cart updated.", "success")

    except Exception as error:

        print("CART UPDATE ERROR:", str(error))

        flash(
            "Unable to update your cart.",
            "error"
        )

    return redirect(url_for("cart"))


# ==================================================
# REMOVE FROM CART
# ==================================================

@app.route("/remove-from-cart", methods=["POST"])
def remove_from_cart():

    line_id = request.form.get(
        "line_id",
        ""
    ).strip()

    if not line_id:
        flash("Invalid cart item.", "error")
        return redirect(url_for("cart"))

    try:

        cart = get_shopify_cart()

        if not cart:
            return redirect(url_for("cart"))

        valid_line = any(
            line.get("id") == line_id
            for line in get_cart_lines(cart)
        )

        if not valid_line:
            flash("Cart item not found.", "error")
            return redirect(url_for("cart"))

        update_cart_line(
            line_id,
            0
        )

        cart = get_shopify_cart()

        if not cart or cart.get("totalQuantity", 0) == 0:
            clear_shopify_cart()

        flash("Item removed from your cart.", "success")

    except Exception as error:

        print("CART REMOVE ERROR:", str(error))

        flash(
            "Unable to remove this item.",
            "error"
        )

    return redirect(url_for("cart"))
# ==================================================
# CART PAGE
# ==================================================

@app.route("/cart")
def cart():

    try:

        shopify_cart = get_shopify_cart()

        cart_products = build_cart_products(
            shopify_cart
        )

        total = 0
        currency_code = "EGP"

        if shopify_cart:

            total_amount = shopify_cart.get(
                "cost",
                {}
            ).get(
                "totalAmount",
                {}
            )

            total = float(
                total_amount.get(
                    "amount",
                    0
                )
            )

            currency_code = total_amount.get(
                "currencyCode",
                "EGP"
            )

        return render_template(
            "cart.html",
            cart_products=cart_products,
            total=total,
            currency_code=currency_code,
            shopify_cart=shopify_cart
        )

    except Exception as error:

        print(
            "SHOPIFY CART ERROR:",
            str(error)
        )

        flash(
            "Unable to load your shopping bag.",
            "error"
        )

        return render_template(
            "cart.html",
            cart_products=[],
            total=0,
            currency_code="EGP",
            shopify_cart=None
        )
# ==================================================
# CHECKOUT
# ==================================================

@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    try:

        cart = get_shopify_cart()

        if not cart or not cart.get("totalQuantity"):

            flash(
                "Your shopping bag is empty.",
                "error"
            )

            return redirect(
                url_for("cart")
            )

        checkout_url = cart.get(
            "checkoutUrl"
        )

        if not checkout_url:

            raise RuntimeError(
                "Shopify checkout URL is missing."
            )

        return redirect(
            checkout_url
        )

    except Exception as error:

        print(
            "SHOPIFY CHECKOUT ERROR:",
            str(error)
        )

        flash(
            "Unable to open checkout. Please try again.",
            "error"
        )

        return redirect(
            url_for("cart")
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
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not name or not email or not message:

            flash(
                "Please complete all fields.",
                "error"
            )

            return redirect(
                url_for("contact")
            )

        print(
            "NEW ROXX CONTACT MESSAGE:",
            name,
            email,
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
# ADMIN CONFIGURATION
# ==================================================

ADMIN_USERNAME = os.environ.get(
    "ROXX_ADMIN_USERNAME",
    ""
).strip()

ADMIN_PASSWORD = os.environ.get(
    "ROXX_ADMIN_PASSWORD",
    ""
)


def admin_logged_in():

    return session.get(
        "admin_logged_in",
        False
    )


# ==================================================
# ADMIN LOGIN
# ==================================================

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

        if not ADMIN_USERNAME or not ADMIN_PASSWORD:

            flash(
                "Admin login is not configured.",
                "error"
            )

            return redirect(
                url_for("admin_login")
            )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session.clear()

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

    shopify_admin_url = (
        "https://admin.shopify.com/store/"
        + SHOPIFY_STORE_DOMAIN.replace(
            ".myshopify.com",
            ""
        )
    )

    return render_template(
        "admin_dashboard.html",

        products=[],

        orders=[],

        shopify_admin_url=shopify_admin_url,

        shopify_products_url=(
            shopify_admin_url + "/products"
        ),

        shopify_orders_url=(
            shopify_admin_url + "/orders"
        ),

        shopify_analytics_url=(
            shopify_admin_url + "/analytics"
        )
    )


# ==================================================
# OLD ADMIN PRODUCT ROUTES
# Redirect to Shopify Admin
# ==================================================

@app.route(
    "/admin/add-product",
    methods=["POST"]
)
def admin_add_product():

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    return redirect(
        "https://admin.shopify.com/store/"
        + SHOPIFY_STORE_DOMAIN.replace(
            ".myshopify.com",
            ""
        )
        + "/products"
    )


@app.route(
    "/admin/delete-product/<int:product_id>",
    methods=["POST"]
)
def admin_delete_product(product_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    return redirect(
        "https://admin.shopify.com/store/"
        + SHOPIFY_STORE_DOMAIN.replace(
            ".myshopify.com",
            ""
        )
        + "/products"
    )


@app.route(
    "/admin/update-order/<int:order_id>",
    methods=["POST"]
)
def admin_update_order(order_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    return redirect(
        "https://admin.shopify.com/store/"
        + SHOPIFY_STORE_DOMAIN.replace(
            ".myshopify.com",
            ""
        )
        + "/orders"
    )


# ==================================================
# ADMIN LOGOUT
# ==================================================
@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(
        url_for("admin_login")
    )


# ==================================================
# SHOPIFY CONNECTION TEST
# ==================================================

@app.route("/shopify-test")
def shopify_test():

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    try:

        products = get_all_products()

        return {

            "connection": "successful",

            "products_found": len(products),

            "products": [
                product["name"]
                for product in products
            ]

        }

    except Exception as error:

        return {

            "connection": "failed",

            "error": str(error)

        }, 500


# ==================================================
# LOCAL RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )