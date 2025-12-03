#!/bin/bash

# Render deployment script
# This script runs during the build process on Render

echo "🚀 Starting RealtyGenie Backend deployment..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p /opt/render/project/src/creds
mkdir -p /opt/render/project/src/logs
mkdir -p /opt/render/project/src/gemini_responses

# Set permissions
echo "🔐 Setting proper permissions..."
chmod 755 /opt/render/project/src/creds
chmod 755 /opt/render/project/src/logs

echo "✅ Build completed successfully!"
echo "🎯 Starting server on port $PORT..."

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1