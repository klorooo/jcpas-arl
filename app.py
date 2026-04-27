from flask import Flask, render_template, redirect, url_for, session
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd
import uuid
import csv
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ FIXED: PRODUCTS now include prices
PRODUCT_MAP = {
    "CPU": "Intel i5 12400F CPU",
    "GPU": "NVIDIA RTX 4060 GPU",
    "RAM": "Corsair Vengeance 16GB RAM",
    "SSD": "Samsung 980 1TB SSD",
    "Power_Supply": "Cooler Master PSU 650W",
    "Motherboard": "ASUS ROG Motherboard",
    "PC_Case": "NZXT H510 Case",
    "Cooling_Fan": "Cooler Master Fan",
    "Monitor": "LG UltraGear Monitor",
    "Monitor_Stand": "Adjustable Monitor Stand",
    "Keyboard": "Logitech Mechanical Keyboard",
    "Mouse": "Razer Gaming Mouse",
    "Headset": "HyperX Cloud II Headset",
    "Mousepad": "SteelSeries Mousepad",
    "USB_Hub": "Anker USB Hub",
    "USB_Cable": "USB-C Cable",
    "Laptop_Bag": "Waterproof Laptop Bag",
    "Keyboard_and_Mouse_Combo": "Logitech Combo Set",
    "RGB_Lighting": "RGB LED Strip Kit",
    "Webcam": "Logitech HD Webcam"
}

PRODUCTS = [(value, 2000 + i*500) for i, (key, value) in enumerate(PRODUCT_MAP.items())]

# Load dataset safely
if os.path.exists("processed_transactions.csv"):
    df = pd.read_csv("processed_transactions.csv")
else:
    df = pd.DataFrame(columns=["transaction_id"] + [p[0] for p in PRODUCTS])

# ---- ARL FUNCTION ----
def generate_rules(cart_items=None):
    if len(df) < 5:
        return []

    temp_df = df.drop(columns=["transaction_id"]).astype(bool)

    frequent_itemsets = apriori(temp_df, min_support=0.1, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)

    rules = rules[
        rules['antecedents'].apply(lambda x: len(x) == 1) &
        rules['consequents'].apply(lambda x: len(x) == 1)
    ]

    pairs = []

    for _, row in rules.iterrows():
        a_raw = list(row['antecedents'])[0]
        b_raw = list(row['consequents'])[0]

        # 🔥 FILTER based on cart
        if cart_items and a_raw not in cart_items:
            continue

        a = PRODUCT_MAP.get(a_raw, a_raw)
        b = PRODUCT_MAP.get(b_raw, b_raw)

        pairs.append({
            "item1": a,
            "item2": b,
            "confidence": round(row["confidence"], 2),
            "lift": round(row["lift"], 2)
        })

    return pairs

# ---- ROUTES ----

@app.route('/')
def home():
    cart = session.get('cart', [])

    # Extract raw names for ARL (reverse mapping)
    cart_labels = []
    for item in cart:
        for key, value in PRODUCT_MAP.items():
            if value == item["name"]:
                cart_labels.append(key)

    recommended_pairs = generate_rules(cart_labels)

    return render_template(
        "index.html",
        products=PRODUCTS,
        recommended_pairs=recommended_pairs
    )

@app.route('/add_to_cart/<name>/<int:price>')
def add_to_cart(name, price):
    cart = session.get('cart', [])
    cart.append({"name": name, "price": price})
    session['cart'] = cart
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route('/checkout')
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('home'))

    transaction_id = str(uuid.uuid4())[:8]

    filename = "processed_transactions.csv"
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["transaction_id"] + [p[0] for p in PRODUCTS])

        row = [transaction_id]
        for product, _ in PRODUCTS:
            row.append(1 if any(item["name"] == product for item in cart) else 0)

        writer.writerow(row)

    session['cart'] = []

    total = sum(item['price'] for item in cart)
    return render_template("receipt.html", transaction_id=transaction_id, cart=cart, total=total)

if __name__ == '__main__':
    app.run(debug=True)
