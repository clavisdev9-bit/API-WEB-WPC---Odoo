"""
Odoo External API - Main Application
"""
from flask import Flask
from config import Config
from app.routes.system_routes import system_bp
from app.routes.contact_routes import contact_bp
from app.routes.quote_routes import quote_bp

# Create Flask app
app = Flask(__name__)

# Register blueprints
app.register_blueprint(system_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(quote_bp)

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
