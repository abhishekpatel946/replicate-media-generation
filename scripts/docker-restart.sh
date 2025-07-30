#!/bin/bash
# Docker cleanup and restart script for Fleek Media Service

echo "🧹 Cleaning up Docker containers and images..."

# Stop and remove containers
docker-compose down

# Remove any existing images to force rebuild
docker-compose down --rmi all --volumes --remove-orphans

echo "🔨 Rebuilding and starting services..."

# Build and start services
docker-compose up --build -d

echo "📊 Checking service status..."
docker-compose ps

echo "🎉 Done! Services should be running now."
echo "📝 Check logs with: docker-compose logs -f api"
echo "🩺 Test health: curl http://localhost:8000/health" 