#!/bin/bash

# Elastic Beanstalk predeploy hook for Docker container management
# This script ensures proper Docker container setup

set -e

echo "Setting up Docker container configuration..."

# Stop any running containers from previous deployments
echo "Stopping existing containers..."
sudo docker stop $(sudo docker ps -q) 2>/dev/null || echo "No containers to stop"

# Clean up old containers
echo "Removing old containers..."
sudo docker container prune -f

# Clean up unused images (keep last 3 versions)
echo "Cleaning up old Docker images..."
sudo docker image prune -f

# Ensure Docker service is running
sudo systemctl enable docker
sudo systemctl start docker

# Check Docker daemon status
if ! sudo systemctl is-active --quiet docker; then
    echo "ERROR: Docker daemon is not running!"
    exit 1
fi

# Verify Docker can run containers
if ! sudo docker run --rm hello-world &>/dev/null; then
    echo "ERROR: Docker cannot run containers properly!"
    exit 1
fi

echo "Docker setup completed successfully!"
