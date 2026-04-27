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

# 🆕 IMPROVED: Build stage detection and smart recommendations
def get_build_stage(cart_labels):
    """Detect what stage of PC build the user is at"""
    core_components = set(['CPU', 'GPU', 'Motherboard', 'RAM', 'PSU', 'Case'])
    peripherals = set(['Monitor', 'Keyboard', 'Mouse', 'Headset', 'KBM_Combo'])
    accessories = set(['Stand', 'Mousepad', 'USB_Hub', 'Cable', 'Sleeve', 'RGB', 'Webcam', 'SSD', 'Fan'])
    
    core_count = len(cart_labels & core_components)
    peri_count = len(cart_labels & peripherals)
    acc_count = len(cart_labels & accessories)
    
    if core_count >= 4:
        return "complete_core", "peripherals"
    elif core_count >= 2:
        return "building_core", "core_complements"
    elif peri_count >= 2:
        return "peripherals", "accessories"
    else:
        return "starting", "popular_bundles"

# 🔥 ENHANCED RULE-BASED RECOMMENDATIONS
def generate_rules(cart_items=None):
    if not cart_items:
        # Popular starter bundles for empty carts
        popular_bundles = [
            ("CPU", "Motherboard", 0.92, 4.2),
            ("Monitor", "Keyboard", 0.88, 3.8),
            ("GPU", "PSU", 0.85, 3.5)
        ]
        return [{"item1": PRODUCT_MAP[a], "item2": PRODUCT_MAP[b], "confidence": conf, "lift": lift} 
                for a, b, conf, lift in popular_bundles]

    # Get cart names for filtering
    cart_names = [item["name"] for item in cart_items]
    
    # 🆕 IMPROVED RULES: More logical PC build sequences
    rules = {
        # Core build progression
        "CPU": ["Motherboard", "RAM", "SSD"],  # Start with MB+RAM+Storage
        "Motherboard": ["CPU", "RAM", "PSU"],  # Complete core
        "RAM": ["CPU", "Motherboard", "SSD"],
        "SSD": ["CPU", "RAM", "Motherboard"],
        
        # Power & Case after core
        "PSU": ["GPU", "Case", "Motherboard"],
        "GPU": ["PSU", "Case", "CPU"],
        "Case": ["PSU", "Motherboard", "Fan", "RGB"],
        "Fan": ["Case", "RGB"],
        
        # Peripherals after core build
        "Monitor": ["Keyboard", "Mouse", "Headset", "Stand"],
        "Keyboard": ["Mouse", "Mousepad", "Monitor", "KBM_Combo"],
        "Mouse": ["Keyboard", "Mousepad", "Monitor"],
        "Headset": ["Monitor", "Keyboard", "Mouse"],
        "KBM_Combo": ["Monitor", "Headset", "Mousepad"],
        
        # Accessories (always relevant)
        "Stand": ["Webcam", "Monitor"],
        "Mousepad": ["Mouse", "Keyboard"],
        "USB_Hub": ["Webcam", "Cable"],
        "Cable": ["USB_Hub", "Webcam"],
        "RGB": ["Fan", "Case"],
        "Webcam": ["Monitor", "Stand", "USB_Hub"],
        "Sleeve": ["Cable", "USB_Hub"]  # Mobile setup accessories
    }
    
    recommendations = []
    seen_items = set(cart_names)  # 🚫 AVOID ALREADY IN CART
    
    # Stage-aware recommendations
    stage, focus = get_build_stage(cart_items)
    
    # Prioritize based on build stage
    priority_items = []
    for cart_key in cart_items:
        key = next((k for k, v in PRODUCT_MAP.items() if v == cart_key["name"]), None)
        if key and key in rules:
            # Filter out items already in cart
            available_recs = [r for r in rules[key] if PRODUCT_MAP[r] not in seen_items]
            priority_items.extend(available_recs[:2])  # Top 2 per cart item
    
    # Generate recommendations from priority items
    for rec_key in priority_items:
        if PRODUCT_MAP[rec_key] not in seen_items and len(recommendations) < 6:
            # Find a cart item to pair with
            for cart_key in cart_items:
                cart_key_name = cart_key["name"]
                if cart_key_name not in seen_items:  # Shouldn't happen
                    recommendations.append({
                        "item1": cart_key_name,
                        "item2": PRODUCT_MAP[rec_key],
                        "confidence": round(random.uniform(0.75, 0.98), 2),
                        "lift": round(random.uniform(2.8, 5.2), 2)
                    })
                    seen_items.add(PRODUCT_MAP[rec_key])
                    break
    
    # Smart fallback based on stage
    if len(recommendations) < 3:
        fallbacks = {
            "complete_core": [("Monitor", "Keyboard"), ("Mouse", "Headset")],
            "building_core": [("PSU", "Case"), ("SSD", "RAM")],
            "peripherals": [("Mousepad", "Stand"), ("Webcam", "USB_Hub")],
            "starting": [("CPU", "Motherboard"), ("Monitor", "Keyboard")]
        }
        stage_fallbacks = fallbacks.get(stage, fallbacks["starting"])
        
        for item1_key, item2_key in stage_fallbacks:
            item1 = PRODUCT_MAP[item1_key]
            item2 = PRODUCT_MAP[item2_key]
            if item1 not in seen_items and item2 not in seen_items:
                recommendations.append({
                    "item1": item1,
                    "item2": item2,
                    "confidence": 0.85,
                    "lift": 3.9
                })
    
    return recommendations[:6]

# ---- ROUTES ----

@app.route('/')
def home():
    cart = session.get('cart', [])
    
    # Pass actual cart items (with names) to generate_rules
    recommended_pairs = generate_rules(cart)

    return render_template(
        "index.html",
        products=PRODUCTS,
        recommended_pairs=recommended_pairs,
        cart_count=len(cart),
        cart_items=cart  # Pass cart for template awareness
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
    
    # 🆕 Cart-specific recommendations
    recommended_pairs = generate_rules(cart)
    
    return render_template("cart.html", cart=cart, total=total, recommended_pairs=recommended_pairs)

@app.route('/checkout')
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('home'))

    transaction_id = str(uuid.uuid4())[:8]
    session['cart'] = []
    total = sum(item['price'] for item in cart)
    return render_template("receipt.html", transaction_id=transaction_id, cart=cart, total=total)

if __name__ == '__main__':
    app.run(debug=True)
