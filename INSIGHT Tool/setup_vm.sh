#!/bin/bash

# INSIGHT Tool Deployment Script for Ubuntu
# Usage: sudo ./setup_vm.sh

set -e

echo "=================================================="
echo "   INSIGHT Tool - Automated Deployment Script     "
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this script as root (sudo ./setup_vm.sh)"
  exit 1
fi

# 1. Update System
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    echo "Docker installed successfully."
else
    echo "Docker is already installed."
fi

# Ensure Docker service is running
systemctl start docker
systemctl enable docker

# 3. Create required directories
echo "Creating data directories..."
mkdir -p Data_Storage/Repositories indices models neo4j_data

# Set permissions for data directories
chmod -R 777 Data_Storage indices models neo4j_data

# 4. Environment Configuration
echo "--------------------------------------------------"
echo "Configuring Environment..."

if [ ! -f .env ]; then
    echo "Creating .env file..."
    
    read -p "GitHub App ID: " app_id
    read -p "Webhook Secret: " webhook_secret
    read -p "Gemini API Key (optional): " gemini_key
    read -p "OpenAI API Key (optional): " openai_key
    
    echo ""
    echo "--------------------------------------------------"
    echo "Private Key Configuration"
    echo "You can either provide the path to your private-key.pem file"
    echo "OR skip and paste the content manually if asked."
    read -p "Path to private-key.pem (leave empty to paste content): " key_path
    
    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
        echo "Reading key from $key_path..."
        # Read and base64 encode
        key_base64=$(base64 -w 0 "$key_path")
    else
        echo "Please paste your Private Key (PEM format) below."
        echo "Press Ctrl+D when finished:"
        # Read multiline input
        key_content=$(cat)
        # Base64 encode the content
        key_base64=$(echo "$key_content" | base64 -w 0)
    fi
    
    cat > .env <<EOF
# Production Configuration
GITHUB_APP_ID=$app_id
APP_ID=$app_id
WEBHOOK_SECRET=$webhook_secret
GEMINI_API_KEY=$gemini_key
OPENAI_API_KEY=$openai_key
GITHUB_PRIVATE_KEY_BASE64=$key_base64
FLASK_ENV=production
FLASK_DEBUG=False
# Port to run on (Host machine)
PORT=80
POOL_PROCESSOR_MAX_WORKERS=4
# Model paths
BUGLOCALIZATION_MODEL_PATH=microsoft/unixcoder-base
# Database Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EOF
    echo ".env file created."
else
    echo ".env file already exists. Skipping creation."
    
    # Ensure PORT is set to 80 if not present
    if ! grep -q "^PORT=" .env; then
        echo "PORT=80" >> .env
        echo "Added PORT=80 to .env"
    fi
fi

# 5. Deploy with Docker Compose
echo "--------------------------------------------------"
echo "Building and Starting Application..."

# Remove old convenience override if it somehow survived (though we deleted it locally)
rm -f docker-compose.prod.yml

# Check/Install Compose Plugin
if ! docker compose version &> /dev/null; then
  echo "Installing Docker Compose Plugin..."
  apt-get install -y docker-compose-plugin
fi

docker compose down --remove-orphans || true
docker compose up -d --build

# 6. Verification
echo "--------------------------------------------------"
echo "Deployment Complete!"
PUBLIC_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo "Application running at: http://$PUBLIC_IP/"
echo "Webhook URL: http://$PUBLIC_IP/"
echo ""
echo "Databases:"
echo "- Neo4j: Running in container 'neo4j' (Port 7474 for UI)"
echo "- FAISS: Embedded (Indices stored in ./indices)"
echo ""
echo "Useful Commands:"
echo "  View Logs: docker compose logs -f"
echo "  Stop App:  docker compose down"
