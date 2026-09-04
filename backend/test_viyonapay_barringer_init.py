"""
Test Viyonapay Barringer service initialization
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from viyonapay_service import viyonapay_service, viyonapay_barringer_service
    from config import Config
    
    print("=" * 60)
    print("Testing Viyonapay Service Initialization")
    print("=" * 60)
    
    # Test Truaxis configuration
    print("\n1. Testing Viyonapay Truaxis (Original):")
    print(f"   Config Type: {viyonapay_service.config_type}")
    print(f"   Base URL: {viyonapay_service.base_url}")
    print(f"   Client ID: {viyonapay_service.client_id[:20]}..." if viyonapay_service.client_id else "   Client ID: Not set")
    print(f"   VPA: {viyonapay_service.vpa}")
    print(f"   Private Key Loaded: {'✓ Yes' if viyonapay_service.client_private_key else '✗ No'}")
    print(f"   Public Key Loaded: {'✓ Yes' if viyonapay_service.server_public_key else '✗ No'}")
    
    # Test Barringer configuration
    print("\n2. Testing Viyonapay Barringer:")
    print(f"   Config Type: {viyonapay_barringer_service.config_type}")
    print(f"   Base URL: {viyonapay_barringer_service.base_url}")
    print(f"   Client ID: {viyonapay_barringer_service.client_id[:20]}..." if viyonapay_barringer_service.client_id else "   Client ID: Not set")
    print(f"   VPA: {viyonapay_barringer_service.vpa}")
    print(f"   Private Key Loaded: {'✓ Yes' if viyonapay_barringer_service.client_private_key else '✗ No'}")
    print(f"   Public Key Loaded: {'✓ Yes' if viyonapay_barringer_service.server_public_key else '✗ No'}")
    
    # Check environment variables
    print("\n3. Environment Variables Check:")
    print(f"   VIYONAPAY_CLIENT_ID: {'✓ Set' if Config.VIYONAPAY_CLIENT_ID else '✗ Not set'}")
    print(f"   VIYONAPAY_BARRINGER_CLIENT_ID: {'✓ Set' if Config.VIYONAPAY_BARRINGER_CLIENT_ID else '✗ Not set'}")
    
    # Test token generation (optional - comment out if you don't want to generate tokens yet)
    print("\n4. Testing Token Generation:")
    
    try:
        print("   Testing Truaxis token generation...")
        truaxis_token = viyonapay_service.generate_access_token()
        if truaxis_token:
            print(f"   ✓ Truaxis token generated: {truaxis_token[:30]}...")
        else:
            print("   ✗ Truaxis token generation failed")
    except Exception as e:
        print(f"   ✗ Truaxis token error: {e}")
    
    try:
        print("   Testing Barringer token generation...")
        barringer_token = viyonapay_barringer_service.generate_access_token()
        if barringer_token:
            print(f"   ✓ Barringer token generated: {barringer_token[:30]}...")
        else:
            print("   ✗ Barringer token generation failed")
    except Exception as e:
        print(f"   ✗ Barringer token error: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Service initialization test complete!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error during initialization test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
