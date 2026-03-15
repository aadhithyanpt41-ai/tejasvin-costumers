import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import (
    get_all_orders, get_order, create_order,
    update_order_status, cancel_order, init_db,
    log_activity, get_activity_logs,
    get_all_products, add_product, update_product, delete_product,
    get_site_settings, update_site_settings,
    get_site_content, update_site_content
)

app = Flask(__name__)
CORS(app, origins=[
    "https://tejasvin.in",
    "https://www.tejasvin.in",
    "https://orders.tejasvin.in",
    "http://localhost",
    "http://127.0.0.1",
])

# Initialize DB connection on startup
init_db()

# ── HEALTH ────────────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "Tejasvin Orders Backend"}), 200

# ── ORDERS ────────────────────────────────────────────────────────────────────

@app.route('/api/orders', methods=['GET'])
def fetch_orders():
    """Fetch all orders. Optional ?email= filter for user-facing page."""
    try:
        orders = get_all_orders()
        email_filter = request.args.get('email', '').strip().lower()
        if email_filter:
            orders = [o for o in orders if o.get('email', '').lower() == email_filter]
        return jsonify({"success": True, "data": orders}), 200
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def fetch_order(order_id):
    """Fetch a single order by ID."""
    try:
        order = get_order(order_id)
        if order:
            return jsonify({"success": True, "data": order}), 200
        return jsonify({"success": False, "error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def new_order():
    """Create a new order from checkout."""
    try:
        data = request.json or {}
        for field in ['customer', 'items', 'total']:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
        order_id = create_order(data)
        return jsonify({"success": True, "order_id": order_id}), 201
    except Exception as e:
        print(f"Error creating order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_status(order_id):
    """Update order status / location / expected delivery (Admin)."""
    try:
        data = request.json or {}
        status = data.get('status')
        location = data.get('location')
        expected_delivery = data.get('expectedDelivery')
        if not status and location is None:
            return jsonify({"success": False, "error": "Provide status or location"}), 400
        success = update_order_status(order_id, status, location, expected_delivery)
        if success:
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Order not found"}), 404
    except Exception as e:
        print(f"Error updating order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
def cancel_order_endpoint(order_id):
    """Cancel an order (only Pending or Processing allowed)."""
    try:
        success = cancel_order(order_id)
        if success:
            return jsonify({"success": True, "message": "Order cancelled"}), 200
        return jsonify({"success": False, "error": "Cannot cancel this order"}), 400
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ── CMS: PRODUCTS ─────────────────────────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
def fetch_products():
    """Fetch all products."""
    try:
        products = get_all_products()
        return jsonify({"success": True, "data": products}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    """Create a new product."""
    try:
        data = request.json or {}
        required = ['title', 'price', 'image']
        if not all(k in data for k in required):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
            
        product_id = add_product(data)
        if product_id:
            return jsonify({"success": True, "id": product_id}), 201
        return jsonify({"success": False, "error": "Failed to create product"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['PUT', 'DELETE'])
def modify_product(product_id):
    """Update or delete a product."""
    try:
        if request.method == 'DELETE':
            success = delete_product(product_id)
            return jsonify({"success": success})
        else:
            data = request.json or {}
            success = update_product(product_id, data)
            return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── CMS: SETTINGS & CONTENT ───────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update site settings."""
    try:
        if request.method == 'GET':
            settings = get_site_settings()
            return jsonify({"success": True, "data": settings}), 200
        else:
            data = request.json or {}
            success = update_site_settings(data)
            return jsonify({"success": success}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/content', methods=['GET'])
def fetch_content():
    """Fetch all dynamic content."""
    try:
        content = get_site_content()
        return jsonify({"success": True, "data": content}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/content/<content_key>', methods=['PUT'])
def modify_content(content_key):
    """Update a specific content block."""
    try:
        data = request.json or {}
        value = data.get('value')
        if value is None:
            return jsonify({"success": False, "error": "Missing value"}), 400
        success = update_site_content(content_key, value)
        return jsonify({"success": success}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── ACTIVITY TRACKING ─────────────────────────────────────────────────────────

@app.route('/api/activity', methods=['POST'])
def track_activity():
    """Log a user activity event (page view, etc.) from the frontend."""
    try:
        data = request.json or {}
        ip = request.remote_addr or ''
        # Anonymise to /24 subnet
        parts = ip.split('.')
        if len(parts) == 4:
            ip = '.'.join(parts[:3]) + '.0'
        data['ip'] = ip
        log_activity(data)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Fetch recent activity logs for Admin Dashboard."""
    try:
        limit = int(request.args.get('limit', 200))
        logs = get_activity_logs(limit)
        return jsonify({"success": True, "data": logs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
