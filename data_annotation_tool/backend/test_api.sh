#!/bin/bash

# Test script for Data Annotation Tool API

BASE_URL="http://127.0.0.1:8000"

echo "Testing Data Annotation Tool API..."
echo "=================================="
echo ""

# Test 1: Health Check
echo "1. Testing Health Check (GET /)"
curl -s "$BASE_URL/" | python3 -m json.tool
echo ""
echo ""

# Test 2: API Root
echo "2. Testing API Root (GET /api/)"
curl -s "$BASE_URL/api/" | python3 -m json.tool || echo "API root endpoint"
echo ""
echo ""

# Test 3: List available endpoints
echo "3. Available API Endpoints:"
echo "   - POST /api/files/upload/          - Upload CSV file"
echo "   - POST /api/files/save/             - Save edited CSV"
echo "   - POST /api/files/upload_to_s3/     - Upload CSV to S3"
echo "   - POST /api/s3-config/test_connection/ - Test S3 connection"
echo ""
echo ""

# Test 4: Check if server is running
echo "4. Server Status:"
if curl -s "$BASE_URL/" > /dev/null; then
    echo "   ✓ Server is running"
else
    echo "   ✗ Server is not running"
    echo "   Start server with: python manage.py runserver"
fi

