import os

class Config:
    """Configuration class for the Odoo External API"""
    
    # Odoo Configuration
    ODOO_URL = os.getenv('ODOO_URL', "https://edu-wpc.odoo.com/")
    ODOO_DB = os.getenv('ODOO_DB', "edu-wpc")
    ODOO_USERNAME = os.getenv('ODOO_USERNAME', "jeisaganela9@gmail.com")
    ODOO_API_KEY = os.getenv('ODOO_API_KEY', "c7b3897d26ca341c94465bd63e33d0d4e43a54e4")
    
    # Flask Configuration
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
