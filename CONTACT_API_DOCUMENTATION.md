# Dokumentasi API Contact

## Overview
API Contact menyediakan endpoint untuk mengelola data kontak dengan field lengkap sesuai dengan mapping Odoo Studio.

## Field Mapping
Berikut adalah mapping field antara API dan Odoo Studio:

| Field API | Field Odoo Studio | Deskripsi |
|-----------|-------------------|-----------|
| id | x_studio_id | ID unik kontak |
| street | street | Alamat jalan |
| street2 | street2 | Alamat jalan tambahan |
| city | city | Kota |
| state_id | state_id | ID provinsi/state |
| zip | zip | Kode pos |
| country_id | country_id | ID negara |
| vat | vat | NPWP |
| x_studio_your_business | x_studio_your_business | Tipe bisnis |
| function | function | Posisi/jabatan |
| phone | phone | Nomor telepon |
| mobile | mobile | Nomor handphone |
| email | email | Alamat email |
| website | website | Website |
| title | title | Gelar |
| lang | lang | Bahasa |
| category_id | category_id | Tags/kategori |

## Endpoints

### 1. GET /contact/contacts
Mengambil semua data kontak dengan field lengkap.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+628123456789",
      "mobile": "+628123456789",
      "website": "https://example.com",
      "function": "Manager",
      "title": "Mr.",
      "lang": "en_US",
      "x_studio_your_business": "I am a business",
      "x_studio_id": "CUST001",
      "vat": "12.345.678.9-012.000",
      "street": "Jl. Contoh No. 123",
      "street2": "RT 01/RW 02",
      "city": "Jakarta",
      "zip": "12345",
      "country_id": 105,
      "country_name": "Indonesia",
      "state_id": 1,
      "state_name": "DKI Jakarta",
      "tags": ["VIP", "Customer"],
      "tag_ids": [1, 2]
    }
  ],
  "count": 1
}
```

### 2. GET /contact/contacts/{id}
Mengambil data kontak berdasarkan ID.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+628123456789",
    "mobile": "+628123456789",
    "website": "https://example.com",
    "function": "Manager",
    "title": "Mr.",
    "lang": "en_US",
    "x_studio_your_business": "I am a business",
    "x_studio_id": "CUST001",
    "vat": "12.345.678.9-012.000",
    "street": "Jl. Contoh No. 123",
    "street2": "RT 01/RW 02",
    "city": "Jakarta",
    "zip": "12345",
    "country_id": 105,
    "country_name": "Indonesia",
    "state_id": 1,
    "state_name": "DKI Jakarta",
    "tags": ["VIP", "Customer"],
    "tag_ids": [1, 2]
  }
}
```

### 3. POST /contact/contacts/create
Membuat kontak baru.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+628123456789",
  "mobile": "+628123456789",
  "website": "example.com",
  "function": "Manager",
  "title": "Mr.",
  "lang": "en_US",
  "x_studio_your_business": "I am a business",
  "x_studio_id": "CUST001",
  "vat": "12.345.678.9-012.000",
  "street": "Jl. Contoh No. 123",
  "street2": "RT 01/RW 02",
  "city": "Jakarta",
  "zip": "12345",
  "country_id": 105,
  "state_id": 1,
  "category_id": [1, 2]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+628123456789",
    "mobile": "+628123456789",
    "website": "https://example.com",
    "function": "Manager",
    "title": "Mr.",
    "lang": "en_US",
    "x_studio_your_business": "I am a business",
    "x_studio_id": "CUST001",
    "vat": "12.345.678.9-012.000",
    "street": "Jl. Contoh No. 123",
    "street2": "RT 01/RW 02",
    "city": "Jakarta",
    "zip": "12345",
    "country_id": 105,
    "country_name": "Indonesia",
    "state_id": 1,
    "state_name": "DKI Jakarta",
    "tags": ["VIP", "Customer"],
    "tag_ids": [1, 2]
  },
  "message": "Contact created successfully"
}
```

### 4. PUT /contact/contacts/{id}
Memperbarui data kontak yang sudah ada.

**Request Body:** (sama dengan POST, semua field opsional)

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "John Doe Updated",
    "email": "john.updated@example.com",
    "phone": "+628123456789",
    "mobile": "+628123456789",
    "website": "https://example.com",
    "function": "Senior Manager",
    "title": "Mr.",
    "lang": "en_US",
    "x_studio_your_business": "I am a business",
    "x_studio_id": "CUST001",
    "vat": "12.345.678.9-012.000",
    "street": "Jl. Contoh No. 123",
    "street2": "RT 01/RW 02",
    "city": "Jakarta",
    "zip": "12345",
    "country_id": 105,
    "country_name": "Indonesia",
    "state_id": 1,
    "state_name": "DKI Jakarta",
    "tags": ["VIP", "Customer"],
    "tag_ids": [1, 2]
  },
  "message": "Contact updated successfully"
}
```

### 5. DELETE /contact/contacts/{id}
Menghapus kontak berdasarkan ID.

**Response:**
```json
{
  "success": true,
  "message": "Contact with ID 1 deleted successfully"
}
```

### 6. GET /contact/tags
Mengambil semua tag/kategori yang tersedia.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "VIP",
      "color": 1
    },
    {
      "id": 2,
      "name": "Customer",
      "color": 2
    }
  ],
  "count": 2
}
```

### 7. GET /contact/countries
Mengambil semua negara yang tersedia.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 105,
      "name": "Indonesia",
      "code": "ID"
    }
  ],
  "count": 1
}
```

### 8. GET /contact/states
Mengambil semua provinsi/state yang tersedia.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "DKI Jakarta",
      "country": "Indonesia"
    }
  ],
  "count": 1
}
```

### 9. GET /contact/states/country/{country_id}
Mengambil semua provinsi/state berdasarkan negara.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "DKI Jakarta",
      "country": "Indonesia"
    }
  ],
  "count": 1
}
```

## Validasi

### Field Wajib
- `name`: Nama kontak (wajib)

### Validasi Format
- **NPWP (vat)**: Harus 15 digit dengan format XX.XXX.XXX.X-XXX.XXX
- **Email**: Harus format email yang valid
- **Website**: Otomatis ditambahkan https:// jika tidak ada
- **Business Type**: Harus "I am a business" atau "I am a freight forwarder"
- **Tags (category_id)**: Harus berupa array ID tag yang valid

### Field Opsional
Semua field lainnya bersifat opsional dan akan diset ke `null` jika tidak diisi.

## Error Handling

Semua endpoint mengembalikan response dengan format:
```json
{
  "success": false,
  "error": "Error message",
  "details": "Detailed error information (optional)"
}
```

**HTTP Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 404: Not Found
- 500: Internal Server Error

## Contoh Penggunaan

### Membuat Kontak Baru
```bash
curl -X POST http://localhost:5000/contact/contacts/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+628123456789",
    "x_studio_your_business": "I am a business",
    "vat": "12.345.678.9-012.000",
    "street": "Jl. Contoh No. 123",
    "city": "Jakarta",
    "country_id": 105,
    "state_id": 1
  }'
```

### Mengambil Semua Kontak
```bash
curl -X GET http://localhost:5000/contact/contacts
```

### Mengupdate Kontak
```bash
curl -X PUT http://localhost:5000/contact/contacts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe Updated",
    "email": "john.updated@example.com"
  }'
```

### Menghapus Kontak
```bash
curl -X DELETE http://localhost:5000/contact/contacts/1
```
