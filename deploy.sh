#!/bin/bash
echo "Starting deployment..."
docker-compose up --build -d
echo "Deployment started. Backend on port 8000, Frontend on port 3000."
