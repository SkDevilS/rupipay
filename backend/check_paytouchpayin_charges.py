#!/usr/bin/env python3
"""
Check if merchant has charge configuration for Paytouchpayin
"""

from database import get_db_connection

merchant_id = "7679022140"

print("=" * 80)
print("CHECKING PAYTOUCHPAYIN CHARGE CONFIGURATION")
print("=" * 80)

conn = get_db_connection()
cursor = conn.cursor()

# Get merchant scheme_id
cursor.execute("""
    SELECT merchant_id, scheme_id, merchant_type, is_active
    FROM merchants
    WHERE merchant_id = %s
""", (merchant_id,))

merchant = cursor.fetchone()

if not merchant:
    print(f"\n❌ Merchant {merchant_id} not found!")
    exit(1)

print(f"\n📋 Merchant Details:")
print(f"  Merchant ID: {merchant['merchant_id']}")
print(f"  Scheme ID: {merchant['scheme_id']}")
print(f"  Type: {merchant['merchant_type']}")
print(f"  Active: {merchant['is_active']}")

scheme_id = merchant['scheme_id']

if not scheme_id:
    print(f"\n❌ Merchant has no scheme_id assigned!")
    exit(1)

# Check commercial_charges table
print(f"\n" + "=" * 80)
print(f"CHECKING COMMERCIAL_CHARGES FOR SCHEME_ID: {scheme_id}")
print("=" * 80)

cursor.execute("""
    SELECT *
    FROM commercial_charges
    WHERE scheme_id = %s AND service_type = 'PAYIN'
    ORDER BY min_amount
""", (scheme_id,))

charges = cursor.fetchall()

if not charges:
    print(f"\n❌ No PAYIN charges configured for scheme_id: {scheme_id}")
    print(f"\nYou need to add charge configuration:")
    print(f"""
INSERT INTO commercial_charges 
(scheme_id, service_type, min_amount, max_amount, charge_type, charge_value)
VALUES
({scheme_id}, 'PAYIN', 0, 999999999, 'PERCENTAGE', 2.0);
""")
else:
    print(f"\n✅ Found {len(charges)} charge configuration(s):")
    for charge in charges:
        print(f"\n  Range: ₹{charge['min_amount']} - ₹{charge['max_amount']}")
        print(f"  Type: {charge['charge_type']}")
        print(f"  Value: {charge['charge_value']}")

# Test with amount 100
test_amount = 100
print(f"\n" + "=" * 80)
print(f"TESTING WITH AMOUNT: ₹{test_amount}")
print("=" * 80)

cursor.execute("""
    SELECT charge_value, charge_type
    FROM commercial_charges
    WHERE scheme_id = %s 
    AND service_type = 'PAYIN'
    AND %s BETWEEN min_amount AND max_amount
    ORDER BY min_amount DESC
    LIMIT 1
""", (scheme_id, test_amount))

applicable_charge = cursor.fetchone()

if not applicable_charge:
    print(f"\n❌ No applicable charge found for amount ₹{test_amount}")
else:
    charge_type = applicable_charge['charge_type']
    charge_value = float(applicable_charge['charge_value'])
    
    if charge_type == 'PERCENTAGE':
        charge_amount = (test_amount * charge_value) / 100
    else:
        charge_amount = charge_value
    
    print(f"\n✅ Applicable Charge:")
    print(f"  Type: {charge_type}")
    print(f"  Value: {charge_value}")
    print(f"  Charge Amount: ₹{charge_amount}")
    print(f"  Final Amount: ₹{test_amount + charge_amount}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("✅ CHECK COMPLETE")
print("=" * 80)
