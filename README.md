# Quotation API (Odoo)

API sederhana untuk membuat Quotation (`sale.order`) dari website dan melakukan lookup data yang diperlukan.

## Jalankan proyek

1) Install dependencies
```bash
pip install -r requirements.txt
```
2) Set kredensial Odoo (opsional)
```bash
export ODOO_URL="https://your-odoo-instance.com/"
export ODOO_DB="your_database"
export ODOO_USERNAME="your_email@example.com"
export ODOO_API_KEY="your_api_key"
```
3) Start server
```bash
python main.py
```
Base URL default: `http://127.0.0.1:5000`

## Endpoints utama

- GET `/lookups/transportation-methods` → opsi Transportation
- GET `/lookups/pickup-origins?transportation=<value>` → daftar origin by Transportation
- GET `/lookups/pickup-destinations?transportation=<value>` → daftar destination by Transportation
- GET `/quotes` → list quotation ringkas
- POST `/quote/create` → buat contact + quotation

## Buat quotation (POST /quote/create)
Header:
- `Content-Type: application/json`

Wajib:
- `name`
- `pickup_origin_id`
- `pickup_destination_id`
- `terms_condition`
- `transportation_method` (key atau label; dinormalisasi otomatis)

Opsional yang disarankan:
- Contact: `email`, `phone`, `state_id`, `country_id`, `x_studio_your_business`
- Sales: `salesperson_id` (ID `res.users`) → agar email From mengikuti salesperson
- Cargo: `commodity_id`, `uom_id`, `qty`, `kgs_chg`, `kgs_wt`, `ratio` (API auto-deteksi nama teknis field di Odoo dari label, jadi aman saat Studio berubah)

Contoh body:
```json
{
  "name": "Nama Pemohon",
  "email": "user@example.com",
  "phone": "081234567890",
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

Ringkasan response sukses:
```json
{
  "success": true,
  "data": {
    "contact": { "id": 123, "name": "Nama Pemohon", "state_id": 1, "state_name": "Jakarta" },
    "sales_order": {
      "id": 456,
      "name": "SO001",
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
  }
}
```

Catatan penting:
- Origin/Destination harus cocok dengan `transportation_method` (jika tidak, request ditolak).
- UOM pada response adalah nama/label, bukan ID.
- Untuk From email = email salesperson, set template Odoo: `{{ object.user_id.email_formatted }}` dan gunakan SMTP yang sesuai alamat salesperson yang dipakai.

## Troubleshooting singkat
- `Invalid state_id` → gunakan ID valid dari Odoo.
- `Invalid pickup_origin_id or pickup_destination_id` → ambil dari endpoint lookup.
- `Origin/Destination not allowed for selected transportation_method` → pastikan transport konsisten.
