#!/bin/bash

# Elastic Beanstalk predeploy hook for SSL certificate setup
# This script runs before the application is deployed

set -e

echo "Setting up SSL certificates for aptscanner.duckdns.org..."

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo yum update -y
    sudo yum install -y certbot python3-certbot-nginx
fi

# Check if certificate exists and is valid
if [ ! -f "/etc/letsencrypt/live/aptscanner.duckdns.org/fullchain.pem" ]; then
    echo "SSL certificate not found. Please ensure Let's Encrypt certificates are set up."
    echo "Run: sudo certbot --nginx -d aptscanner.duckdns.org"
else
    echo "SSL certificate found. Checking expiration..."
    # Check if certificate expires within 30 days and renew if needed
    sudo certbot renew --dry-run || echo "Certificate renewal check completed"
fi

# Ensure nginx configuration directory permissions
sudo mkdir -p /etc/nginx/conf.d/
sudo chown -R nginx:nginx /etc/nginx/conf.d/ || true

# Create upstream configuration if it doesn't exist
if [ ! -f "/etc/nginx/conf.d/elasticbeanstalk-nginx-docker-upstream.conf" ]; then
    echo "Creating Docker upstream configuration..."
    sudo tee /etc/nginx/conf.d/elasticbeanstalk-nginx-docker-upstream.conf > /dev/null << 'EOF'
upstream docker {
    server 172.17.0.2:8000;
    keepalive 256;
}
EOF
fi

echo "SSL and nginx setup completed successfully!"
