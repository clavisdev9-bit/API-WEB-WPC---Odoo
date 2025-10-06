# Panduan Integrasi Formulir (Website → Backend Odoo)

Dokumen singkat ini menjelaskan cara form "Get Quote" mengirim data ke backend untuk membuat Contact dan Sales Order (Quote) di Odoo Studio.

## Basis URL
- Lokal (dev): `http://127.0.0.1:5000`

## Endpoint
- `GET /states` – Ambil daftar State/City untuk dropdown
- `GET /lookups/pickup-origins?transportation=<metode>` – List origin sesuai Transportation Method
- `GET /lookups/pickup-destinations?transportation=<metode>` – List destination sesuai Transportation Method
- `POST /quote/create` – Kirim semua data form (Personal Information + Shipment) sekali kirim

## Pemetaan Field Form → Odoo
- Bagian Personal Information (model `res.partner`)
  - `name` → `name` (wajib)
  - `email` → `email`
  - `phone` → `phone`
  - `business_type` (select) → `x_studio_your_business` ("I am a business" | "I am a freight forwarder")
  - `state_id` (hasil pilih dropdown) → `state_id` (integer ID)

- Bagian Shipment/Quote (model `sale.order`)
  - `pickup_origin_id` (ID) → `x_studio_pickup_origin` (many2one)
  - `pickup_destination_id` (ID) → `x_studio_pickup_destination` (many2one)
  - `terms_condition` (Cargo Details) → `x_studio_terms_condition`
  - `transportation_method` (select) → `x_studio_transportation_method`

Wajib: semua field di atas harus tersedia sebagai field custom di Odoo Studio (tanpa fallback ke field `note`).

## Alur Penggunaan di Frontend
1) Saat halaman dimuat, panggil `GET /states` untuk mengisi dropdown State/City.
2) Ambil opsi dropdown berdasarkan Transportation Method:
   - `GET /lookups/pickup-origins?transportation=Ocean`
   - `GET /lookups/pickup-destinations?transportation=Ocean`
   Gunakan `id` dari hasil endpoint tersebut untuk field `pickup_origin_id` dan `pickup_destination_id`.
3) Saat submit, kirim satu request ke `POST /quote/create` dengan body JSON berikut.

### Request – `POST /quote/create`
Header: `Content-Type: application/json`

Body contoh:
```json
{
  "name": "Nama Pemohon",
  "email": "user@example.com",
  "phone": "081234567890",
  "x_studio_your_business": "I am a business",
  "state_id": 1,
  "pickup_origin_id": 12,
  "pickup_destination_id": 34,
  "terms_condition": "Pieces, weights, dimensions, special handling...",
  "transportation_method": "Ocean"
}
```
Validasi minimal di sisi klien: `name`, `transportation_method`, `pickup_origin_id`, `pickup_destination_id` (dan `email` jika diwajibkan oleh UI). `state_id` diambil dari pilihan `GET /states`.

Catatan:
- `transportation_method` boleh dikirim sebagai key atau label (mis. "ocean" atau "Ocean"); backend akan menormalkan otomatis.
- Origin/Destination harus cocok dengan `transportation_method` yang dipilih (jika tidak, backend menolak).

### Respon Sukses
```json
{
  "success": true,
  "data": {
    "contact": { "id": 123, "name": "Nama Pemohon", "state_id": [1, "Jakarta"] },
    "sales_order": {
      "id": 456,
      "name": "SO001",
      "partner_id": [123, "Nama Pemohon"],
      "state": "draft",
      "x_studio_transportation_method": "Ocean",
      "x_studio_pickup_origin": [12, "Origin Name"],
      "x_studio_pickup_destination": [34, "Destination Name"],
      "x_studio_terms_condition": "Pieces, weights, dimensions..."
    }
  },
  "message": "Quote created successfully"
}
```

## Contoh: `GET /states`
Respon (ringkas):
```json
{
  "success": true,
  "data": [ { "id": 1, "name": "Jakarta", "country": "Indonesia" } ],
  "count": 1
}
```

## Error yang Umum & Solusi Singkat
- `Invalid state_id`: pastikan `state_id` berasal dari `GET /states` dan berupa angka.
- `Origin/Destination not allowed for selected transportation_method`: pastikan Anda mengambil ID origin/destination dari endpoint lookup menggunakan transportation method yang sama.
- Field custom belum ada: buat field di Odoo Studio dengan nama persis: `x_studio_pickup_origin`, `x_studio_pickup_destination`, `x_studio_terms_condition`, `x_studio_transportation_method`.
