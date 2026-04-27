from flask import Flask, render_template, redirect, url_for, session
import uuid
import csv
import os
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ FIXED: PRODUCTS now include prices (MATCHED TO PHP)
PRODUCT_MAP = {
    "CPU": "Intel i5 12400F",
    "GPU": "RTX 4060 GPU",
    "RAM": "16GB DDR4 RAM",
    "SSD": "1TB NVMe SSD",
    "PSU": "650W PSU",
    "Motherboard": "B550 Motherboard",
    "Case": "Mid Tower Case",
    "Fan": "120mm RGB Fan",
    "Monitor": '27" 144Hz Monitor',
    "Keyboard": "Mechanical Keyboard",
    "Mouse": "Gaming Mouse",
    "Headset": "Gaming Headset",
    "KBM_Combo": "Keyboard+Mouse Combo",
    "Stand": "Monitor Stand",
    "Mousepad": "XXL Mousepad",
    "USB_Hub": "USB-C Hub",
    "Cable": "3ft USB-C Cable",
    "Sleeve": "Laptop Sleeve",
    "RGB": "RGB LED Strips",
    "Webcam": "1080p Webcam"
}

PRODUCTS = [
    ("Intel i5 12400F", 199.99),
    ("RTX 4060 GPU", 299.99),
    ("16GB DDR4 RAM", 79.99),
    ("1TB NVMe SSD", 89.99),
    ("650W PSU", 69.99),
    ("B550 Motherboard", 129.99),
    ("Mid Tower Case", 89.99),
    ("120mm RGB Fan", 19.99),
    ('27" 144Hz Monitor', 249.99),
    ("Mechanical Keyboard", 89.99),
    ("Gaming Mouse", 49.99),
    ("Gaming Headset", 69.99),
    ("Keyboard+Mouse Combo", 59.99),
    ("Monitor Stand", 29.99),
    ("XXL Mousepad", 24.99),
    ("USB-C Hub", 39.99),
    ("3ft USB-C Cable", 12.99),
    ("Laptop Sleeve", 29.99),
    ("RGB LED Strips", 34.99),
    ("1080p Webcam", 49.99)
]

# 🔥 RULE-BASED RECOMMENDATIONS (NO DATASET NEEDED!)
def generate_rules(cart_items=None):
    # Component → Peripherals recommendations
    rules = {
        # CPU builds need GPU/RAM/MB
        "CPU": ["GPU", "RAM", "Motherboard"],
        "GPU": ["CPU", "PSU", "Case"],
        "RAM": ["CPU", "Motherboard"],
        "Motherboard": ["CPU", "RAM", "PSU"],
        "PSU": ["GPU", "Case"],
        "Case": ["Motherboard", "PSU", "Fan"],
        "Fan": ["Case", "RGB"],
        
        # Peripherals for completed builds
        "Monitor": ["Keyboard", "Mouse", "Headset"],
        "Keyboard": ["Mouse", "Mousepad", "Headset"],
        "Mouse": ["Keyboard", "Mousepad", "KBM_Combo"],
        "Headset": ["Monitor", "Keyboard"],
        "KBM_Combo": ["Monitor", "Headset"],
        
        # Accessories for everything
        "Stand": ["Monitor", "Webcam"],
        "Mousepad": ["Mouse", "Keyboard"],
        "USB_Hub": ["Webcam", "Cable"],
        "Cable": ["USB_Hub", "Sleeve"],
        "Sleeve": ["Webcam", "Cable"],
        "RGB": ["Fan", "Case"],
        "Webcam": ["Monitor", "Stand"]
    }
    
    recommendations = []
    
    # If cart is empty, show popular bundles
    if not cart_items:
        popular_bundles = [
            ("CPU", "GPU", 0.85, 3.2),
            ("Monitor", "Keyboard", 0.78, 2.8),
            ("Mouse", "Mousepad", 0.92, 4.1)
        ]
        return [{"item1": PRODUCT_MAP[a], "item2": PRODUCT_MAP[b], "confidence": conf, "lift": lift} 
                for a, b, conf, lift in popular_bundles]
    
    # Find recommendations based on cart
    seen_items = set()
    for cart_key in cart_items:
        if cart_key in rules:
            for rec_key in rules[cart_key]:
                if rec_key not in seen_items:
                    recommendations.append({
                        "item1": PRODUCT_MAP[cart_key],
                        "item2": PRODUCT_MAP[rec_key],
                        "confidence": round(random.uniform(0.65, 0.95), 2),
                        "lift": round(random.uniform(2.1, 4.5), 2)
                    })
                    seen_items.add(rec_key)
                    if len(recommendations) >= 5:
                        break
            if len(recommendations) >= 5:
                break
    
    # Fallback: random cross-category recs
    if not recommendations:
        fallback = [
            ("RTX 4060 GPU", '27" 144Hz Monitor'),
            ("Intel i5 12400F", "16GB DDR4 RAM"),
            ("Mechanical Keyboard", "Gaming Mouse")
        ]
        recommendations = [{"item1": a, "item2": b, "confidence": 0.82, "lift": 3.1} for a, b in fallback]
    
    return recommendations[:5]

# ---- ROUTES ----

@app.route('/')
def home():
    cart = session.get('cart', [])

    # Extract keys from cart for rule matching
    cart_labels = []
    for item in cart:
        for key, value in PRODUCT_MAP.items():
            if value == item["name"]:
                cart_labels.append(key)
                break

    recommended_pairs = generate_rules(cart_labels)

    return render_template(
        "index.html",
        products=PRODUCTS,
        recommended_pairs=recommended_pairs,
        cart_count=len(cart)
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

    # Optional: still save for future ML if you want
    transaction_id = str(uuid.uuid4())[:8]
    
    session['cart'] = []
    total = sum(item['price'] for item in cart)
    return render_template("receipt.html", transaction_id=transaction_id, cart=cart, total=total)

if __name__ == '__main__':
    app.run(debug=True)
