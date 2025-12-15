# Phase 1: Quick Start - Free Deployment Guide (Next 30 Days)

## Overview
**Duration**: 30 days
**Cost**: $0-15/month
**Goal**: Deploy your AI CI/CD failure agent system and validate product-market fit

---

## OPTION A: Deploy on Your Machine (Fastest - 2-4 hours)

### Prerequisites (check you have these):
- Docker installed (https://docs.docker.com/get-docker/)
- Docker Compose (usually included with Docker)
- 4GB+ RAM available
- 50GB free disk space

### Step 1: Clone & Setup Your Repo (15 minutes)

```bash
# Clone the repository
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter

# Create environment file
cp .env.example .env

# Edit .env with your settings (optional for testing)
vim .env
```

### Step 2: Start with Docker Compose (30 minutes)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

**What starts automatically:**
- ✅ Python FastAPI application
- ✅ PostgreSQL database
- ✅ Redis cache (if configured)
- ✅ Prometheus metrics
- ✅ Grafana dashboards (on http://localhost:3000)

### Step 3: Access Your System (5 minutes)

```bash
# Application API
http://localhost:8000
http://localhost:8000/docs  # Swagger UI

# Monitoring
http://localhost:3000  # Grafana (admin/admin)
http://localhost:9090  # Prometheus

# Database
PostgreSQL: localhost:5432
```

### Step 4: Run Test Suite (15 minutes)

```bash
# Run unit tests
docker-compose exec app python -m pytest tests/ -v

# Run integration tests
docker-compose exec app python -m pytest tests/integration/ -v

# Check code coverage
docker-compose exec app python -m pytest --cov=src tests/
```

---

## OPTION B: Deploy on Cloud VPS ($10/month)

### Best providers:
- **Hetzner** ($3.99/month - 2 CPU, 4GB RAM, 40GB SSD)
- **Linode** ($6/month - 1GB RAM) - need to upgrade to 4GB
- **DigitalOcean** ($6/month droplet)

### Why this option:
- ✅ Always running (24/7)
- ✅ Real domain support
- ✅ Production-like environment
- ✅ SSL/TLS ready
- ⚠️ Requires Linux knowledge

### Setup Steps (45 minutes):

1. **Create VPS on Hetzner** ($3.99/month)
   - CPU: 2 cores minimum
   - RAM: 4GB minimum
   - SSD: 40GB minimum
   - OS: Ubuntu 22.04 LTS

2. **Connect to VPS**

```bash
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Deploy Application**

```bash
# Clone repo
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

4. **Configure Domain (optional)**

```bash
# Get your VPS IP
echo $HOSTNAME -I

# Point your domain A record to this IP in DNS settings
# Then access: http://yourdomain.com
```

5. **Enable SSL with Let's Encrypt** (free)

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get certificate (if using Nginx)
certbot certonly --standalone -d yourdomain.com

# Update docker-compose to use certificate
# Edit docker-compose.yml SSL paths
```

---

## OPTION C: AWS Free Tier (12 months FREE)

### Setup ($0 for 12 months):

1. **Create AWS Account**
   - Go to aws.amazon.com/free
   - Sign up (free tier eligible)
   - No credit card charges for first 12 months (within limits)

2. **Launch EC2 Instance** (t3.micro - free tier)

```bash
# In AWS Console:
# 1. Go to EC2 Dashboard
# 2. Click "Launch Instance"
# 3. Select: Ubuntu 22.04 LTS
# 4. Instance type: t3.micro (free tier eligible)
# 5. Storage: 20GB (free tier includes 30GB)
# 6. Create security group:
#    - Allow SSH (22)
#    - Allow HTTP (80)
#    - Allow HTTPS (443)
#    - Allow App port (8000)
# 7. Launch
```

3. **Connect & Deploy**

```bash
# Download .pem file and set permissions
chmod 400 your-key.pem

# Connect
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP

# Follow Docker setup from OPTION B above
```

4. **Attach RDS Database** (free tier)

```bash
# In AWS Console:
# 1. Go to RDS Dashboard
# 2. Create database
# 3. Engine: PostgreSQL
# 4. Instance: db.t3.micro (free tier)
# 5. Storage: 20GB (free)
# 6. Update docker-compose.yml with RDS endpoint
```

---

## VALIDATION PHASE (Days 5-30)

### What to test:

1. **Core AI Functionality**
   ```bash
   # Test CI/CD failure detection
   curl -X POST http://localhost:8000/api/analyze-failure \
     -H "Content-Type: application/json" \
     -d '{"error_log": "your test error"}'
   ```

2. **Spam/Fraud Detection**
   ```bash
   # Test email spam detection
   curl -X POST http://localhost:8000/api/analyze-email \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "subject": "test"}'
   ```

3. **Performance**
   - Response time: < 2 seconds
   - CPU usage: < 50%
   - Memory usage: < 2GB
   - Uptime: check Grafana

4. **Data Storage**
   - PostgreSQL storing data correctly
   - Backups running (check logs)

### Get First Users:

```
Phase 1A (Days 1-10): Internal testing
- Test with your team
- Verify all features work
- Document issues

Phase 1B (Days 11-20): Beta users
- Invite 5-10 beta testers
- GitHub / Product Hunt / Reddit announcements
- Gather feedback

Phase 1C (Days 21-30): Refine & Polish
- Fix bugs from beta feedback
- Improve documentation
- Prepare for Phase 2
```

---

## MONITORING & DEBUGGING

### View Logs

```bash
# All services
docker-compose logs --tail=100

# Specific service
docker-compose logs -f app
docker-compose logs -f database

# With timestamps
docker-compose logs -f --timestamps
```

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database connection
docker-compose exec app python -c "from src.database import get_db; print('DB OK')"

# Check all endpoints
curl http://localhost:8000/metrics  # Prometheus metrics
```

### Common Issues & Fixes

**Issue**: Port already in use
```bash
# Find process using port
lsof -i :8000
# Kill process
kill -9 PID
```

**Issue**: Out of memory
```bash
# Increase Docker memory in docker-compose.yml
# Set memory limits:
memory: 2g
memory_reservation: 1g
```

**Issue**: Database connection fails
```bash
# Check PostgreSQL is running
docker-compose ps database

# Reset database
docker-compose down -v
docker-compose up -d
```

---

## NEXT STEPS

### If validation successful (you have users):
- ✅ Move to **Phase 2**: AWS Free Tier ($0 for 12 months)
- ✅ Scale up resources as needed
- ✅ Begin monetization planning

### If validation needs work:
- 🔄 Stay on local/VPS setup
- 🔄 Iterate on features
- 🔄 Improve AI model accuracy
- 🔄 Expand user base

---

## Support & Resources

- **Docker Docs**: https://docs.docker.com
- **PostgreSQL**: https://www.postgresql.org/docs
- **Prometheus**: https://prometheus.io/docs
- **Grafana**: https://grafana.com/docs
- **Your Repo**: https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter

---

**Document Version**: 1.0
**Created**: December 15, 2025
**Status**: Ready for implementation
**Timeline**: Start immediately, complete within 30 days
