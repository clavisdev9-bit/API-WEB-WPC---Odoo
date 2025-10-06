"""
Odoo helper functions for data retrieval
"""
from flask import Response
import json
from collections import OrderedDict

def ordered_jsonify(data):
    """Custom jsonify that preserves field order"""
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json'
    )

def get_states(models, ODOO_DB, uid, ODOO_API_KEY):
    """
    Fungsi untuk mengambil semua data state dari model res.country.state
    
    Args:
        models: Odoo XML-RPC models object
        ODOO_DB: Database name
        uid: User ID
        ODOO_API_KEY: API Key
    
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

def get_countries(models, ODOO_DB, uid, ODOO_API_KEY):
    """
    Fungsi untuk mengambil semua data country dari model res.country
    
    Args:
        models: Odoo XML-RPC models object
        ODOO_DB: Database name
        uid: User ID
        ODOO_API_KEY: API Key
    
    Returns:
        list: Semua data country dengan field id dan name
    """
    # Ambil semua ID country
    country_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, 
        'res.country', 
        'search', 
        [[]]  # Domain kosong = semua records
    )
    
    if not country_ids:
        return []
    
    # Ambil data country dengan field terbatas
    countries = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'res.country',
        'read',
        [country_ids],
        {'fields': ['id', 'name', 'code']}
    )
    
    # Sederhanakan struktur response
    simplified_countries = []
    for country in countries:
        simplified_country = {
            'id': country.get('id'),
            'name': country.get('name'),
            'code': country.get('code')
        }
        simplified_countries.append(simplified_country)
    
    return simplified_countries





