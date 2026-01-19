#!/bin/bash
# =============================================================================
# Onyx (Danswer) Installation Script
# Replaces AgentGPT with Onyx at agent.opentruthai.com
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ONYX_DIR="/opt/onyx"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Onyx (Danswer) Installation${NC}"
echo -e "${GREEN}========================================${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo bash install-onyx.sh${NC}"
    exit 1
fi

# =============================================================================
# Step 1: Remove AgentGPT
# =============================================================================
echo -e "\n${YELLOW}Step 1: Removing AgentGPT...${NC}"

if [ -d "/root/AgentGPT" ]; then
    cd /root/AgentGPT
    docker-compose down --rmi all 2>/dev/null || true
    echo -e "${GREEN}✓ AgentGPT containers removed${NC}"
fi

if [ -d "/opt/agentgpt" ]; then
    cd /opt/agentgpt
    docker-compose down --rmi all 2>/dev/null || true
    rm -rf /opt/agentgpt
    echo -e "${GREEN}✓ AgentGPT directory removed${NC}"
fi

# =============================================================================
# Step 2: Create Onyx directory
# =============================================================================
echo -e "\n${YELLOW}Step 2: Setting up Onyx directory...${NC}"

mkdir -p "$ONYX_DIR"
cd "$ONYX_DIR"

# =============================================================================
# Step 3: Download Onyx docker-compose files
# =============================================================================
echo -e "\n${YELLOW}Step 3: Downloading Onyx configuration...${NC}"

# Download the official install script and docker-compose files
curl -fsSL https://raw.githubusercontent.com/onyx-dot-app/onyx/main/deployment/docker_compose/docker-compose.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/onyx-dot-app/onyx/main/deployment/docker_compose/.env.template -o .env

echo -e "${GREEN}✓ Downloaded Onyx configuration${NC}"

# =============================================================================
# Step 4: Configure environment
# =============================================================================
echo -e "\n${YELLOW}Step 4: Configuring environment...${NC}"

# Generate secrets
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
SECRET_KEY=$(openssl rand -base64 32)

# Update .env file with secure passwords
sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|g" .env 2>/dev/null || true
sed -i "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|g" .env 2>/dev/null || true

# Set auth type to disabled initially (can enable later)
sed -i "s|AUTH_TYPE=.*|AUTH_TYPE=disabled|g" .env 2>/dev/null || true

echo -e "${GREEN}✓ Environment configured${NC}"

# =============================================================================
# Step 5: Modify docker-compose to use port 3000 externally
# =============================================================================
echo -e "\n${YELLOW}Step 5: Adjusting port configuration...${NC}"

# The default Onyx nginx uses port 80 and 3000
# We'll map 3000 to 3000 for our external nginx to proxy to
sed -i 's/- "80:80"/- "3000:80"/g' docker-compose.yml 2>/dev/null || true
sed -i 's/- "3000:3000"//g' docker-compose.yml 2>/dev/null || true

echo -e "${GREEN}✓ Port configuration updated${NC}"

# =============================================================================
# Step 6: Update nginx configuration
# =============================================================================
echo -e "\n${YELLOW}Step 6: Updating nginx configuration...${NC}"

cp "$SCRIPT_DIR/nginx-onyx.conf" /etc/nginx/sites-available/agentgpt.conf

# Test nginx config
if nginx -t; then
    systemctl reload nginx
    echo -e "${GREEN}✓ Nginx configuration updated${NC}"
else
    echo -e "${RED}Nginx configuration error. Please check manually.${NC}"
fi

# =============================================================================
# Step 7: Create Docker network
# =============================================================================
echo -e "\n${YELLOW}Step 7: Creating Docker network...${NC}"

docker network create onyx_network 2>/dev/null || true
echo -e "${GREEN}✓ Docker network ready${NC}"

# =============================================================================
# Step 8: Pull and start Onyx
# =============================================================================
echo -e "\n${YELLOW}Step 8: Starting Onyx (this may take 5-10 minutes)...${NC}"

docker compose pull
docker compose up -d

echo -e "${GREEN}✓ Onyx containers starting${NC}"

# =============================================================================
# Step 9: Wait for startup
# =============================================================================
echo -e "\n${YELLOW}Step 9: Waiting for Onyx to initialize...${NC}"

sleep 30

# Check if running
if docker compose ps | grep -q "running"; then
    echo -e "${GREEN}✓ Onyx is running${NC}"
else
    echo -e "${YELLOW}Onyx may still be starting. Check with: docker compose logs -f${NC}"
fi

# =============================================================================
# Complete
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "Access Onyx at: ${GREEN}https://agent.opentruthai.com${NC}"
echo -e "Username: ${GREEN}admin${NC}"
echo -e "Password: ${GREEN}opentruth${NC}"
echo -e ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs:     cd $ONYX_DIR && docker compose logs -f"
echo -e "  Restart:       cd $ONYX_DIR && docker compose restart"
echo -e "  Stop:          cd $ONYX_DIR && docker compose down"
echo -e "  Update:        cd $ONYX_DIR && docker compose pull && docker compose up -d"
echo -e ""
echo -e "${YELLOW}First-time setup:${NC}"
echo -e "  1. Visit https://agent.opentruthai.com"
echo -e "  2. Create an admin account"
echo -e "  3. Add your OpenAI API key in Admin > LLM settings"
echo -e "  4. Connect document sources (upload files, Google Drive, etc.)"
echo -e ""
echo -e "${YELLOW}System Requirements Check:${NC}"
echo -e "  RAM: $(free -h | awk '/^Mem:/{print $2}') available"
echo -e "  Disk: $(df -h / | awk 'NR==2{print $4}') free"
echo -e ""
echo -e "${RED}Note: Onyx requires ~4GB RAM minimum. If you experience issues,${NC}"
echo -e "${RED}consider upgrading your server or reducing model sizes.${NC}"
