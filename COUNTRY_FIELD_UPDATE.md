# Update Field Country pada /contacts

## Perubahan yang Dibuat

### 1. Fungsi Baru di `app/functions/odoo_functions.py`
- **`get_countries()`**: Fungsi untuk mengambil semua data country dari model `res.country`
- Mengembalikan data dengan field: `id`, `name`, `code`

### 2. Endpoint Baru di `app/routes/contact_routes.py`
- **`GET /countries`**: Endpoint untuk mengambil semua countries untuk dropdown selection

### 3. Update Endpoint `/contacts`
- **`GET /contacts`**: Sekarang mengembalikan field `country_id`, `country_name`, `state_name`
- **`POST /contacts/create`**: 
  - Mendukung field `country_id` (opsional)
  - **Fitur Auto-fill**: Jika `state_id` dipilih, `country_id` akan otomatis terisi berdasarkan country dari state tersebut
  - Prioritas: `country_id` dari request > `country_id` dari state > `False`
- **`GET /contacts/<id>`**: Sekarang mengembalikan field `country_id`, `country_name`, `state_name`

## Cara Penggunaan

### 1. Ambil Daftar Countries
```bash
GET /countries
```

Response:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Indonesia",
      "code": "ID"
    }
  ],
  "count": 1
}
```

### 2. Ambil States berdasarkan Country
```bash
GET /states/country/1
```

Response:
```json
{
  "success": true,
  "data": [
    {
      "id": 616,
      "name": "Banten (ID)",
      "country": "Indonesia"
    },
    {
      "id": 617,
      "name": "Bengkulu (ID)",
      "country": "Indonesia"
    }
  ],
  "count": 2
}
```

### 2. Buat Contact dengan Auto-fill Country
```bash
POST /contacts/create
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "081234567890",
  "x_studio_your_business": "I am a business",
  "state_id": 1
}
```

Response:
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "081234567890",
    "x_studio_your_business": "I am a business",
    "country_id": [1, "Indonesia"],
    "country_name": "Indonesia",
    "state_id": [1, "Jakarta"],
    "state_name": "Jakarta"
  },
  "message": "Contact created successfully. Country automatically set to Indonesia based on selected state"
}
```

### 3. Buat Contact dengan Country Manual
```bash
POST /contacts/create
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "country_id": 2,
  "state_id": 5
}
```

## Fitur Auto-fill Country

### Pada POST /contacts/create dan POST /quote/create:
- Jika user memilih `state_id` tanpa `country_id`, sistem akan otomatis mengisi `country_id` berdasarkan country dari state tersebut
- Jika user mengirim `country_id` dan `state_id`, `country_id` dari request akan digunakan (tidak di-override)
- Response akan memberitahu jika country diisi otomatis
- **Auto-fill berlaku untuk kedua endpoint**: `/contacts/create` dan `/quote/create`

### Pada GET /contacts dan GET /contacts/<id>:
- **Mengambil data langsung dari database**: Field `country_id` dan `country_name` diambil langsung dari database seperti field lainnya
- **Tidak ada auto-fill**: Auto-fill hanya berlaku saat POST contact, bukan saat GET contact
- Jika `country_id` di database adalah `false`, maka `country_name` akan `null`

## Field yang Tersedia

### Contact Response Fields:
- `id`: Contact ID
- `name`: Contact name
- `email`: Email address
- `phone`: Phone number
- `x_studio_your_business`: Business type
- `country_id`: Country ID (integer only) - **Format sederhana, hanya ID**
- `country_name`: Country name (string)
- `state_id`: State ID (integer only) - **Format sederhana, hanya ID**
- `state_name`: State name (string) - **Semua field tersedia untuk fleksibilitas maksimal**
