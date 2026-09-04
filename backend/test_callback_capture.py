#!/usr/bin/env python3
"""
Test endpoint to capture and display Mudrape callback data
This creates a temporary endpoint that logs everything Mudrape sends
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Store captured callbacks
captured_callbacks = []

@app.route('/test-callback', methods=['POST', 'GET'])
def test_callback():
    """Capture any callback data"""
    
    timestamp = datetime.now().isoformat()
    
    callback_info = {
        'timestamp': timestamp,
        'method': request.method,
        'content_type': request.content_type,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'form': dict(request.form) if request.form else None,
        'json': request.json if request.is_json else None,
        'data': request.data.decode('utf-8') if request.data else None
    }
    
    captured_callbacks.append(callback_info)
    
    print("=" * 80)
    print(f"CALLBACK CAPTURED AT {timestamp}")
    print("=" * 80)
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"\nHeaders:")
    for key, value in request.headers:
        print(f"  {key}: {value}")
    
    print(f"\nQuery Parameters: {dict(request.args)}")
    
    if request.form:
        print(f"\nForm Data:")
        print(json.dumps(dict(request.form), indent=2))
    
    if request.is_json:
        print(f"\nJSON Data:")
        print(json.dumps(request.json, indent=2))
    
    if request.data:
        print(f"\nRaw Data:")
        print(request.data.decode('utf-8'))
    
    print("=" * 80)
    
    # Save to file
    with open('captured_callbacks.json', 'w') as f:
        json.dump(captured_callbacks, f, indent=2)
    
    return jsonify({
        'success': True,
        'message': 'Callback captured',
        'timestamp': timestamp
    }), 200

@app.route('/view-callbacks', methods=['GET'])
def view_callbacks():
    """View all captured callbacks"""
    return jsonify({
        'total': len(captured_callbacks),
        'callbacks': captured_callbacks
    }), 200

@app.route('/clear-callbacks', methods=['POST'])
def clear_callbacks():
    """Clear captured callbacks"""
    global captured_callbacks
    count = len(captured_callbacks)
    captured_callbacks = []
    return jsonify({
        'success': True,
        'message': f'Cleared {count} callbacks'
    }), 200

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("Mudrape Callback Capture Server")
    print("=" * 80)
    print("\nThis server will capture and display all callback data from Mudrape")
    print("\nEndpoints:")
    print("  POST /test-callback  - Capture callback data")
    print("  GET  /view-callbacks - View all captured callbacks")
    print("  POST /clear-callbacks - Clear captured callbacks")
    print("\nConfigure this URL in Mudrape dashboard:")
    print("  http://YOUR_SERVER_IP:5001/test-callback")
    print("\nOr use ngrok for testing:")
    print("  ngrok http 5001")
    print("  Then use: https://YOUR_NGROK_URL/test-callback")
    print("\n" + "=" * 80 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
