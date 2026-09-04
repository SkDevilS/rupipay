"""
Backfill unsettled wallet for existing SUCCESS payin transactions
that were processed before the unsettled wallet feature was implemented
"""

from database import get_db_connection
from wallet_service import wallet_service

def backfill_unsettled_wallet(dry_run=True):
    """
    Backfill unsettled wallet for SUCCESS payins that don't have wallet transactions
    
    Args:
        dry_run: If True, only show what would be done without making changes
    """
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS payins that don't have corresponding UNSETTLED_CREDIT transactions
            cursor.execute("""
                SELECT 
                    p.txn_id,
                    p.merchant_id,
                    p.order_id,
                    p.amount,
                    p.charge_amount,
                    p.net_amount,
                    p.created_at,
                    p.completed_at
                FROM payin_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON p.txn_id = mwt.reference_id 
                    AND mwt.txn_type = 'UNSETTLED_CREDIT'
                WHERE p.status = 'SUCCESS'
                AND mwt.txn_id IS NULL
                ORDER BY p.created_at DESC
            """)
            
            missing_txns = cursor.fetchall()
            
            print("=" * 80)
            print("BACKFILL UNSETTLED WALLET")
            print("=" * 80)
            print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
            print(f"Found {len(missing_txns)} SUCCESS payins without UNSETTLED_CREDIT transactions")
            print()
            
            if not missing_txns:
                print("✓ All SUCCESS payins have corresponding wallet transactions")
                return
            
            total_amount = 0
            for txn in missing_txns:
                net_amount = float(txn['net_amount'])
                total_amount += net_amount
                
                print(f"TXN: {txn['txn_id']}")
                print(f"  Merchant: {txn['merchant_id']}")
                print(f"  Order: {txn['order_id']}")
                print(f"  Amount: ₹{txn['amount']:.2f}")
                print(f"  Charge: ₹{txn['charge_amount']:.2f}")
                print(f"  Net: ₹{net_amount:.2f}")
                print(f"  Created: {txn['created_at']}")
                print()
            
            print(f"Total net amount to backfill: ₹{total_amount:.2f}")
            print()
            
            if dry_run:
                print("=" * 80)
                print("DRY RUN - No changes made")
                print("=" * 80)
                print("To apply changes, run:")
                print("  python3 backfill_unsettled_wallet.py --apply")
                return
            
            # Apply backfill
            print("=" * 80)
            print("APPLYING BACKFILL")
            print("=" * 80)
            
            for txn in missing_txns:
                merchant_id = txn['merchant_id']
                net_amount = float(txn['net_amount'])
                
                # Get current unsettled balance
                cursor.execute("""
                    SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet_result = cursor.fetchone()
                
                if wallet_result:
                    unsettled_before = float(wallet_result['unsettled_balance'])
                    unsettled_after = unsettled_before + net_amount
                    
                    cursor.execute("""
                        UPDATE merchant_wallet
                        SET unsettled_balance = %s, last_updated = NOW()
                        WHERE merchant_id = %s
                    """, (unsettled_after, merchant_id))
                else:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, 0.00, 0.00, %s)
                    """, (merchant_id, net_amount))
                    unsettled_before = 0.00
                    unsettled_after = net_amount
                
                # Record wallet transaction
                wallet_txn_id = wallet_service.generate_txn_id('MWT')
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                """, (
                    merchant_id, 
                    wallet_txn_id, 
                    net_amount,
                    unsettled_before,
                    unsettled_after,
                    f"Backfilled: Payin credited to unsettled wallet - {txn['order_id']}",
                    txn['txn_id']
                ))
                
                print(f"✓ Backfilled {merchant_id}: ₹{net_amount:.2f} (before: ₹{unsettled_before:.2f}, after: ₹{unsettled_after:.2f})")
            
            conn.commit()
            
            print()
            print("=" * 80)
            print("BACKFILL COMPLETE")
            print("=" * 80)
            print(f"Processed {len(missing_txns)} transactions")
            print(f"Total amount backfilled: ₹{total_amount:.2f}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    # Check for --apply flag
    apply = '--apply' in sys.argv
    
    backfill_unsettled_wallet(dry_run=not apply)
