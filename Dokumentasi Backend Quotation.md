# Dokumentasi Singkat Quotation API

Tujuan: buat quotation (sale.order) dari form website, lengkap dengan contact. Ringkas, langsung pakai.

## Base URL
- Dev: `http://127.0.0.1:5000`

## Endpoints
- `GET /lookups/pickup-origins?transportation=<value>` – daftar origin by transportation
- `GET /lookups/pickup-destinations?transportation=<value>` – daftar destination by transportation
- `GET /lookups/transportation-methods` – opsi Transportation Method
- `GET /quotes` – list quotation ringkas
- `POST /quote/create` – buat contact + quotation

## Buat Quotation – `POST /quote/create`
Header: `Content-Type: application/json`

Field wajib:
- `name` (contact)
- `email` (digunakan untuk dedupe contact)
- `pickup_origin_id` (ID)
- `pickup_destination_id` (ID)
- `terms_condition` (text)
- `transportation_method` (boleh key atau label; dinormalisasi otomatis)

Field opsional penting:
- `phone`, `state_id`, `country_id`, `x_studio_your_business`
- `salesperson_id` (ID `res.users`; dipakai untuk set Salesperson/From email)
- Cargo fields (opsional, otomatis deteksi nama teknis di Odoo):
  - `commodity_id` (many2one)
  - `uom_id` (many2one)
  - `qty` (int)
  - `kgs_chg` (int)
  - `kgs_wt` (int)
  - `ratio` (float)

Contoh body:
```json
{
  "name": "Nama Pemohon",
  "email": "user@example.com",
  "phone": "081234567890",
  "state_id": 1,
  "pickup_origin_id": 12,
  "pickup_destination_id": 34,
  "terms_condition": "Pieces, weights, dimensions, special handling...",
  "transportation_method": "Ocean",
  "salesperson_id": 5,
  "commodity_id": 7,
  "uom_id": 1,
  "qty": 100,
  "kgs_chg": 50,
  "kgs_wt": 75,
  "ratio": 1.5
}
```

Respon sukses (ringkas):
```json
{
  "success": true,
  "data": {
    "contact": {
      "id": 123,
      "name": "Nama Pemohon",
      "email": "user@example.com",
      "phone": "081234567890",
      "country_id": 104,
      "country_name": "Indonesia",
      "state_id": 1,
      "state_name": "Jakarta"
    },
    "sales_order": {
      "id": 456,
      "name": "SO001",
      "partner_id": [123, "Nama Pemohon"],
      "state": "draft",
      "transportation_method": "Ocean",
      "pickup_origin": [12, "Origin Name"],
      "pickup_destination": [34, "Destination Name"],
      "terms_condition": "Pieces, weights, dimensions...",
      "commodity": 7,
      "uom": "Unit(s)",
      "qty": 100,
      "kgs_chg": 50,
      "kgs_wt": 75,
      "ratio": 1.5
    },
    "contact_action": "created"
  },
  "message": "Quote created successfully"
}
```

Catatan penting:
- Origin/Destination harus sesuai `transportation_method` (kalau tidak, request ditolak).
- Field pickup origin/destination sekarang sama-sama many2one ke model `x_pickup`; API otomatis membaca nama field, relation, dan domain dari metadata Odoo sehingga payload tetap sama walaupun technical field berubah.
- Nama teknis field cargo (commodity/uom/qty/kgs_chg/kgs_wt/ratio) dideteksi otomatis dari label di Odoo. Tidak perlu ubah API saat nama teknis berubah.
- Contact dideduplicate berdasarkan *name + email* (case-insensitive). Jika email berbeda, API otomatis bikin contact baru. Gunakan `force_create=true` bila ingin memaksa create baru.
- UOM di response dikembalikan sebagai nama/label (bukan ID).
- Untuk email “From” mengikuti Salesperson di quotation, isi `salesperson_id` dan set template From di Odoo ke `{{ object.user_id.email_formatted }}` serta gunakan SMTP yang sesuai email tersebut.

## Lookup cepat
Contoh panggilan:
```
GET /lookups/pickup-origins?transportation=Ocean
GET /lookups/pickup-destinations?transportation=Ocean
GET /lookups/transportation-methods
```

## Error umum
- `Invalid state_id` → gunakan ID valid dari Odoo.
- `Invalid pickup_origin_id or pickup_destination_id` → pastikan ID dari endpoint lookup.
- `Origin/Destination not allowed for selected transportation_method` → transport harus konsisten.
