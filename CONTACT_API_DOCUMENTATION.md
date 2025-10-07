# Dokumentasi API Contact

## Overview
API Contact menyediakan endpoint untuk mengelola data kontak dengan field lengkap sesuai dengan mapping Odoo Studio.

## Field Mapping
Berikut adalah mapping field antara API Response dan Odoo Studio:

| Field API Response | Field Odoo Studio | Deskripsi |
|-------------------|-------------------|-----------|
| id | id | ID database Odoo (auto-increment) |
| name | name | Nama kontak |
| custom_id | x_studio_id | ID custom kontak |
| street | street | Alamat jalan |
| street2 | street2 | Alamat jalan tambahan |
| city | city | Kota |
| state | state_id | Array objek state dengan id dan name |
| zip | zip | Kode pos |
| country | country_id | Array objek country dengan id dan name |
| npwp | vat | NPWP |
| your_business | x_studio_your_business | Tipe bisnis |
| job_position | function | Posisi/jabatan |
| phone | phone | Nomor telepon |
| mobile | mobile | Nomor handphone |
| email | email | Alamat email |
| website | website | Website |
| title | title | Gelar |
| language | lang | Bahasa |
| company_type | company_type | Tipe perusahaan (person/company) |
| tags | category_id | Tags/kategori (many2many) |

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
      "custom_id": "CUST001",
      "street": "Jl. Contoh No. 123",
      "street2": "RT 01/RW 02",
      "city": "Jakarta",
      "country": [
        {
          "country_id": 105,
          "country_name": "Indonesia"
        }
      ],
      "state": [
        {
          "state_id": 1,
          "state_name": "DKI Jakarta"
        }
      ],
      "zip": "12345",
      "npwp": "12.345.678.9-012.000",
      "your_business": "I am a business",
      "job_position": "Manager",
      "phone": "+628123456789",
      "mobile": "+628123456789",
      "email": "john@example.com",
      "website": "https://example.com",
      "title": "Mr.",
      "language": "en_US",
      "company_type": "person",
      "tags": [
        {"id": 1, "name": "VIP"},
        {"id": 2, "name": "Customer"}
      ]
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
    "Name": "John Doe",
    "ID": "CUST001",
    "Street": "Jl. Contoh No. 123",
    "Street2": "RT 01/RW 02",
    "City": "Jakarta",
    "Country": 105,
    "State": 1,
    "Zip": "12345",
    "NPWP": "12.345.678.9-012.000",
    "Your Business": "I am a business",
    "Job Position": "Manager",
    "Phone": "+628123456789",
    "Mobile": "+628123456789",
    "Email": "john@example.com",
    "Website": "https://example.com",
    "Title": "Mr.",
    "Language": "en_US",
    "Company Type": "person",
    "Tags": [
      {"id": 1, "name": "VIP"},
      {"id": 2, "name": "Customer"}
    ],
    "country_name": "Indonesia",
    "state_name": "DKI Jakarta"
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
  "job_position": "Manager",
  "title": "Mr.",
  "language": "en_US",
  "company_type": "person",
  "your_business": "I am a business",
  "custom_id": "CUST001",
  "npwp": "12.345.678.9-012.000",
  "street": "Jl. Contoh No. 123",
  "street2": "RT 01/RW 02",
  "city": "Jakarta",
  "zip": "12345",
  "country": [105],
  "state": [1],
  "tags": [1, 2]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "Name": "John Doe",
    "ID": "CUST001",
    "Street": "Jl. Contoh No. 123",
    "Street2": "RT 01/RW 02",
    "City": "Jakarta",
    "Country": 105,
    "State": 1,
    "Zip": "12345",
    "NPWP": "12.345.678.9-012.000",
    "Your Business": "I am a business",
    "Job Position": "Manager",
    "Phone": "+628123456789",
    "Mobile": "+628123456789",
    "Email": "john@example.com",
    "Website": "https://example.com",
    "Title": "Mr.",
    "Language": "en_US",
    "Company Type": "person",
    "Tags": [
      {"id": 1, "name": "VIP"},
      {"id": 2, "name": "Customer"}
    ],
    "country_name": "Indonesia",
    "state_name": "DKI Jakarta"
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
- **your_business**: Harus "I am a business" atau "I am a freight forwarder"
- **company_type**: Harus "person" (Individual) atau "company" (Company)
- **tags**: Field many2many yang harus berupa array ID tag yang valid

### Field Tags
Field tags adalah many2many field yang memungkinkan pemilihan multiple tags:
- **Format Input**: Array of integers `[1, 2, 3]` (ID tag)
- **Format Output**: 
  - `tags`: Array of objects `[{"id": 1, "name": "VIP"}, {"id": 2, "name": "Customer"}]`
- **Validasi**: Semua ID tag harus ada di database `res.partner.category`
- **Note**: Field `category_id` tidak dikembalikan di response untuk menghindari redundansi

### Field Company Type
Field company_type menentukan tipe kontak:
- **"person"**: Untuk individu/perorangan (Individual)
- **"company"**: Untuk perusahaan (Company)
- **Default**: Jika tidak diisi, Odoo akan menggunakan default value

### Field Country dan State
Field country dan state menggunakan struktur array dengan objek:
- **Format Input**: Array of integers `[105]` atau `[1]` (ID country/state)
- **Format Output**: 
  - `country`: Array of objects `[{"country_id": 105, "country_name": "Indonesia"}]`
  - `state`: Array of objects `[{"state_id": 1, "state_name": "DKI Jakarta"}]`
- **Validasi**: Semua ID country/state harus ada di database
- **Note**: Field ini mengembalikan array untuk konsistensi dengan field many2many lainnya

### Field ID
Field `id` adalah ID database Odoo yang auto-increment:
- **Format**: Integer (contoh: 1, 2, 3, 19)
- **Sumber**: Database Odoo `res.partner.id`
- **Fungsi**: Primary key untuk identifikasi unik kontak di database
- **Note**: Field ini tidak bisa diubah saat create/update, hanya untuk identifikasi

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
