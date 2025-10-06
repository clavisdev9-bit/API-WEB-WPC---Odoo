# Struktur Folder API

## Organisasi Kode

```
Quotation API/
├── app/
│   ├── functions/           # Helper functions
│   │   ├── __init__.py
│   │   └── odoo_functions.py
│   ├── models/              # Database connections
│   │   ├── __init__.py
│   │   └── odoo_connection.py
│   └── routes/              # API endpoints
│       ├── __init__.py
│       ├── system_routes.py
│       ├── contact_routes.py
│       └── quote_routes.py
├── main.py                  # Main application file
├── config.py                # Configuration
├── external_api.py          # Old file (can be removed)
└── requirements.txt
```

## Penjelasan Struktur

### 1. `/app/functions/`
- **`odoo_functions.py`**: Helper functions untuk operasi Odoo
  - `ordered_jsonify()`: Custom JSON response
  - `get_states()`: Ambil data state dari Odoo

### 2. `/app/models/`
- **`odoo_connection.py`**: Koneksi dan autentikasi Odoo
  - Setup XML-RPC connection
  - Authentication
  - Global variables untuk models, uid, dll

### 3. `/app/routes/`
- **`system_routes.py`**: System endpoints
  - `GET /` - Home page
  - `GET /health` - Health check

- **`contact_routes.py`**: Contact related endpoints
  - `GET /states` - Get all states
  - `GET /contacts` - Get all contacts
  - `POST /contacts/create` - Create contact
  - `GET /contacts/<id>` - Get contact by ID

- **`quote_routes.py`**: Quote/Sales Order endpoints
  - `POST /quote/create` - Create complete quote
  - `GET /quotes` - Get all quotes

### 4. `/main.py`
- Main Flask application
- Register semua blueprints
- Run application

## Keuntungan Struktur Ini

1. **Separation of Concerns**: Setiap file punya tanggung jawab yang jelas
2. **Modularity**: Mudah untuk menambah/mengubah functionality
3. **Maintainability**: Kode lebih mudah di-maintain dan debug
4. **Scalability**: Mudah untuk menambah route/function baru
5. **Team Development**: Multiple developer bisa kerja di file berbeda

## Cara Menjalankan

```bash
# Ganti dari external_api.py ke main.py
python main.py
```

## Menambah Endpoint Baru

1. **Untuk function baru**: Tambah di `/app/functions/odoo_functions.py`
2. **Untuk route baru**: Tambah di file route yang sesuai atau buat file baru
3. **Untuk model baru**: Tambah di `/app/models/odoo_connection.py`

## Import Pattern

```python
# Import functions
from app.functions.odoo_functions import ordered_jsonify, get_states

# Import models
from app.models.odoo_connection import models, ODOO_DB, uid, ODOO_API_KEY
```
