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

def process_category_id(category_id):
    """Helper function to safely process category_id (many2many field) and extract tags"""
    if not category_id or category_id == False:
        return []
    
    # Debug: Print the raw category_id data
    print(f"DEBUG: Raw category_id data: {category_id}, type: {type(category_id)}")
    
    if isinstance(category_id, list):
        # Untuk many2many field, Odoo mengembalikan list of tuples (id, name)
        if category_id and isinstance(category_id[0], (list, tuple)) and len(category_id[0]) >= 2:
            # Return array of objects dengan id dan name
            tags = []
            for tag in category_id:
                tag_id = tag[0]
                tag_name = tag[1] if len(tag) > 1 else None
                # Jika name kosong atau None, coba ambil dari database
                if not tag_name:
                    try:
                        # Ambil nama tag dari database
                        tag_data = models.execute_kw(
                            ODOO_DB, uid, ODOO_API_KEY,
                            'res.partner.category',
                            'read',
                            [tag_id],
                            {'fields': ['name']}
                        )
                        print(f"DEBUG: Tag data from DB for ID {tag_id}: {tag_data}")
                        if tag_data and tag_data[0].get('name'):
                            tag_name = tag_data[0]['name']
                    except Exception as e:
                        print(f"DEBUG: Error getting tag name for ID {tag_id}: {e}")
                        tag_name = f"Tag {tag_id}"  # Fallback name
                
                tags.append({
                    "id": tag_id,
                    "name": tag_name
                })
        else:
            # Jika format tidak sesuai (list of integers), ambil nama dari database
            tags = []
            for tag_id in category_id:
                tag_name = None
                try:
                    # Ambil nama tag dari database
                    tag_data = models.execute_kw(
                        ODOO_DB, uid, ODOO_API_KEY,
                        'res.partner.category',
                        'read',
                        [tag_id],
                        {'fields': ['name']}
                    )
                    print(f"DEBUG: Tag data from DB for ID {tag_id}: {tag_data}")
                    if tag_data and tag_data[0].get('name'):
                        tag_name = tag_data[0]['name']
                except Exception as e:
                    print(f"DEBUG: Error getting tag name for ID {tag_id}: {e}")
                    tag_name = f"Tag {tag_id}"  # Fallback name
                
                tags.append({
                    "id": tag_id,
                    "name": tag_name
                })
    else:
        # Jika single value, ambil nama dari database
        tag_name = None
        try:
            tag_data = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner.category',
                'read',
                [category_id],
                {'fields': ['name']}
            )
            print(f"DEBUG: Tag data from DB for ID {category_id}: {tag_data}")
            if tag_data and tag_data[0].get('name'):
                tag_name = tag_data[0]['name']
        except Exception as e:
            print(f"DEBUG: Error getting tag name for ID {category_id}: {e}")
            tag_name = f"Tag {category_id}"  # Fallback name
        
        tags = [{"id": category_id, "name": tag_name}]
    
    return tags

def process_country_state(country_id, country_name, state_id, state_name):
    """Process country and state fields into structured format"""
    country_data = []
    state_data = []
    
    # Process country
    if country_id and country_id != False:
        country_data.append({
            "country_id": country_id,
            "country_name": country_name if country_name else None
        })
    
    # Process state
    if state_id and state_id != False:
        state_data.append({
            "state_id": state_id,
            "state_name": state_name if state_name else None
        })
    
    return country_data, state_data

def convert_odoo_to_label_fields(contact_data):
    """Convert Odoo field names to label names in response with proper field order"""
    field_mapping = {
        'x_studio_id': 'contact_id',
        'street': 'street',
        'street2': 'street2',
        'city': 'city',
        'state_id': 'state',
        'zip': 'zip',
        'country_id': 'country',
        'vat': 'npwp',
        'x_studio_your_business': 'your_business',
        'function': 'job_position',
        'phone': 'phone',
        'mobile': 'mobile',
        'email': 'email',
        'website': 'website',
        'title': 'title',
        'lang': 'language',
        'category_id': 'tags',
        'company_type': 'company_type'
    }
    
    # Define field order based on Odoo Studio layout
    field_order = [
        'name',         # Contact name
        'contact_id',    # Contact ID
        'street',       # Address fields
        'street2',
        'city',
        'country',      # Country with new structure
        'state',        # State with new structure
        'zip',
        'npwp',         # Business fields
        'your_business',
        'job_position', # Contact details
        'phone',
        'mobile',
        'email',
        'website',
        'title',
        'language',
        'company_type',
        'tags',         # Tags
    ]
    
    # Create ordered dictionary with label names
    converted_data = {}
    
    # First, convert all fields
    for odoo_field, label_name in field_mapping.items():
        if odoo_field in contact_data:
            converted_data[label_name] = contact_data[odoo_field]
    
    # Handle special fields
    # if 'id' in contact_data:
    #     converted_data['id'] = contact_data['id']
    if 'name' in contact_data:
        converted_data['name'] = contact_data['name']
    
    # Process country and state with new structure
    country_data, state_data = process_country_state(
        contact_data.get('country_id'),
        contact_data.get('country_name'),
        contact_data.get('state_id'),
        contact_data.get('state_name')
    )
    converted_data['country'] = country_data
    converted_data['state'] = state_data
    
    # Keep other fields that don't have mapping
    for key, value in contact_data.items():
        if key not in field_mapping and key not in ['id', 'name', 'country_id', 'state_id', 'country_name', 'state_name']:
            converted_data[key] = value
    
    # Return ordered dictionary based on field_order
    ordered_data = {}
    for field in field_order:
        if field in converted_data:
            ordered_data[field] = converted_data[field]
    
    # Add any remaining fields that weren't in the order list
    for key, value in converted_data.items():
        if key not in ordered_data:
            ordered_data[key] = value
    
    return ordered_data

def convert_label_to_odoo_fields(data):
    """Convert label field names to Odoo field names for input processing"""
    label_to_odoo_mapping = {
        'name': 'name',
        'contact_id': 'x_studio_id',
        'street': 'street',
        'street2': 'street2',
        'city': 'city',
        'state': 'state_id',
        'zip': 'zip',
        'country': 'country_id',
        'npwp': 'vat',
        'your_business': 'x_studio_your_business',
        'job_position': 'function',
        'phone': 'phone',
        'mobile': 'mobile',
        'email': 'email',
        'website': 'website',
        'title': 'title',
        'language': 'lang',
        'tags': 'category_id',
        'company_type': 'company_type'
    }
    
    # Convert label names to Odoo field names
    converted_data = {}
    for label_name, odoo_field in label_to_odoo_mapping.items():
        if label_name in data:
            converted_data[odoo_field] = data[label_name]
    
    # Keep other fields that don't have mapping
    for key, value in data.items():
        if key not in label_to_odoo_mapping:
            converted_data[key] = value
    
    return converted_data

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
            'company_type','id', 'name', 'email', 'phone', 'mobile', 'website', 'function', 'title', 'lang',
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
        contact['tags'] = process_category_id(contact.get('category_id'))
        # Hapus field category_id yang tidak diperlukan di response
        if 'category_id' in contact:
            del contact['category_id']
            
        # Proses field yang mungkin False menjadi None untuk konsistensi
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id', 'company_type']:
            if contact.get(field) == False:
                contact[field] = None
    
    # Convert field names to label names
    converted_contacts = []
    for contact in contacts:
        converted_contact = convert_odoo_to_label_fields(contact)
        converted_contacts.append(converted_contact)
    
    return ordered_jsonify({
        'success': True,
        'data': converted_contacts,
        'count': len(converted_contacts)
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
        
        # Convert label field names to Odoo field names
        data = convert_label_to_odoo_fields(data)
        
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
        
        # Validasi company type
        valid_company_types = ["person", "company"]
        if 'company_type' in data and data['company_type'] not in valid_company_types:
            return ordered_jsonify({
                'success': False,
                'error': f'company_type must be one of: {valid_company_types}'
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
        
        # Validasi category_id (tags) jika ada - many2many field
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
                
                # Validasi tag ID ada di database
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
            'company_type': data.get('company_type', False),
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
        contact['tags'] = process_category_id(contact.get('category_id'))
        # Hapus field category_id yang tidak diperlukan di response
        if 'category_id' in contact:
            del contact['category_id']
            
        # Proses field yang mungkin False menjadi None untuk konsistensi
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id', 'company_type']:
            if contact.get(field) == False:
                contact[field] = None
        
        # Convert field names to label names
        converted_contact = convert_odoo_to_label_fields(contact)
        
        # Siapkan response message
        message = 'Contact created successfully'
        if country_id_from_state and not data.get('country_id'):
            message += f'. Country automatically set to {converted_contact["country_name"]} based on selected state'
        
        return ordered_jsonify({
            'success': True,
            'data': converted_contact,
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
            'x_studio_your_business', 'x_studio_id', 'vat', 'category_id', 'company_type',
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
    contact['tags'] = process_category_id(contact.get('category_id'))
    # Hapus field category_id yang tidak diperlukan di response
    if 'category_id' in contact:
        del contact['category_id']
        
    # Proses field yang mungkin False menjadi None untuk konsistensi
    for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id', 'company_type']:
        if contact.get(field) == False:
            contact[field] = None
    
    # Convert field names to label names
    converted_contact = convert_odoo_to_label_fields(contact)
    
    return ordered_jsonify({
        'success': True,
        'data': converted_contact
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
        
        # Convert label field names to Odoo field names
        data = convert_label_to_odoo_fields(data)
        
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
        
        # Validasi company type jika ada
        valid_company_types = ["person", "company"]
        if 'company_type' in data and data['company_type'] not in valid_company_types:
            return ordered_jsonify({
                'success': False,
                'error': f'company_type must be one of: {valid_company_types}'
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
        
        # Validasi category_id (tags) jika ada - many2many field
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
                
                # Validasi tag ID ada di database
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
                     'x_studio_your_business', 'x_studio_id', 'vat', 'company_type', 'street', 'street2', 
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
                'x_studio_your_business', 'x_studio_id', 'vat', 'category_id', 'company_type',
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
        contact['tags'] = process_category_id(contact.get('category_id'))
        # Hapus field category_id yang tidak diperlukan di response
        if 'category_id' in contact:
            del contact['category_id']
            
        # Proses field yang mungkin False menjadi None
        for field in ['street', 'street2', 'city', 'zip', 'vat', 'function', 'title', 'lang', 'mobile', 'website', 'x_studio_id', 'company_type']:
            if contact.get(field) == False:
                contact[field] = None
        
        # Convert field names to label names
        converted_contact = convert_odoo_to_label_fields(contact)
        
        return ordered_jsonify({
            'success': True,
            'data': converted_contact,
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





