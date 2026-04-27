# arl.py - RENDER.COM PRODUCTION READY v2.0
"""
JCPAS Association Rule Learning (ARL) API
Built with Flask + Pandas + MLXtend + SQLite
Live at: https://jcpas-arl-3.onrender.com
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
import os
import json
import sqlite3
from datetime import datetime
import logging
from functools import lru_cache

# ========================================
# INITIALIZATION
# ========================================
app = Flask(__name__)

# Production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS for all origins (frontend compatibility)
CORS(app, resources={r"/*": {"origins": "*"}})

# Config
DB_FILE = os.environ.get('DB_FILE', 'arl_data.db')
PORT = int(os.environ.get('PORT', 10000))

# Product Catalog
PRODUCT_MAP = {
    1: {"name": "Mechanical Gaming Keyboard", "price": 129.99, "category": "Keyboards", "emoji": "⌨️"},
    2: {"name": "Wireless RGB Mouse", "price": 89.99, "category": "Mice", "emoji": "🖱️"},
    3: {"name": "Noise-Canceling Headset", "price": 199.99, "category": "Headsets", "emoji": "🎧"},
    4: {"name": "2TB NVMe SSD", "price": 249.99, "category": "Storage", "emoji": "💾"},
    5: {"name": "Intel i5 12400F CPU", "price": 250.00, "category": "CPU", "emoji": "🧠"},
    6: {"name": "NVIDIA RTX 4060 GPU", "price": 450.00, "category": "GPU", "emoji": "🎮"},
    7: {"name": "Corsair Vengeance 16GB RAM", "price": 89.99, "category": "RAM", "emoji": "💾"},
    8: {"name": "Samsung 980 1TB SSD", "price": 129.99, "category": "SSD", "emoji": "💿"},
    9: {"name": "Cooler Master PSU 650W", "price": 89.99, "category": "Power Supply", "emoji": "🔌"},
    10: {"name": "ASUS ROG Motherboard", "price": 299.99, "category": "Motherboard", "emoji": "⚙️"}
}

# ========================================
# DATABASE
# ========================================
def init_db():
    """Initialize SQLite with indexes"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      items TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      total_items INTEGER)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_user ON transactions(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_time ON transactions(timestamp)')
        conn.commit()
        conn.close()
        logger.info(f"✅ Database ready: {DB_FILE}")
    except Exception as e:
        logger.error(f"❌ DB init failed: {e}")

def record_transaction(user_id, items):
    """Record user transaction"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, items, total_items) VALUES (?, ?, ?)",
                 (user_id, json.dumps(items), len(items)))
        conn.commit()
        conn.close()
        logger.info(f"💾 Saved {len(items)} items for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Transaction save failed: {e}")

@lru_cache(maxsize=128)
def load_all_transactions():
    """Cached transaction loader for ARL"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT items FROM transactions LIMIT 1000")
        rows = c.fetchall()
        conn.close()
        
        transactions = []
        for row in rows:
            try:
                transactions.append(json.loads(row[0]))
            except:
                continue
        logger.info(f"📊 Loaded {len(transactions)} transactions")
        return transactions
    except Exception as e:
        logger.error(f"❌ Load transactions failed: {e}")
        return []

# ========================================
# API ROUTES
# ========================================
@app.route('/', methods=['GET'])
def home():
    """🏠 ROOT - Production landing page"""
    return jsonify({
        "🚀": "JCPAS ARL API v2.0 LIVE!",
        "status": "healthy",
        "endpoints": {
            "/": "Home",
            "/health": "Health check",
            "/stats": "Database stats",
            "/products": "Product catalog",
            "/transaction (POST)": "Record transaction",
            "/recommendations/<user_id>": "Get ARL recommendations"
        },
        "docs": "https://jcpas-arl-3.onrender.com/health",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """✅ Health check"""
    return jsonify({
        "status": "healthy",
        "ARL": "ready",
        "products": len(PRODUCT_MAP),
        "transactions": len(load_all_transactions()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/products', methods=['GET'])
def get_products():
    """📦 Product catalog"""
    return jsonify({
        "success": True,
        "products": list(PRODUCT_MAP.values()),
        "total": len(PRODUCT_MAP)
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """📈 System stats"""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users, AVG(total_items) as avg_items FROM transactions")
        result = c.fetchone()
        conn.close()
        
        return jsonify({
            "total_transactions": result[0] if result else 0,
            "total_users": result[1] if result else 0,
            "avg_items_per_transaction": round(float(result[2]) if result else 0, 2),
            "products": len(PRODUCT_MAP),
            "arl_transactions": len(load_all_transactions())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/transaction', methods=['POST'])
def add_transaction():
    """💾 Record transaction for ARL"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data"}), 400
        
        user_id = data.get('user_id')
        items = data.get('items', [])
        
        if not user_id or not items:
            return jsonify({"success": False, "error": "Missing user_id or items"}), 400
        
        record_transaction(int(user_id), [int(i) for i in items])
        return jsonify({
            "success": True,
            "message": f"Saved {len(items)} items for user {user_id}",
            "next": f"/recommendations/{user_id}"
        })
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    """🤖 ARL Recommendations Engine"""
    try:
        logger.info(f"🤖 ARL computing for user {user_id}")
        
        # Get user history
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT items FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
        user_rows = c.fetchall()
        conn.close()
        
        user_transactions = [json.loads(row[0]) for row in user_rows if row[0]]
        user_items = set(item for trans in user_transactions for item in trans)
        
        if not user_transactions:
            return _fallback_recommendations(user_items)
        
        # Build transaction matrix
        all_transactions = load_all_transactions()
        if len(all_transactions) < 5:
            return _fallback_recommendations(user_items)
        
        products = list(PRODUCT_MAP.keys())
        matrix = []
        for transaction in all_transactions:
            row = [0] * len(products)
            for item_id in transaction:
                if item_id in products:
                    row[products.index(item_id)] = 1
            matrix.append(row)
        
        df = pd.DataFrame(matrix, columns=[str(pid) for pid in products]).astype(bool)
        
        # Generate association rules
        frequent_itemsets = apriori(df, min_support=0.05, use_colnames=True)
        if frequent_itemsets.empty:
            return _fallback_recommendations(user_items)
        
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.2)
        if rules.empty:
            return _fallback_recommendations(user_items)
        
        rules = rules.sort_values('lift', ascending=False).head(20)
        
        # Filter relevant recommendations
        recommendations = []
        for _, rule in rules.iterrows():
            antecedent = int(list(rule['antecedents'])[0])
            consequent = int(list(rule['consequents'])[0])
            
            if (antecedent in user_items and 
                consequent not in user_items and 
                consequent in PRODUCT_MAP and 
                len(recommendations) < 8):
                
                info = PRODUCT_MAP[consequent]
                rec = {
                    "id": consequent,
                    "name": info["name"],
                    "price": info["price"],
                    "category": info["category"],
                    "emoji": info["emoji"],
                    "confidence": float(rule["confidence"]),
                    "lift": float(rule["lift"]),
                    "support": float(rule["support"])
                }
                recommendations.append(rec)
        
        stats = {
            "user_transactions": len(user_transactions),
            "user_items": len(user_items),
            "total_rules": len(rules),
            "avg_confidence": float(rules['confidence'].mean())
        }
        
        logger.info(f"✅ Generated {len(recommendations)} recs for user {user_id}")
        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Recommendations error: {e}")
        return _fallback_recommendations(set())

def _fallback_recommendations(user_items):
    """Fallback recommendations"""
    recs = []
    for pid in sorted(PRODUCT_MAP.keys()):
        if pid not in user_items:
            info = PRODUCT_MAP[pid]
            recs.append({
                "id": pid, "name": info["name"], "price": info["price"],
                "category": info["category"], "emoji": info["emoji"],
                "confidence": 0.65, "lift": 1.15, "support": 0.1,
                "fallback": True
            })
            if len(recs) >= 6:
                break
    
    return jsonify({
        "success": True,
        "recommendations": recs,
        "stats": {"fallback": True}
    })

# ========================================
# STARTUP
# ========================================
if __name__ == '__main__':
    init_db()
    logger.info("🚀 JCPAS ARL API v2.0 starting...")
    logger.info(f"📍 Database: {DB_FILE}")
    logger.info(f"🌐 Products: {len(PRODUCT_MAP)}")
    logger.info(f"🔌 Port: {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
