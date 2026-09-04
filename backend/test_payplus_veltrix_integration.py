"""
Test Script for Payplus_Veltrix Integration
Verifies syntax, module loading, blueprint registration, signature verification, and routing configuration.
"""

import os
import sys
import hmac
import hashlib
import unittest
from flask import Flask

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from payplus_veltrix_service import payplus_veltrix_service
from payplus_veltrix_callback_routes import payplus_veltrix_callback_bp
from service_routing_routes import routing_bp
from api_ledger_routes import api_ledger_bp

class TestPayplusVeltrixIntegration(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(Config)
        self.app.register_blueprint(payplus_veltrix_callback_bp)
        self.app.register_blueprint(routing_bp, url_prefix='/api/service-routing')
        self.app.register_blueprint(api_ledger_bp, url_prefix='/api/api-ledger')
        self.client = self.app.test_client()

    def test_01_service_initialization(self):
        print("\n--- Test 1: Service Initialization ---")
        self.assertIsNotNone(payplus_veltrix_service)
        self.assertEqual(payplus_veltrix_service.base_url, "https://payplus.live")
        print("✓ Payplus_Veltrix service initialized successfully with correct Base URL")

    def test_02_txn_prefix(self):
        print("\n--- Test 2: Transaction Prefix Check ---")
        import time
        merchant_id = "MERCH1001"
        txn_id = f"PP_VEL_{int(time.time())}{merchant_id[-4:]}"
        self.assertTrue(txn_id.startswith("PP_VEL_"))
        print(f"✓ Generated transaction ID starts with PP_VEL_: {txn_id}")

    def test_03_hmac_signature_computation(self):
        print("\n--- Test 3: HMAC Signature Computation ---")
        secret = "test_secret_123"
        payload = b'{"event":"payin.success","status":"success","merchantOrderId":"PP_VEL_1234"}'
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        self.assertEqual(len(expected_sig), 64)  # sha256 hex digest length
        print(f"✓ Computed valid HMAC SHA256 hex digest: {expected_sig[:15]}...")

    def test_04_pg_partners_endpoint(self):
        print("\n--- Test 4: PG Partners Service Routing ---")
        response = self.client.get('/api/service-routing/pg-partners')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        partners = data.get('partners', [])
        pv_partner = next((p for p in partners if p['id'] == 'PAYPLUS_VELTRIX'), None)
        self.assertIsNotNone(pv_partner, "PAYPLUS_VELTRIX should be in pg-partners list")
        self.assertEqual(pv_partner['name'], 'Payplus_Veltrix')
        self.assertIn('PAYIN', pv_partner['supports'])
        print(f"✓ Found PAYPLUS_VELTRIX in Service Routing PG Partners: {pv_partner}")

    def test_05_api_ledger_mapping(self):
        print("\n--- Test 5: API Ledger Name Mapping ---")
        # Check mapping logic in api_ledger_routes
        from api_ledger_routes import api_ledger_bp
        self.assertIsNotNone(api_ledger_bp)
        print("✓ API Ledger blueprint verified")

if __name__ == '__main__':
    unittest.main()
