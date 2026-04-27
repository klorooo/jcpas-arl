from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
import os
import json
from datetime import datetime
import sys
import locale

# Fix Unicode encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

app = Flask(__name__)
CORS(app)

# Product mapping with IDs and prices
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

# File paths
TRANSACTIONS_FILE = "transactions.json"
STATS_FILE = "arl_stats.json"

class DataManager:
    """Handles data loading and saving"""
    
    @staticmethod
    def load_data(filename, default=None):
        if default is None:
            default = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load {filename}, using default")
                return default
        return default
    
    @staticmethod
    def save_data(filename, data):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving {filename}: {e}")

class TransactionProcessor:
    """Processes transactions for ARL analysis"""
    
    @staticmethod
    def get_user_transactions(user_id):
        transactions = DataManager.load_data(TRANSACTIONS_FILE)
        return [t for t in transactions if str(t.get('user_id')) == str(user_id)]
    
    @staticmethod
    def build_transaction_matrix(user_transactions, products):
        """Build boolean transaction matrix"""
        matrix = []
        for transaction in user_transactions:
            row = [False] * len(products)
            for item_id in transaction.get('items', []):
                if item_id in products:
                    idx = products.index(item_id)
                    row[idx] = True
            matrix.append(row)
        return pd.DataFrame(matrix, columns=[str(pid) for pid in products]).astype(bool)
    
    @staticmethod
    def generate_rules(df):
        """Generate association rules from transaction matrix"""
        try:
            # Find frequent itemsets
            frequent_itemsets = apriori(df, min_support=0.05, use_colnames=True)
            if frequent_itemsets.empty:
                return pd.DataFrame()
            
            # Generate rules
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.3)
            
            # Filter for single antecedent/consequent rules
            rules = rules[
                rules['antecedents'].apply(lambda x: len(x) == 1) &
                rules['consequents'].apply(lambda x: len(x) == 1)
            ].head(20)
            
            return rules if not rules.empty else pd.DataFrame()
        except Exception as e:
            print(f"Error generating rules: {e}")
            return pd.DataFrame()

def log_message(message):
    """Safe logging with emoji support"""
    print(f"[ARL] {message}", flush=True)

@app.route('/api/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    try:
        log_message(f"Generating recommendations for user {user_id}")
        user_transactions = TransactionProcessor.get_user_transactions(user_id)
        
        if len(user_transactions) < 1:
            # Fallback recommendations
            popular = sorted(PRODUCT_MAP.items(), key=lambda x: x[1]['price'], reverse=True)[:6]
            recs = [{"id": pid, **info, "confidence": 0.65, "lift": 1.15} 
                   for pid, info in popular]
            return jsonify({
                "success": True,
                "recommendations": recs,
                "message": "Welcome! Buy more to unlock AI recommendations",
                "stats": {"user_transactions": 0}
            })
        
        # Build and analyze transaction matrix
        products = list(PRODUCT_MAP.keys())
        df = TransactionProcessor.build_transaction_matrix(user_transactions, products)
        rules = TransactionProcessor.generate_rules(df)
        
        if rules.empty:
            return jsonify({
                "success": False, 
                "message": "No patterns found yet. Need more purchase data!"
            })
        
        # Extract recommendations
        recommendations = []
        seen_products = set()
        
        for _, rule in rules.iterrows():
            antecedent = int(list(rule['antecedents'])[0])
            consequent = int(list(rule['consequents'])[0])
            
            if consequent in seen_products or consequent not in PRODUCT_MAP:
                continue
            
            info = PRODUCT_MAP[consequent]
            rec = {
                "id": consequent,
                "name": info["name"],
                "price": info["price"],
                "image": info["emoji"],
                "category": info["category"],
                "confidence": round(float(rule["confidence"]), 3),
                "lift": round(float(rule["lift"]), 2),
                "support": round(float(rule["support"]), 3)
            }
            recommendations.append(rec)
            seen_products.add(consequent)
            
            if len(recommendations) >= 8:
                break
        
        stats = {
            "user_transactions": len(user_transactions),
            "total_rules": len(rules),
            "avg_confidence": round(float(rules['confidence'].mean()), 3)
        }
        
        log_message(f"Generated {len(recommendations)} recommendations")
        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "stats": stats
        })
        
    except Exception as e:
        log_message(f"Error generating recommendations: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/transaction', methods=['POST'])
def add_transaction():
    try:
        data = request.json
        user_id = data.get('user_id')
        items = data.get('items', [])
        
        if not user_id or not items:
            return jsonify({"success": False, "message": "Missing user_id or items"}), 400
        
        transactions = DataManager.load_data(TRANSACTIONS_FILE)
        transaction = {
            "user_id": int(user_id),
            "items": [int(item) for item in items],
            "timestamp": datetime.now().isoformat(),
            "total_items": len(items)
        }
        
        transactions.append(transaction)
        DataManager.save_data(TRANSACTIONS_FILE, transactions)
        
        log_message(f"Recorded transaction for user {user_id}: {len(items)} items")
        return jsonify({"success": True, "message": "Transaction saved successfully"})
        
    except Exception as e:
        log_message(f"Transaction error: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        transactions = DataManager.load_data(TRANSACTIONS_FILE)
        total_transactions = len(transactions)
        total_users = len(set(str(t['user_id']) for t in transactions))
        total_items = sum(len(t.get('items', [])) for t in transactions)
        avg_items = round(total_items / max(1, total_transactions), 1)
        
        stats = {
            "total_transactions": total_transactions,
            "total_users": total_users,
            "products": len(PRODUCT_MAP),
            "avg_items_per_transaction": avg_items,
            "total_items": total_items
        }
        
        return jsonify(stats)
    except Exception:
        return jsonify({
            "total_transactions": 0, 
            "total_users": 0, 
            "products": len(PRODUCT_MAP)
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "ARL": "ready", 
        "products": len(PRODUCT_MAP),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Clear all transaction data (for testing)"""
    try:
        DataManager.save_data(TRANSACTIONS_FILE, [])
        log_message("Cleared all transaction data")
        return jsonify({"success": True, "message": "Data cleared"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 JCPAS ARL API Starting...")
    print(f"📦 Products loaded: {len(PRODUCT_MAP)}")
    print(f"💾 Data files: {TRANSACTIONS_FILE}, {STATS_FILE}")
    print("🌐 API endpoints:")
    print("   GET  /api/recommendations/<user_id>")
    print("   POST /api/transaction")
    print("   GET  /api/stats")
    print("   GET  /api/health")
    print("   POST /api/clear (testing)")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)