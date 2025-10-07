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
        {'fields': [
            'id', 'name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
            'x_studio_your_business', 'x_studio_id', 'vat', 'category_id',
            'street', 'street2', 'city', 'zip', 'country_id', 'state_id'
        ]}
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
            
        # Proses category_id (tags) - ambil nama tag jika ada
        if contact.get('category_id') and contact['category_id'] != False:
            if isinstance(contact['category_id'], list):
                contact['tags'] = [tag[1] for tag in contact['category_id']]  # Ambil nama tag
                contact['tag_ids'] = [tag[0] for tag in contact['category_id']]  # Ambil ID tag
            else:
                contact['tags'] = [contact['category_id']]
                contact['tag_ids'] = [contact['category_id']]
        else:
            contact['tags'] = []
            contact['tag_ids'] = []
            
        # Proses field yang mungkin False menjadi None untuk konsistensi
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id']:
            if contact.get(field) == False:
                contact[field] = None
    
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
        
        # Validasi NPWP (vat) - format Indonesia
        if 'vat' in data and data['vat']:
            vat = data['vat'].replace('.', '').replace('-', '').replace(' ', '')
            if not vat.isdigit() or len(vat) != 15:
                return ordered_jsonify({
                    'success': False,
                    'error': 'NPWP must be 15 digits (format: XX.XXX.XXX.X-XXX.XXX)'
                }), 400
        
        # Validasi email format
        if 'email' in data and data['email']:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data['email']):
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400
        
        # Validasi website format
        if 'website' in data and data['website']:
            if not data['website'].startswith(('http://', 'https://')):
                data['website'] = 'https://' + data['website']
        
        # Validasi category_id (tags) jika ada
        if 'category_id' in data and data['category_id']:
            if not isinstance(data['category_id'], list):
                return ordered_jsonify({
                    'success': False,
                    'error': 'category_id must be a list of tag IDs'
                }), 400
            
            # Cek apakah semua tag ID valid
            for tag_id in data['category_id']:
                if not isinstance(tag_id, int):
                    return ordered_jsonify({
                        'success': False,
                        'error': 'All tag IDs must be integers'
                    }), 400
                
                tag_exists = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner.category',
                    'search',
                    [[['id', '=', tag_id]]]
                )
                if not tag_exists:
                    return ordered_jsonify({
                        'success': False,
                        'error': f'Tag with ID {tag_id} not found'
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
            'mobile': data.get('mobile', False),
            'website': data.get('website', False),
            'function': data.get('function', False),
            'title': data.get('title', False),
            'lang': data.get('lang', False),
            'x_studio_your_business': data.get('x_studio_your_business', False),
            'x_studio_id': data.get('x_studio_id', False),
            'vat': data.get('vat', False),
            'street': data.get('street', False),
            'street2': data.get('street2', False),
            'city': data.get('city', False),
            'zip': data.get('zip', False),
            'country_id': final_country_id,
            'state_id': data.get('state_id', False),
            'category_id': [(6, 0, data.get('category_id', []))] if data.get('category_id') else False
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
            {'fields': [
                'id', 'name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
                'x_studio_your_business', 'x_studio_id', 'vat', 'category_id',
                'street', 'street2', 'city', 'zip', 'country_id', 'state_id'
            ]}
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
            
        # Proses category_id (tags) - ambil nama tag jika ada
        if contact.get('category_id') and contact['category_id'] != False:
            if isinstance(contact['category_id'], list):
                contact['tags'] = [tag[1] for tag in contact['category_id']]  # Ambil nama tag
                contact['tag_ids'] = [tag[0] for tag in contact['category_id']]  # Ambil ID tag
            else:
                contact['tags'] = [contact['category_id']]
                contact['tag_ids'] = [contact['category_id']]
        else:
            contact['tags'] = []
            contact['tag_ids'] = []
            
        # Proses field yang mungkin False menjadi None untuk konsistensi
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id']:
            if contact.get(field) == False:
                contact[field] = None
        
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

@contact_bp.route('/tags', methods=['GET'])
@handle_odoo_errors
def get_all_tags():
    """Get all available tags/categories for contact"""
    # Ambil semua ID tag
    tag_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'res.partner.category', 
        'search', 
        [[]]  # Domain kosong = semua records
    )
    
    if not tag_ids:
        return ordered_jsonify({
            'success': True,
            'data': [],
            'count': 0
        })
    
    # Ambil data tag dengan field yang diperlukan
    tags = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.partner.category',
        'read',
        [tag_ids],
        {'fields': ['id', 'name', 'color']}
    )
    
    return ordered_jsonify({
        'success': True,
        'data': tags,
        'count': len(tags)
    })

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
        {'fields': [
            'id', 'name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
            'x_studio_your_business', 'x_studio_id', 'vat', 'category_id',
            'street', 'street2', 'city', 'zip', 'country_id', 'state_id'
        ]}
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
        
    # Proses category_id (tags) - ambil nama tag jika ada
    if contact.get('category_id') and contact['category_id'] != False:
        if isinstance(contact['category_id'], list):
            contact['tags'] = [tag[1] for tag in contact['category_id']]  # Ambil nama tag
            contact['tag_ids'] = [tag[0] for tag in contact['category_id']]  # Ambil ID tag
        else:
            contact['tags'] = [contact['category_id']]
            contact['tag_ids'] = [contact['category_id']]
    else:
        contact['tags'] = []
        contact['tag_ids'] = []
        
    # Proses field yang mungkin False menjadi None untuk konsistensi
    for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id']:
        if contact.get(field) == False:
            contact[field] = None
    
    return ordered_jsonify({
        'success': True,
        'data': contact
    })

@contact_bp.route('/contacts/<int:contact_id>', methods=['PUT'])
@handle_odoo_errors
def update_contact(contact_id):
    """Update an existing contact"""
    try:
        # Ambil data dari request body
        data = request.get_json()
        
        if not data:
            return ordered_jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Cek apakah contact ada
        contact_exists = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'search',
            [[['id', '=', contact_id]]]
        )
        
        if not contact_exists:
            return ordered_jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        # Validasi business type jika ada
        valid_business_types = ["I am a business", "I am a freight forwarder"]
        if 'x_studio_your_business' in data and data['x_studio_your_business'] not in valid_business_types:
            return ordered_jsonify({
                'success': False,
                'error': f'x_studio_your_business must be one of: {valid_business_types}'
            }), 400
        
        # Validasi NPWP (vat) - format Indonesia
        if 'vat' in data and data['vat']:
            vat = data['vat'].replace('.', '').replace('-', '').replace(' ', '')
            if not vat.isdigit() or len(vat) != 15:
                return ordered_jsonify({
                    'success': False,
                    'error': 'NPWP must be 15 digits (format: XX.XXX.XXX.X-XXX.XXX)'
                }), 400
        
        # Validasi email format
        if 'email' in data and data['email']:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data['email']):
                return ordered_jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400
        
        # Validasi website format
        if 'website' in data and data['website']:
            if not data['website'].startswith(('http://', 'https://')):
                data['website'] = 'https://' + data['website']
        
        # Validasi category_id (tags) jika ada
        if 'category_id' in data and data['category_id']:
            if not isinstance(data['category_id'], list):
                return ordered_jsonify({
                    'success': False,
                    'error': 'category_id must be a list of tag IDs'
                }), 400
            
            # Cek apakah semua tag ID valid
            for tag_id in data['category_id']:
                if not isinstance(tag_id, int):
                    return ordered_jsonify({
                        'success': False,
                        'error': 'All tag IDs must be integers'
                    }), 400
                
                tag_exists = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner.category',
                    'search',
                    [[['id', '=', tag_id]]]
                )
                if not tag_exists:
                    return ordered_jsonify({
                        'success': False,
                        'error': f'Tag with ID {tag_id} not found'
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
        
        # Validasi country_id jika ada
        if 'country_id' in data and data['country_id']:
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
        
        # Siapkan data untuk update
        update_data = {}
        for field in ['name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
                     'x_studio_your_business', 'x_studio_id', 'vat', 'street', 'street2', 
                     'city', 'zip', 'country_id', 'state_id']:
            if field in data:
                update_data[field] = data[field]
        
        # Handle category_id khusus
        if 'category_id' in data:
            if data['category_id']:
                update_data['category_id'] = [(6, 0, data['category_id'])]
            else:
                update_data['category_id'] = [(5, 0, 0)]  # Remove all tags
        
        # Update contact di Odoo
        models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'write',
            [contact_id, update_data]
        )
        
        # Ambil data contact yang sudah diupdate
        updated_contact = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'read',
            [contact_id],
            {'fields': [
                'id', 'name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
                'x_studio_your_business', 'x_studio_id', 'vat', 'category_id',
                'street', 'street2', 'city', 'zip', 'country_id', 'state_id'
            ]}
        )
        
        # Proses data contact yang sudah diupdate
        contact = updated_contact[0]
        if contact.get('country_id') and contact['country_id'] != False:
            contact['country_name'] = contact['country_id'][1] if isinstance(contact['country_id'], list) else contact['country_id']
        else:
            contact['country_name'] = None
            
        if contact.get('state_id') and contact['state_id'] != False:
            contact['state_name'] = contact['state_id'][1] if isinstance(contact['state_id'], list) else contact['state_id']
        else:
            contact['state_name'] = None
            
        # Ubah country_id dan state_id menjadi integer saja
        if contact.get('country_id') and contact['country_id'] != False:
            if isinstance(contact['country_id'], list):
                contact['country_id'] = contact['country_id'][0]
        else:
            contact['country_id'] = None
            
        if contact.get('state_id') and contact['state_id'] != False:
            if isinstance(contact['state_id'], list):
                contact['state_id'] = contact['state_id'][0]
        else:
            contact['state_id'] = None
            
        # Proses category_id (tags)
        if contact.get('category_id') and contact['category_id'] != False:
            if isinstance(contact['category_id'], list):
                contact['tags'] = [tag[1] for tag in contact['category_id']]
                contact['tag_ids'] = [tag[0] for tag in contact['category_id']]
            else:
                contact['tags'] = [contact['category_id']]
                contact['tag_ids'] = [contact['category_id']]
        else:
            contact['tags'] = []
            contact['tag_ids'] = []
            
        # Proses field yang mungkin False menjadi None
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id']:
            if contact.get(field) == False:
                contact[field] = None
        
        return ordered_jsonify({
            'success': True,
            'data': contact,
            'message': 'Contact updated successfully'
        })
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to update contact',
            'details': str(e)
        }), 500

@contact_bp.route('/contacts/<int:contact_id>', methods=['DELETE'])
@handle_odoo_errors
def delete_contact(contact_id):
    """Delete a contact"""
    try:
        # Cek apakah contact ada
        contact_exists = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'search',
            [[['id', '=', contact_id]]]
        )
        
        if not contact_exists:
            return ordered_jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        # Hapus contact dari Odoo
        models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'unlink',
            [contact_id]
        )
        
        return ordered_jsonify({
            'success': True,
            'message': f'Contact with ID {contact_id} deleted successfully'
        })
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to delete contact',
            'details': str(e)
        }), 500





