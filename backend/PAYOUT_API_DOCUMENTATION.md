# Payout API Documentation

## Overview

The Payout API allows merchants to settle funds from their wallet to their registered bank accounts. This document covers the complete integration process and testing procedures.

---

## Base URL

```
Production: https://api.moneyone.co.in/api
Development: http://localhost:5000/api
```

---

## Authentication

All payout API requests require JWT authentication token obtained from merchant login.

### Headers Required

```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

---

## Endpoints

### 1. Direct Payout (IMPS/NEFT/RTGS)

Transfer funds directly to any bank account without pre-registration.

**Endpoint:** `POST /payout/client/direct-payout`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 1000.00,
  "tpin": "1234",
  "account_holder_name": "John Doe",
  "account_number": "1234567890",
  "ifsc_code": "SBIN0001234",
  "bank_name": "State Bank of India",
  "payment_type": "IMPS",
  "purpose": "Vendor Payment",
  "bene_email": "john@example.com",
  "bene_mobile": "9876543210"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| amount | decimal | Yes | Payout amount (must be ≤ available balance) |
| tpin | string | Yes | 4-digit Transaction PIN for security verification |
| account_holder_name | string | Yes | Beneficiary account holder name |
| account_number | string | Yes | Beneficiary bank account number |
| ifsc_code | string | Yes | Bank IFSC code |
| bank_name | string | Yes | Bank name |
| payment_type | string | No | Payment mode: IMPS, NEFT, or RTGS (default: IMPS) |
| purpose | string | No | Purpose of payment (default: "Payout") |
| bene_email | string | No | Beneficiary email address |
| bene_mobile | string | No | Beneficiary mobile number |

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Payout initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "DP20250225120000ABC123",
  "amount": 1000.00,
  "charges": 10.00,
  "net_amount": 990.00,
  "status": "QUEUED",
  "beneficiary": {
    "name": "John Doe",
    "account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India"
  }
}
```

**Error Responses:**

**400 Bad Request - Missing Fields:**
```json
{
  "success": false,
  "message": "account_holder_name is required"
}
```

**400 Bad Request - Invalid TPIN:**
```json
{
  "success": false,
  "message": "Invalid TPIN"
}
```

**400 Bad Request - Insufficient Balance:**
```json
{
  "success": false,
  "message": "Insufficient balance. Required: ₹1000, Available: ₹500"
}
```

**400 Bad Request - Invalid Payment Type:**
```json
{
  "success": false,
  "message": "Invalid payment_type. Must be IMPS, NEFT, or RTGS"
}
```

---

### 2. Settle Fund (Payout to Bank)

Transfer funds from merchant wallet to registered bank account.

**Endpoint:** `POST /payout/client/settle-fund`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "bank_id": 1,
  "amount": 1000.00,
  "tpin": "1234"
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| bank_id | integer | Yes | ID of the registered bank account |
| amount | decimal | Yes | Amount to settle (must be ≤ available balance) |
| tpin | string | Yes | 4-digit Transaction PIN for security verification |

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Settlement initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "ADMIN20250225120000ABC123"
}
```

**Error Responses:**

**400 Bad Request - Missing Fields:**
```json
{
  "success": false,
  "message": "bank_id is required"
}
```

**400 Bad Request - Invalid TPIN:**
```json
{
  "success": false,
  "message": "Invalid TPIN"
}
```

**400 Bad Request - TPIN Not Set:**
```json
{
  "success": false,
  "message": "TPIN not set"
}
```

**400 Bad Request - Insufficient Balance:**
```json
{
  "success": false,
  "message": "Insufficient balance. Required: ₹1000, Available: ₹500"
}
```

**404 Not Found - Bank Not Found:**
```json
{
  "success": false,
  "message": "Bank not found"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "message": "Database connection failed"
}
```

---

### 2. Get Bank Accounts

Retrieve list of registered bank accounts for the merchant.

**Endpoint:** `GET /merchant/banks`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "banks": [
    {
      "id": 1,
      "bank_name": "State Bank of India",
      "account_number": "1234567890",
      "ifsc_code": "SBIN0001234",
      "branch_name": "New Delhi Branch",
      "account_holder_name": "John Doe",
      "is_active": true,
      "created_at": "2025-02-20 10:30:00"
    }
  ]
}
```

---

### 3. Get Wallet Balance

Check available wallet balance before initiating payout.

**Endpoint:** `GET /merchant/wallet/overview`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "balance": 5000.00,
  "totalPayin": 10000.00,
  "totalPayout": 5000.00,
  "merchantId": "9000000001"
}
```

---

### 4. Get Payout Report

Retrieve payout transaction history.

**Endpoint:** `GET /payout/client/report?page=1&limit=50&status=SUCCESS`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Records per page (default: 50) |
| status | string | No | Filter by status (SUCCESS, FAILED, QUEUED, etc.) |
| from_date | string | No | Start date (YYYY-MM-DD) |
| to_date | string | No | End date (YYYY-MM-DD) |

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "txn_id": "TXN1A2B3C4D5E6F7",
      "reference_id": "ADMIN20250225120000ABC123",
      "amount": 1000.00,
      "charge_amount": 10.00,
      "net_amount": 990.00,
      "bene_name": "John Doe",
      "bene_bank": "State Bank of India",
      "account_no": "1234567890",
      "ifsc_code": "SBIN0001234",
      "payment_type": "IMPS",
      "status": "SUCCESS",
      "utr": "123456789012",
      "created_at": "2025-02-25 12:00:00",
      "completed_at": "2025-02-25 12:05:00"
    }
  ]
}
```

---

### 5. Get Payout Statistics

Get payout transaction statistics by status.

**Endpoint:** `GET /payout/client/stats`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "stats": {
    "success": {
      "count": 10,
      "amount": 50000.00
    },
    "pending": {
      "count": 2,
      "amount": 5000.00
    },
    "failed": {
      "count": 1,
      "amount": 1000.00
    },
    "queued": {
      "count": 3,
      "amount": 10000.00
    }
  }
}
```

---

### 6. Check Payout Status (Real-time)

Check real-time payout status from payment gateway and automatically update database.

**Endpoint:** `POST /payout/client/check-status/{txn_id}`

**Request Headers:**
```
Authorization: Bearer {merchant_token}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| txn_id | string | Yes | Transaction ID from payout initiation response |

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Status checked and updated successfully",
  "data": {
    "txn_id": "TXN1A2B3C4D5E6F7",
    "reference_id": "DP20250225120000ABC123",
    "amount": 1000.00,
    "status": "SUCCESS",
    "utr": "402512345678",
    "pg_txn_id": "MUDRAPE_TXN_123456",
    "created_at": "2025-02-25 12:00:00",
    "completed_at": "2025-02-25 12:00:15"
  }
}
```

**Error Responses:**

**404 Not Found - Transaction Not Found:**
```json
{
  "success": false,
  "message": "Transaction not found or unauthorized"
}
```

**400 Bad Request - Not Mudrape Transaction:**
```json
{
  "success": false,
  "message": "Only Mudrape transactions can be checked"
}
```

**400 Bad Request - Gateway Error:**
```json
{
  "success": false,
  "message": "Failed to check status from Mudrape"
}
```

**Use Cases:**
- Add "Check Status" button in your payout dashboard
- Poll for status updates on pending transactions
- Get real-time status without waiting for webhooks
- Verify transaction completion with UTR

**Important Notes:**
- This endpoint queries the payment gateway directly
- Database is automatically updated with latest status
- Only works for Mudrape transactions
- Can only check your own transactions
- Recommended polling interval: 30 seconds

---

## Payout Flow

### Step-by-Step Process

1. **Merchant Login**
   - Obtain JWT token via `/api/merchant/login`

2. **Check Wallet Balance**
   - GET `/api/merchant/wallet/overview`
   - Ensure sufficient balance for payout

3. **Get Bank Accounts**
   - GET `/api/merchant/banks`
   - Select bank account for settlement

4. **Initiate Payout**
   - POST `/api/payout/client/settle-fund`
   - Provide bank_id, amount, and TPIN

5. **Track Status**
   - GET `/api/payout/client/report`
   - Monitor transaction status

---

## Payout Status Values

| Status | Description |
|--------|-------------|
| INITIATED | Payout request created, pending processing |
| QUEUED | Payout queued with payment gateway |
| INPROCESS | Payout being processed by bank |
| SUCCESS | Payout completed successfully |
| FAILED | Payout failed (amount refunded to wallet) |
| REVERSED | Payout reversed by bank (amount refunded) |

---

## Payout Charges

Payout charges are deducted based on your commercial scheme:

**Example:**
- Settlement Amount: ₹1000
- Payout Charge: ₹10 (1% or fixed)
- Amount Deducted from Wallet: ₹1000
- Amount Sent to Bank: ₹990

**Note:** The full settlement amount is deducted from your wallet, and charges are applied before sending to the bank.

---

## Testing with Postman

### Prerequisites

1. Install Postman: https://www.postman.com/downloads/
2. Have merchant credentials ready
3. Ensure TPIN is set for your merchant account

### Step 1: Merchant Login

**Request:**
```
POST https://api.moneyone.co.in/api/merchant/login
Content-Type: application/json

{
  "merchantId": "9000000001",
  "password": "your_password",
  "captcha": "ABCD",
  "sessionId": "test_session"
}
```

**Save the token from response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "merchantId": "9000000001"
}
```

### Step 2: Get Bank Accounts

**Request:**
```
GET https://api.moneyone.co.in/api/merchant/banks
Authorization: Bearer {token_from_step_1}
```

**Note the bank ID from response:**
```json
{
  "success": true,
  "banks": [
    {
      "id": 1,
      "bank_name": "State Bank of India",
      "account_number": "1234567890"
    }
  ]
}
```

### Step 3: Check Wallet Balance

**Request:**
```
GET https://api.moneyone.co.in/api/merchant/wallet/overview
Authorization: Bearer {token_from_step_1}
```

**Response:**
```json
{
  "success": true,
  "balance": 5000.00
}
```

### Step 4A: Direct Payout (Recommended)

Send payout to any bank account without pre-registration:

**Request:**
```
POST https://api.moneyone.co.in/api/payout/client/direct-payout
Authorization: Bearer {token_from_step_1}
Content-Type: application/json

{
  "amount": 1000.00,
  "tpin": "1234",
  "account_holder_name": "John Doe",
  "account_number": "1234567890",
  "ifsc_code": "SBIN0001234",
  "bank_name": "State Bank of India",
  "payment_type": "IMPS",
  "purpose": "Vendor Payment"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Payout initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "DP20250225120000ABC123",
  "amount": 1000.00,
  "charges": 10.00,
  "net_amount": 990.00,
  "status": "QUEUED",
  "beneficiary": {
    "name": "John Doe",
    "account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India"
  }
}
```

### Step 4B: Settle to Registered Bank (Alternative)

Use pre-registered bank account:

**Request:**
```
POST https://api.moneyone.co.in/api/payout/client/settle-fund
Authorization: Bearer {token_from_step_1}
Content-Type: application/json

{
  "bank_id": 1,
  "amount": 1000.00,
  "tpin": "1234"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Settlement initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "ADMIN20250225120000ABC123"
}
```

### Step 5: Check Payout Status

**Request:**
```
POST https://api.moneyone.co.in/api/payout/client/check-status/TXN1A2B3C4D5E6F7
Authorization: Bearer {token_from_step_1}
```

**Response:**
```json
{
  "success": true,
  "message": "Status checked and updated successfully",
  "data": {
    "txn_id": "TXN1A2B3C4D5E6F7",
    "reference_id": "DP20250225120000ABC123",
    "amount": 1000.00,
    "status": "SUCCESS",
    "utr": "402512345678",
    "created_at": "2025-02-25 12:00:00",
    "completed_at": "2025-02-25 12:00:15"
  }
}
```

### Step 6: View Payout Report

**Request:**
```
GET https://api.moneyone.co.in/api/payout/client/report?status=QUEUED
Authorization: Bearer {token_from_step_1}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "txn_id": "TXN1A2B3C4D5E6F7",
      "amount": 1000.00,
      "status": "SUCCESS",
      "utr": "402512345678",
      "created_at": "2025-02-25 12:00:00",
      "completed_at": "2025-02-25 12:00:15"
    }
  ]
}
```

---

## Postman Collection

### Import This Collection

Create a new collection in Postman and add these requests:

**Collection Variables:**
- `base_url`: https://api.moneyone.co.in/api
- `merchant_token`: (will be set after login)

**Requests:**

1. **Merchant Login**
   - Method: POST
   - URL: `{{base_url}}/merchant/login`
   - Body: Raw JSON
   - Test Script: `pm.environment.set("merchant_token", pm.response.json().token);`

2. **Get Banks**
   - Method: GET
   - URL: `{{base_url}}/merchant/banks`
   - Headers: `Authorization: Bearer {{merchant_token}}`

3. **Get Wallet Balance**
   - Method: GET
   - URL: `{{base_url}}/merchant/wallet/overview`
   - Headers: `Authorization: Bearer {{merchant_token}}`

4. **Settle Fund**
   - Method: POST
   - URL: `{{base_url}}/payout/client/settle-fund`
   - Headers: `Authorization: Bearer {{merchant_token}}`
   - Body: Raw JSON

5. **Check Payout Status**
   - Method: POST
   - URL: `{{base_url}}/payout/client/check-status/TXN1A2B3C4D5E6F7`
   - Headers: `Authorization: Bearer {{merchant_token}}`
   - Note: Replace TXN1A2B3C4D5E6F7 with actual transaction ID

6. **Get Payout Report**
   - Method: GET
   - URL: `{{base_url}}/payout/client/report`
   - Headers: `Authorization: Bearer {{merchant_token}}`

---

## Error Handling

### Common Errors and Solutions

**1. "Invalid TPIN"**
- Solution: Verify TPIN is correct (4 digits)
- Reset TPIN if forgotten via merchant dashboard

**2. "TPIN not set"**
- Solution: Set TPIN first via merchant dashboard (Security > Change PIN)

**3. "Insufficient balance"**
- Solution: Ensure wallet has enough balance
- Check available balance via wallet overview API

**4. "Bank not found"**
- Solution: Verify bank_id is correct
- Get valid bank IDs from banks API

**5. "Unauthorized"**
- Solution: Token expired, login again to get new token

**6. "Payment gateway not configured"**
- Solution: Contact admin to configure service routing for PAYOUT

---

## Security Best Practices

1. **Never share TPIN**
   - TPIN is like ATM PIN, keep it confidential

2. **Use HTTPS only**
   - Always use secure connection (https://)

3. **Token Management**
   - Store tokens securely
   - Tokens expire after 1 hour
   - Refresh token before expiry

4. **Validate Amounts**
   - Always validate amount before submission
   - Check wallet balance first

5. **Monitor Transactions**
   - Regularly check payout reports
   - Set up alerts for failed transactions

---

## Webhook/Callback (Optional)

Configure callback URL to receive payout status updates:

**Endpoint:** `PUT /merchant/callbacks`

**Request:**
```json
{
  "payinCallbackUrl": "",
  "payoutCallbackUrl": "https://your-domain.com/payout-callback"
}
```

**Callback Payload (Sent to Your URL):**
```json
{
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "ADMIN20250225120000ABC123",
  "amount": "1000.00",
  "status": "SUCCESS",
  "utr": "123456789012",
  "timestamp": "2025-02-25T12:05:00"
}
```

---

## Rate Limits

- Maximum 100 requests per minute per merchant
- Maximum 1000 payouts per day per merchant
- Minimum payout amount: ₹100
- Maximum payout amount: ₹50,000 per transaction

---

## Support

For technical support:
- Email: support@moneyone.co.in
- Documentation: https://docs.moneyone.co.in
- Status Page: https://status.moneyone.co.in

---

## Changelog

### Version 1.0.0 (2025-02-25)
- Initial release
- Settle fund endpoint
- Bank management
- Payout reporting
- Statistics API

---

**Happy Integrating! 🚀**
