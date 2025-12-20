# DEVBOTTEAM: Automated Deployment System

## 🎯 Team Deployment Infrastructure

Comprehensive automated deployment system for the DEVBOTTEAM to deploy the ClickUp-Telegram Bot to production, staging, and development environments.

---

## 📋 System Overview

```
DEVBOTTEAM Deployment Architecture:

┌─────────────────────────────────────────────────────────────┐
│                  DEVBOTTEAM COMMAND CENTER                  │
│                  (Deployment Controller)                     │
└─────────────┬──────────────────────────────┬────────────────┘
              │                              │
       ┌──────▼──────┐              ┌────────▼─────────┐
       │ STAGING ENV │              │ PRODUCTION ENV   │
       │  (Test)     │              │  (Live)          │
       │             │              │                  │
       │ - Node.js   │              │ - Node.js (PM2)  │
       │ - PostgreSQL│              │ - PostgreSQL     │
       │ - ngrok     │              │ - Domain/SSL     │
       │ - Mock Bot  │              │ - Real Bot       │
       └─────────────┘              └──────────────────┘
              │                              │
       ┌──────▼──────────────────────────────▼──────┐
       │    Telegram Bot API & ClickUp API        │
       └──────────────────────────────────────────┘
```

---

## 🚀 Quick Start for DEVBOTTEAM

### Prerequisites
- Node.js 18+
- PostgreSQL 13+
- Telegram Bot Token (from BotFather)
- ClickUp API Token
- PM2 (for production)
- ngrok (for development webhooks)

### One-Command Setup

```bash
# Clone repository
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter
cd ci-failure-agent-spam-scam-fixing-filter

# Install dependencies
npm install

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Choose deployment type
bash scripts/deploy.sh <dev|staging|production>
```

---

## 📁 Deployment Scripts Structure

```
scripts/
├── deploy.sh                 # Main deployment orchestrator
├── setup-dev.sh             # Development environment setup
├── setup-staging.sh         # Staging environment setup  
├── setup-production.sh      # Production environment setup
├── start-server.sh          # Start the bot server
├── stop-server.sh           # Stop the bot server
├── restart-server.sh        # Restart the bot server
├── health-check.sh          # Health check and monitoring
├── backup-database.sh       # Database backup
├── rollback.sh              # Rollback to previous version
└── logs.sh                  # View and manage logs
```

---

## 🌍 Environment Types

### 1. **DEVELOPMENT** (Local Machine)
- **Purpose**: Testing and debugging
- **Server**: localhost:3000
- **Database**: Local PostgreSQL
- **Tunneling**: ngrok for webhook
- **Bot**: Test bot (@dev_bot)
- **Channel**: Private test channel
- **Restart**: npm run dev (auto-reload with nodemon)

**Setup**:
```bash
bash scripts/setup-dev.sh

# Terminal 1: Start ngrok
ngrok http 3000

# Terminal 2: Start server
npm run dev

# Terminal 3: Monitor logs
pm2 logs clickup-bot --follow
```

### 2. **STAGING** (Test Server)
- **Purpose**: UAT and integration testing
- **Server**: staging.your-domain.com
- **Database**: Staging PostgreSQL
- **Tunneling**: None (has domain)
- **Bot**: Staging bot (@staging_bot)
- **Channel**: @company_staging_tasks
- **Monitoring**: Full metrics collection

**Setup**:
```bash
bash scripts/setup-staging.sh

# Verify deployment
bash scripts/health-check.sh staging
```

### 3. **PRODUCTION** (Live Server)
- **Purpose**: Live team operations
- **Server**: bot.your-domain.com (with SSL)
- **Database**: Production PostgreSQL (replicated)
- **Tunneling**: None (has domain)
- **Bot**: Real bot (@clickup_tasks_bot)
- **Channel**: @company_tasks (public)
- **Monitoring**: Critical alerts enabled
- **Uptime**: 99.5%+ SLA

**Setup**:
```bash
bash scripts/setup-production.sh

# Verify deployment
bash scripts/health-check.sh production

# Check PM2 status
pm2 status
pm2 logs clickup-bot
```

---

## 📊 Deployment Configuration Files

### .env.example (Template)
```
# General
PORT=3000
NODE_ENV=development
LOG_LEVEL=debug

# Database
DB_USER=postgres
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clickup_bot

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel

# ClickUp
CLICKUP_API_TOKEN=your_clickup_token
CLICKUP_TEAM_ID=your_team_id
CLICKUP_WORKSPACE_ID=your_workspace_id

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=3000
SERVER_URL=https://your-domain.com

# SSL/TLS
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain/privkey.pem

# Monitoring
MONITORING_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn
```

### ecosystem.config.js (PM2 Configuration)
```javascript
module.exports = {
  apps: [{
    name: 'clickup-bot',
    script: './src/index.js',
    instances: 1,
    exec_mode: 'cluster',
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      LOG_LEVEL: 'info'
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }]
};
```

---

## 🔄 Deployment Workflow

### Daily Deployment Process

```
1. PRE-DEPLOYMENT (5 min)
   ├─ Pull latest code from main branch
   ├─ Run tests
   ├─ Check database health
   └─ Verify all credentials

2. STAGING DEPLOYMENT (10 min)
   ├─ Deploy to staging
   ├─ Run integration tests
   ├─ Verify webhook connections
   └─ Check error logs

3. PRODUCTION DEPLOYMENT (5 min)
   ├─ Create backup of current version
   ├─ Deploy to production
   ├─ Run health checks
   └─ Verify live updates

4. POST-DEPLOYMENT (5 min)
   ├─ Monitor error rates
   ├─ Check response times
   ├─ Notify team of deployment
   └─ Document any issues
```

---

## 📈 Monitoring & Metrics

### Server Metrics
```bash
# Check server status
pm2 status

# View real-time monitoring
pm2 monit

# View all logs
pm2 logs

# View error logs only
pm2 logs --err

# Save logs for analysis
pm2 save
pm2 flush logs
```

### Key Metrics to Monitor
- **Response Time**: Should be < 500ms
- **Error Rate**: Should be < 1%
- **Memory Usage**: Should be < 200MB
- **CPU Usage**: Should be < 50%
- **Database Connections**: Active connections
- **Webhook Delivery Rate**: 100% success
- **Uptime**: Track daily/weekly/monthly

---

## 🔒 Security Checklist

- [ ] Environment variables secured (not in git)
- [ ] SSL/HTTPS enabled
- [ ] Database password changed from default
- [ ] API tokens rotated (quarterly)
- [ ] Firewall rules configured
- [ ] Database backups automated
- [ ] Error logs encrypted
- [ ] Access logs maintained
- [ ] Rate limiting enabled
- [ ] Input validation implemented

---

## 🆘 Troubleshooting for DEVBOTTEAM

### Issue: Bot Not Starting
```bash
# Check logs
pm2 logs clickup-bot --err --lines 50

# Verify environment variables
echo $TELEGRAM_BOT_TOKEN
echo $CLICKUP_API_TOKEN

# Check database connection
psql -U postgres -d clickup_bot -c "SELECT NOW()"

# Restart server
pm2 restart clickup-bot
```

### Issue: Webhooks Not Triggering
```bash
# Verify webhook URL is accessible
curl https://your-domain.com/health

# Check webhook logs
psql -U postgres -d clickup_bot -c "SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 10;"

# Test webhook manually
curl -X POST https://your-domain.com/webhook/clickup \
  -H "Content-Type: application/json" \
  -d '{"event": "task.created", "task": {"id": "123", "name": "Test"}}'
```

### Issue: High Memory Usage
```bash
# Check memory leaks
pm2 monit

# Restart with memory limit
pm2 restart clickup-bot --max-memory-restart 1G

# Check for open connections
lsof -i :3000
```

---

## 🔄 Rollback Procedure

If deployment fails or causes issues:

```bash
# 1. Stop current version
pm2 stop clickup-bot

# 2. Restore previous version
git checkout HEAD~1
npm install

# 3. Restore database backup
bash scripts/restore-backup.sh <backup-date>

# 4. Restart service
pm2 start clickup-bot

# 5. Verify health
bash scripts/health-check.sh

# 6. Document incident
echo "Incident: [Description]" >> incidents.log
```

---

## 📝 Team Responsibilities

### DevOps Lead
- Manages deployment infrastructure
- Configures servers and databases
- Sets up monitoring and alerts
- Handles security patches

### Backend Developer
- Develops and tests code
- Reviews pull requests
- Manages deployments to staging
- Provides hotfixes for production

### QA Engineer
- Tests in staging environment
- Verifies integrations
- Reports issues
- Signs off on production deployment

---

## 📅 Deployment Schedule

- **Staging Deployments**: Multiple times daily (after commits)
- **Production Deployments**: 2x weekly (Tuesday & Friday, 10 AM UTC)
- **Hotfixes**: On-demand (with team approval)
- **Database Backups**: Daily at 2 AM UTC

---

## 📞 Support & Escalation

1. **Level 1**: Check logs and health status
2. **Level 2**: Review recent commits
3. **Level 3**: Rollback to previous version
4. **Level 4**: Restore from database backup
5. **Emergency**: Page on-call engineer

---

## ✅ Success Criteria

- ✅ All health checks passing
- ✅ Response times < 500ms
- ✅ Error rate < 1%
- ✅ All webhooks delivering
- ✅ Database backups current
- ✅ Logs clean (no critical errors)
- ✅ Team notifications working
- ✅ Uptime > 99.5%

---

**System Version**: 1.0.0
**Last Updated**: 2025-12-20
**Maintained By**: DEVBOTTEAM
