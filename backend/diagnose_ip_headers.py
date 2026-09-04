#!/usr/bin/env python3
"""
Diagnose IP Headers - Check what headers are being sent
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/test-ip', methods=['GET', 'POST'])
def test_ip():
    """Test endpoint to see all IP-related headers"""
    
    headers_info = {
        'remote_addr': request.remote_addr,
        'x_forwarded_for': request.headers.get('X-Forwarded-For'),
        'x_real_ip': request.headers.get('X-Real-IP'),
        'cf_connecting_ip': request.headers.get('CF-Connecting-IP'),
        'x_forwarded_proto': request.headers.get('X-Forwarded-Proto'),
        'x_forwarded_port': request.headers.get('X-Forwarded-Port'),
        'all_headers': dict(request.headers)
    }
    
    print("\n" + "="*80)
    print("IP HEADER DIAGNOSTIC")
    print("="*80)
    print(f"request.remote_addr: {request.remote_addr}")
    print(f"X-Forwarded-For: {request.headers.get('X-Forwarded-For')}")
    print(f"X-Real-IP: {request.headers.get('X-Real-IP')}")
    print(f"CF-Connecting-IP: {request.headers.get('CF-Connecting-IP')}")
    print("\nAll Headers:")
    for key, value in request.headers:
        print(f"  {key}: {value}")
    print("="*80 + "\n")
    
    return jsonify(headers_info), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
