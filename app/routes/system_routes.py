"""
System routes (health check, home page)
"""
from flask import Blueprint
from app.functions.odoo_functions import ordered_jsonify
from app.models.odoo_connection import uid

# Create blueprint
system_bp = Blueprint('system', __name__)

@system_bp.route('/')
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
                'GET /quotes': 'Get all quotes (sales orders)',
                'GET /quotes/test-fields': 'Test which custom fields are available'
            },
            'system': {
                'GET /health': 'Health check'
            }
        },
        'field_mapping': {
            'pickup_origin': 'x_studio_pickup_origin',
            'pickup_destination': 'x_studio_pickup_destination', 
            'terms_condition': 'x_studio_terms_condition',
            'transportation_method': 'x_studio_transportation_method'
        }
    })

@system_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return ordered_jsonify({
        'status': 'healthy',
        'odoo_connection': 'connected' if uid else 'disconnected',
        'user_id': uid
    })
