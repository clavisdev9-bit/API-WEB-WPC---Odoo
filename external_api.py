from flask import Flask, jsonify, request, Response
import xmlrpc.client
import os
import json
from functools import wraps
from collections import OrderedDict
from config import Config

app = Flask(__name__)

# Configuration
ODOO_URL = Config.ODOO_URL
ODOO_DB = Config.ODOO_DB
ODOO_USERNAME = Config.ODOO_USERNAME
ODOO_API_KEY = Config.ODOO_API_KEY

# Initialize Odoo connection
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(ODOO_URL))
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(ODOO_URL))

# Authenticate
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {})

if not uid:
    print("Authentication failed. Please check your credentials.")
    exit()

print(f"Authentication successful. User ID: {uid}")

def handle_odoo_errors(f):
    """Decorator to handle Odoo API errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'An error occurred while processing the request'
            }), 500
    return decorated_function

def ordered_jsonify(data):
    """Custom jsonify that preserves field order"""
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json'
    )

def get_states():
    """
    Fungsi untuk mengambil semua data state dari model res.country.state
    
    Returns:
        list: Semua data state dengan field id dan name
    """
    # Ambil semua ID state
    state_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'res.country.state', 
        'search', 
        [[]]  # Domain kosong = semua records
    )
    
    if not state_ids:
        return []
    
    # Ambil data state dengan field terbatas
    states = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.country.state',
        'read',
        [state_ids],
        {'fields': ['id', 'name', 'country_id']}
    )
    
    # Sederhanakan struktur response
    simplified_states = []
    for state in states:
        simplified_state = {
            'id': state.get('id'),
            'name': state.get('name'),
            'country': state.get('country_id')[1] if state.get('country_id') else None
        }
        simplified_states.append(simplified_state)
    
    return simplified_states

# API Routes

@app.route('/')
def home():
    """Home endpoint with API information"""
    return ordered_jsonify({
        'message': 'Odoo External API',
        'version': '1.0.0',
        'endpoints': {
            'contacts': {
                'GET /states': 'Get all states for dropdown',
                'GET /contacts': 'Get all contacts',
                'POST /contacts/create': 'Create new contact',
                'GET /contacts/<id>': 'Get specific contact by ID'
            },
            'quotes': {
                'POST /quote/create': 'Create complete quote (contact + sales order)',
                'GET /quotes': 'Get all quotes (sales orders)'
            },
            'system': {
                'GET /health': 'Health check'
            }
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return ordered_jsonify({
        'status': 'healthy',
        'odoo_connection': 'connected' if uid else 'disconnected',
        'user_id': uid
    })

@app.route('/states', methods=['GET'])
@handle_odoo_errors
def get_all_states():
    """Get all states for dropdown selection"""
    states = get_states()
    
    return ordered_jsonify({
        'success': True,
        'data': states,
        'count': len(states)
    })

@app.route('/contacts', methods=['GET'])
@handle_odoo_errors
def get_all_contacts():
    """Get all contacts"""
    # Ambil semua ID contact
    contact_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'res.partner', 
        'search', 
        [[]]  # Domain kosong = semua records
    )
    
    if not contact_ids:
        return ordered_jsonify({
            'success': True,
            'data': [],
            'count': 0
        })
    
    # Ambil data contact dengan field yang diperlukan
    contacts = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.partner',
        'read',
        [contact_ids],
        {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'state_id']}
    )
    
    return ordered_jsonify({
        'success': True,
        'data': contacts,
        'count': len(contacts)
    })

@app.route('/contacts/create', methods=['POST'])
@handle_odoo_errors
def create_contact():
    """Create new contact with specified fields"""
    try:
        # Ambil data dari request body
        data = request.get_json()
        
        if not data:
            return ordered_jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validasi field wajib
        required_fields = ['name']
        for field in required_fields:
            if field not in data:
                return ordered_jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400
        
        # Validasi business type
        valid_business_types = ["I am a business", "I am a freight forwarder"]
        if 'x_studio_your_business' in data and data['x_studio_your_business'] not in valid_business_types:
            return ordered_jsonify({
                'success': False,
                'error': f'x_studio_your_business must be one of: {valid_business_types}'
            }), 400
        
        # Validasi state_id jika ada
        if 'state_id' in data and data['state_id']:
            # Cek apakah state_id ada di database
            state_exists = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.country.state',
                'search',
                [[['id', '=', data['state_id']]]]
            )
            if not state_exists:
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid state_id'
                }), 400
        
        # Siapkan data untuk Odoo
        contact_data = {
            'name': data['name'],
            'email': data.get('email', False),
            'phone': data.get('phone', False),
            'x_studio_your_business': data.get('x_studio_your_business', False),
            'state_id': data.get('state_id', False)
        }
        
        # Buat contact baru di Odoo
        new_contact_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'create',
            [contact_data]
        )
        
        # Ambil data contact yang baru dibuat
        new_contact = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'read',
            [new_contact_id],
            {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'state_id']}
        )
        
        return ordered_jsonify({
            'success': True,
            'data': new_contact[0],
            'message': 'Contact created successfully'
        }), 201
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to create contact',
            'details': str(e)
        }), 500

@app.route('/contacts/<int:contact_id>', methods=['GET'])
@handle_odoo_errors
def get_contact_by_id(contact_id):
    """Get a specific contact by ID"""
    # Ambil data contact berdasarkan ID
    contacts = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.partner',
        'read',
        [contact_id],
        {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'state_id']}
    )
    
    if not contacts:
        return ordered_jsonify({
            'success': False,
            'error': 'Contact not found'
        }), 404
    
    return ordered_jsonify({
        'success': True,
        'data': contacts[0]
    })

@app.route('/quote/create', methods=['POST'])
@handle_odoo_errors
def create_quote():
    """Create contact and sales order from complete form data"""
    try:
        # Ambil data dari request body
        data = request.get_json()
        
        if not data:
            return ordered_jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validasi field wajib untuk contact
        required_contact_fields = ['name']
        for field in required_contact_fields:
            if field not in data:
                return ordered_jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400
        
        # Validasi field wajib untuk sales order
        required_quote_fields = ['pickup_address', 'delivery_address', 'cargo_details', 'transportation_method']
        for field in required_quote_fields:
            if field not in data:
                return ordered_jsonify({
                    'success': False,
                    'error': f'Field {field} is required'
                }), 400
        
        # Validasi business type
        valid_business_types = ["I am a business", "I am a freight forwarder"]
        if 'x_studio_your_business' in data and data['x_studio_your_business'] not in valid_business_types:
            return ordered_jsonify({
                'success': False,
                'error': f'x_studio_your_business must be one of: {valid_business_types}'
            }), 400
        
        # Validasi state_id jika ada
        if 'state_id' in data and data['state_id']:
            state_exists = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.country.state',
                'search',
                [[['id', '=', data['state_id']]]]
            )
            if not state_exists:
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid state_id'
                }), 400
        
        # 1. Buat Contact dulu
        contact_data = {
            'name': data['name'],
            'email': data.get('email', False),
            'phone': data.get('phone', False),
            'x_studio_your_business': data.get('x_studio_your_business', False),
            'state_id': data.get('state_id', False)
        }
        
        new_contact_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'create',
            [contact_data]
        )
        
        # 2. Buat Sales Order dengan referensi ke contact
        sales_order_data = {
            'partner_id': new_contact_id,  # Link ke contact yang baru dibuat
            'x_studio_pickup_address': data['pickup_address'],
            'x_studio_delivery_address': data['delivery_address'],
            'x_studio_cargo_details': data['cargo_details'],
            'x_studio_transportation_method': data['transportation_method'],
            'state': 'draft'  # Status draft untuk quotation
        }
        
        new_quote_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order',
            'create',
            [sales_order_data]
        )
        
        # 3. Ambil data yang baru dibuat untuk response
        new_contact = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'read',
            [new_contact_id],
            {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'state_id']}
        )
        
        new_quote = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order',
            'read',
            [new_quote_id],
            {'fields': ['id', 'name', 'partner_id', 'state', 'x_studio_pickup_address', 'x_studio_delivery_address', 'x_studio_cargo_details', 'x_studio_transportation_method']}
        )
        
        return ordered_jsonify({
            'success': True,
            'data': {
                'contact': new_contact[0],
                'sales_order': new_quote[0]
            },
            'message': 'Quote created successfully'
        }), 201
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to create quote',
            'details': str(e)
        }), 500

@app.route('/quotes', methods=['GET'])
@handle_odoo_errors
def get_all_quotes():
    """Get all sales orders (quotes)"""
    # Ambil semua ID sales order
    quote_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'sale.order', 
        'search', 
        [[]]  # Domain kosong = semua records
    )
    
    if not quote_ids:
        return ordered_jsonify({
            'success': True,
            'data': [],
            'count': 0
        })
    
    # Ambil data sales order dengan field yang diperlukan
    quotes = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'sale.order',
        'read',
        [quote_ids],
        {'fields': ['id', 'name', 'partner_id', 'state', 'x_studio_pickup_address', 'x_studio_delivery_address', 'x_studio_cargo_details', 'x_studio_transportation_method', 'create_date']}
    )
    
    return ordered_jsonify({
        'success': True,
        'data': quotes,
        'count': len(quotes)
    })



if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)