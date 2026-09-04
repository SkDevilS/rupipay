"""
Script to check payin transaction charge structure
This will help us understand how charges are stored in the database
"""

from database import get_db_connection

def check_payin_structure():
    conn = get_db_connection()
    
    if not conn:
        print("Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get a few sample payin transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    amount,
                    charge_amount,
                    status,
                    created_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                AND charge_amount > 0
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            payins = cursor.fetchall()
            
            print("\n" + "="*80)
            print("PAYIN TRANSACTION CHARGE STRUCTURE ANALYSIS")
            print("="*80)
            
            if not payins:
                print("\nNo payin transactions found with charges")
                return
            
            print(f"\nFound {len(payins)} sample transactions:\n")
            
            for payin in payins:
                print(f"Transaction ID: {payin['txn_id']}")
                print(f"  Amount:        ₹{payin['amount']:,.2f}")
                print(f"  Charge Amount: ₹{payin['charge_amount']:,.2f}")
                print(f"  Status:        {payin['status']}")
                print(f"  Created:       {payin['created_at']}")
                
                # Calculate what merchant should receive
                merchant_receives = float(payin['amount']) - float(payin['charge_amount'])
                print(f"  Merchant Gets: ₹{merchant_receives:,.2f}")
                print(f"  Charge %:      {(float(payin['charge_amount'])/float(payin['amount'])*100):.2f}%")
                print()
            
            print("\n" + "="*80)
            print("INTERPRETATION:")
            print("="*80)
            print("\nIf 'amount' field includes charges:")
            print("  - Customer pays: amount")
            print("  - Merchant gets: amount - charge_amount")
            print("  - This is the CORRECT structure")
            print("\nIf 'amount' field is base amount (without charges):")
            print("  - Customer pays: amount + charge_amount")
            print("  - Merchant gets: amount")
            print("  - This would be INCORRECT for our current logic")
            print("\n" + "="*80)
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_payin_structure()
