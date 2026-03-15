import os
import random
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

# Global variable to track if firebase is initialized
_firebase_initialized = False

def init_db():
    """Initialize Firebase Admin SDK"""
    global _firebase_initialized
    if _firebase_initialized:
        return True
        
    try:
        cred_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        db_url = os.environ.get('FIREBASE_DATABASE_URL')
        
        if not db_url:
            print("WARNING: FIREBASE_DATABASE_URL not found in .env file")
            print("Running in mock mode (Returning dummy data). Set FIREBASE_DATABASE_URL to connect to real database.")
            return False
            
        cred = None
        if cred_json:
            import json
            try:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                print(f"Error parsing FIREBASE_CREDENTIALS_JSON: {e}")
                return False
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            print(f"WARNING: Firebase credentials not found at {cred_path}")
            print("Running in mock mode.")
            return False
            
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
        _firebase_initialized = True
        print("Firebase Realtime Database initialized successfully.")
        return True
        
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        return False

# ── DATABASE OPERATIONS ────────────────────────────────────────────────────────

def get_all_orders():
    """Retrieve all orders from Firebase"""
    if not _firebase_initialized:
        return _get_mock_orders()
        
    try:
        ref = db.reference('orders')
        orders_dict = ref.get()
        if not orders_dict:
            return []
        orders = []
        for order_id, order_data in orders_dict.items():
            order_data['id'] = order_id
            orders.append(order_data)
        orders.sort(key=lambda x: x.get('date', ''), reverse=True)
        return orders
    except Exception as e:
        print(f"Error fetching orders from Firebase: {e}")
        return []

def get_order(order_id):
    """Retrieve a specific order by ID"""
    if not _firebase_initialized:
        mock_orders = _get_mock_orders()
        return next((o for o in mock_orders if o['id'] == order_id), None)
        
    try:
        ref = db.reference(f'orders/{order_id}')
        order = ref.get()
        if order:
            order['id'] = order_id
        return order
    except Exception as e:
        print(f"Error fetching order {order_id}: {e}")
        return None

def create_order(order_data):
    """Create a new order in Firebase"""
    year = datetime.now().year
    random_digits = random.randint(1000, 9999)
    order_id = f"ORD-{year}-{random_digits}"
    
    new_order = {
        'date': datetime.now().isoformat(),
        'customer': order_data.get('customer', 'Guest'),
        'email': order_data.get('email', ''),
        'phone': order_data.get('phone', ''),
        'address': order_data.get('address', ''),
        'items': order_data.get('items', []),
        'total': float(order_data.get('total', 0)),
        'paymentId': order_data.get('paymentId', ''),
        'status': 'Pending',
        'location': 'Order Received',
        'expectedDelivery': 'Calculating...'
    }
    
    if not _firebase_initialized:
        print(f"MOCK MODE: Created order {order_id}")
        return order_id
        
    try:
        ref = db.reference(f'orders/{order_id}')
        ref.set(new_order)
        return order_id
    except Exception as e:
        print(f"Error creating order: {e}")
        raise e

def update_order_status(order_id, status=None, location=None, expected_delivery=None):
    """Update an order's status, location and/or expected delivery"""
    if not _firebase_initialized:
        print(f"MOCK MODE: Updated order {order_id} — status={status}, location={location}")
        return True
        
    try:
        ref = db.reference(f'orders/{order_id}')
        if not ref.get():
            return False
            
        updates = {}
        if status:
            updates['status'] = status
        if location is not None:
            updates['location'] = location
        if expected_delivery is not None:
            updates['expectedDelivery'] = expected_delivery
            
        if updates:
            ref.update(updates)
        return True
    except Exception as e:
        print(f"Error updating order {order_id}: {e}")
        return False

def cancel_order(order_id):
    """Cancel an order (only if Pending or Processing)"""
    if not _firebase_initialized:
        print(f"MOCK MODE: Cancelled order {order_id}")
        return True
        
    try:
        ref = db.reference(f'orders/{order_id}')
        order = ref.get()
        if not order:
            return False
        if order.get('status') not in ['Pending', 'Processing']:
            return False
        ref.update({'status': 'Cancelled', 'location': 'Cancelled by User'})
        return True
    except Exception as e:
        print(f"Error cancelling order {order_id}: {e}")
        return False

# ── ACTIVITY TRACKING ─────────────────────────────────────────────────────────

def log_activity(event_data: dict):
    """Log a user activity event to Firebase under 'activity' node"""
    if not _firebase_initialized:
        print(f"MOCK MODE: Activity logged — {event_data.get('event')} on {event_data.get('page')}")
        return

    try:
        ts = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        ref = db.reference(f'activity/{ts}')
        event_data['_timestamp'] = datetime.now().isoformat()
        ref.set(event_data)
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_activity_logs(limit: int = 200) -> list:
    """Retrieve recent activity logs from Firebase"""
    if not _firebase_initialized:
        return []

    try:
        ref = db.reference('activity')
        raw = ref.order_by_key().limit_to_last(limit).get()
        if not raw:
            return []
        logs = []
        for key, val in raw.items():
            if isinstance(val, dict):
                val['_key'] = key
                logs.append(val)
        logs.reverse()
        return logs
    except Exception as e:
        print(f"Error fetching activity logs: {e}")
        return []

# ── MOCK DATA FALLBACK ────────────────────────────────────────────────────────

def _get_mock_orders():
    """Return dummy data when Firebase is not initialized"""
    return [
        {
            'id': 'ORD-2026-9843',
            'date': '2026-03-14T10:30:00',
            'customer': 'Rahul Kumar',
            'email': 'rahul.k@example.com',
            'phone': '+91 9876543210',
            'address': 'Mumbai, Maharashtra - 400001',
            'items': [{'name': 'ABHIMANYU Oversized Tee', 'size': 'L', 'qty': 2, 'price': 999}],
            'total': 1998.00,
            'paymentId': 'pay_mock_1',
            'status': 'Processing',
            'location': 'Mumbai Sorting Facility',
            'expectedDelivery': '2026-03-18'
        },
        {
            'id': 'ORD-2026-9842',
            'date': '2026-03-13T15:45:00',
            'customer': 'Anita Sharma',
            'email': 'anita.s@example.com',
            'phone': '+91 8765432109',
            'address': 'New Delhi - 110001',
            'items': [{'name': 'BHISHMA Oversized Tee', 'size': 'M', 'qty': 1, 'price': 999}],
            'total': 999.00,
            'paymentId': 'pay_mock_2',
            'status': 'Shipped',
            'location': 'In Transit to New Delhi',
            'expectedDelivery': '2026-03-16'
        }
    ]
