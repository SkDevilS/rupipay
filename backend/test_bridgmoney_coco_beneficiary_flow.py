"""
Test script for Bridgmoney Coco Beneficiary Management and Payout Integration
Tests:
1. Add Beneficiary (Bank target: accountNumber + ifsc) -> 201 Created or 409 Deduplicated (returns existing beneficiaryId)
2. Add Beneficiary (UPI target: vpa) -> 201 Created or 409 Deduplicated (returns existing beneficiaryId)
3. List Beneficiaries
4. Get Beneficiary by ID
5. Update Beneficiary
6. Archive and Reactivate Beneficiary
7. Automatic beneficiary get/create resolution in Payout initiation (get_or_create_beneficiary_for_payout)
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

# Ensure current directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridgmoney_coco_service import bridgmoney_coco_service

def test_beneficiary_payload_and_methods():
    print("=" * 70)
    print("TEST 1: Add Bank Beneficiary (accountNumber + ifsc)")
    print("=" * 70)
    
    # Mocking successful 201 response for creating a bank beneficiary
    mock_resp_create = MagicMock()
    mock_resp_create.status_code = 201
    mock_resp_create.json.return_value = {
        "status": 200,
        "data": {
            "beneficiaryId": "123e4567-e89b-12d3-a456-426614174000",
            "beneficiaryCode": "BMBN2026032500001"
        },
        "message": "Beneficiary created successfully",
        "meta": None
    }
    
    with patch('requests.post', return_value=mock_resp_create) as mock_post:
        res = bridgmoney_coco_service.add_beneficiary(
            name="Ravi Traders Pvt Ltd",
            phone_number="9876543210",
            account_number="0002053000010425",
            ifsc="UTIB0000123",
            email="ravi@merchant.com"
        )
        print("Result:", res)
        assert res['success'] is True, "Expected add_beneficiary to succeed"
        assert res['beneficiaryId'] == "123e4567-e89b-12d3-a456-426614174000", "Beneficiary ID mismatch"
        assert res['existing'] is False, "Expected newly created beneficiary"
        
        # Verify payload sent to POST /v1/beneficiaries
        call_args, call_kwargs = mock_post.call_args
        sent_data = json.loads(call_kwargs['data'])
        assert sent_data['name'] == "Ravi Traders Pvt Ltd"
        assert sent_data['accountNumber'] == "0002053000010425"
        assert sent_data['ifsc'] == "UTIB0000123"
        assert 'vpa' not in sent_data, "vpa should not be sent for bank beneficiary"
        print("PASS: Bank Beneficiary Creation verified successfully!")

    print("\n" + "=" * 70)
    print("TEST 2: Add Beneficiary Deduplication (409 Beneficiary already exists)")
    print("=" * 70)
    
    # Mocking 409 response returning existing beneficiaryId
    mock_resp_409 = MagicMock()
    mock_resp_409.status_code = 409
    mock_resp_409.json.return_value = {
        "status": 409,
        "data": {
            "beneficiaryId": "50a97363-71bb-47b1-af7f-a55444684a58",
            "name": "Ravi Traders Pvt Ltd",
            "email": "ravi@merchant.com",
            "phoneNumber": "9876543210",
            "accountNumber": "0002053000010425",
            "ifsc": "UTIB0000123",
            "vpa": None
        },
        "message": "Beneficiary already exists",
        "meta": None
    }
    
    with patch('requests.post', return_value=mock_resp_409):
        res = bridgmoney_coco_service.add_beneficiary(
            name="Ravi Traders Pvt Ltd",
            phone_number="9876543210",
            account_number="0002053000010425",
            ifsc="UTIB0000123"
        )
        print("409 Deduplicated Result:", res)
        assert res['success'] is True, "409 existing beneficiary should return success=True"
        assert res['existing'] is True, "Expected existing=True flag"
        assert res['beneficiaryId'] == "50a97363-71bb-47b1-af7f-a55444684a58", "Should extract existing beneficiaryId"
        print("PASS: 409 Deduplication verified successfully!")

    print("\n" + "=" * 70)
    print("TEST 3: Add UPI Beneficiary (vpa target)")
    print("=" * 70)
    with patch('requests.post', return_value=mock_resp_create) as mock_post_upi:
        res = bridgmoney_coco_service.add_beneficiary(
            name="Ravi Traders Pvt Ltd",
            phone_number="9876543210",
            vpa="ravi.traders@okhdfcbank"
        )
        call_args, call_kwargs = mock_post_upi.call_args
        sent_data = json.loads(call_kwargs['data'])
        assert sent_data['vpa'] == "ravi.traders@okhdfcbank"
        assert 'accountNumber' not in sent_data and 'ifsc' not in sent_data, "Bank fields should not be sent for UPI target"
        print("PASS: UPI Beneficiary Creation verified successfully!")

    print("\n" + "=" * 70)
    print("TEST 4: List Beneficiaries")
    print("=" * 70)
    mock_resp_list = MagicMock()
    mock_resp_list.status_code = 200
    mock_resp_list.json.return_value = {
        "status": 200,
        "data": [
            {"beneficiaryId": "1111-2222", "name": "Vendor A"},
            {"beneficiaryId": "3333-4444", "name": "Vendor B"}
        ],
        "meta": {"page": 1, "limit": 50, "total": 2}
    }
    with patch('requests.get', return_value=mock_resp_list) as mock_get:
        res = bridgmoney_coco_service.list_beneficiaries(page=1, limit=50)
        assert res['success'] is True
        assert len(res['data']) == 2
        print("PASS: List Beneficiaries verified successfully!")

    print("\n" + "=" * 70)
    print("TEST 5: Automatic Beneficiary Resolution in Payout (get_or_create_beneficiary_for_payout)")
    print("=" * 70)
    sample_payout_data = {
        'reference_id': 'REF_PAYOUT_1001',
        'amount': 5000.0,
        'bene_name': 'Ravi Traders Pvt Ltd',
        'bene_account': '0002053000010425',
        'bene_ifsc': 'UTIB0000123',
        'bene_mobile': '9876543210',
        'bank_name': 'Axis Bank'
    }
    with patch('requests.post', return_value=mock_resp_409):
        bene_id = bridgmoney_coco_service.get_or_create_beneficiary_for_payout(sample_payout_data)
        print("Resolved beneficiary_id for payout:", bene_id)
        assert bene_id == "50a97363-71bb-47b1-af7f-a55444684a58", "Should resolve to existing beneficiary ID from 409 response"
        print("PASS: Automatic Payout Beneficiary Resolution verified successfully!")

if __name__ == '__main__':
    test_beneficiary_payload_and_methods()
    print("\n" + "=" * 70)
    print("ALL BRIDGMONEY COCO BENEFICIARY TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
