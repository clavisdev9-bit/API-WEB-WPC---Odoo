# Odoo External API

API untuk mengakses data Odoo secara eksternal menggunakan Flask dan XML-RPC.

## Fitur

- ✅ Mengambil data contact dari Odoo
- ✅ Filter berdasarkan perusahaan
- ✅ Pencarian contact berdasarkan nama
- ✅ Mengambil contact berdasarkan ID
- ✅ Error handling yang baik
- ✅ Response format JSON yang konsisten

## Instalasi

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (opsional):
```bash
export ODOO_URL="https://your-odoo-instance.com/"
export ODOO_DB="your_database"
export ODOO_USERNAME="your_email@example.com"
export ODOO_API_KEY="your_api_key"
```

3. Jalankan aplikasi:
```bash
python external_api.py
```

API akan berjalan di `http://localhost:5000`

## Endpoints

### 1. Home
- **URL**: `/`
- **Method**: `GET`
- **Description**: Informasi API dan daftar endpoint

### 2. Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Description**: Cek status koneksi ke Odoo

### 3. Get All Contacts
- **URL**: `/contacts`
- **Method**: `GET`
- **Parameters**:
  - `limit` (int, optional): Jumlah maksimal data (default: 10)
  - `fields` (string, optional): Field yang ingin ditampilkan, dipisahkan koma
  - `order_by` (string, optional): Field untuk mengurutkan data (default: 'name')

**Contoh**:
```
GET /contacts?limit=5&fields=id,name,email&order_by=name
```

### 4. Get Company Contacts
- **URL**: `/contacts/company`
- **Method**: `GET`
- **Parameters**:
  - `limit` (int, optional): Jumlah maksimal data (default: 10)
  - `fields` (string, optional): Field yang ingin ditampilkan, dipisahkan koma
  - `order_by` (string, optional): Field untuk mengurutkan data (default: 'name')

**Contoh**:
```
GET /contacts/company?limit=3&order_by=name
```

### 5. Search Contacts
- **URL**: `/contacts/search`
- **Method**: `GET`
- **Parameters**:
  - `q` (string, required): Kata kunci pencarian
  - `limit` (int, optional): Jumlah maksimal data (default: 10)
  - `fields` (string, optional): Field yang ingin ditampilkan, dipisahkan koma
  - `order_by` (string, optional): Field untuk mengurutkan data (default: 'name')

**Contoh**:
```
GET /contacts/search?q=John&limit=5&order_by=name
```

### 6. Get Contact by ID
- **URL**: `/contacts/{id}`
- **Method**: `GET`
- **Parameters**:
  - `fields` (string, optional): Field yang ingin ditampilkan, dipisahkan koma

**Contoh**:
```
GET /contacts/123?fields=id,name,email
```

## Response Format

Semua response menggunakan format JSON dengan struktur:

```json
{
  "success": true,
  "data": [...],
  "count": 5,
  "limit": 10,
  "order_by": "name"
}
```

### Urutan Field

Field dalam response JSON akan selalu ditampilkan dalam urutan yang konsisten sesuai dengan parameter `fields` yang diberikan. Jika tidak ada parameter `fields`, maka urutan default adalah:

1. `id`
2. `name` 
3. `email`
4. `phone`
5. `is_company`
6. `street`
7. `city`
8. `country_id`
9. `vat`


Untuk error:
```json
{
  "success": false,
  "error": "Error message",
  "message": "An error occurred while processing the request"
}
```

## Contoh Penggunaan

### Menggunakan curl:

```bash
# Get all contacts
curl http://localhost:5000/contacts

# Get company contacts
curl http://localhost:5000/contacts/company

# Search contacts
curl "http://localhost:5000/contacts/search?q=John"

# Get specific contact
curl http://localhost:5000/contacts/123
```

### Menggunakan Python requests:

```python
import requests

# Get all contacts
response = requests.get('http://localhost:5000/contacts')
data = response.json()
print(data)

# Search contacts
response = requests.get('http://localhost:5000/contacts/search', params={'q': 'John'})
data = response.json()
print(data)
```

## Konfigurasi

Edit file `config.py` atau set environment variables untuk mengubah konfigurasi:

- `ODOO_URL`: URL instance Odoo
- `ODOO_DB`: Nama database
- `ODOO_USERNAME`: Username untuk autentikasi
- `ODOO_API_KEY`: API key untuk autentikasi
- `FLASK_DEBUG`: Mode debug (True/False)
- `FLASK_HOST`: Host untuk menjalankan server
- `FLASK_PORT`: Port untuk menjalankan server

## Troubleshooting

1. **Authentication failed**: Periksa credentials di `config.py`
2. **Connection error**: Pastikan URL Odoo dapat diakses
3. **No data returned**: Periksa domain dan filter yang digunakan
