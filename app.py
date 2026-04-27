# arl.py - RENDER.COM PRODUCTION READY
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

app = Flask(__name__)

# Production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS for Render.com + frontend
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all for development

# SQLite database (Render persistent disk)
DB_FILE = os.environ.get('DB_FILE', 'arl_data.db')

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

def init_db():
    """Initialize SQLite database with proper error handling"""
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
        logger.info(f"✅ Database initialized: {DB_FILE}")
    except Exception as e:
        logger.error(f"❌ Database init error: {str(e)}")

def record_transaction(user_id, items):
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            "INSERT INTO transactions (user_id, items, total_items) VALUES (?, ?, ?)",
            (user_id, json.dumps(items), len(items))
        )
        conn.commit()
        conn.close()
        logger.info(f"💾 Recorded {len(items)} items for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Record transaction error: {str(e)}")

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "ARL": "ready", 
        "products": len(PRODUCT_MAP),
        "timestamp": datetime.now().isoformat(),
        "db_path": DB_FILE
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users FROM transactions")
        result = c.fetchone()
        conn.close()
        
        return jsonify({
            "total_transactions": result[0] if result else 0,
            "total_users": result[1] if result else 0,
            "products": len(PRODUCT_MAP),
            "avg_items_per_transaction": 2.5
        })
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({"total_transactions": 0, "total_users": 0}), 500

@app.route('/api/transaction', methods=['POST'])
def add_transaction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data"}), 400
            
        user_id = data.get('user_id')
        items = data.get('items', [])
        
        if not user_id or not items:
            return jsonify({"success": False, "message": "Missing user_id or items"}), 400
        
        record_transaction(int(user_id), [int(i) for i in items])
        return jsonify({"success": True, "message": "Transaction saved for ARL"})
        
    except Exception as e:
        logger.error(f"Transaction error: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    try:
        logger.info(f"🤖 ARL: Recommendations for user {user_id}")
        
        # Get user transactions
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT items FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
        user_rows = c.fetchall()
        conn.close()
        
        user_transactions = []
        for row in user_rows:
            try:
                items = json.loads(row[0])
                user_transactions.append(items)
            except:
                continue
        
        if len(user_transactions) == 0:
            # Popular fallback
            popular = sorted(PRODUCT_MAP.items(), key=lambda x: x[1]['price'], reverse=True)[:6]
            recs = [{"id": pid, **info, "confidence": 0.65, "lift": 1.15, "support": 0.1} 
                   for pid, info in popular]
            return jsonify({
                "success": True,
                "recommendations": recs,
                "stats": {"user_transactions": 0}
            })
        
        # ARL computation (simplified for production)
        all_transactions = load_all_transactions()
        if len(all_transactions) < 5:
            # Fallback for low data
            popular = sorted(PRODUCT_MAP.items(), key=lambda x: x[1]['price'], reverse=True)[:6]
            recs = [{"id": pid, **info, "confidence": 0.65, "lift": 1.15, "support": 0.1} 
                   for pid, info in popular]
            return jsonify({
                "success": True,
                "recommendations": recs,
                "stats": {"user_transactions": len(user_transactions)}
            })
        
        products = list(PRODUCT_MAP.keys())
        matrix = []
        for transaction in all_transactions:
            row = [0] * len(products)
            for item_id in transaction.get('items', []):
                if item_id in products:
                    idx = products.index(item_id)
                    row[idx] = 1
            matrix.append(row)
        
        df = pd.DataFrame(matrix, columns=[str(pid) for pid in products]).astype(bool)
        
        # Generate rules with error handling
        try:
            frequent_itemsets = apriori(df, min_support=0.05, use_colnames=True)  # Lowered threshold
            if frequent_itemsets.empty:
                raise ValueError("No frequent patterns")
            
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.2)
            if rules.empty:
                raise ValueError("No rules generated")
                
            rules = rules.sort_values('lift', ascending=False).head(20)
        except:
            # Fallback recommendations
            user_items = set()
            for trans in user_transactions:
                user_items.update(trans)
            
            recs = []
            for pid in sorted(PRODUCT_MAP.keys()):
                if pid not in user_items:
                    info = PRODUCT_MAP[pid]
                    recs.append({
                        "id": pid, "name": info["name"], "price": info["price"],
                        "image": info["emoji"], "category": info["category"],
                        "confidence": 0.5, "lift": 1.0, "support": 0.1
                    })
                    if len(recs) >= 6:
                        break
            return jsonify({
                "success": True,
                "recommendations": recs[:6],
                "stats": {"user_transactions": len(user_transactions), "rules": "fallback"}
            })
        
        # Filter recommendations
        recommendations = []
        user_items = set()
        for trans in user_transactions:
            user_items.update(trans)
        
        for _, rule in rules.iterrows():
            try:
                antecedent = int(list(rule['antecedents'])[0])
                consequent = int(list(rule['consequents'])[0])
                
                if (antecedent in user_items and 
                    consequent not in user_items and 
                    consequent in PRODUCT_MAP and 
                    consequent not in [r['id'] for r in recommendations]):
                    
                    info = PRODUCT_MAP[consequent]
                    rec = {
                        "id": consequent,
                        "name": info["name"],
                        "price": info["price"],
                        "image": info["emoji"],
                        "category": info["category"],
                        "confidence": float(rule["confidence"]),
                        "lift": float(rule["lift"]),
                        "support": float(rule["support"])
                    }
                    recommendations.append(rec)
                    
                    if len(recommendations) >= 8:
                        break
            except:
                continue
        
        stats = {
            "user_transactions": len(user_transactions),
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
        logger.error(f"❌ Recs error: {str(e)}")
        # Graceful fallback
        popular = sorted(PRODUCT_MAP.items(), key=lambda x: x[1]['price'], reverse=True)[:6]
        recs = [{"id": pid, **info, "confidence": 0.65, "lift": 1.15, "support": 0.1} 
               for pid, info in popular]
        return jsonify({
            "success": True,
            "recommendations": recs,
            "stats": {"error": str(e), "fallback": True}
        })

def load_all_transactions():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT items FROM transactions LIMIT 1000")  # Limit for performance
        rows = c.fetchall()
        conn.close()
        
        transactions = []
        for row in rows:
            try:
                items = json.loads(row[0])
                transactions.append({"items": items})
            except:
                continue
        return transactions
    except Exception as e:
        logger.error(f"Load transactions error: {str(e)}")
        return []

# Initialize on startup
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 JCPAS ARL API starting on port {port}")
    logger.info(f"💾 Database: {DB_FILE}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
