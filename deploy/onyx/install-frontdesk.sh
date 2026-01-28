#!/bin/bash
# =============================================================================
# J. Austin Front Desk CRM - Installation Script
# Deploys alongside Onyx at agent.opentruthai.com/frontdesk
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FRONTDESK_DIR="/opt/frontdesk"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}J. Austin Front Desk CRM Installation${NC}"
echo -e "${GREEN}========================================${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo bash install-frontdesk.sh${NC}"
    exit 1
fi

# =============================================================================
# Step 1: Create application directory
# =============================================================================
echo -e "\n${YELLOW}Step 1: Setting up application directory...${NC}"

mkdir -p "$FRONTDESK_DIR"
cp -r "$REPO_DIR/frontdesk/"* "$FRONTDESK_DIR/"
cp "$REPO_DIR/frontdesk/Dockerfile" "$FRONTDESK_DIR/"
cp "$REPO_DIR/frontdesk/docker-compose.yml" "$FRONTDESK_DIR/"
echo -e "${GREEN}✓ Files copied to $FRONTDESK_DIR${NC}"

# =============================================================================
# Step 2: Create environment file
# =============================================================================
echo -e "\n${YELLOW}Step 2: Creating environment file...${NC}"

if [ ! -f "$FRONTDESK_DIR/.env" ]; then
    SECRET_KEY=$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9' | head -c 50)
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

    cat > "$FRONTDESK_DIR/.env" << EOF
# Django Settings
FRONTDESK_SECRET_KEY=${SECRET_KEY}
FRONTDESK_DEBUG=False
FRONTDESK_ALLOWED_HOSTS=agent.opentruthai.com,localhost

# Database
FRONTDESK_DB_NAME=frontdesk
FRONTDESK_DB_USER=frontdesk
FRONTDESK_DB_PASSWORD=${DB_PASSWORD}
FRONTDESK_DB_HOST=frontdesk-db
FRONTDESK_DB_PORT=5432

# Redis
FRONTDESK_REDIS_URL=redis://frontdesk-redis:6379/1

# SendGrid
SENDGRID_API_KEY=

# Twilio (optional, for future use)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE=

# AI Integration (use one or both)
ANTHROPIC_API_KEY=
GROK_API_KEY=

# Front Desk AI
FRONTDESK_AI_API_KEY=
EOF

    echo -e "${GREEN}✓ Environment file created${NC}"
    echo -e "${YELLOW}IMPORTANT: Edit $FRONTDESK_DIR/.env with your API keys!${NC}"
else
    echo -e "${YELLOW}Environment file already exists${NC}"
fi

# =============================================================================
# Step 3: Update nginx configuration
# =============================================================================
echo -e "\n${YELLOW}Step 3: Updating nginx configuration...${NC}"

cp "$SCRIPT_DIR/nginx-combined.conf" /etc/nginx/sites-available/agentgpt.conf

if nginx -t; then
    systemctl reload nginx
    echo -e "${GREEN}✓ Nginx updated with /frontdesk route${NC}"
else
    echo -e "${RED}Nginx configuration error!${NC}"
fi

# =============================================================================
# Step 4: Build and start Docker containers
# =============================================================================
echo -e "\n${YELLOW}Step 4: Building and starting CRM containers...${NC}"

cd "$FRONTDESK_DIR"
docker compose build
docker compose up -d

echo -e "${GREEN}✓ CRM containers started${NC}"

# =============================================================================
# Step 5: Run migrations and create admin user
# =============================================================================
echo -e "\n${YELLOW}Step 5: Running database migrations...${NC}"

sleep 10  # Wait for DB to start
docker compose exec -T frontdesk-web python manage.py migrate
docker compose exec -T frontdesk-web python manage.py collectstatic --noinput

echo -e "${GREEN}✓ Migrations complete${NC}"

echo -e "\n${YELLOW}Creating admin user...${NC}"
docker compose exec -T frontdesk-web python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@opentruthai.com', 'opentruth')
    print('Admin user created')
else:
    print('Admin user already exists')
"

echo -e "${GREEN}✓ Admin user ready${NC}"

# =============================================================================
# Complete
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "CRM URL: ${GREEN}https://agent.opentruthai.com/frontdesk/${NC}"
echo -e "Django Admin: ${GREEN}https://agent.opentruthai.com/frontdesk/admin/${NC}"
echo -e ""
echo -e "Login: admin / opentruth"
echo -e ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Edit $FRONTDESK_DIR/.env with your API keys"
echo -e "2. Restart: cd $FRONTDESK_DIR && docker compose restart"
echo -e ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Logs:    cd $FRONTDESK_DIR && docker compose logs -f"
echo -e "  Restart: cd $FRONTDESK_DIR && docker compose restart"
echo -e "  Stop:    cd $FRONTDESK_DIR && docker compose down"
