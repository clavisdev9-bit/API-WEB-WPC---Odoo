"""
Quote and Sales Order related routes
"""
from flask import Blueprint, request
from app.functions.odoo_functions import ordered_jsonify
from app.models.odoo_connection import models, ODOO_DB, uid, ODOO_API_KEY
from functools import wraps
import ast

# Create blueprint
quote_bp = Blueprint('quotes', __name__)

def _safe_lower(value):
    try:
        return str(value or '').strip().casefold()
    except Exception:
        return ''

def _parse_domain(val):
    """
    Parse domain value from fields_get (could be list/tuple/string).
    Returns list.
    """
    if isinstance(val, (list, tuple)):
        return list(val)
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, (list, tuple)):
                return list(parsed)
        except Exception:
            pass
    return []

def get_sale_order_field_map():
    """
    Deteksi nama teknis field di sale.order berdasarkan label (string).
    Mengembalikan dict:
      {
        'commodity': <field_name>,
        'uom': <field_name>,
        'qty': <field_name>,
        'kgs_chg': <field_name>,
        'kgs_wt': <field_name>,
        'ratio': <field_name>,
      }
    Dengan fallback ke nama yang selama ini digunakan jika tidak ditemukan.
    """
    # Default fallback (nama teknis historis)
    field_map = {
        'commodity': 'x_studio_commodity',
        'uom': 'x_studio_many2one_field_1ef_1j58pa43n',
        'qty': 'x_studio_qty',
        'kgs_chg': 'x_studio_kgs_chg_1',
        'kgs_wt': 'x_studio_kgs_wt',
        'ratio': 'x_studio_ratio',
    }
    try:
        fields_meta = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'fields_get',
            [], {'attributes': ['string', 'type', 'relation']}
        )
        # Kandidat label (lowercase) untuk tiap field
        label_candidates = {
            'commodity': ['commodity', 'description of goods', 'commodity code'],
            'uom': ['unit of measure', 'uom', 'uom type'],
            'qty': ['qty', 'quantity', 'pcs'],
            'kgs_chg': ['kgs chg', 'chargeable weight', 'chg wt', 'chg'],
            'kgs_wt': ['kgs wt', 'actual weight', 'weight'],
            'ratio': ['ratio', 'dim factor', 'volumetric ratio'],
        }
        # Pemetaan berdasarkan label string
        for fname, meta in (fields_meta or {}).items():
            label = _safe_lower(meta.get('string'))
            if not label:
                continue
            # Coba cocokkan
            for key, candidates in label_candidates.items():
                if any(lbl in label for lbl in candidates):
                    # Validasi tipe dasar wajar (tidak ketat agar fleksibel)
                    field_map[key] = fname
        return field_map
    except Exception:
        # Jika gagal, pakai fallback
        return field_map

def get_pickup_fields_meta():
    """
    Dapatkan metadata field pickup origin/destination (field name, relation model, domain).
    Menggunakan label untuk deteksi dinamis; fallback ke nama historis.
    """
    defaults = {
        'origin': {
            'field': 'x_studio_pickup_origin',
            'relation': None,
            'domain': []
        },
        'destination': {
            'field': 'x_studio_pickup_destination',
            'relation': None,
            'domain': []
        }
    }
    try:
        fields_meta = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'fields_get',
            [], {'attributes': ['string', 'relation', 'domain']}
        )

        def match_field(candidates, default_key):
            for fname, meta in (fields_meta or {}).items():
                label = _safe_lower(meta.get('string'))
                if not label:
                    continue
                for cand in candidates:
                    if cand in label:
                        relation = meta.get('relation')
                        domain = _parse_domain(meta.get('domain', []))
                        return {
                            'field': fname,
                            'relation': relation,
                            'domain': domain
                        }
            return defaults[default_key]

        origin_meta = match_field(['pickup origin', 'origin'], 'origin')
        dest_meta = match_field(['pickup destination', 'destination'], 'destination')

        # Pastikan domain berbentuk list
        origin_meta['domain'] = _parse_domain(origin_meta.get('domain', []))
        dest_meta['domain'] = _parse_domain(dest_meta.get('domain', []))

        # Jika relation tidak ditemukan, fallback ke defaults
        if not origin_meta.get('relation'):
            origin_meta['relation'] = defaults['origin']['relation']
        if not dest_meta.get('relation'):
            dest_meta['relation'] = defaults['destination']['relation']

        return {
            'origin': origin_meta,
            'destination': dest_meta
        }
    except Exception:
        return defaults

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
        required_contact_fields = ['name', 'email']
        for field in required_contact_fields:
            if field not in data or not data.get(field):
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
        # Logika dedupe:
        # - Jika ada force_create = true → selalu buat baru
        # - Cek name dulu (case-insensitive, trim whitespace)
        # - Jika name sama, lanjut cek email
        # - Jika name DAN email sama → reuse contact yang ada
        # - Jika name sama tapi email beda → create baru (orang berbeda)
        # - Jika name tidak ketemu → create baru
        partner_id = None
        force_create = bool(data.get('force_create', False))
        if not force_create and data.get('name') and data.get('email'):
            # Normalisasi name untuk matching (case-insensitive, trim)
            search_name = str(data['name']).strip()
            search_email = str(data['email']).strip().lower()
            
            # Cari berdasarkan name (case-insensitive)
            found = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'search_read',
                [[['name', 'ilike', search_name]]],
                {'fields': ['id', 'name', 'email'], 'limit': 10}  # Ambil beberapa untuk cek exact match
            )
            
            if found:
                # Cek exact match name (case-insensitive) dan email
                for partner in found:
                    partner_name = str(partner.get('name', '')).strip()
                    partner_email = str(partner.get('email', '')).strip().lower() if partner.get('email') else ''
                    
                    # Exact match name (case-insensitive) dan email
                    if partner_name.lower() == search_name.lower() and partner_email == search_email:
                        partner_id = partner['id']
                        break

        # Tentukan country_id yang akan digunakan
        # Prioritas: country_id dari request > country_id dari state > False
        final_country_id = data.get('country_id', country_id_from_state) if data.get('country_id') else country_id_from_state
        
        contact_action = 'reused'
        if not partner_id:
            # Jika contact tidak ditemukan, otomatis buat baru
            # Hanya kirim field yang tidak None
            contact_data = {
                'name': data['name'],
                'company_type': 'person',
                'active': True
            }
            # Tambahkan field optional hanya jika ada nilainya
            if data.get('email'):
                contact_data['email'] = data['email']
            if data.get('phone'):
                contact_data['phone'] = data['phone']
            if data.get('x_studio_your_business'):
                contact_data['x_studio_your_business'] = data['x_studio_your_business']
            if final_country_id:
                contact_data['country_id'] = final_country_id
            if data.get('state_id'):
                contact_data['state_id'] = data['state_id']
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
            if 'x_studio_your_business' in data and data.get('x_studio_your_business'):
                updates['x_studio_your_business'] = data['x_studio_your_business']
            if 'state_id' in data and data.get('state_id'):
                updates['state_id'] = data['state_id']
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

        # Ambil metadata pickup origin/destination (field name, relation, domain)
        pickup_meta = get_pickup_fields_meta()
        origin_field_meta = pickup_meta.get('origin', {})
        dest_field_meta = pickup_meta.get('destination', {})

        origin_model_name = origin_field_meta.get('relation')
        dest_model_name = dest_field_meta.get('relation')

        # Validasi keberadaan record origin/destination dan kesesuaian transportation method
        if not origin_model_name or not dest_model_name:
            return ordered_jsonify({
                'success': False,
                'error': 'Pickup field relation not found in Odoo'
            }), 500

        def build_domain(base_domain, extra_condition):
            domain = []
            if base_domain:
                domain.extend(list(base_domain))
            domain.append(extra_condition)
            return domain

        # Pastikan ID valid sesuai domain field
        origin_domain = build_domain(
            origin_field_meta.get('domain', []),
            ['id', '=', int(data['pickup_origin_id'])]
        )
        dest_domain = build_domain(
            dest_field_meta.get('domain', []),
            ['id', '=', int(data['pickup_destination_id'])]
        )

        origin_ok = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            origin_model_name, 'search_count',
            [origin_domain]
        )
        dest_ok = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            dest_model_name, 'search_count',
            [dest_domain]
        )
        if not origin_ok or not dest_ok:
            return ordered_jsonify({
                'success': False,
                'error': 'Invalid pickup_origin_id or pickup_destination_id'
            }), 400

        def read_transport_method(model_name, record_id):
            try:
                rec = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    model_name, 'read',
                    [int(record_id)],
                    {'fields': ['x_studio_transportation_method']}
                )
                return rec[0] if rec else {}
            except Exception:
                return {}

        origin_rec = read_transport_method(origin_model_name, data['pickup_origin_id'])
        dest_rec = read_transport_method(dest_model_name, data['pickup_destination_id'])

        if (origin_rec and origin_rec.get('x_studio_transportation_method') not in (False, data['transportation_method'])) or \
           (dest_rec and dest_rec.get('x_studio_transportation_method') not in (False, data['transportation_method'])):
            return ordered_jsonify({
                'success': False,
                'error': 'Origin/Destination not allowed for selected transportation_method'
            }), 400

        # 2. Buat Sales Order dengan referensi ke contact
        # Tanpa fallback ke note: wajib gunakan field custom yang telah disediakan
        origin_field_name = origin_field_meta.get('field', 'x_studio_pickup_origin')
        dest_field_name = dest_field_meta.get('field', 'x_studio_pickup_destination')
        sales_order_data = {
            'partner_id': partner_id,  # Link ke contact yang ditemukan/dibuat
            'state': 'draft',  # Status draft untuk quotation
            'x_studio_transportation_method': data['transportation_method'],
            origin_field_name: data['pickup_origin_id'],
            dest_field_name: data['pickup_destination_id'],
            'x_studio_terms_condition': data['terms_condition']
        }
        
        # Optional: tambahkan field-field baru (commodity, uom, qty, kgs_chg, kgs_wt, ratio)
        # Hanya kirim field yang benar-benar ada nilainya (bukan None, bukan False untuk many2one)
        # Dan pastikan field tersebut ada di Odoo sebelum dikirim
        so_field_map = get_sale_order_field_map()
        try:
            # Validasi field yang ada di Odoo
            available_fields = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'sale.order', 'fields_get',
                [], {}
            )
        except Exception:
            available_fields = {}
        
        # Hanya tambahkan field jika field tersebut ada di Odoo
        if 'commodity_id' in data and data.get('commodity_id') not in (None, False, ''):
            field_name = so_field_map.get('commodity')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data['commodity_id']
        if 'uom_id' in data and data.get('uom_id') not in (None, False, ''):
            field_name = so_field_map.get('uom')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data['uom_id']
        if 'qty' in data and data.get('qty') is not None:
            field_name = so_field_map.get('qty')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data.get('qty', 0)
        if 'kgs_chg' in data and data.get('kgs_chg') is not None:
            field_name = so_field_map.get('kgs_chg')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data.get('kgs_chg', 0)
        if 'kgs_wt' in data and data.get('kgs_wt') is not None:
            field_name = so_field_map.get('kgs_wt')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data.get('kgs_wt', 0)
        if 'ratio' in data and data.get('ratio') is not None:
            field_name = so_field_map.get('ratio')
            if field_name and field_name in available_fields:
                sales_order_data[field_name] = data.get('ratio', 0.0)
        
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
        read_fields = ['id', 'name', 'partner_id', 'state', 'create_date', 'x_studio_transportation_method', origin_field_name, dest_field_name, 'x_studio_terms_condition', so_field_map['commodity'], so_field_map['uom'], so_field_map['qty'], so_field_map['kgs_chg'], so_field_map['kgs_wt'], so_field_map['ratio']]
        new_quote = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order',
            'read',
            [new_quote_id],
            {'fields': read_fields}
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
        
        if origin_field_name in quote_data:
            quote_data['pickup_origin'] = quote_data[origin_field_name]
            del quote_data[origin_field_name]
        
        if dest_field_name in quote_data:
            quote_data['pickup_destination'] = quote_data[dest_field_name]
            del quote_data[dest_field_name]
        
        if 'x_studio_terms_condition' in quote_data:
            quote_data['terms_condition'] = quote_data['x_studio_terms_condition']
            del quote_data['x_studio_terms_condition']
        
        # Normalisasi field-field baru
        if so_field_map['commodity'] in quote_data:
            # Handle many2one: ambil ID saja jika berupa list [id, name]
            if isinstance(quote_data[so_field_map['commodity']], list) and len(quote_data[so_field_map['commodity']]) >= 1:
                quote_data['commodity'] = quote_data[so_field_map['commodity']][0]
            else:
                quote_data['commodity'] = quote_data[so_field_map['commodity']]
            del quote_data[so_field_map['commodity']]
        if so_field_map['uom'] in quote_data:
            # Handle many2one: kembalikan NAMA jika berupa list [id, name]
            if isinstance(quote_data[so_field_map['uom']], list):
                if len(quote_data[so_field_map['uom']]) >= 2:
                    quote_data['uom'] = quote_data[so_field_map['uom']][1]
                elif len(quote_data[so_field_map['uom']]) >= 1:
                    # Fallback ke id jika nama tidak tersedia
                    quote_data['uom'] = quote_data[so_field_map['uom']][0]
                else:
                    quote_data['uom'] = None
            else:
                quote_data['uom'] = quote_data[so_field_map['uom']]
            del quote_data[so_field_map['uom']]
        if so_field_map['qty'] in quote_data:
            quote_data['qty'] = quote_data[so_field_map['qty']]
            del quote_data[so_field_map['qty']]
        if so_field_map['kgs_chg'] in quote_data:
            quote_data['kgs_chg'] = quote_data[so_field_map['kgs_chg']]
            del quote_data[so_field_map['kgs_chg']]
        if so_field_map['kgs_wt'] in quote_data:
            quote_data['kgs_wt'] = quote_data[so_field_map['kgs_wt']]
            del quote_data[so_field_map['kgs_wt']]
        if so_field_map['ratio'] in quote_data:
            quote_data['ratio'] = quote_data[so_field_map['ratio']]
            del quote_data[so_field_map['ratio']]
        
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
    so_field_map = get_sale_order_field_map()
    pickup_meta = get_pickup_fields_meta()
    origin_field_name = pickup_meta.get('origin', {}).get('field', 'x_studio_pickup_origin')
    dest_field_name = pickup_meta.get('destination', {}).get('field', 'x_studio_pickup_destination')
    read_fields = ['id', 'name', 'partner_id', 'create_date', 'x_studio_transportation_method', origin_field_name, dest_field_name, 'x_studio_terms_condition', so_field_map['commodity'], so_field_map['uom'], so_field_map['qty'], so_field_map['kgs_chg'], so_field_map['kgs_wt'], so_field_map['ratio']]
    quotes = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'sale.order',
        'read',
        [quote_ids],
        {'fields': read_fields}
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
        
        # Ubah pickup origin/destination menjadi nama generik
        if origin_field_name in quote:
            quote['pickup_origin'] = quote[origin_field_name]
            del quote[origin_field_name]
        
        if dest_field_name in quote:
            quote['pickup_destination'] = quote[dest_field_name]
            del quote[dest_field_name]
        
        # Ubah x_studio_terms_condition menjadi terms_condition
        if 'x_studio_terms_condition' in quote:
            quote['terms_condition'] = quote['x_studio_terms_condition']
            del quote['x_studio_terms_condition']
        
        # Normalisasi field-field baru
        if so_field_map['commodity'] in quote:
            # Handle many2one: ambil ID saja jika berupa list [id, name]
            if isinstance(quote[so_field_map['commodity']], list) and len(quote[so_field_map['commodity']]) >= 1:
                quote['commodity'] = quote[so_field_map['commodity']][0]
            else:
                quote['commodity'] = quote[so_field_map['commodity']]
            del quote[so_field_map['commodity']]
        if so_field_map['uom'] in quote:
            # Handle many2one: kembalikan NAMA jika berupa list [id, name]
            if isinstance(quote[so_field_map['uom']], list):
                if len(quote[so_field_map['uom']]) >= 2:
                    quote['uom'] = quote[so_field_map['uom']][1]
                elif len(quote[so_field_map['uom']]) >= 1:
                    quote['uom'] = quote[so_field_map['uom']][0]
                else:
                    quote['uom'] = None
            else:
                quote['uom'] = quote[so_field_map['uom']]
            del quote[so_field_map['uom']]
        if so_field_map['qty'] in quote:
            quote['qty'] = quote[so_field_map['qty']]
            del quote[so_field_map['qty']]
        if so_field_map['kgs_chg'] in quote:
            quote['kgs_chg'] = quote[so_field_map['kgs_chg']]
            del quote[so_field_map['kgs_chg']]
        if so_field_map['kgs_wt'] in quote:
            quote['kgs_wt'] = quote[so_field_map['kgs_wt']]
            del quote[so_field_map['kgs_wt']]
        if so_field_map['ratio'] in quote:
            quote['ratio'] = quote[so_field_map['ratio']]
            del quote[so_field_map['ratio']]
    
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

    pickup_meta = get_pickup_fields_meta()
    origin_meta = pickup_meta.get('origin', {})
    model_name = origin_meta.get('relation')
    if not model_name:
        return ordered_jsonify({'success': True, 'data': [], 'count': 0})

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

    domain = _parse_domain(origin_meta.get('domain', []))
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

    pickup_meta = get_pickup_fields_meta()
    dest_meta = pickup_meta.get('destination', {})
    model_name = dest_meta.get('relation')
    if not model_name:
        return ordered_jsonify({'success': True, 'data': [], 'count': 0})

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

    domain = _parse_domain(dest_meta.get('domain', []))
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
        pickup_meta = get_pickup_fields_meta()
        origin_field_name = pickup_meta.get('origin', {}).get('field', 'x_studio_pickup_origin')
        dest_field_name = pickup_meta.get('destination', {}).get('field', 'x_studio_pickup_destination')
        test_fields = [
            'x_studio_transportation_method',
            origin_field_name,
            dest_field_name,
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

@quote_bp.route('/lookups/commodities', methods=['GET'])
@handle_odoo_errors
def get_commodities():
    """Ambil list Commodity untuk dropdown.
    
    Response: { success, data: [{ id, name }], count }
    """
    try:
        # Deteksi field commodity dari sale.order
        so_field_map = get_sale_order_field_map()
        commodity_field = so_field_map.get('commodity')
        
        if not commodity_field:
            return ordered_jsonify({'success': True, 'data': [], 'count': 0})
        
        # Ambil metadata field untuk dapatkan relation model
        fields_meta = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'fields_get',
            [commodity_field], {'attributes': ['relation', 'string']}
        )
        
        relation_model = fields_meta.get(commodity_field, {}).get('relation')
        if not relation_model:
            return ordered_jsonify({'success': True, 'data': [], 'count': 0})
        
        # Ambil semua record dari model relation
        # Cek field yang tersedia di model
        try:
            model_fields = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                relation_model, 'fields_get',
                [], {'attributes': ['store', 'type']}
            )
            # Tentukan field yang akan di-request (hanya yang ada)
            fields_to_read = ['id']
            if 'name' in model_fields:
                fields_to_read.append('name')
            if 'display_name' in model_fields:
                fields_to_read.append('display_name')
            
            # Tentukan order by (hanya field yang stored, bukan computed)
            order_by = None
            if 'name' in model_fields:
                # Cek apakah name stored (bukan computed)
                name_meta = model_fields.get('name', {})
                if name_meta.get('store', True):  # Default True jika tidak ada info
                    order_by = 'name'
            # Jangan pakai display_name untuk order karena biasanya computed
            if not order_by and 'id' in model_fields:
                order_by = 'id'
        except Exception:
            fields_to_read = ['id']
            order_by = None
        
        # Build search_read params
        search_params = {'fields': fields_to_read}
        if order_by:
            search_params['order'] = order_by
        
        records = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            relation_model, 'search_read',
            [[]],
            search_params
        )
        
        # Format response
        options = []
        for rec in records:
            name = rec.get('display_name') or rec.get('name') or ''
            options.append({
                'id': rec.get('id'),
                'name': name
            })
        
        return ordered_jsonify({'success': True, 'data': options, 'count': len(options)})
    
    except Exception as e:
        return ordered_jsonify({'success': False, 'error': 'Failed to fetch commodities', 'details': str(e)}), 500

@quote_bp.route('/lookups/uoms', methods=['GET'])
@handle_odoo_errors
def get_uoms():
    """Ambil list Unit of Measure (UOM) untuk dropdown.
    
    Response: { success, data: [{ id, name }], count }
    """
    try:
        # Deteksi field UOM dari sale.order
        so_field_map = get_sale_order_field_map()
        uom_field = so_field_map.get('uom')
        
        if not uom_field:
            return ordered_jsonify({'success': True, 'data': [], 'count': 0})
        
        # Ambil metadata field untuk dapatkan relation model
        fields_meta = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'fields_get',
            [uom_field], {'attributes': ['relation', 'string']}
        )
        
        relation_model = fields_meta.get(uom_field, {}).get('relation')
        if not relation_model:
            return ordered_jsonify({'success': True, 'data': [], 'count': 0})
        
        # Ambil semua record dari model relation (biasanya uom.uom)
        # Cek field yang tersedia di model
        try:
            model_fields = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                relation_model, 'fields_get',
                [], {'attributes': ['store', 'type']}
            )
            # Tentukan field yang akan di-request (hanya yang ada)
            fields_to_read = ['id']
            if 'name' in model_fields:
                fields_to_read.append('name')
            if 'display_name' in model_fields:
                fields_to_read.append('display_name')
            
            # Tentukan order by (hanya field yang stored, bukan computed)
            order_by = None
            if 'name' in model_fields:
                # Cek apakah name stored (bukan computed)
                name_meta = model_fields.get('name', {})
                if name_meta.get('store', True):  # Default True jika tidak ada info
                    order_by = 'name'
            # Jangan pakai display_name untuk order karena biasanya computed
            if not order_by and 'id' in model_fields:
                order_by = 'id'
        except Exception:
            fields_to_read = ['id']
            order_by = None
        
        # Build search_read params
        search_params = {'fields': fields_to_read}
        if order_by:
            search_params['order'] = order_by
        
        records = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            relation_model, 'search_read',
            [[]],
            search_params
        )
        
        # Format response
        options = []
        for rec in records:
            name = rec.get('display_name') or rec.get('name') or ''
            options.append({
                'id': rec.get('id'),
                'name': name
            })
        
        return ordered_jsonify({'success': True, 'data': options, 'count': len(options)})
    
    except Exception as e:
        return ordered_jsonify({'success': False, 'error': 'Failed to fetch UOMs', 'details': str(e)}), 500
