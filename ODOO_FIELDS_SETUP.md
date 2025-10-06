# Setup Field Custom di Odoo Studio

## Field yang Perlu Dibuat di Model `sale.order`

Untuk menggunakan endpoint quote dengan field terpisah, Anda perlu membuat field custom berikut di Odoo Studio:

### 1. Buka Odoo Studio
- Login ke Odoo Studio Anda
- Pilih aplikasi **Sales**
- Klik **Configure** atau **Customize**

### 2. Tambah Field di Model `sale.order`

#### Field: `x_studio_pickup_origin`
- **Type**: Text
- **Label**: Pickup Origin
- **Required**: No
- **Help**: Address atau port untuk pickup origin

#### Field: `x_studio_pickup_destination`
- **Type**: Text  
- **Label**: Pickup Destination
- **Required**: No
- **Help**: Address atau port untuk pickup destination

#### Field: `x_studio_terms_condition`
- **Type**: Text (Multiline)
- **Label**: Terms & Condition
- **Required**: No
- **Help**: Detail kargo dan terms condition (pieces, weights, dimensions, special handling)

#### Field: `x_studio_transportation_method`
- **Type**: Selection
- **Label**: Transportation Method
- **Required**: No
- **Options**:
  - `Ocean`
  - `Air`
  - `Ground`
  - `Rail`

### 3. Tambah Field di Model `res.partner`

#### Field: `x_studio_your_business`
- **Type**: Selection
- **Label**: Business Type
- **Required**: No
- **Options**:
  - `I am a business`
  - `I am a freight forwarder`

## Setup View di Sales Order

### 1. Tambah Field ke Form View
- Edit Sales Order form view
- Tambahkan field baru di section yang sesuai
- Group field shipping di section terpisah

### 2. Tambah Field ke Tree View (Optional)
- Edit Sales Order list view
- Tambahkan kolom untuk field penting
- Gunakan untuk quick reference

## Testing

Setelah field dibuat, test endpoint:

```bash
POST /quote/create
{
  "name": "Test User",
  "email": "test@example.com",
  "phone": "081234567890",
  "x_studio_your_business": "I am a business",
  "state_id": 1,
  "pickup_origin": "123 Main St, New York",
  "pickup_destination": "456 Oak Ave, Los Angeles", 
  "terms_condition": "2 boxes, 50kg each, fragile items",
  "transportation_method": "Ocean"
}
```

## Field Mapping yang Benar

API sekarang menggunakan field yang benar sesuai database Odoo Studio:

| Form Field | Database Field | Description |
|------------|----------------|-------------|
| `pickup_origin` | `x_studio_pickup_origin` | Pickup origin address |
| `pickup_destination` | `x_studio_pickup_destination` | Pickup destination address |
| `terms_condition` | `x_studio_terms_condition` | Cargo details & terms |
| `transportation_method` | `x_studio_transportation_method` | Transportation method |

## Field yang Digunakan

Data akan disimpan di field custom yang benar:
- **`x_studio_transportation_method`**: Transportation method
- **`x_studio_pickup_origin`**: Pickup origin address
- **`x_studio_pickup_destination`**: Pickup destination address  
- **`x_studio_terms_condition`**: Cargo details & terms condition
- **`partner_id`**: Link ke contact
- **`state`**: Status draft

## Response Format

```json
{
  "success": true,
  "data": {
    "contact": {...},
    "sales_order": {
      "id": 123,
      "name": "SO001",
      "partner_id": [456, "John Doe"],
      "state": "draft",
      "x_studio_transportation_method": "Ocean",
      "x_studio_pickup_origin": "123 Main St, New York",
      "x_studio_pickup_destination": "456 Oak Ave, Los Angeles",
      "x_studio_terms_condition": "2 boxes, 50kg each, fragile items",
      "create_date": "2024-01-01 10:00:00"
    }
  }
}
```
