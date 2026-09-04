"""
Configure Vega callback URL
This script shows the current Vega callback configuration
"""

import os
from database import get_db_connection

def configure_vega_callback():
    """Show Vega callback URL configuration"""
    
    print("=" * 80)
    print("Vega Callback URL Configuration")
    print("=" * 80)
    
    # Get backend URL from environment
    backend_url = os.getenv('BACKEND_URL', 'https://admin.moneyone.co.in')
    mudrape_callback_url = f"{backend_url}/api/callback/mudrape/payin"
    
    print(f"Backend URL: {backend_url}")
    print(f"Configured Callback URL: {mudrape_callback_url}")
    
    print("\n" + "=" * 80)
    print("CURRENT SETUP - Vega uses Mudrape callback system")
    print("=" * 80)
    print(f"✅ Vega team is already configured to send callbacks to:")
    print(f"   {mudrape_callback_url}")
    print("\n✅ Our system now detects Vega transactions automatically")
    print("✅ Callbacks are processed and forwarded to merchants")
    print("✅ PG partner information is included in merchant callbacks")
    
    print("\n" + "=" * 80)
    print("How It Works")
    print("=" * 80)
    print("1. Vega sends callbacks to the Mudrape callback URL")
    print("2. System detects callback format:")
    print("   - Vega format: has 'referenceId' and 'orderId' fields")
    print("   - Mudrape format: has 'ref_id' field")
    print("3. System processes callback based on detected format")
    print("4. System finds transaction by referenceId (Vega) or ref_id (Mudrape)")
    print("5. If pg_partner = 'Vega', it's processed as a Vega transaction")
    print("6. Wallet credits and merchant callbacks work the same way")
    print("7. Merchant receives callback with pg_partner = 'Vega' or 'Mudrape'")
    
    print("\n" + "=" * 80)
    print("Callback Data Format Expected from Vega")
    print("=" * 80)
    print("Vega will send callbacks in this specific format:")
    print("""
    {
        "referenceId": "TRACK-1710000000000-ABCDEFG",  // Required - matches order_id in our DB
        "orderId": "VEGA_ORDER_123456",                // Optional - Vega's internal order ID
        "status": "SUCCESS",                           // Required - SUCCESS/FAILED
        "amount": 1,                                   // Required - transaction amount (number)
        "message": "Payment successful",               // Optional - status message
        "timestamp": "2026-03-10T09:25:44.418Z"       // Required - callback timestamp
    }
    """)
    
    print("\n" + "=" * 80)
    print("Mudrape Callback Format (Still Supported)")
    print("=" * 80)
    print("Regular Mudrape callbacks continue to work in existing format:")
    print("""
    {
        "ref_id": "MUDRAPE-REF-123456",               // Required - matches order_id in our DB
        "txn_id": "MUDRAPE_TXN_123456",               // Optional - Mudrape's txn ID
        "status": "SUCCESS",                          // Required - SUCCESS/FAILED/INITIATED
        "amount": 100.00,                             // Optional - transaction amount
        "utr": "UTR123456789",                        // Optional - bank reference number
        "source": "Mudrape",                          // Optional - source identifier
        "payeeVpa": "test@paytm",                     // Optional - payee VPA
        "timestamp": "2026-03-10T10:30:00Z"          // Optional - callback timestamp
    }
    """)
    
    print("\n" + "=" * 80)
    print("Merchant Callback Format")
    print("=" * 80)
    print("Merchants will receive callbacks in this format for Vega transactions:")
    print("""
    {
        "utr": "",                                     // Empty for Vega (not provided)
        "amount": 1.00,
        "ref_id": "TRACK-1710000000000-ABCDEFG",      // Vega's referenceId
        "source": "Vega",
        "status": "SUCCESS",
        "txn_id": "internal_txn_id",
        "pg_txn_id": "VEGA_ORDER_123456",             // Vega's orderId
        "pg_partner": "Vega",                         // Identifies this as Vega transaction
        "payeeVpa": "",                               // Empty for Vega
        "timestamp": "2026-03-10T09:25:44.418Z",
        "order_id": "TRACK-1710000000000-ABCDEFG"     // For backward compatibility
    }
    """)
    
    print("For Mudrape transactions, merchants receive:")
    print("""
    {
        "utr": "UTR123456789",
        "amount": 100.00,
        "ref_id": "MUDRAPE-REF-123456",
        "source": "Mudrape",
        "status": "SUCCESS",
        "txn_id": "internal_txn_id",
        "pg_txn_id": "MUDRAPE_TXN_123456",
        "pg_partner": "Mudrape",                      // Identifies this as Mudrape transaction
        "payeeVpa": "test@paytm",
        "timestamp": "2026-03-10T10:30:00Z",
        "order_id": "MUDRAPE-REF-123456"
    }
    """)
    
    # Check if there are any Vega transactions in the system
    print("\n" + "=" * 80)
    print("Current Vega Transactions")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM payin_transactions 
                    WHERE pg_partner = 'Vega'
                """)
                vega_count = cursor.fetchone()['count']
                
                print(f"Total Vega transactions in system: {vega_count}")
                
                if vega_count > 0:
                    cursor.execute("""
                        SELECT order_id, status, amount, created_at 
                        FROM payin_transactions 
                        WHERE pg_partner = 'Vega' 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """)
                    recent_txns = cursor.fetchall()
                    
                    print("\nRecent Vega transactions:")
                    for txn in recent_txns:
                        print(f"- Order ID: {txn['order_id']}, Status: {txn['status']}, Amount: {txn['amount']}")
                else:
                    print("No Vega transactions found yet.")
                    print("Create a test transaction first to verify the callback flow.")
        else:
            print("❌ Could not connect to database")
            
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")
    finally:
        if conn:
            conn.close()
    
    print("\n" + "=" * 80)
    print("Testing")
    print("=" * 80)
    print("1. Run test script to create test transaction and test callbacks:")
    print("   cd backend && python test_vega_callback.py")
    print("2. Monitor logs to ensure callbacks are received and processed")
    print("3. Verify merchant callback forwarding is working")
    print("4. Check that pg_partner = 'Vega' is included in merchant callbacks")
    
    print(f"\nConfigured callback URL: {mudrape_callback_url}")
    print("✅ No changes needed - Vega team already has this URL")

if __name__ == '__main__':
    configure_vega_callback()