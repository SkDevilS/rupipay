#!/usr/bin/env python3
"""
Add debug logging to Rang callback handler to capture actual callback data
"""

def create_debug_callback_route():
    """Create a debug version of the callback route with extensive logging"""
    
    debug_route = '''
@rang_callback_bp.route('/rang-payin-callback-debug', methods=['POST'])
def rang_payin_callback_debug():
    """Debug version of Rang payin callback with extensive logging"""
    import json
    import logging
    from datetime import datetime
    
    # Set up detailed logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Log everything about the incoming request
        logger.info("=" * 80)
        logger.info("RANG CALLBACK DEBUG - RECEIVED")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info(f"Method: {request.method}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Remote Address: {request.remote_addr}")
        
        # Log all headers
        logger.info("Headers:")
        for header, value in request.headers:
            logger.info(f"  {header}: {value}")
        
        # Log content type
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Content-Length: {request.content_length}")
        
        # Log raw data
        raw_data = request.get_data()
        logger.info(f"Raw Data: {raw_data}")
        
        # Try to parse as form data
        if request.form:
            logger.info("Form Data:")
            for key, value in request.form.items():
                logger.info(f"  {key}: {value}")
        
        # Try to parse as JSON
        try:
            json_data = request.get_json()
            if json_data:
                logger.info(f"JSON Data: {json.dumps(json_data, indent=2)}")
        except:
            logger.info("No valid JSON data")
        
        # Try to parse as query parameters
        if request.args:
            logger.info("Query Parameters:")
            for key, value in request.args.items():
                logger.info(f"  {key}: {value}")
        
        # Determine callback data based on content type
        callback_data = {}
        
        if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            callback_data = request.form.to_dict()
            logger.info("Using form data as callback data")
        elif request.content_type and 'application/json' in request.content_type:
            callback_data = request.get_json() or {}
            logger.info("Using JSON data as callback data")
        else:
            # Try both
            callback_data = request.form.to_dict() if request.form else (request.get_json() or {})
            logger.info("Using fallback data parsing")
        
        logger.info(f"Parsed Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Log what we expect vs what we got
        expected_fields = ['status_id', 'amount', 'utr', 'client_id', 'message']
        logger.info("Field Analysis:")
        for field in expected_fields:
            if field in callback_data:
                logger.info(f"  ✅ {field}: {callback_data[field]}")
            else:
                logger.info(f"  ❌ {field}: MISSING")
        
        # Log any extra fields
        extra_fields = set(callback_data.keys()) - set(expected_fields)
        if extra_fields:
            logger.info("Extra fields received:")
            for field in extra_fields:
                logger.info(f"  + {field}: {callback_data[field]}")
        
        # Save debug data to database
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO callback_logs 
            (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            'DEBUG',
            'DEBUG_RANG_CALLBACK',
            'DEBUG_ENDPOINT',
            json.dumps({
                'headers': dict(request.headers),
                'content_type': request.content_type,
                'raw_data': raw_data.decode('utf-8', errors='ignore'),
                'form_data': dict(request.form),
                'json_data': request.get_json(),
                'parsed_data': callback_data
            }),
            200,
            'Debug callback received and logged'
        ))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Debug data saved to callback_logs table")
        logger.info("=" * 80)
        
        return jsonify({
            'status': 'success',
            'message': 'Debug callback received and logged',
            'data_received': callback_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in debug callback: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
'''
    
    print("Debug callback route code:")
    print(debug_route)
    
    print("\nTo add this to your rang_callback_routes.py:")
    print("1. Add the above route to the file")
    print("2. Test with: https://api.moneyone.co.in/rang-payin-callback-debug")
    print("3. Check callback_logs table for debug entries")

if __name__ == "__main__":
    create_debug_callback_route()