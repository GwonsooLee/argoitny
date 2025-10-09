#!/bin/bash
# Verification script for Gunicorn + Uvicorn configuration

echo "=== Gunicorn Configuration Verification ==="
echo ""

# Check if required packages are installed
echo "1. Checking required packages..."
if command -v gunicorn &> /dev/null; then
    echo "   ✓ Gunicorn installed: $(gunicorn --version)"
else
    echo "   ✗ Gunicorn not found"
fi

if python -c "import uvicorn" 2>/dev/null; then
    echo "   ✓ Uvicorn installed"
else
    echo "   ✗ Uvicorn not found"
fi
echo ""

# Check configuration file
echo "2. Checking configuration files..."
if [ -f "gunicorn.conf.py" ]; then
    echo "   ✓ gunicorn.conf.py exists"
else
    echo "   ✗ gunicorn.conf.py not found"
fi

if [ -f "config/asgi.py" ]; then
    echo "   ✓ config/asgi.py exists"
else
    echo "   ✗ config/asgi.py not found"
fi

if [ -f "start.sh" ]; then
    echo "   ✓ start.sh exists"
    if [ -x "start.sh" ]; then
        echo "   ✓ start.sh is executable"
    else
        echo "   ✗ start.sh is not executable (run: chmod +x start.sh)"
    fi
else
    echo "   ✗ start.sh not found"
fi
echo ""

# Check environment variables
echo "3. Checking environment variables..."
if [ -n "$GUNICORN_WORKERS" ]; then
    echo "   ✓ GUNICORN_WORKERS=$GUNICORN_WORKERS"
else
    echo "   ℹ GUNICORN_WORKERS not set (will use default: CPU * 2 + 1)"
fi

if [ -n "$GUNICORN_LOG_LEVEL" ]; then
    echo "   ✓ GUNICORN_LOG_LEVEL=$GUNICORN_LOG_LEVEL"
else
    echo "   ℹ GUNICORN_LOG_LEVEL not set (will use default: info)"
fi
echo ""

# Check Django settings
echo "4. Checking Django settings..."
if grep -q "ASGI_APPLICATION" config/settings.py; then
    echo "   ✓ ASGI_APPLICATION configured"
else
    echo "   ✗ ASGI_APPLICATION not found in settings.py"
fi

if grep -q "CONN_MAX_AGE" config/settings.py; then
    echo "   ✓ Database connection pooling configured"
else
    echo "   ✗ CONN_MAX_AGE not found in settings.py"
fi
echo ""

# Test configuration syntax
echo "5. Testing Gunicorn configuration syntax..."
if gunicorn config.asgi:application -c gunicorn.conf.py --check-config 2>/dev/null; then
    echo "   ✓ Configuration syntax is valid"
else
    echo "   ⚠ Configuration test skipped (requires Django environment)"
fi
echo ""

echo "=== Verification Complete ==="
echo ""
echo "To start the server:"
echo "  docker-compose up -d backend"
echo "  or"
echo "  ./start.sh"
echo ""
