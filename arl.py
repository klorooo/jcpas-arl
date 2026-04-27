# arl.py - ADD the missing import at the top
import os  # <-- Add this line
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "ARL": "ready"})

@app.route('/api/stats') 
def stats():
    return jsonify({"total_transactions": 127, "total_users": 45})

@app.route('/api/recommendations/<int:user_id>')
def recommendations(user_id):
    return jsonify({
        "success": True,
        "recommendations": [
            {"id": 1, "name": "Keyboard", "price": 129.99, "confidence": 0.85},
            {"id": 2, "name": "Mouse", "price": 89.99, "confidence": 0.78}
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
