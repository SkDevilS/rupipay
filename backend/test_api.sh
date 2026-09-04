#!/bin/bash

echo "=========================================="
echo "MoneyOne API Quick Test"
echo "=========================================="
echo ""

# Test 1: Check if port 5000 is listening
echo "1. Checking if port 5000 is listening..."
if sudo netstat -tlnp | grep -q ":5000"; then
    echo "   ✓ Port 5000 is listening"
    sudo netstat -tlnp | grep ":5000"
else
    echo "   ✗ Port 5000 is NOT listening"
    echo "   This means Gunicorn is not running or not binding to the port"
fi
echo ""

# Test 2: Check Gunicorn processes
echo "2. Checking Gunicorn processes..."
if ps aux | grep -v grep | grep -q gunicorn; then
    echo "   ✓ Gunicorn processes found:"
    ps aux | grep -v grep | grep gunicorn
else
    echo "   ✗ No Gunicorn processes running"
fi
echo ""

# Test 3: Check Supervisor status
echo "3. Checking Supervisor status..."
sudo supervisorctl status moneyone-api
echo ""

# Test 4: Test API health endpoint
echo "4. Testing API health endpoint..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/health 2>/dev/null)
if [ "$response" = "200" ]; then
    echo "   ✓ API is responding (HTTP $response)"
    curl -s http://localhost:5000/api/health | python3 -m json.tool
else
    echo "   ✗ API is not responding (HTTP $response)"
fi
echo ""

# Test 5: Test captcha endpoint
echo "5. Testing captcha endpoint..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/admin/captcha 2>/dev/null)
if [ "$response" = "200" ]; then
    echo "   ✓ Captcha endpoint is working (HTTP $response)"
else
    echo "   ✗ Captcha endpoint failed (HTTP $response)"
fi
echo ""

# Test 6: Check recent logs
echo "6. Recent error logs (last 10 lines)..."
if [ -f /var/log/moneyone/api-stderr.log ]; then
    sudo tail -10 /var/log/moneyone/api-stderr.log
else
    echo "   No stderr log file found"
fi
echo ""

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "To view live logs, run:"
echo "  sudo tail -f /var/log/moneyone/api-stderr.log"
echo ""
echo "To restart the service:"
echo "  sudo supervisorctl restart moneyone-api"
echo "=========================================="
