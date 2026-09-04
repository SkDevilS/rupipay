# Direct Payout API - Quick Testing Guide

## Overview

The Direct Payout API allows you to send IMPS/NEFT/RTGS payments to any bank account without pre-registering it. This is perfect for vendor payments, salary disbursements, or any ad-hoc payouts.

---

## API Endpoint

```
POST https://api.moneyone.co.in/api/payout/client/direct-payout
```

---

## Quick Test in Postman

### Step 1: Login to Get Token

```
POST https://api.moneyone.co.in/api/merchant/login

Body:
{
  "merchantId": "9000000001",
  "password": "your_password",
  "captcha": "ABCD",
  "sessionId": "test"
}
```

Copy the `token` from response.

### Step 2: Send Direct Payout

```
POST https://api.moneyone.co.in/api/payout/client/direct-payout

Headers:
Authorization: Bearer {your_token}
Content-Type: application/json

Body:
{
  "amount": 100.00,
  "tpin": "1234",
  "account_holder_name": "John Doe",
  "account_number": "1234567890",
  "ifsc_code": "SBIN0001234",
  "bank_name": "State Bank of India",
  "payment_type": "IMPS",
  "purpose": "Test Payment"
}
```

### Expected Response

```json
{
  "success": true,
  "message": "Payout initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "DP20250225120000ABC123",
  "amount": 100.00,
  "charges": 2.00,
  "net_amount": 98.00,
  "status": "QUEUED",
  "beneficiary": {
    "name": "John Doe",
    "account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India"
  }
}
```

---

## Request Parameters

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| amount | decimal | Payout amount | 1000.00 |
| tpin | string | 4-digit Transaction PIN | "1234" |
| account_holder_name | string | Beneficiary name | "John Doe" |
| account_number | string | Bank account number | "1234567890" |
| ifsc_code | string | Bank IFSC code | "SBIN0001234" |
| bank_name | string | Bank name | "State Bank of India" |

### Optional Fields

| Field | Type | Description | Default | Options |
|-------|------|-------------|---------|---------|
| payment_type | string | Payment mode | "IMPS" | IMPS, NEFT, RTGS |
| purpose | string | Payment purpose | "Payout" | Any text |
| bene_email | string | Beneficiary email | "" | email@example.com |
| bene_mobile | string | Beneficiary mobile | "" | "9876543210" |

---

## Payment Types

### IMPS (Immediate Payment Service)
- **Speed:** Instant (within seconds)
- **Availability:** 24x7 including holidays
- **Limit:** Up to ₹5,00,000 per transaction
- **Best for:** Urgent payments, small to medium amounts

### NEFT (National Electronic Funds Transfer)
- **Speed:** Within 2 hours
- **Availability:** 24x7 (processed in batches)
- **Limit:** No maximum limit
- **Best for:** Regular payments, any amount

### RTGS (Real Time Gross Settlement)
- **Speed:** Real-time (within 30 minutes)
- **Availability:** 7 AM to 6 PM on working days
- **Limit:** Minimum ₹2,00,000
- **Best for:** Large value transactions

---

## Response Fields

| Field | Description |
|-------|-------------|
| success | true/false indicating success |
| message | Human-readable message |
| txn_id | Your transaction ID for tracking |
| reference_id | Unique reference for this payout |
| amount | Total amount deducted from wallet |
| charges | Payout charges as per your scheme |
| net_amount | Amount sent to beneficiary bank |
| status | Current status (QUEUED, INITIATED, SUCCESS, FAILED) |
| beneficiary | Beneficiary details for confirmation |

---

## Status Values

| Status | Description |
|--------|-------------|
| INITIATED | Payout request created |
| QUEUED | Sent to payment gateway |
| INPROCESS | Being processed by bank |
| SUCCESS | Money credited to beneficiary |
| FAILED | Payout failed, amount refunded |
| REVERSED | Bank reversed the transaction |

---

## Error Handling

### Common Errors

**1. Invalid TPIN**
```json
{
  "success": false,
  "message": "Invalid TPIN"
}
```
**Solution:** Verify your 4-digit TPIN is correct

**2. Insufficient Balance**
```json
{
  "success": false,
  "message": "Insufficient balance. Required: ₹1000, Available: ₹500"
}
```
**Solution:** Add funds to your wallet first

**3. Invalid IFSC Code**
```json
{
  "success": false,
  "message": "Invalid IFSC code format"
}
```
**Solution:** Verify IFSC code is 11 characters (e.g., SBIN0001234)

**4. Missing Required Field**
```json
{
  "success": false,
  "message": "account_holder_name is required"
}
```
**Solution:** Ensure all required fields are provided

**5. Invalid Payment Type**
```json
{
  "success": false,
  "message": "Invalid payment_type. Must be IMPS, NEFT, or RTGS"
}
```
**Solution:** Use only IMPS, NEFT, or RTGS

---

## Testing Checklist

- [ ] Merchant login successful
- [ ] Token obtained and saved
- [ ] Wallet has sufficient balance
- [ ] TPIN is set and known
- [ ] All required fields provided
- [ ] Valid IFSC code format
- [ ] Valid payment type (IMPS/NEFT/RTGS)
- [ ] Amount is within limits
- [ ] Response received with txn_id
- [ ] Status can be tracked

---

## Sample cURL Command

```bash
curl -X POST https://api.moneyone.co.in/api/payout/client/direct-payout \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "tpin": "1234",
    "account_holder_name": "John Doe",
    "account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India",
    "payment_type": "IMPS",
    "purpose": "Test Payment"
  }'
```

---

## Sample Python Code

```python
import requests

# Login first
login_response = requests.post(
    'https://api.moneyone.co.in/api/merchant/login',
    json={
        'merchantId': '9000000001',
        'password': 'your_password',
        'captcha': 'ABCD',
        'sessionId': 'test'
    }
)
token = login_response.json()['token']

# Send payout
payout_response = requests.post(
    'https://api.moneyone.co.in/api/payout/client/direct-payout',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json={
        'amount': 100.00,
        'tpin': '1234',
        'account_holder_name': 'John Doe',
        'account_number': '1234567890',
        'ifsc_code': 'SBIN0001234',
        'bank_name': 'State Bank of India',
        'payment_type': 'IMPS',
        'purpose': 'Test Payment'
    }
)

print(payout_response.json())
```

---

## Sample Node.js Code

```javascript
const axios = require('axios');

async function sendPayout() {
  // Login first
  const loginResponse = await axios.post(
    'https://api.moneyone.co.in/api/merchant/login',
    {
      merchantId: '9000000001',
      password: 'your_password',
      captcha: 'ABCD',
      sessionId: 'test'
    }
  );
  
  const token = loginResponse.data.token;
  
  // Send payout
  const payoutResponse = await axios.post(
    'https://api.moneyone.co.in/api/payout/client/direct-payout',
    {
      amount: 100.00,
      tpin: '1234',
      account_holder_name: 'John Doe',
      account_number: '1234567890',
      ifsc_code: 'SBIN0001234',
      bank_name: 'State Bank of India',
      payment_type: 'IMPS',
      purpose: 'Test Payment'
    },
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  console.log(payoutResponse.data);
}

sendPayout();
```

---

## Tracking Payout Status

After initiating payout, track its status:

```
GET https://api.moneyone.co.in/api/payout/client/report?status=QUEUED
Authorization: Bearer {your_token}
```

Or get all payouts:

```
GET https://api.moneyone.co.in/api/payout/client/report
Authorization: Bearer {your_token}
```

---

## Important Notes

1. **Charges:** Payout charges are deducted from the amount before sending to bank
   - Example: ₹1000 payout with ₹10 charges = ₹1000 deducted from wallet, ₹990 sent to bank

2. **TPIN Security:** Never share your TPIN. It's like your ATM PIN.

3. **Balance Check:** Always check wallet balance before initiating payout.

4. **IFSC Validation:** Ensure IFSC code is correct to avoid failed transactions.

5. **Status Tracking:** Save the `txn_id` to track transaction status later.

6. **Webhook:** Configure webhook URL to receive real-time status updates.

---

## Support

For issues or questions:
- Email: support@moneyone.co.in
- Documentation: https://docs.moneyone.co.in

---

**Happy Testing! 🚀**
