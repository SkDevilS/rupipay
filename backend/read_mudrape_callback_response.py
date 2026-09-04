#!/usr/bin/env python3
"""
Script to read and analyze Mudrape callback responses with PG transaction IDs
Useful for debugging callback issues and verifying data flow
"""

import sys
from database import get_db_connection
from datetime import datetime, timedelta
import json

def format_datetime(dt):
    """Format datetime for display"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def read_payout_callbacks(pg_txn_id=None, client_txn_id=None, limit=10, hours=24):
    """
    Read Mudrape payout callback responses
    
    Args:
        pg_txn_id: Mudrape transaction ID (optional)
        client_txn_id: Our reference_id (optional)
        limit: Number of records to fetch
        hours: Look back this many hours
    """
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 100)
            print("MUDRAPE PAYOUT CALLBACK RESPONSES")
            print("=" * 100)
            
            # Build query based on filters
            query = """
                SELECT 
                    pt.txn_id,
                    pt.reference_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.total_deduction,
                    pt.status,
                    pt.payout_mode,
                    pt.beneficiary_name,
                    pt.beneficiary_account,
                    pt.pg_partner,
                    pt.pg_txn_id,
                    pt.utr,
                    pt.created_at,
                    pt.completed_at,
                    pt.updated_at,
                    m.full_name as merchant_name
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.pg_partner = 'Mudrape'
            """
            params = []
            
            if pg_txn_id:
                query += " AND pt.pg_txn_id = %s"
                params.append(pg_txn_id)
            elif client_txn_id:
                query += " AND pt.reference_id = %s"
                params.append(client_txn_id)
            else:
                # Look back specified hours
                query += " AND pt.created_at >= NOW() - INTERVAL %s HOUR"
                params.append(hours)
            
            query += " ORDER BY pt.created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo transactions found matching the criteria")
                print("=" * 100)
                return
            
            print(f"\nFound {len(transactions)} transaction(s)\n")
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{'─' * 100}")
                print(f"TRANSACTION #{idx}")
                print(f"{'─' * 100}")
                
                print(f"\n📋 Transaction Details:")
                print(f"   TXN ID:           {txn['txn_id']}")
                print(f"   Reference ID:     {txn['reference_id']} (Client TXN ID)")
                print(f"   Merchant:         {txn['merchant_name']} ({txn['merchant_id']})")
                print(f"   Status:           {txn['status']}")
                
                print(f"\n💰 Amount Details:")
                print(f"   Amount:           ₹{float(txn['amount']):.2f}")
                print(f"   Charge:           ₹{float(txn['charge_amount']):.2f}")
                print(f"   Total Deduction:  ₹{float(txn['total_deduction']):.2f}")
                
                print(f"\n🏦 Payout Details:")
                print(f"   Mode:             {txn['payout_mode']}")
                print(f"   Beneficiary:      {txn['beneficiary_name']}")
                print(f"   Account:          {txn['beneficiary_account']}")
                
                print(f"\n🔗 Gateway Details:")
                print(f"   PG Partner:       {txn['pg_partner']}")
                print(f"   PG TXN ID:        {txn['pg_txn_id'] if txn['pg_txn_id'] else 'NOT SET'}")
                print(f"   UTR:              {txn['utr'] if txn['utr'] else 'NOT SET'}")
                
                print(f"\n⏰ Timestamps:")
                print(f"   Created:          {format_datetime(txn['created_at'])}")
                print(f"   Completed:        {format_datetime(txn['completed_at'])}")
                print(f"   Last Updated:     {format_datetime(txn['updated_at'])}")
                
                # Check callback logs for this transaction
                cursor.execute("""
                    SELECT 
                        callback_url,
                        request_data,
                        response_code,
                        response_data,
                        created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (txn['txn_id'],))
                
                callback_logs = cursor.fetchall()
                
                if callback_logs:
                    print(f"\n📞 Callback Logs ({len(callback_logs)} found):")
                    for log_idx, log in enumerate(callback_logs, 1):
                        print(f"\n   Callback #{log_idx}:")
                        print(f"   URL:              {log['callback_url']}")
                        print(f"   Response Code:    {log['response_code']}")
                        print(f"   Timestamp:        {format_datetime(log['created_at'])}")
                        
                        # Parse request data
                        try:
                            request_data = json.loads(log['request_data'])
                            print(f"   Request Data:")
                            print(f"      Status:        {request_data.get('status')}")
                            print(f"      UTR:           {request_data.get('utr')}")
                            print(f"      PG TXN ID:     {request_data.get('pg_txn_id')}")
                        except:
                            print(f"   Request Data:     {log['request_data'][:100]}...")
                        
                        if log['response_data']:
                            print(f"   Response:         {log['response_data'][:200]}...")
                else:
                    print(f"\n📞 Callback Logs:    No callbacks sent yet")
                
                # Check if this is a recent update
                if txn['updated_at']:
                    time_since_update = datetime.now() - txn['updated_at']
                    if time_since_update.total_seconds() < 300:  # Less than 5 minutes
                        print(f"\n⚡ RECENT UPDATE: Updated {int(time_since_update.total_seconds())} seconds ago")
            
            print(f"\n{'=' * 100}")
            
    finally:
        conn.close()

def read_payin_callbacks(pg_txn_id=None, order_id=None, limit=10, hours=24):
    """
    Read Mudrape payin callback responses
    
    Args:
        pg_txn_id: Mudrape transaction ID (optional)
        order_id: Our order_id (optional)
        limit: Number of records to fetch
        hours: Look back this many hours
    """
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 100)
            print("MUDRAPE PAYIN CALLBACK RESPONSES")
            print("=" * 100)
            
            # Build query based on filters
            query = """
                SELECT 
                    pt.txn_id,
                    pt.order_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.net_amount,
                    pt.charge_amount,
                    pt.status,
                    pt.pg_partner,
                    pt.pg_txn_id,
                    pt.bank_ref_no as utr,
                    pt.created_at,
                    pt.completed_at,
                    pt.updated_at,
                    m.full_name as merchant_name
                FROM payin_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.pg_partner = 'Mudrape'
            """
            params = []
            
            if pg_txn_id:
                query += " AND pt.pg_txn_id = %s"
                params.append(pg_txn_id)
            elif order_id:
                query += " AND pt.order_id = %s"
                params.append(order_id)
            else:
                # Look back specified hours
                query += " AND pt.created_at >= NOW() - INTERVAL %s HOUR"
                params.append(hours)
            
            query += " ORDER BY pt.created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo transactions found matching the criteria")
                print("=" * 100)
                return
            
            print(f"\nFound {len(transactions)} transaction(s)\n")
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{'─' * 100}")
                print(f"TRANSACTION #{idx}")
                print(f"{'─' * 100}")
                
                print(f"\n📋 Transaction Details:")
                print(f"   TXN ID:           {txn['txn_id']}")
                print(f"   Order ID:         {txn['order_id']}")
                print(f"   Merchant:         {txn['merchant_name']} ({txn['merchant_id']})")
                print(f"   Status:           {txn['status']}")
                
                print(f"\n💰 Amount Details:")
                print(f"   Amount:           ₹{float(txn['amount']):.2f}")
                print(f"   Net Amount:       ₹{float(txn['net_amount']):.2f}")
                print(f"   Charge:           ₹{float(txn['charge_amount']):.2f}")
                
                print(f"\n🔗 Gateway Details:")
                print(f"   PG Partner:       {txn['pg_partner']}")
                print(f"   PG TXN ID:        {txn['pg_txn_id'] if txn['pg_txn_id'] else 'NOT SET'}")
                print(f"   UTR:              {txn['utr'] if txn['utr'] else 'NOT SET'}")
                
                print(f"\n⏰ Timestamps:")
                print(f"   Created:          {format_datetime(txn['created_at'])}")
                print(f"   Completed:        {format_datetime(txn['completed_at'])}")
                print(f"   Last Updated:     {format_datetime(txn['updated_at'])}")
                
                # Check wallet transactions
                cursor.execute("""
                    SELECT 
                        txn_id,
                        txn_type,
                        amount,
                        balance_before,
                        balance_after,
                        description,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    print(f"\n💳 Wallet Transactions ({len(wallet_txns)} found):")
                    for wtxn in wallet_txns:
                        print(f"   - {wtxn['txn_type']}: ₹{float(wtxn['amount']):.2f}")
                        print(f"     Balance: ₹{float(wtxn['balance_before']):.2f} → ₹{float(wtxn['balance_after']):.2f}")
                        print(f"     Time: {format_datetime(wtxn['created_at'])}")
                else:
                    print(f"\n💳 Wallet Transactions: None found")
                
                # Check callback logs
                cursor.execute("""
                    SELECT 
                        callback_url,
                        request_data,
                        response_code,
                        response_data,
                        created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (txn['txn_id'],))
                
                callback_logs = cursor.fetchall()
                
                if callback_logs:
                    print(f"\n📞 Callback Logs ({len(callback_logs)} found):")
                    for log_idx, log in enumerate(callback_logs, 1):
                        print(f"\n   Callback #{log_idx}:")
                        print(f"   URL:              {log['callback_url']}")
                        print(f"   Response Code:    {log['response_code']}")
                        print(f"   Timestamp:        {format_datetime(log['created_at'])}")
                        
                        # Parse request data
                        try:
                            request_data = json.loads(log['request_data'])
                            print(f"   Request Data:")
                            print(f"      Status:        {request_data.get('status')}")
                            print(f"      Amount:        ₹{request_data.get('amount')}")
                            print(f"      UTR:           {request_data.get('utr')}")
                            print(f"      PG TXN ID:     {request_data.get('pg_txn_id')}")
                        except:
                            print(f"   Request Data:     {log['request_data'][:100]}...")
                        
                        if log['response_data']:
                            print(f"   Response:         {log['response_data'][:200]}...")
                else:
                    print(f"\n📞 Callback Logs:    No callbacks sent yet")
                
                # Check if this is a recent update
                if txn['updated_at']:
                    time_since_update = datetime.now() - txn['updated_at']
                    if time_since_update.total_seconds() < 300:  # Less than 5 minutes
                        print(f"\n⚡ RECENT UPDATE: Updated {int(time_since_update.total_seconds())} seconds ago")
            
            print(f"\n{'=' * 100}")
            
    finally:
        conn.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Read recent payout callbacks:")
        print("    python3 read_mudrape_callback_response.py payout [--limit 10] [--hours 24]")
        print("")
        print("  Read specific payout by PG TXN ID:")
        print("    python3 read_mudrape_callback_response.py payout --pg-txn-id <mudrape_txn_id>")
        print("")
        print("  Read specific payout by Client TXN ID:")
        print("    python3 read_mudrape_callback_response.py payout --client-txn-id <reference_id>")
        print("")
        print("  Read recent payin callbacks:")
        print("    python3 read_mudrape_callback_response.py payin [--limit 10] [--hours 24]")
        print("")
        print("  Read specific payin by PG TXN ID:")
        print("    python3 read_mudrape_callback_response.py payin --pg-txn-id <mudrape_txn_id>")
        print("")
        print("  Read specific payin by Order ID:")
        print("    python3 read_mudrape_callback_response.py payin --order-id <order_id>")
        sys.exit(1)
    
    txn_type = sys.argv[1].lower()
    
    if txn_type not in ['payout', 'payin']:
        print("ERROR: Transaction type must be 'payout' or 'payin'")
        sys.exit(1)
    
    # Parse arguments
    pg_txn_id = None
    client_txn_id = None
    order_id = None
    limit = 10
    hours = 24
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--pg-txn-id' and i + 1 < len(sys.argv):
            pg_txn_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--client-txn-id' and i + 1 < len(sys.argv):
            client_txn_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--order-id' and i + 1 < len(sys.argv):
            order_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--hours' and i + 1 < len(sys.argv):
            hours = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # Execute based on transaction type
    if txn_type == 'payout':
        read_payout_callbacks(pg_txn_id, client_txn_id, limit, hours)
    else:
        read_payin_callbacks(pg_txn_id, order_id, limit, hours)

if __name__ == '__main__':
    main()
