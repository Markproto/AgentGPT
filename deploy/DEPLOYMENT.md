# AgentGPT Deployment Guide

This guide explains how to deploy AgentGPT on the same server as Legal.opentruthai.com.

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │           Nginx Reverse Proxy           │
                    │         (Port 80/443 - SSL)             │
                    └─────────────┬───────────────┬───────────┘
                                  │               │
                    ┌─────────────▼───┐   ┌───────▼─────────────┐
                    │                 │   │                     │
                    │  Legal.open...  │   │     AgentGPT        │
                    │  (Port 3000)    │   │    (Port 3001)      │
                    │                 │   │                     │
                    └─────────────────┘   └─────────────────────┘
                                  │               │
                    ┌─────────────▼───────────────▼─────────────┐
                    │             Docker Network                │
                    │               (webnet)                    │
                    └───────────────────────────────────────────┘
```

## Prerequisites

- Ubuntu 20.04+ or similar Linux server
- Docker and Docker Compose installed
- Nginx installed and configured
- Certbot for SSL certificates
- Domain DNS configured (agent.opentruthai.com → server IP)

## Quick Deployment

### Option 1: Automated Deployment

```bash
# Clone or copy the repository
cd /path/to/AgentGPT

# Run the deployment script
sudo bash deploy/deploy.sh
```

### Option 2: Manual Deployment

#### Step 1: Create Docker Network

```bash
# Create shared network for both apps
docker network create webnet
```

#### Step 2: Configure Environment

```bash
# Copy environment template
cp deploy/.env.production.example .env.production

# Generate NEXTAUTH_SECRET
openssl rand -base64 32

# Edit with your values
nano .env.production
```

Required environment variables:
- `NEXTAUTH_SECRET` - Generated secret for auth sessions
- `NEXTAUTH_URL` - https://agent.opentruthai.com
- `OPENAI_API_KEY` - Your OpenAI API key

#### Step 3: Setup Nginx

```bash
# Copy nginx configuration
sudo cp deploy/nginx/agentgpt.conf /etc/nginx/sites-available/

# Enable the site
sudo ln -s /etc/nginx/sites-available/agentgpt.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

#### Step 4: Obtain SSL Certificate

```bash
# Using certbot
sudo certbot --nginx -d agent.opentruthai.com
```

#### Step 5: Build and Start

```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

## Configuration Details

### Port Mapping

| Service | Internal Port | External Port | URL |
|---------|---------------|---------------|-----|
| Legal.opentruthai.com | 3000 | 3000 | https://legal.opentruthai.com |
| AgentGPT | 3000 | 3001 | https://agent.opentruthai.com |

### Environment Variables

See `deploy/.env.production.example` for all available options.

**Critical Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXTAUTH_SECRET` | Auth session encryption key | Yes |
| `NEXTAUTH_URL` | Full URL of the application | Yes |
| `OPENAI_API_KEY` | OpenAI API key for AI features | Yes |
| `DATABASE_URL` | Database connection string | Yes |

**OAuth Providers (Optional):**

| Provider | Client ID Var | Client Secret Var |
|----------|---------------|-------------------|
| Google | `GOOGLE_CLIENT_ID` | `GOOGLE_CLIENT_SECRET` |
| GitHub | `GITHUB_CLIENT_ID` | `GITHUB_CLIENT_SECRET` |
| Discord | `DISCORD_CLIENT_ID` | `DISCORD_CLIENT_SECRET` |

### Database Options

**SQLite (Default - Simple):**
```env
DATABASE_URL=file:./db/db.sqlite
```

**PostgreSQL (Recommended for Production):**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/agentgpt
```

## Management Commands

### View Logs
```bash
cd /opt/agentgpt
docker-compose logs -f
```

### Restart Application
```bash
docker-compose restart
```

### Stop Application
```bash
docker-compose down
```

### Rebuild After Changes
```bash
docker-compose up -d --build
```

### Database Migrations
```bash
docker-compose exec agentgpt npx prisma migrate deploy
```

### Access Container Shell
```bash
docker-compose exec agentgpt sh
```

## Updating AgentGPT

```bash
cd /opt/agentgpt

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build
```

## Troubleshooting

### Application Not Starting

Check logs:
```bash
docker-compose logs -f agentgpt
```

Common issues:
- Missing environment variables
- Invalid OpenAI API key
- Port conflict

### Nginx 502 Bad Gateway

1. Check if container is running:
```bash
docker-compose ps
```

2. Check container health:
```bash
docker-compose logs agentgpt
```

3. Verify port binding:
```bash
curl http://localhost:3001
```

### Database Issues

Reset database (development only):
```bash
docker-compose exec agentgpt npx prisma migrate reset
```

### SSL Certificate Issues

Renew certificate:
```bash
sudo certbot renew
```

## Security Considerations

1. **Environment Files**: Never commit `.env.production` to version control
2. **API Keys**: Rotate OpenAI API keys periodically
3. **OAuth**: Use production credentials for OAuth providers
4. **Database**: Use PostgreSQL/MySQL for production with proper backups
5. **Firewall**: Only expose ports 80/443 through nginx

## Monitoring

### Health Check Endpoint

The application exposes a health check at `/api/health` (implement if needed).

### Resource Usage

```bash
docker stats agentgpt
```

## Backup Strategy

### Database Backup (SQLite)

```bash
# Backup
cp /opt/agentgpt/db/db.sqlite /backup/agentgpt-$(date +%Y%m%d).sqlite

# Restore
cp /backup/agentgpt-YYYYMMDD.sqlite /opt/agentgpt/db/db.sqlite
docker-compose restart
```

### Database Backup (PostgreSQL)

```bash
# Backup
pg_dump -U agentgpt agentgpt > /backup/agentgpt-$(date +%Y%m%d).sql

# Restore
psql -U agentgpt agentgpt < /backup/agentgpt-YYYYMMDD.sql
```

## Support

For issues, check:
1. Docker logs: `docker-compose logs -f`
2. Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
3. Application logs in the container
