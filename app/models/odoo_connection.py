"""
Odoo connection and authentication
"""
import xmlrpc.client
from config import Config

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








