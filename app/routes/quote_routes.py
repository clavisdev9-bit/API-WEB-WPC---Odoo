"""
Quote and Sales Order related routes
"""
from flask import Blueprint, request
from app.functions.odoo_functions import ordered_jsonify
from app.models.odoo_connection import models, ODOO_DB, uid, ODOO_API_KEY
from functools import wraps

# Create blueprint
quote_bp = Blueprint('quotes', __name__)

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

@quote_bp.route('/quote/create', methods=['POST'])
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
        # Sekarang origin/destination berupa dropdown (many2one) → kirim ID
        required_quote_fields = ['pickup_origin_id', 'pickup_destination_id', 'terms_condition', 'transportation_method']
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
        
        # 1. Validasi/temukan Contact terlebih dahulu untuk menghindari duplikasi
        # Kebijakan dedupe yang lebih ketat:
        # - Jika ada force_create = true → selalu buat baru
        # - Jika ada email → gunakan email sebagai satu-satunya kunci dedupe
        # - Jika tidak ada email tapi ada phone → dedupe hanya jika phone SAMA dan name juga SAMA
        # - Jika tidak ada email & phone → JANGAN dedupe (hindari pakai name saja)
        partner_id = None
        force_create = bool(data.get('force_create', False))
        if not force_create:
            if data.get('email'):
                found = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner', 'search',
                    [[['email', '=', data['email']]]],
                    {'limit': 1}
                )
                if found:
                    partner_id = found[0]
            elif data.get('phone'):
                found = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner', 'search_read',
                    [[['phone', '=', data['phone']]]],
                    {'fields': ['id', 'name'], 'limit': 1}
                )
                if found and str(found[0].get('name', '')).strip().casefold() == str(data['name']).strip().casefold():
                    partner_id = found[0]['id']

        # Tentukan country_id yang akan digunakan
        # Prioritas: country_id dari request > country_id dari state > False
        final_country_id = data.get('country_id', country_id_from_state) if data.get('country_id') else country_id_from_state
        
        contact_action = 'reused'
        if not partner_id:
            # Jika contact tidak ditemukan, otomatis buat baru
            contact_data = {
                'name': data['name'],
                'email': data.get('email', False),
                'phone': data.get('phone', False),
                'x_studio_your_business': data.get('x_studio_your_business', False),
                'country_id': final_country_id,
                'state_id': data.get('state_id', False),
                'company_type': 'person',
                'active': True
            }
            partner_id = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner',
                'create',
                [contact_data]
            )
            contact_action = 'created'
        else:
            # Optional: sinkronkan field baru ke contact yang direuse (tanpa overwrite agresif)
            updates = {}
            if data.get('name'):
                updates['name'] = data['name']
            if data.get('email'):
                updates['email'] = data['email']
            if data.get('phone'):
                updates['phone'] = data['phone']
            if 'x_studio_your_business' in data:
                updates['x_studio_your_business'] = data.get('x_studio_your_business') or False
            if 'state_id' in data:
                updates['state_id'] = data.get('state_id') or False
            if final_country_id:
                updates['country_id'] = final_country_id
            updates['active'] = True
            if updates:
                try:
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_API_KEY,
                        'res.partner', 'write',
                        [partner_id, updates]
                    )
                except Exception:
                    pass
        
        # Normalisasi transportation_method: terima key atau label
        def normalize_transportation(value, model_name='sale.order'):
            try:
                fields_meta = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    model_name, 'fields_get',
                    [], {'attributes': ['selection']}
                )
                sel = fields_meta.get('x_studio_transportation_method', {}).get('selection', [])
                # sel: list of [key, label]
                for key, label in sel:
                    if str(value).lower() == str(key).lower() or str(value).lower() == str(label).lower():
                        return key
            except Exception:
                pass
            return value

        data['transportation_method'] = normalize_transportation(data['transportation_method'])

        # Validasi keberadaan record origin/destination dan kesesuaian transportation method
        # Dapatkan technical model name dari label Studio
        origin_model_rec = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'ir.model', 'search_read',
            [[['name', '=', 'Pickup Origin']]],
            {'fields': ['model'], 'limit': 1}
        )
        dest_model_rec = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'ir.model', 'search_read',
            [[['name', '=', 'Pickup Destination']]],
            {'fields': ['model'], 'limit': 1}
        )
        if not origin_model_rec or not dest_model_rec:
            return ordered_jsonify({
                'success': False,
                'error': 'Lookup models not found in Odoo (Pickup Origin/Destination)'
            }), 500

        origin_model_name = origin_model_rec[0]['model']
        dest_model_name = dest_model_rec[0]['model']

        # Pastikan ID valid
        origin_ok = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            origin_model_name, 'search_count',
            [[['id', '=', int(data['pickup_origin_id'])]]]
        )
        dest_ok = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            dest_model_name, 'search_count',
            [[['id', '=', int(data['pickup_destination_id'])]]]
        )
        if not origin_ok or not dest_ok:
            return ordered_jsonify({
                'success': False,
                'error': 'Invalid pickup_origin_id or pickup_destination_id'
            }), 400

        # Opsional: validasi filter transport method konsisten
        origin_rec = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            origin_model_name, 'read',
            [int(data['pickup_origin_id'])],
            {'fields': ['x_studio_transportation_method']}
        )
        dest_rec = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            dest_model_name, 'read',
            [int(data['pickup_destination_id'])],
            {'fields': ['x_studio_transportation_method']}
        )
        if (origin_rec and origin_rec[0].get('x_studio_transportation_method') != data['transportation_method']) or \
           (dest_rec and dest_rec[0].get('x_studio_transportation_method') != data['transportation_method']):
            return ordered_jsonify({
                'success': False,
                'error': 'Origin/Destination not allowed for selected transportation_method'
            }), 400

        # 2. Buat Sales Order dengan referensi ke contact
        # Tanpa fallback ke note: wajib gunakan field custom yang telah disediakan
        sales_order_data = {
            'partner_id': partner_id,  # Link ke contact yang ditemukan/dibuat
            'state': 'draft',  # Status draft untuk quotation
            'x_studio_transportation_method': data['transportation_method'],
            'x_studio_pickup_origin': data['pickup_origin_id'],
            'x_studio_pickup_destination': data['pickup_destination_id'],
            'x_studio_terms_condition': data['terms_condition']
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
            [partner_id],
            {'fields': ['id', 'name', 'email', 'phone', 'x_studio_your_business', 'country_id', 'state_id']}
        )
        
        # Ambil data sales order dengan field custom (tanpa fallback)
        new_quote = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order',
            'read',
            [new_quote_id],
            {'fields': ['id', 'name', 'partner_id', 'state', 'create_date', 'x_studio_transportation_method', 'x_studio_pickup_origin', 'x_studio_pickup_destination', 'x_studio_terms_condition']}
        )
        
        # Ubah nama field untuk contact
        contact_data = new_contact[0]
        if 'x_studio_your_business' in contact_data:
            contact_data['business_type'] = contact_data['x_studio_your_business']
            del contact_data['x_studio_your_business']
        
        # Tambahkan informasi country dan state yang lebih detail
        if contact_data.get('country_id') and contact_data['country_id'] != False:
            contact_data['country_name'] = contact_data['country_id'][1] if isinstance(contact_data['country_id'], list) else contact_data['country_id']
            # Ubah country_id menjadi integer saja
            if isinstance(contact_data['country_id'], list):
                contact_data['country_id'] = contact_data['country_id'][0]
        else:
            contact_data['country_name'] = None
            contact_data['country_id'] = None
            
        if contact_data.get('state_id') and contact_data['state_id'] != False:
            contact_data['state_name'] = contact_data['state_id'][1] if isinstance(contact_data['state_id'], list) else contact_data['state_id']
            # Ubah state_id menjadi integer saja
            if isinstance(contact_data['state_id'], list):
                contact_data['state_id'] = contact_data['state_id'][0]
        else:
            contact_data['state_name'] = None
            contact_data['state_id'] = None
        
        # Ubah nama field untuk sales order
        quote_data = new_quote[0]
        if 'x_studio_transportation_method' in quote_data:
            quote_data['transportation_method'] = quote_data['x_studio_transportation_method']
            del quote_data['x_studio_transportation_method']
        
        if 'x_studio_pickup_origin' in quote_data:
            quote_data['pickup_origin'] = quote_data['x_studio_pickup_origin']
            del quote_data['x_studio_pickup_origin']
        
        if 'x_studio_pickup_destination' in quote_data:
            quote_data['pickup_destination'] = quote_data['x_studio_pickup_destination']
            del quote_data['x_studio_pickup_destination']
        
        if 'x_studio_terms_condition' in quote_data:
            quote_data['terms_condition'] = quote_data['x_studio_terms_condition']
            del quote_data['x_studio_terms_condition']
        
        # Siapkan response message
        message = 'Quote created successfully'
        if country_id_from_state and not data.get('country_id') and contact_action == 'created':
            message += f'. Country automatically set to {contact_data["country_name"]} based on selected state'
        
        return ordered_jsonify({
            'success': True,
            'data': {
                'contact': contact_data,
                'sales_order': quote_data,
                'contact_action': contact_action
            },
            'message': message
        }), 201
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to create quote',
            'details': str(e)
        }), 500

@quote_bp.route('/quotes', methods=['GET'])
@handle_odoo_errors
def get_all_quotes():
    """Get all sales orders (quotes) with partner email information"""
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
    
    # Ambil data sales order dengan field custom dan partner_id (tanpa state dari sales order)
    quotes = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'sale.order',
        'read',
        [quote_ids],
        {'fields': ['id', 'name', 'partner_id', 'create_date', 'x_studio_transportation_method', 'x_studio_pickup_origin', 'x_studio_pickup_destination', 'x_studio_terms_condition']}
    )
    
    # Ambil informasi partner untuk setiap quote
    partner_ids = [quote['partner_id'][0] for quote in quotes if quote.get('partner_id') and isinstance(quote['partner_id'], list)]
    if partner_ids:
        partners = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner',
            'read',
            [partner_ids],
            {'fields': ['id', 'name', 'email', 'phone', 'state_id']}
        )
        
        # Ambil semua state_id yang unik dari partners
        state_ids = list(set([partner['state_id'][0] for partner in partners if partner.get('state_id')]))
        
        # Ambil informasi state
        states = {}
        if state_ids:
            state_data = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.country.state',
                'read',
                [state_ids],
                {'fields': ['id', 'name', 'code']}
            )
            states = {state['id']: state for state in state_data}
        
        # Buat mapping partner_id -> partner data
        partner_map = {partner['id']: partner for partner in partners}
        
        # Tambahkan informasi partner ke setiap quote
        for quote in quotes:
            if quote.get('partner_id'):
                partner_id = quote['partner_id'][0]
                if partner_id in partner_map:
                    partner = partner_map[partner_id]
                    
                    # Kelompokkan semua informasi partner dalam objek partner_id
                    partner_info = {
                        'id': partner_id,
                        'name': partner['name'],
                        'email': partner['email'],
                        'phone': partner['phone']
                    }
                    
                    # Ambil state dari partner
                    if partner.get('state_id'):
                        state_id = partner['state_id'][0]
                        if state_id in states:
                            partner_info['state'] = states[state_id]['name']
                            partner_info['state_code'] = states[state_id]['code']
                        else:
                            partner_info['state'] = None
                            partner_info['state_code'] = None
                    else:
                        partner_info['state'] = None
                        partner_info['state_code'] = None
                    
                    # Ganti partner_id dengan objek lengkap dan ubah nama key
                    quote['customer'] = partner_info
                    # Hapus partner_id yang lama
                    if 'partner_id' in quote:
                        del quote['partner_id']
                else:
                    # Jika partner tidak ditemukan, set customer menjadi null
                    quote['customer'] = None
                    # Hapus partner_id yang lama
                    if 'partner_id' in quote:
                        del quote['partner_id']
            else:
                # Jika tidak ada partner_id, set customer menjadi null
                quote['customer'] = None
                # Hapus partner_id yang lama
                if 'partner_id' in quote:
                    del quote['partner_id']
    
    # Ubah nama field yang memiliki prefix x_studio_
    for quote in quotes:
        # Ubah x_studio_transportation_method menjadi transportation_method
        if 'x_studio_transportation_method' in quote:
            quote['transportation_method'] = quote['x_studio_transportation_method']
            del quote['x_studio_transportation_method']
        
        # Ubah x_studio_pickup_origin menjadi pickup_origin
        if 'x_studio_pickup_origin' in quote:
            quote['pickup_origin'] = quote['x_studio_pickup_origin']
            del quote['x_studio_pickup_origin']
        
        # Ubah x_studio_pickup_destination menjadi pickup_destination
        if 'x_studio_pickup_destination' in quote:
            quote['pickup_destination'] = quote['x_studio_pickup_destination']
            del quote['x_studio_pickup_destination']
        
        # Ubah x_studio_terms_condition menjadi terms_condition
        if 'x_studio_terms_condition' in quote:
            quote['terms_condition'] = quote['x_studio_terms_condition']
            del quote['x_studio_terms_condition']
    
    return ordered_jsonify({
        'success': True,
        'data': quotes,
        'count': len(quotes)
    })

# ===================== LOOKUP ENDPOINTS =====================

@quote_bp.route('/lookups/pickup-origins', methods=['GET'])
@handle_odoo_errors
def get_pickup_origins():
    """Ambil list Pickup Origin terfilter oleh transportation method (selection)."""
    transportation = request.args.get('transportation')
    if not transportation:
        return ordered_jsonify({
            'success': False,
            'error': 'Query param transportation is required'
        }), 400

    # Cari technical model name berdasarkan display name "Pickup Origin"
    origin_model = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'ir.model', 'search_read',
        [[['name', '=', 'Pickup Origin']]],
        {'fields': ['model'], 'limit': 1}
    )
    if not origin_model:
        return ordered_jsonify({'success': True, 'data': [], 'count': 0})

    model_name = origin_model[0]['model']

    # Deteksi field yang tersedia secara dinamis
    fields_meta = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        model_name, 'fields_get',
        [], {'attributes': ['type', 'string']}
    )

    def pick_field(candidates):
        for cand in candidates:
            if cand in fields_meta:
                return cand
        return None

    # Berdasarkan struktur terbaru: x_name (Pickup Address), x_studio_country, x_studio_pickup_code, x_studio_transportation_method
    address_field = pick_field(['x_name', 'x_studio_pickup_address', 'x_studio_address', 'x_studio_address_pickup', 'address', 'name'])
    country_field = pick_field(['x_studio_country', 'country_id', 'x_studio_country_id'])
    pickup_code_field = pick_field(['x_studio_pickup_code'])
    transport_field = pick_field(['x_studio_transportation_method', 'transportation_method', 'x_transportation_method', 'x_transportation'])

    # Jangan minta alias; tidak perlu display_name
    fields_to_read = ['id']
    if address_field:
        fields_to_read.append(address_field)
    if country_field:
        fields_to_read.append(country_field)
    if pickup_code_field:
        fields_to_read.append(pickup_code_field)

    domain = []
    if transport_field:
        domain.append([transport_field, '=', transportation])

    records = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        model_name, 'search_read',
        [domain],
        {'fields': fields_to_read}
    )

    # Rapikan country menjadi string nama dan ubah nama field
    for rec in records:
        # Hapus display_name jika terbawa
        if 'display_name' in rec:
            del rec['display_name']

        # Normalisasi alamat
        if address_field and address_field in rec:
            rec['pickup_origin_address'] = rec[address_field]
            if address_field in rec:
                del rec[address_field]
        
        # Normalisasi country
        if country_field and country_field in rec:
            rec['country'] = rec[country_field]
            if country_field in rec:
                del rec[country_field]

        # Tambahkan pickup_code jika ada
        if pickup_code_field and pickup_code_field in rec:
            rec['pickup_code'] = rec[pickup_code_field]
            if pickup_code_field in rec:
                del rec[pickup_code_field]
            
            # Tambahkan country_name
            if isinstance(rec.get('country'), list) and len(rec['country']) == 2:
                rec['country_name'] = rec['country'][1]
            else:
                rec['country_name'] = None
        else:
            rec['country'] = None
            rec['country_name'] = None

    return ordered_jsonify({'success': True, 'data': records, 'count': len(records)})


@quote_bp.route('/lookups/pickup-destinations', methods=['GET'])
@handle_odoo_errors
def get_pickup_destinations():
    """Ambil list Pickup Destination terfilter oleh transportation method (selection)."""
    transportation = request.args.get('transportation')
    if not transportation:
        return ordered_jsonify({
            'success': False,
            'error': 'Query param transportation is required'
        }), 400

    # Cari technical model name berdasarkan display name "Pickup Destination"
    dest_model = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'ir.model', 'search_read',
        [[['name', '=', 'Pickup Destination']]],
        {'fields': ['model'], 'limit': 1}
    )
    if not dest_model:
        return ordered_jsonify({'success': True, 'data': [], 'count': 0})

    model_name = dest_model[0]['model']

    # Deteksi field yang tersedia secara dinamis
    fields_meta = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        model_name, 'fields_get',
        [], {'attributes': ['type', 'string']}
    )

    def pick_field(candidates):
        for cand in candidates:
            if cand in fields_meta:
                return cand
        return None

    # Berdasarkan struktur terbaru: x_name (Pickup Address), x_studio_country, x_studio_pickup_code, x_studio_transportation_method
    address_field = pick_field(['x_name', 'x_studio_pickup_address', 'x_studio_address', 'x_studio_address_pickup', 'address', 'name'])
    country_field = pick_field(['x_studio_country', 'country_id', 'x_studio_country_id'])
    pickup_code_field = pick_field(['x_studio_pickup_code'])
    transport_field = pick_field(['x_studio_transportation_method', 'transportation_method', 'x_transportation_method', 'x_transportation'])

    # Jangan minta alias; tidak perlu display_name
    fields_to_read = ['id']
    if address_field:
        fields_to_read.append(address_field)
    if country_field:
        fields_to_read.append(country_field)
    if pickup_code_field:
        fields_to_read.append(pickup_code_field)

    domain = []
    if transport_field:
        domain.append([transport_field, '=', transportation])

    records = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        model_name, 'search_read',
        [domain],
        {'fields': fields_to_read}
    )

    # Rapikan country menjadi string nama dan ubah nama field
    for rec in records:
        # Hapus display_name jika terbawa
        if 'display_name' in rec:
            del rec['display_name']

        # Normalisasi alamat
        if address_field and address_field in rec:
            rec['pickup_destination_address'] = rec[address_field]
            if address_field in rec:
                del rec[address_field]
        
        # Normalisasi country
        if country_field and country_field in rec:
            rec['country'] = rec[country_field]
            if country_field in rec:
                del rec[country_field]

        # Tambahkan pickup_code jika ada
        if pickup_code_field and pickup_code_field in rec:
            rec['pickup_code'] = rec[pickup_code_field]
            if pickup_code_field in rec:
                del rec[pickup_code_field]
            
            # Tambahkan country_name
            if isinstance(rec.get('country'), list) and len(rec['country']) == 2:
                rec['country_name'] = rec['country'][1]
            else:
                rec['country_name'] = None
        else:
            rec['country'] = None
            rec['country_name'] = None

    return ordered_jsonify({'success': True, 'data': records, 'count': len(records)})

@quote_bp.route('/quotes/test-fields', methods=['GET'])
@handle_odoo_errors
def test_quote_fields():
    """Test endpoint untuk mengecek field custom yang tersedia"""
    try:
        # Coba baca field custom satu per satu
        test_quote_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY, 
            'sale.order', 
            'search', 
            [[]],  # Ambil quote pertama yang ada
            {'limit': 1}
        )
        
        if not test_quote_id:
            return ordered_jsonify({
                'success': True,
                'message': 'No quotes found to test fields',
                'available_fields': []
            })
        
        available_fields = []
        test_fields = [
            'x_studio_transportation_method',
            'x_studio_pickup_origin', 
            'x_studio_pickup_destination',
            'x_studio_terms_condition'
        ]
        
        for field in test_fields:
            try:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'sale.order',
                    'read',
                    [test_quote_id[0]],
                    {'fields': [field]}
                )
                available_fields.append(field)
            except:
                pass
        
        return ordered_jsonify({
            'success': True,
            'message': 'Field availability test completed',
            'available_fields': available_fields,
            'unavailable_fields': [f for f in test_fields if f not in available_fields]
        })
        
    except Exception as e:
        return ordered_jsonify({
            'success': False,
            'error': 'Failed to test fields',
            'details': str(e)
        }), 500

@quote_bp.route('/lookups/transportation-methods', methods=['GET'])
@handle_odoo_errors
def get_transportation_methods():
    """Ambil opsi selection dari field Transportation Method pada sale.order.

    Response: { success, data: [{ value, label }], count }
    """
    # 1) Coba baca dari model studio khusus: x_transportation
    try:
        records = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'x_transportation', 'search_read',
            [[]], {'fields': ['id', 'name', 'display_name']}
        )
        if records:
            options = []
            for rec in records:
                label = rec.get('display_name') or rec.get('name') or ''
                value = rec.get('name') or label
                options.append({'value': value, 'id': rec.get('id')})
            return ordered_jsonify({'success': True, 'data': options, 'count': len(options)})
    except Exception:
        # Abaikan, lanjut ke fallback
        pass

    # 2) Fallback: Baca metadata field selection dari sale.order
    try:
        fields_meta = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'fields_get',
            [], {'attributes': ['selection']}
        )
        selection = fields_meta.get('x_studio_transportation_method', {}).get('selection', [])
        options = []
        for item in selection:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                options.append({'value': item[0]})
        return ordered_jsonify({'success': True, 'data': options, 'count': len(options)})
    except Exception as e:
        return ordered_jsonify({'success': False, 'error': 'Failed to fetch transportation methods', 'details': str(e)}), 500
