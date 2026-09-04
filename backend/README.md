# MoneyOne Admin Backend

Python Flask backend for MoneyOne Admin Panel with JWT authentication and CAPTCHA verification.

## Features

- JWT Token-based authentication
- CAPTCHA verification for login
- Secure password hashing with bcrypt
- Activity logging
- Account lockout after failed attempts
- MySQL database integration

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Database

Edit `.env` file with your MySQL credentials:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=moneyone_db
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
```

### 3. Run the Application

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 4. Default Admin Credentials

- Admin ID: `6239572985`
- Password: `admin@123`

## API Endpoints

### Public Endpoints

- `GET /api/admin/captcha` - Generate CAPTCHA
- `POST /api/admin/login` - Admin login
- `GET /api/admin/health` - Health check

### Protected Endpoints (Require JWT Token)

- `GET /api/admin/verify` - Verify JWT token
- `POST /api/admin/logout` - Admin logout
- `GET /api/admin/activity-logs` - Get activity logs

## Security Features

- Password hashing with bcrypt
- JWT token expiration (1 hour)
- CAPTCHA verification
- Account lockout after 5 failed attempts (15 minutes)
- Activity logging with IP and user agent
- CORS protection

## Database Schema

### admin_users
- id (Primary Key)
- admin_id (Unique)
- password_hash
- is_active
- created_at
- last_login
- login_attempts
- locked_until

### admin_activity_logs
- id (Primary Key)
- admin_id (Foreign Key)
- action
- ip_address
- user_agent
- status
- created_at


---

## PayU Payin Integration

Complete PayU payment gateway integration for merchant payin transactions.

### Quick Start Testing

1. **Configure PayU credentials in `.env`:**
```env
PAYU_MERCHANT_KEY=your_merchant_key
PAYU_MERCHANT_SALT=your_merchant_salt
PAYU_BASE_URL=https://test.payu.in
PAYU_TEST_MODE=True
```

2. **Test APIs with Postman:**
   - See **QUICK_API_TEST.md** for step-by-step guide
   - Login → Create order → Complete payment → Verify

3. **Complete a payment:**
```bash
# Use test script to simulate PayU callback
python test_payment_callback.py <txn_id> success
```

### Documentation Files

| File | Purpose |
|------|---------|
| **QUICK_API_TEST.md** | Quick start guide for API testing with Postman |
| **COMPLETE_PAYMENT_GUIDE.md** | How to complete payments (INITIATED → SUCCESS) |
| **API_TESTING_GUIDE.md** | Comprehensive API documentation |
| **PAYIN_INTEGRATION.md** | PayU integration technical details |
| **test_payment_callback.py** | Script to simulate PayU callbacks |
| **manual_complete_payment.sql** | SQL queries for manual payment completion |

### Payin API Endpoints

**Merchant APIs (Encrypted):**
- `POST /api/payin/order/create` - Create payment order
- `GET /api/payin/status/{txn_id}` - Check transaction status
- `GET /api/payin/transactions` - View all transactions
- `GET /api/merchant/wallet/overview` - Check wallet balance

**Admin APIs:**
- `GET /api/payin/admin/transactions` - View all merchant transactions
- `GET /api/payin/admin/pending` - View pending transactions

**PayU Callbacks:**
- `POST /api/payin/callback/success` - PayU success callback
- `POST /api/payin/callback/failure` - PayU failure callback

**Service Routing:**
- `GET /api/service-routing/config` - Get routing configuration
- `POST /api/service-routing/config` - Configure payment gateway routing

### Testing Flow

```
1. Login (Merchant)
   ↓
2. Create Payin Order (encrypted payload)
   ↓
   Status: INITIATED
   ↓
3. Complete Payment
   - Option A: Test script (recommended)
     python test_payment_callback.py <txn_id> success
   - Option B: Manual SQL (see manual_complete_payment.sql)
   - Option C: Real payment (use payment_url)
   ↓
   Status: SUCCESS
   Wallet: +net_amount (amount - charges)
   ↓
4. Verify
   - Check transaction status
   - Check wallet balance
```

### Database Tables (Payin)

- `payin_transactions` - Payment transaction records
- `merchant_wallet` - Merchant wallet balances
- `wallet_transactions` - Wallet transaction history
- `service_routing` - Payment gateway routing configuration
- `callback_logs` - Callback attempt logs
- `commercial_schemes` - Charge configuration
- `commercial_charges` - Charge rules

### Common Issues

**"All fields are required" error in encrypt API:**
- Use "raw" body type with "JSON" format in Postman
- Don't use form-data

**Payment stuck in INITIATED status:**
- Use `test_payment_callback.py` to simulate completion
- Or manually update database using SQL queries in `manual_complete_payment.sql`

**Token expired:**
- Login again to get a new JWT token

### Get Started

👉 **Start here:** Open `QUICK_API_TEST.md` for step-by-step API testing guide
