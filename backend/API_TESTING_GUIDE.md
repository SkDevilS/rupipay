# PayU Payin API Testing Guide

## Complete Testing Flow for Real Money Transactions

This guide will help you test the PayU payin integration with real money transactions.

---

## Prerequisites

### 1. PayU Account Setup
- Sign up for PayU merchant account at https://www.payu.in/
- Get your **Merchant Key** and **Merchant Salt** from PayU dashboard
- Update `backend/.env` with your credentials:
```env
PAYU_MERCHANT_KEY=your_actual_merchant_key
PAYU_MERCHANT_SALT=your_actual_merchant_salt
PAYU_BASE_URL=https://secure.payu.in
PAYU_TEST_MODE=False  # Set to False for production
```

### 2. Install Dependencies
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend (Client)
cd moneyone_client
npm install
```

### 3. Initialize Database
```bash
cd backend
python app.py
```

This will create all necessary tables including:
- payin_transactions
- merchant_wallet
- wallet_transactions
- service_routing
- callback_logs

---

## Step-by-Step Testing Process

### Step 1: Start the Backend Server

```bash
cd backend
python app.py
```

Server will start on `http://localhost:5000`

### Step 2: Start the Frontend (Admin Dashboard)

```bash
cd moneyone_admin
npm run dev
```

Admin dashboard will be available at `http://localhost:5173` (or similar)

### Step 3: Start the Frontend (Merchant Dashboard)

```bash
cd moneyone_client
npm run dev
```

Merchant dashboard will be available at `http://localhost:5174` (or similar)

---

## Testing APIs

### 1. Admin Login

**Endpoint:** `POST http://localhost:5000/api/admin/login`

**Get Captcha First:**
```bash
curl http://localhost:5000/api/admin/captcha
```

**Login Request:**
```json
{
  "adminId": "6239572985",
  "password": "admin@123",
  "captcha": "ABCD",
  "sessionId": "session_id_from_captcha_response"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "adminId": "6239572985"
}
```

**Save the token** - you'll need it for subsequent admin API calls.

---

### 2. Onboard a Test Merchant

**Endpoint:** `POST http://localhost:5000/api/admin/merchants/onboard`

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data
```

**Form Data:**
```
fullName: Test Merchant
email: merchant@test.com
mobile: 9876543210
aadharCard: 123456789012
panNo: ABCDE1234F
pincode: 110001
state: Delhi
city: New Delhi
address: Test Address
merchantType: BOTH
accountNum: 1234567890
ifscCode: SBIN0001234
gstNo: 29ABCDE1234F1Z5
schemeId: 1
dob: 1990-01-01
houseNumber: 123
landmark: Near Test Market

# Upload files (use actual image/PDF files)
aadharFront: [file]
aadharBack: [file]
panCard: [file]
gstCertificate: [file]
shopPhoto: [file]
profilePhoto: [file]
```

**Response:**
```json
{
  "success": true,
  "message": "Merchant onboarded successfully",
  "merchantId": "9876543210",
  "emailSent": true
}
```

**Note:** Merchant credentials will be sent to the provided email.

---

### 3. Configure Service Routing (Admin)

**Endpoint:** `POST http://localhost:5000/api/routing/services`

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body (For All Users):**
```json
{
  "merchantId": null,
  "serviceType": "PAYIN",
  "routingType": "ALL_USERS",
  "pgPartner": "PayU",
  "priority": 1
}
```

**OR (For Specific Merchant):**
```json
{
  "merchantId": "9876543210",
  "serviceType": "PAYIN",
  "routingType": "SINGLE_USER",
  "pgPartner": "PayU",
  "priority": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Service routing created successfully"
}
```

---

### 4. Merchant Login

**Endpoint:** `POST http://localhost:5000/api/merchant/login`

**Get Captcha First:**
```bash
curl http://localhost:5000/api/merchant/captcha
```

**Login Request:**
```json
{
  "merchantId": "9876543210",
  "password": "password_from_email",
  "captcha": "ABCD",
  "sessionId": "session_id_from_captcha_response"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "merchantId": "9876543210",
  "merchantName": "Test Merchant",
  "email": "merchant@test.com"
}
```

**Save the merchant token** for subsequent merchant API calls.

---

### 5. Get Merchant Credentials

**Endpoint:** `GET http://localhost:5000/api/merchant/credentials`

**Headers:**
```
Authorization: Bearer {merchant_token}
```

**Response:**
```json
{
  "success": true,
  "credentials": {
    "merchant_id": "9876543210",
    "authorization_key": "Basic_base64_encoded_key",
    "module_secret": "secret_key",
    "aes_iv": "iv_value",
    "aes_key": "aes_key_value",
    "environment": "PRODUCTION",
    "base_url": "https://api.moneyone.co.in"
  },
  "ipWhitelist": [],
  "callbacks": {
    "payin_callback_url": "",
    "payout_callback_url": ""
  }
}
```

**Save these credentials** - you'll need them for API integration.

---

### 6. Create Payin Order (Real Money Transaction)

#### Option A: Using Merchant Dashboard (Recommended for Testing)

1. Login to merchant dashboard
2. Go to "Generate QR" page
3. Fill in the form:
   - Amount: 100 (or any amount)
   - Order ID: TEST_ORDER_001
   - Customer Name: John Doe
   - Customer Mobile: 9876543210
   - Customer Email: customer@test.com
4. Click "Generate Payment QR"
5. QR code and payment link will be generated
6. Customer can scan QR or click payment link
7. Complete payment on PayU page

#### Option B: Using API (For Integration)

**Step 1: Encrypt Payload**

**Endpoint:** `POST http://localhost:5000/api/merchant/encrypt`

**Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request:**
```json
{
  "plainText": "{\"amount\":\"100\",\"orderid\":\"TEST_ORDER_001\",\"payee_fname\":\"John\",\"payee_lname\":\"Doe\",\"payee_mobile\":\"9876543210\",\"payee_email\":\"customer@test.com\",\"productinfo\":\"Payment\"}"
}
```

**Response:**
```json
{
  "success": true,
  "encryptedText": "encrypted_base64_string"
}
```

**Step 2: Create Order**

**Endpoint:** `POST http://localhost:5000/api/payin/order/create`

**Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request:**
```json
{
  "data": "encrypted_base64_string_from_step1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order created successfully",
  "data": "encrypted_response"
}
```

**Step 3: Decrypt Response**

**Endpoint:** `POST http://localhost:5000/api/merchant/decrypt`

**Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request:**
```json
{
  "encryptedText": "encrypted_response_from_step2"
}
```

**Response:**
```json
{
  "success": true,
  "decryptedText": "{\"txn_id\":\"PAYIN_9876543210_TEST_ORDER_001_20250214120000\",\"order_id\":\"TEST_ORDER_001\",\"amount\":100.0,\"charge_amount\":2.0,\"net_amount\":98.0,\"payment_url\":\"https://secure.payu.in/_payment\",\"payment_params\":{...}}"
}
```

**Step 4: Redirect Customer to Payment URL**

Use the `payment_url` and `payment_params` from decrypted response to redirect customer to PayU payment page.

**Example Payment URL:**
```
https://secure.payu.in/_payment?key=merchant_key&txnid=PAYIN_9876543210_TEST_ORDER_001_20250214120000&amount=100.00&productinfo=Payment&firstname=John&lastname=Doe&email=customer@test.com&phone=9876543210&surl=callback_success_url&furl=callback_failure_url&hash=generated_hash
```

---

### 7. Complete Payment on PayU

1. Customer will be redirected to PayU payment page
2. Select payment method (UPI, Card, Net Banking, etc.)
3. Complete the payment
4. PayU will send callback to your server
5. Transaction status will be updated automatically

---

### 8. Check Transaction Status

**Endpoint:** `GET http://localhost:5000/api/payin/status/{txn_id}`

**Headers:**
```
Authorization: Bearer {merchant_token}
```

**Example:**
```bash
curl -H "Authorization: Bearer {merchant_token}" \
  http://localhost:5000/api/payin/status/PAYIN_9876543210_TEST_ORDER_001_20250214120000
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "txn_id": "PAYIN_9876543210_TEST_ORDER_001_20250214120000",
    "order_id": "TEST_ORDER_001",
    "amount": 100.0,
    "charge_amount": 2.0,
    "net_amount": 98.0,
    "status": "SUCCESS",
    "payment_mode": "UPI",
    "created_at": "2025-02-14T12:00:00",
    "completed_at": "2025-02-14T12:05:00"
  }
}
```

**Status Values:**
- `INITIATED` - Order created, payment not started
- `PENDING` - Payment in progress
- `SUCCESS` - Payment successful, amount credited to wallet
- `FAILED` - Payment failed
- `CANCELLED` - Payment cancelled by user

---

### 9. Check Wallet Balance

**Endpoint:** `GET http://localhost:5000/api/merchant/wallet/overview`

**Headers:**
```
Authorization: Bearer {merchant_token}
```

**Response:**
```json
{
  "success": true,
  "balance": 98.0,
  "totalPayin": 98.0,
  "totalPayout": 0.0,
  "merchantId": "9876543210"
}
```

**Note:** Balance shows net amount (after charges deduction)

---

### 10. View Transaction Report

**Endpoint:** `GET http://localhost:5000/api/payin/transactions?page=1&limit=50&status=SUCCESS`

**Headers:**
```
Authorization: Bearer {merchant_token}
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "txn_id": "PAYIN_9876543210_TEST_ORDER_001_20250214120000",
      "order_id": "TEST_ORDER_001",
      "amount": 100.0,
      "charge_amount": 2.0,
      "net_amount": 98.0,
      "status": "SUCCESS",
      "payment_mode": "UPI",
      "payee_name": "John Doe",
      "payee_mobile": "9876543210",
      "created_at": "2025-02-14T12:00:00",
      "completed_at": "2025-02-14T12:05:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1,
    "pages": 1
  }
}
```

---

## Testing with Real Money - Important Notes

### 1. PayU Test Environment
- For testing without real money, use PayU test credentials
- Set `PAYU_TEST_MODE=True` in `.env`
- Use PayU test cards: https://docs.payu.in/docs/test-cards

### 2. Production Environment
- Set `PAYU_TEST_MODE=False` in `.env`
- Use actual PayU merchant credentials
- Real money will be transacted
- Ensure proper commercial scheme is configured

### 3. Minimum Transaction Amount
- PayU minimum: ₹10
- Test with small amounts first (₹10-₹100)

### 4. Payment Methods Supported
- UPI (Google Pay, PhonePe, Paytm, etc.)
- Credit/Debit Cards
- Net Banking
- Wallets

### 5. Transaction Flow Timeline
- Order Creation: Instant
- Payment Redirect: Instant
- Payment Completion: 5-30 seconds
- Callback Received: 5-60 seconds
- Wallet Credit: Instant after callback

---

## Webhook/Callback Testing

### 1. Setup Callback URL

**Endpoint:** `PUT http://localhost:5000/api/merchant/callbacks`

**Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request:**
```json
{
  "payinCallbackUrl": "https://your-domain.com/payin-callback",
  "payoutCallbackUrl": ""
}
```

### 2. Callback Payload (Sent to Your URL)

```json
{
  "txn_id": "PAYIN_9876543210_TEST_ORDER_001_20250214120000",
  "order_id": "TEST_ORDER_001",
  "amount": "100.00",
  "status": "SUCCESS",
  "pg_txn_id": "403993715527370646",
  "bank_ref_no": "123456789",
  "payment_mode": "UPI",
  "timestamp": "2025-02-14T12:05:00"
}
```

### 3. Testing Callbacks Locally

Use ngrok or similar tool to expose local server:

```bash
ngrok http 5000
```

Then use the ngrok URL as callback URL:
```
https://abc123.ngrok.io/payin-callback
```

---

## Troubleshooting

### Issue 1: Hash Mismatch Error
**Solution:** Verify `PAYU_MERCHANT_SALT` is correct in `.env`

### Issue 2: Callback Not Received
**Solution:** 
- Check callback URL is publicly accessible
- Review `callback_logs` table in database
- Verify firewall settings

### Issue 3: Wallet Not Updated
**Solution:**
- Check transaction status is `SUCCESS`
- Review `merchant_wallet` table
- Check `wallet_transactions` table for entries

### Issue 4: Charge Calculation Error
**Solution:**
- Verify merchant has scheme assigned
- Check `commercial_charges` table
- Ensure amount falls within configured range

---

## Database Queries for Verification

### Check Transaction Status
```sql
SELECT * FROM payin_transactions 
WHERE merchant_id = '9876543210' 
ORDER BY created_at DESC;
```

### Check Wallet Balance
```sql
SELECT * FROM merchant_wallet 
WHERE merchant_id = '9876543210';
```

### Check Wallet Transactions
```sql
SELECT * FROM wallet_transactions 
WHERE merchant_id = '9876543210' 
ORDER BY created_at DESC;
```

### Check Callback Logs
```sql
SELECT * FROM callback_logs 
WHERE merchant_id = '9876543210' 
ORDER BY created_at DESC;
```

---

## Production Checklist

Before going live with real money transactions:

- [ ] PayU production credentials configured
- [ ] `PAYU_TEST_MODE=False` in `.env`
- [ ] Commercial schemes configured correctly
- [ ] Service routing configured for merchants
- [ ] Callback URLs configured and tested
- [ ] SSL certificate installed (HTTPS)
- [ ] Firewall rules configured
- [ ] Database backups enabled
- [ ] Monitoring and logging enabled
- [ ] Test transactions completed successfully
- [ ] Merchant onboarding process tested
- [ ] Wallet balance verification working
- [ ] Transaction reports accessible

---

## Support

For PayU related issues:
- PayU Documentation: https://docs.payu.in/
- PayU Support: support@payu.in

For Moneyone platform issues:
- Check application logs
- Review database tables
- Contact technical support

---

## Quick Test Script

Here's a complete test flow using curl:

```bash
# 1. Admin Login
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"adminId":"6239572985","password":"admin@123","captcha":"ABCD","sessionId":"test"}' \
  | jq -r '.token')

# 2. Merchant Login
MERCHANT_TOKEN=$(curl -s -X POST http://localhost:5000/api/merchant/login \
  -H "Content-Type: application/json" \
  -d '{"merchantId":"9876543210","password":"password","captcha":"ABCD","sessionId":"test"}' \
  | jq -r '.token')

# 3. Get Merchant Credentials
curl -H "Authorization: Bearer $MERCHANT_TOKEN" \
  http://localhost:5000/api/merchant/credentials

# 4. Check Wallet Balance
curl -H "Authorization: Bearer $MERCHANT_TOKEN" \
  http://localhost:5000/api/merchant/wallet/overview

# 5. Get Transactions
curl -H "Authorization: Bearer $MERCHANT_TOKEN" \
  http://localhost:5000/api/payin/transactions
```

---

**Happy Testing! 🚀**
