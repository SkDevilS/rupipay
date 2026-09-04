# Quick API Testing Guide - Postman/Thunder Client

## Setup

1. **Start Backend Server:**
```bash
cd backend
python app.py
```
Server runs on: `http://localhost:5000`

2. **Install Postman** or use **Thunder Client** (VS Code extension)

---

## Step 1: Merchant Login

**Method:** POST  
**URL:** `http://localhost:5000/api/merchant/login`  
**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "merchantId": "7679022140",
  "password": "Test@123",
  "captcha": "ABCD",
  "sessionId": "test123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "merchantId": "7679022140"
}
```

**⚠️ SAVE THE TOKEN** - Copy the token value, you'll need it for all other requests!

---

## Step 2: Check Wallet Balance

**Method:** GET  
**URL:** `http://localhost:5000/api/merchant/wallet/overview`  
**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Response:**
```json
{
  "success": true,
  "balance": 0.00,
  "totalPayin": 0.00,
  "totalPayout": 0.00,
  "merchantId": "7679022140"
}
```

---

## Step 3: Create Payin Order

### 3a. First, Encrypt the Payload

**Method:** POST  
**URL:** `http://localhost:5000/api/merchant/encrypt`  
**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "plainText": "{\"amount\":\"100\",\"orderid\":\"TEST001\",\"payee_fname\":\"John\",\"payee_lname\":\"Doe\",\"payee_mobile\":\"9876543210\",\"payee_email\":\"test@example.com\"}"
}
```

**Response:**
```json
{
  "success": true,
  "encryptedText": "base64_encrypted_string_here"
}
```

**⚠️ COPY THE encryptedText** value!

### 3b. Create the Order

**Method:** POST  
**URL:** `http://localhost:5000/api/payin/order/create`  
**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "data": "PASTE_ENCRYPTED_TEXT_HERE"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order created successfully",
  "data": "encrypted_response_here"
}
```

**⚠️ COPY THE data** value from response!

### 3c. Decrypt the Response

**Method:** POST  
**URL:** `http://localhost:5000/api/merchant/decrypt`  
**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "encryptedText": "PASTE_ENCRYPTED_RESPONSE_HERE"
}
```

**Response:**
```json
{
  "success": true,
  "decryptedText": "{\"txn_id\":\"PAYIN_7679022140_TEST001_...\",\"payment_url\":\"https://secure.payu.in/_payment?...\",\"amount\":100.0,\"charge_amount\":2.0,\"net_amount\":98.0}"
}
```

**⚠️ COPY THE txn_id** and **payment_url** from decryptedText!

---

## Step 4: Check Transaction Status

**Method:** GET  
**URL:** `http://localhost:5000/api/payin/status/PAYIN_7679022140_TEST001_20250214120000`  
(Replace with your actual txn_id)

**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "txn_id": "PAYIN_7679022140_TEST001_20250214120000",
    "order_id": "TEST001",
    "amount": 100.0,
    "charge_amount": 2.0,
    "net_amount": 98.0,
    "status": "INITIATED",
    "payment_mode": null,
    "created_at": "2025-02-14T12:00:00",
    "completed_at": null
  }
}
```

---

## Step 5: View All Transactions

**Method:** GET  
**URL:** `http://localhost:5000/api/payin/transactions?page=1&limit=10`  
**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "txn_id": "PAYIN_7679022140_TEST001_20250214120000",
      "order_id": "TEST001",
      "amount": 100.0,
      "charge_amount": 2.0,
      "net_amount": 98.0,
      "status": "INITIATED",
      "created_at": "2025-02-14T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "pages": 1
  }
}
```

---

## Complete Testing Flow (Copy-Paste Ready)

### Using PowerShell/CMD:

```powershell
# 1. Login and get token
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/merchant/login" -Method POST -ContentType "application/json" -Body '{"merchantId":"7679022140","password":"Test@123","captcha":"ABCD","sessionId":"test123"}'
$token = $response.token
Write-Host "Token: $token"

# 2. Check wallet
Invoke-RestMethod -Uri "http://localhost:5000/api/merchant/wallet/overview" -Method GET -Headers @{"Authorization"="Bearer $token"}

# 3. Encrypt payload
$encryptResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/merchant/encrypt" -Method POST -Headers @{"Authorization"="Bearer $token"} -ContentType "application/json" -Body '{"plainText":"{\"amount\":\"100\",\"orderid\":\"TEST001\",\"payee_fname\":\"John\",\"payee_lname\":\"Doe\",\"payee_mobile\":\"9876543210\",\"payee_email\":\"test@example.com\"}"}'
$encrypted = $encryptResponse.encryptedText
Write-Host "Encrypted: $encrypted"

# 4. Create order
$orderResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/payin/order/create" -Method POST -Headers @{"Authorization"="Bearer $token"} -ContentType "application/json" -Body "{`"data`":`"$encrypted`"}"
$encryptedResponse = $orderResponse.data

# 5. Decrypt response
$decryptResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/merchant/decrypt" -Method POST -Headers @{"Authorization"="Bearer $token"} -ContentType "application/json" -Body "{`"encryptedText`":`"$encryptedResponse`"}"
Write-Host "Order Details: $($decryptResponse.decryptedText)"

# 6. View transactions
Invoke-RestMethod -Uri "http://localhost:5000/api/payin/transactions" -Method GET -Headers @{"Authorization"="Bearer $token"}
```

---

## Using curl (Linux/Mac/Git Bash):

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:5000/api/merchant/login \
  -H "Content-Type: application/json" \
  -d '{"merchantId":"7679022140","password":"Test@123","captcha":"ABCD","sessionId":"test123"}' \
  | jq -r '.token')

echo "Token: $TOKEN"

# 2. Check wallet
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/merchant/wallet/overview

# 3. Encrypt payload
ENCRYPTED=$(curl -s -X POST http://localhost:5000/api/merchant/encrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plainText":"{\"amount\":\"100\",\"orderid\":\"TEST001\",\"payee_fname\":\"John\",\"payee_lname\":\"Doe\",\"payee_mobile\":\"9876543210\",\"payee_email\":\"test@example.com\"}"}' \
  | jq -r '.encryptedText')

# 4. Create order
ENCRYPTED_RESPONSE=$(curl -s -X POST http://localhost:5000/api/payin/order/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"data\":\"$ENCRYPTED\"}" \
  | jq -r '.data')

# 5. Decrypt response
curl -X POST http://localhost:5000/api/merchant/decrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"encryptedText\":\"$ENCRYPTED_RESPONSE\"}"

# 6. View transactions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/payin/transactions?page=1&limit=10"
```

---

## Postman Collection Setup

1. Create a new Collection: "Moneyone Payin APIs"
2. Add Environment Variable:
   - Variable: `token`
   - Initial Value: (leave empty)
   - Current Value: (will be set after login)

3. For Login request, add this to Tests tab:
```javascript
pm.environment.set("token", pm.response.json().token);
```

4. For all other requests, use in Headers:
```
Authorization: Bearer {{token}}
```

---

## Testing with Real Payment

After creating order and getting payment_url:

1. Copy the `payment_url` from decrypted response
2. Open it in browser
3. Complete payment on PayU page
4. Check transaction status again - it should be "SUCCESS"
5. Check wallet balance - it should be updated with net_amount

---

## Common Issues

**401 Unauthorized:**
- Token expired or invalid
- Login again to get new token

**400 Bad Request:**
- Check request body format
- Ensure all required fields are present

**500 Internal Server Error:**
- Check backend logs
- Verify database connection
- Ensure PayU credentials are configured

---

## Status Codes

- `INITIATED` - Order created, payment not started
- `PENDING` - Payment in progress  
- `SUCCESS` - Payment completed, wallet credited
- `FAILED` - Payment failed
- `CANCELLED` - Payment cancelled by user
