#!/usr/bin/env python3
"""
Check if pg_txn_id exists and is populated for older transactions
"""
from app import app, db
from sqlalchemy import text

def check_pg_txn_id():
    with app.app_context():
        try:
            # Check if pg_txn_id column exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'payin_transactions' 
                AND column_name = 'pg_txn_id'
            """))
            
            column_exists = result.fetchone()
            
            if not column_exists:
                print("❌ pg_txn_id column does NOT exist in payin_transactions table")
                print("\nYou need to add this column first!")
                return
            
            print("✅ pg_txn_id column exists\n")
            
            # Check total transactions
            result = db.session.execute(text("SELECT COUNT(*) FROM payin_transactions"))
            total = result.fetchone()[0]
            print(f"Total payin transactions: {total}")
            
            # Check transactions with pg_txn_id
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM payin_transactions 
                WHERE pg_txn_id IS NOT NULL AND pg_txn_id != ''
            """))
            with_pg_txn_id = result.fetchone()[0]
            print(f"Transactions with pg_txn_id: {with_pg_txn_id}")
            
            # Check transactions without pg_txn_id
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM payin_transactions 
                WHERE pg_txn_id IS NULL OR pg_txn_id = ''
            """))
            without_pg_txn_id = result.fetchone()[0]
            print(f"Transactions without pg_txn_id: {without_pg_txn_id}")
            
            # Check transactions with UTR
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM payin_transactions 
                WHERE utr IS NOT NULL AND utr != ''
            """))
            with_utr = result.fetchone()[0]
            print(f"Transactions with UTR: {with_utr}")
            
            # Check transactions without UTR but with pg_txn_id
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM payin_transactions 
                WHERE (utr IS NULL OR utr = '') 
                AND (pg_txn_id IS NOT NULL AND pg_txn_id != '')
            """))
            no_utr_but_pg_txn = result.fetchone()[0]
            print(f"Transactions without UTR but with pg_txn_id: {no_utr_but_pg_txn}")
            
            # Check transactions without both UTR and pg_txn_id
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM payin_transactions 
                WHERE (utr IS NULL OR utr = '') 
                AND (pg_txn_id IS NULL OR pg_txn_id = '')
            """))
            no_utr_no_pg_txn = result.fetchone()[0]
            print(f"Transactions without both UTR and pg_txn_id: {no_utr_no_pg_txn}")
            
            print("\n" + "="*60)
            print("SAMPLE DATA (Last 10 transactions)")
            print("="*60)
            
            # Show sample of recent transactions
            result = db.session.execute(text("""
                SELECT 
                    txn_id,
                    status,
                    utr,
                    bank_ref_no,
                    pg_txn_id,
                    created_at
                FROM payin_transactions 
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            
            rows = result.fetchall()
            for row in rows:
                txn_id, status, utr, bank_ref_no, pg_txn_id, created_at = row
                print(f"\nTXN: {txn_id}")
                print(f"  Status: {status}")
                print(f"  UTR: {utr or 'NULL'}")
                print(f"  Bank Ref: {bank_ref_no or 'NULL'}")
                print(f"  PG TXN ID: {pg_txn_id or 'NULL'}")
                print(f"  Date: {created_at}")
                
                # Show what will be displayed
                display_value = utr or bank_ref_no or pg_txn_id or '-'
                print(f"  → Will display: {display_value}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_pg_txn_id()
