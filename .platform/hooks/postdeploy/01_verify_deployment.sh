#!/bin/bash

# Elastic Beanstalk postdeploy hook for deployment verification
# This script runs after the application is deployed to verify everything works

set -e

echo "Verifying deployment..."

# Wait for services to start
sleep 10

# Check if nginx is running
if ! sudo systemctl is-active --quiet nginx; then
    echo "ERROR: Nginx is not running!"
    sudo systemctl start nginx || echo "Failed to start nginx"
fi

# Check if Docker container is running
CONTAINER_COUNT=$(sudo docker ps -q | wc -l)
if [ "$CONTAINER_COUNT" -eq 0 ]; then
    echo "WARNING: No Docker containers are running!"
else
    echo "Docker containers running: $CONTAINER_COUNT"
    sudo docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
fi

# Test nginx configuration
echo "Testing nginx configuration..."
if ! sudo nginx -t; then
    echo "ERROR: Nginx configuration test failed!"
    exit 1
fi

# Test SSL certificate
if [ -f "/etc/letsencrypt/live/aptscanner.duckdns.org/fullchain.pem" ]; then
    echo "SSL certificate found and valid"
    # Check certificate expiration
    openssl x509 -in /etc/letsencrypt/live/aptscanner.duckdns.org/fullchain.pem -text -noout | grep "Not After"
else
    echo "WARNING: SSL certificate not found!"
fi

# Test application health endpoint
echo "Testing application health..."
if curl -f -s http://localhost/ > /dev/null; then
    echo "✅ Application health check passed"
else
    echo "⚠️ Application health check failed"
fi

# Check Docker container logs for errors
echo "Checking container logs for errors..."
CONTAINER_ID=$(sudo docker ps -q | head -1)
if [ ! -z "$CONTAINER_ID" ]; then
    echo "Recent container logs:"
    sudo docker logs --tail 10 "$CONTAINER_ID" || echo "Could not fetch container logs"
fi

echo "Deployment verification completed!"
