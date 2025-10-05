#!/bin/sh
set -e

echo "🔧 Setting up development environment..."

# Install dev dependencies if not already installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "📦 Installing test dependencies..."
    pip install --no-cache-dir \
        pytest>=7.4.0 \
        pytest-django>=4.7.0 \
        pytest-cov>=4.1.0 \
        pytest-mock>=3.12.0 \
        pytest-asyncio>=0.23.0 \
        pytest-xdist>=3.5.0 \
        factory-boy>=3.3.0 \
        faker>=22.0.0 \
        freezegun>=1.4.0 \
        pytest-env>=1.1.0
    echo "✅ Test dependencies installed"
else
    echo "✅ Test dependencies already installed"
fi

echo "🚀 Starting application..."

# Execute the main command
exec "$@"
