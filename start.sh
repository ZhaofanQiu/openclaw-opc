#!/bin/bash
# OpenClaw OPC - Quick Start Script

set -e

echo "🚀 OpenClaw OPC - Quick Start"
echo "=============================="

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Create data directory if not exists
mkdir -p data

echo ""
echo "📦 Building and starting services..."
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health
echo ""
echo "🏥 Health Check:"
if curl -s http://localhost:8080/health > /dev/null; then
    echo "  ✅ Backend: http://localhost:8080"
else
    echo "  ⚠️  Backend not ready yet"
fi

echo "  ✅ Frontend: http://localhost:3000"

echo ""
echo "🎉 OpenClaw OPC is running!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "📚 API Docs:  http://localhost:8080/docs"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f    # View logs"
echo "  docker-compose down       # Stop services"
echo "  docker-compose ps         # Check status"
