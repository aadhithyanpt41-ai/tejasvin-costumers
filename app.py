import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_all_orders, get_order, create_order, update_order_status, cancel_order, init_db

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# Initialize DB connection on startup
init_db()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "Tejasvin Orders Backend"}), 200

@app.route('/api/orders', methods=['GET'])
def fetch_orders():
    """Fetch all orders for the Admin dashboard"""
    try:
        orders = get_all_orders()
        return jsonify({"success": True, "data": orders}), 200
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def fetch_order(order_id):
    """Fetch single order for User Tracking"""
    try:
        order = get_order(order_id)
        if order:
            return jsonify({"success": True, "data": order}), 200
        else:
            return jsonify({"success": False, "error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def new_order():
    """Create a new order from Frontend Cart/Checkout"""
    try:
        data = request.json
        # Basic validation
        required_fields = ['customer', 'items', 'total']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        order_id = create_order(data)
        return jsonify({"success": True, "order_id": order_id, "message": "Order created successfully"}), 201
    except Exception as e:
        print(f"Error creating order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_status(order_id):
    """Update order status or location from Admin Dashboard"""
    try:
        data = request.json
        status = data.get('status')
        location = data.get('location')
        
        if not status and not location:
            return jsonify({"success": False, "error": "Must provide status or location to update"}), 400
            
        success = update_order_status(order_id, status, location)
        
        if success:
            return jsonify({"success": True, "message": "Order updated successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Order not found or update failed"}), 404
            
    except Exception as e:
        print(f"Error updating order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
def cancel_order_endpoint(order_id):
    """Cancel an order from User Tracking Page"""
    try:
        from database import cancel_order
        success = cancel_order(order_id)
        if success:
            return jsonify({"success": True, "message": "Order cancelled successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Order not found or cannot be cancelled (must be Pending)"}), 400
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Run in debug mode if not in production
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
