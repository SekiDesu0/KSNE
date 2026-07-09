#!/bin/bash
set -e

echo "Pulling latest code..."
git pull

echo "Building Docker image..."
docker build -t ksne:latest .

echo "Starting container..."
docker compose up -d

echo "Done. App available at http://localhost:5500"