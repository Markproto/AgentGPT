#!/bin/bash
# =============================================================================
# AgentGPT Production Deployment Script
# =============================================================================
# This script helps deploy AgentGPT alongside Legal.opentruthai.com
# Run with: sudo bash deploy.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="agentgpt"
APP_DIR="/opt/agentgpt"
DOMAIN="agent.opentruthai.com"
NGINX_CONF="/etc/nginx/sites-available/agentgpt.conf"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AgentGPT Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo bash deploy.sh)${NC}"
    exit 1
fi

# Function to prompt for confirmation
confirm() {
    read -p "$1 [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Step 1: Check prerequisites
echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check Nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}Nginx is not installed. Please install Nginx first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Nginx installed${NC}"

# Step 2: Create application directory
echo -e "\n${YELLOW}Step 2: Setting up application directory...${NC}"

if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    echo -e "${GREEN}✓ Created $APP_DIR${NC}"
else
    echo -e "${YELLOW}Directory $APP_DIR already exists${NC}"
fi

# Step 3: Create Docker network if not exists
echo -e "\n${YELLOW}Step 3: Setting up Docker network...${NC}"

if ! docker network ls | grep -q "webnet"; then
    docker network create webnet
    echo -e "${GREEN}✓ Created webnet network${NC}"
else
    echo -e "${YELLOW}webnet network already exists${NC}"
fi

# Step 4: Copy files to app directory
echo -e "\n${YELLOW}Step 4: Copying application files...${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$REPO_DIR"/* "$APP_DIR/"
echo -e "${GREEN}✓ Copied files to $APP_DIR${NC}"

# Step 5: Setup environment file
echo -e "\n${YELLOW}Step 5: Setting up environment...${NC}"

if [ ! -f "$APP_DIR/.env.production" ]; then
    if [ -f "$APP_DIR/deploy/.env.production.example" ]; then
        cp "$APP_DIR/deploy/.env.production.example" "$APP_DIR/.env.production"
        echo -e "${YELLOW}Created .env.production from template${NC}"
        echo -e "${RED}IMPORTANT: Edit $APP_DIR/.env.production with your actual values!${NC}"

        # Generate NEXTAUTH_SECRET
        SECRET=$(openssl rand -base64 32)
        sed -i "s/your-generated-secret-here/$SECRET/" "$APP_DIR/.env.production"
        echo -e "${GREEN}✓ Generated NEXTAUTH_SECRET${NC}"
    fi
else
    echo -e "${YELLOW}.env.production already exists${NC}"
fi

# Step 6: Setup Nginx
echo -e "\n${YELLOW}Step 6: Setting up Nginx...${NC}"

if [ -f "$APP_DIR/deploy/nginx/agentgpt.conf" ]; then
    cp "$APP_DIR/deploy/nginx/agentgpt.conf" "$NGINX_CONF"

    # Enable site if not already enabled
    if [ ! -L "/etc/nginx/sites-enabled/agentgpt.conf" ]; then
        ln -s "$NGINX_CONF" "/etc/nginx/sites-enabled/agentgpt.conf"
    fi

    echo -e "${GREEN}✓ Nginx configuration installed${NC}"
else
    echo -e "${RED}Nginx config not found${NC}"
fi

# Step 7: Setup SSL certificate
echo -e "\n${YELLOW}Step 7: SSL Certificate Setup${NC}"

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo -e "${YELLOW}SSL certificate not found for $DOMAIN${NC}"

    if confirm "Do you want to obtain an SSL certificate now?"; then
        # Stop nginx temporarily to free port 80
        systemctl stop nginx || true

        certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email admin@opentruthai.com

        # Restart nginx
        systemctl start nginx

        echo -e "${GREEN}✓ SSL certificate obtained${NC}"
    else
        echo -e "${YELLOW}Skipping SSL setup. You'll need to set this up manually.${NC}"
        echo -e "${YELLOW}Run: certbot --nginx -d $DOMAIN${NC}"
    fi
else
    echo -e "${GREEN}✓ SSL certificate exists for $DOMAIN${NC}"
fi

# Step 8: Test Nginx configuration
echo -e "\n${YELLOW}Step 8: Testing Nginx configuration...${NC}"

if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration valid${NC}"
else
    echo -e "${RED}Nginx configuration invalid. Please fix errors above.${NC}"
    exit 1
fi

# Step 9: Build and start Docker containers
echo -e "\n${YELLOW}Step 9: Building and starting containers...${NC}"

cd "$APP_DIR"

# Create db directory for SQLite
mkdir -p db

# Build and start
docker-compose build
docker-compose up -d

echo -e "${GREEN}✓ Containers started${NC}"

# Step 10: Reload Nginx
echo -e "\n${YELLOW}Step 10: Reloading Nginx...${NC}"

systemctl reload nginx
echo -e "${GREEN}✓ Nginx reloaded${NC}"

# Step 11: Health check
echo -e "\n${YELLOW}Step 11: Running health check...${NC}"

sleep 10 # Wait for app to start

if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200\|302"; then
    echo -e "${GREEN}✓ Application is responding${NC}"
else
    echo -e "${YELLOW}Application may still be starting. Check logs with: docker-compose logs -f${NC}"
fi

# Final summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "Application URL: https://$DOMAIN"
echo -e "Application directory: $APP_DIR"
echo -e ""
echo -e "${YELLOW}Important next steps:${NC}"
echo -e "1. Edit $APP_DIR/.env.production with your:"
echo -e "   - OpenAI API key"
echo -e "   - OAuth credentials (optional)"
echo -e "   - Stripe keys (optional)"
echo -e ""
echo -e "2. Restart the container after editing:"
echo -e "   cd $APP_DIR && docker-compose restart"
echo -e ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs:     cd $APP_DIR && docker-compose logs -f"
echo -e "  Restart:       cd $APP_DIR && docker-compose restart"
echo -e "  Stop:          cd $APP_DIR && docker-compose down"
echo -e "  Rebuild:       cd $APP_DIR && docker-compose up -d --build"
echo -e ""
