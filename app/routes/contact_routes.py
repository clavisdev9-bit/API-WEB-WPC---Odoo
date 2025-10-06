"""
Contact related routes
"""
from flask import Blueprint, request
from app.functions.odoo_functions import ordered_jsonify
from app.models.odoo_connection import models, ODOO_DB, uid, ODOO_API_KEY
from app.functions.odoo_functions import get_states, get_countries
from functools import wraps

# Create blueprint
contact_bp = Blueprint('contacts', __name__)

def handle_odoo_errors(f):
    """Decorator to handle Odoo API errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return ordered_jsonify({
                'success': False,
                'error': str(e),
                'message': 'An error occurred while processing the request'
            }), 500
    return decorated_function

@contact_bp.route('/states', methods=['GET'])
@handle_odoo_errors
def get_all_states():
    """Get all states for dropdown selection"""
    states = get_states(models, ODOO_DB, uid, ODOO_API_KEY)
    
    return ordered_jsonify({
        'success': True,
        'data': states,
        'count': len(states)
    })

@contact_bp.route('/countries', methods=['GET'])
@handle_odoo_errors
def get_all_countries():
    """Get all countries for dropdown selection"""
    countries = get_countries(models, ODOO_DB, uid, ODOO_API_KEY)
    
    return ordered_jsonify({
        'success': True,
        'data': countries,
        'count': len(countries)
    })

@contact_bp.route('/states/country/<int:country_id>', methods=['GET'])
@handle_odoo_errors
def get_states_by_country(country_id):
    """Get all states for a specific country"""
    # Validasi country_id terlebih dahulu
    country_exists = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.country',
        'search',
        [[['id', '=', country_id]]]
    )
    
    if not country_exists:
        return ordered_jsonify({
            'success': False,
            'error': 'Country not found'
        }), 404
    
    # Ambil states berdasarkan country_id
    state_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'res.country.state', 
        'search', 
        [[['country_id', '=', country_id]]]
    )
    
    if not state_ids:
        return ordered_jsonify({
            'success': True,
            'data': [],
            'count': 0,
            'message': f'No states found for country ID {country_id}'
        })
    
    # Ambil data states
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
    
    return ordered_jsonify({
        'success': True,
        'data': simplified_states,
        'count': len(simplified_states)
    })

@contact_bp.route('/contacts', methods=['GET'])
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
        {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'country_id', 'state_id']}
    )
    
    # Tambahkan informasi country dan state yang lebih detail
    for contact in contacts:
        # Tambahkan country_name jika ada country_id (ambil langsung dari database)
        if contact.get('country_id') and contact['country_id'] != False:
            contact['country_name'] = contact['country_id'][1] if isinstance(contact['country_id'], list) else contact['country_id']
        else:
            contact['country_name'] = None
            
        # Tambahkan state_name jika ada state_id
        if contact.get('state_id') and contact['state_id'] != False:
            contact['state_name'] = contact['state_id'][1] if isinstance(contact['state_id'], list) else contact['state_id']
        else:
            contact['state_name'] = None
            
        # Ubah country_id menjadi integer saja (ambil ID dari array)
        if contact.get('country_id') and contact['country_id'] != False:
            if isinstance(contact['country_id'], list):
                contact['country_id'] = contact['country_id'][0]  # Ambil ID saja
            # Jika sudah integer, biarkan saja
        else:
            contact['country_id'] = None
            
        # Ubah state_id menjadi integer saja (ambil ID dari array)
        if contact.get('state_id') and contact['state_id'] != False:
            if isinstance(contact['state_id'], list):
                contact['state_id'] = contact['state_id'][0]  # Ambil ID saja
            # Jika sudah integer, biarkan saja
        else:
            contact['state_id'] = None
    
    return ordered_jsonify({
        'success': True,
        'data': contacts,
        'count': len(contacts)
    })

@contact_bp.route('/contacts/create', methods=['POST'])
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
        
        # Validasi state_id jika ada dan ambil country_id dari state
        country_id_from_state = None
        if 'state_id' in data and data['state_id']:
            # Cek apakah state_id ada di database dan ambil country_id-nya
            state_data = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.country.state',
                'read',
                [data['state_id']],
                {'fields': ['id', 'country_id']}
            )
            if not state_data:
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid state_id'
                }), 400
            country_id_from_state = state_data[0]['country_id'][0] if state_data[0]['country_id'] else None
        
        # Validasi country_id jika ada (opsional, karena bisa diisi otomatis dari state)
        if 'country_id' in data and data['country_id']:
            # Cek apakah country_id ada di database
            country_exists = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.country',
                'search',
                [[['id', '=', data['country_id']]]]
            )
            if not country_exists:
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid country_id'
                }), 400
        
        # Tentukan country_id yang akan digunakan
        # Prioritas: country_id dari request > country_id dari state > False
        final_country_id = data.get('country_id', country_id_from_state) if data.get('country_id') else country_id_from_state
        
        # Siapkan data untuk Odoo
        contact_data = {
            'name': data['name'],
            'email': data.get('email', False),
            'phone': data.get('phone', False),
            'x_studio_your_business': data.get('x_studio_your_business', False),
            'country_id': final_country_id,
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
            {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'country_id', 'state_id']}
        )
        
        # Tambahkan informasi country dan state yang lebih detail
        contact = new_contact[0]
        if contact.get('country_id') and contact['country_id'] != False:
            contact['country_name'] = contact['country_id'][1] if isinstance(contact['country_id'], list) else contact['country_id']
        else:
            contact['country_name'] = None
            
        if contact.get('state_id') and contact['state_id'] != False:
            contact['state_name'] = contact['state_id'][1] if isinstance(contact['state_id'], list) else contact['state_id']
        else:
            contact['state_name'] = None
            
        # Ubah country_id menjadi integer saja (ambil ID dari array)
        if contact.get('country_id') and contact['country_id'] != False:
            if isinstance(contact['country_id'], list):
                contact['country_id'] = contact['country_id'][0]  # Ambil ID saja
            # Jika sudah integer, biarkan saja
        else:
            contact['country_id'] = None
            
        # Ubah state_id menjadi integer saja (ambil ID dari array)
        if contact.get('state_id') and contact['state_id'] != False:
            if isinstance(contact['state_id'], list):
                contact['state_id'] = contact['state_id'][0]  # Ambil ID saja
            # Jika sudah integer, biarkan saja
        else:
            contact['state_id'] = None
        
        # Siapkan response message
        message = 'Contact created successfully'
        if country_id_from_state and not data.get('country_id'):
            message += f'. Country automatically set to {contact["country_name"]} based on selected state'
        
        return ordered_jsonify({
            'success': True,
            'data': new_contact[0],
            'message': message
        }), 201
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to create contact',
            'details': str(e)
        }), 500

@contact_bp.route('/contacts/<int:contact_id>', methods=['GET'])
@handle_odoo_errors
def get_contact_by_id(contact_id):
    """Get a specific contact by ID"""
    # Ambil data contact berdasarkan ID
    contacts = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.partner',
        'read',
        [contact_id],
        {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'country_id', 'state_id']}
    )
    
    if not contacts:
        return ordered_jsonify({
            'success': False,
            'error': 'Contact not found'
        }), 404
    
    # Tambahkan informasi country dan state yang lebih detail
    contact = contacts[0]
    if contact.get('country_id') and contact['country_id'] != False:
        contact['country_name'] = contact['country_id'][1] if isinstance(contact['country_id'], list) else contact['country_id']
    else:
        contact['country_name'] = None
        
    if contact.get('state_id') and contact['state_id'] != False:
        contact['state_name'] = contact['state_id'][1] if isinstance(contact['state_id'], list) else contact['state_id']
    else:
        contact['state_name'] = None
        
    # Ubah country_id menjadi integer saja (ambil ID dari array)
    if contact.get('country_id') and contact['country_id'] != False:
        if isinstance(contact['country_id'], list):
            contact['country_id'] = contact['country_id'][0]  # Ambil ID saja
        # Jika sudah integer, biarkan saja
    else:
        contact['country_id'] = None
        
    # Ubah state_id menjadi integer saja (ambil ID dari array)
    if contact.get('state_id') and contact['state_id'] != False:
        if isinstance(contact['state_id'], list):
            contact['state_id'] = contact['state_id'][0]  # Ambil ID saja
        # Jika sudah integer, biarkan saja
    else:
        contact['state_id'] = None
    
    return ordered_jsonify({
        'success': True,
        'data': contact
    })





