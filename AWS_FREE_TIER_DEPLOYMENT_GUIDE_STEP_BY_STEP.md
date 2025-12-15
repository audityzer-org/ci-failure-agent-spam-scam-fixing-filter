# AWS Free Tier Deployment Guide - Step by Step
## Your Path to $0/month for 12 Months

**Timeline**: 60 minutes total  
**Cost**: $0 for first 12 months  
**Result**: Production-ready CI/CD failure agent live on AWS

---

## STEP 1: Create AWS Free Tier Account (10 minutes)

### 1.1 Go to AWS Free Tier
```
Open browser: https://aws.amazon.com/free/
```

### 1.2 Click "Create a Free Account"
- Email address (use your real email)
- Password (strong password!)
- AWS account name (e.g., "CI-Failure-Agent")

### 1.3 Enter Payment Information
**IMPORTANT**: They will ask for credit card
- This is for VERIFICATION only
- They will NOT charge you during free tier (12 months)
- Auto-stop happens if you exceed free tier limits

### 1.4 Verify Your Identity
- Phone verification (SMS code sent)
- Confirm identity

### 1.5 Choose Support Plan
- Select: **Basic Plan** (Free)
- Click "Complete Sign Up"

✅ **You now have AWS Free Tier Account**

---

## STEP 2: Set Up EC2 Instance (15 minutes)

### 2.1 Log In to AWS Console
```
Go to: https://console.aws.amazon.com/
Enter your email & password
```

### 2.2 Open EC2 Dashboard
1. Top left: Click **"Services"**
2. Search: **"EC2"**
3. Click **"EC2"** under "Compute"

### 2.3 Launch Instance
1. Big orange button: **"Launch Instance"**
2. Choose Name: `ci-failure-agent-server`

### 2.4 Choose AMI (Amazon Machine Image)
```
Search: Ubuntu 22.04 LTS
Select the FREE TIER ELIGIBLE one
(Should show "Free tier eligible" label)
```

### 2.5 Choose Instance Type
```
Instance type: t3.micro
(This is free tier eligible - 750 hours/month included)
```

### 2.6 Create Key Pair
```
Key pair name: ci-failure-agent-key
Key pair type: RSA
Private key format: .pem
```
**IMPORTANT**: Click "Create key pair"
- File will download: `ci-failure-agent-key.pem`
- **SAVE THIS FILE SAFELY** - you'll need it to connect!

### 2.7 Network Settings
```
Create security group checkbox: CHECKED
Security group name: ci-failure-agent-sg

Add inbound rules:
1. SSH (22) - anywhere (0.0.0.0/0)
2. HTTP (80) - anywhere (0.0.0.0/0)  
3. HTTPS (443) - anywhere (0.0.0.0/0)
4. TCP (8000) - anywhere (0.0.0.0/0)  [Your app port]
5. TCP (3000) - anywhere (0.0.0.0/0)  [Grafana]
6. TCP (9090) - anywhere (0.0.0.0/0)  [Prometheus]
```

### 2.8 Storage Configuration
```
Volume size: 20 GB (Free tier includes 30GB total)
Encryption: Disabled (free tier doesn't charge for encryption)
```

### 2.9 Review and Launch
- Click "Launch Instance"
- Wait 30-60 seconds for instance to start
- You'll see green checkmark when running

✅ **Your EC2 instance is now RUNNING**

---

## STEP 3: Connect to Your Server (10 minutes)

### 3.1 Get Your Instance IP
1. Go to EC2 Instances dashboard
2. Click on your instance: `ci-failure-agent-server`
3. Copy **"Public IPv4 address"** (e.g., 54.123.45.67)

### 3.2 Connect via SSH (on your computer)

**Linux/Mac:**
```bash
# Change permissions on key file
chmod 400 ~/Downloads/ci-failure-agent-key.pem

# Connect to server
ssh -i ~/Downloads/ci-failure-agent-key.pem ubuntu@YOUR_PUBLIC_IP

# Accept: type 'yes' when asked
```

**Windows (PowerShell):**
```powershell
# Set key permissions
icacls "$HOME\\Downloads\\ci-failure-agent-key.pem" /grant:r "$($env:USERNAME):(R)"
icacls "$HOME\\Downloads\\ci-failure-agent-key.pem" /inheritance:r

# Connect
ssh -i "$HOME\\Downloads\\ci-failure-agent-key.pem" ubuntu@YOUR_PUBLIC_IP
```

✅ **You're now connected to your AWS server**

---

## STEP 4: Install Docker & Your App (20 minutes)

### 4.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 4.2 Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 4.3 Add User to Docker Group
```bash
sudo usermod -aG docker ubuntu

# Log out and back in for changes to take effect
exit

# Reconnect via SSH
ssh -i ~/Downloads/ci-failure-agent-key.pem ubuntu@YOUR_PUBLIC_IP
```

### 4.4 Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### 4.5 Clone Your Repository
```bash
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter
```

### 4.6 Start Your Application
```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Expected output:
```
STATUS: Up 30 seconds
HEALTHY
```

### 4.7 Verify Everything Works
```bash
# Check application is responding
curl http://localhost:8000/health

# Should return: {"status": "ok"}
```

✅ **Your CI/CD failure agent is LIVE on AWS**

---

## STEP 5: Access Your System (5 minutes)

### 5.1 Get Your Server IP
From AWS Console:
- Copy your **Public IPv4 address** (e.g., 54.123.45.67)

### 5.2 Access Your Services

**Application API:**
```
http://54.123.45.67:8000
http://54.123.45.67:8000/docs   (Swagger UI)
```

**Monitoring Dashboard (Grafana):**
```
http://54.123.45.67:3000
Login: admin / admin
```

**Metrics (Prometheus):**
```
http://54.123.45.67:9090
```

**PostgreSQL Database:**
```
Host: localhost:5432 (from server only)
```

### 5.3 Test Your API
```bash
# Test CI/CD failure detection
curl -X POST http://54.123.45.67:8000/api/analyze-failure \
  -H "Content-Type: application/json" \
  -d '{"error_log": "TypeError: Cannot read property of undefined"}'

# Test spam detection
curl -X POST http://54.123.45.67:8000/api/analyze-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "subject": "test"}'
```

✅ **Your system is accessible from anywhere on the internet**

---

## STEP 6: Add Custom Domain (Optional - 10 minutes)

### 6.1 Register Domain
- Go to: https://domains.google.com or Route 53
- Search for domain
- Register (usually $10-15/year)

### 6.2 Point Domain to AWS
1. Go to Route 53 in AWS Console
2. Create Hosted Zone for your domain
3. Add A Record:
   ```
   Name: yourdomain.com
   Type: A Record
   Value: 54.123.45.67 (your EC2 public IP)
   ```

### 6.3 Enable SSL (Let's Encrypt - FREE)
```bash
# SSH into your server
ssh -i ~/Downloads/ci-failure-agent-key.pem ubuntu@YOUR_PUBLIC_IP

# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Update docker-compose.yml to use certificate
# Edit environment variables with certificate paths
```

### 6.4 Access via Domain
```
https://yourdomain.com:8000
https://yourdomain.com:3000  (Grafana)
```

✅ **Your system has secure HTTPS with custom domain**

---

## MONITORING YOUR AWS USAGE

### 7.1 Check Free Tier Status
1. AWS Console → Billing
2. Look for "Free Tier Usage"
3. You'll see:
   - EC2: 750 hours/month (your t3.micro uses this)
   - RDS: 750 hours (if you add it)
   - Data transfer: 100GB/month

### 7.2 Set Up Billing Alert
```
1. Billing Dashboard
2. "Billing Preferences"
3. Enable: "Receive Billing Alerts"
4. Set alert at $0.10 (catches any overage)
```

### 7.3 Monthly Monitoring
- Check Billing page monthly
- Verify usage is within free tier
- Stop/delete instances if not using

✅ **You're protected from unexpected charges**

---

## TROUBLESHOOTING

### Problem: Can't Connect via SSH
```bash
# Check security group allows SSH from your IP
AWS Console → EC2 → Security Groups
Ensure port 22 (SSH) is open to your IP

# Check key file permissions
chmod 400 ci-failure-agent-key.pem
```

### Problem: Docker containers not running
```bash
# SSH into server and check
ssh -i key.pem ubuntu@YOUR_IP

# Check logs
docker-compose logs app

# Restart
docker-compose restart
```

### Problem: Port already in use
```bash
# Find what's using the port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

### Problem: Out of disk space
```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a
```

---

## NEXT STEPS

### Immediately (Today):
- ✅ Create AWS account
- ✅ Launch EC2 instance
- ✅ Deploy your application
- ✅ Test all endpoints

### This Week:
- Get first beta testers
- Test all features
- Monitor performance
- Set up backups

### Next Month:
- Add RDS database (free tier)
- Set up automated backups
- Configure monitoring alerts
- Plan Phase 2 scaling

---

## AWS Free Tier Limits (What You Get)

| Service | Free Tier | Your Usage |
|---------|-----------|------------|
| EC2 | 750 hours/month | ✅ t3.micro (covers 24/7) |
| Data Transfer | 100GB/month | ✅ Your app (likely < 10GB) |
| EBS Storage | 30GB/month | ✅ 20GB instance |
| CloudWatch | Basic (free) | ✅ All included |
| RDS | 750 hours/month | ✅ Available if needed |

**Total Monthly Cost: $0**

---

## Congratulations! 🎉

Your CI/CD failure agent is now:
- ✅ Running on AWS
- ✅ Accessible 24/7
- ✅ Costing $0/month
- ✅ Ready for beta users
- ✅ Monitoring and logging enabled
- ✅ Production-grade infrastructure

**Document Version**: 1.0  
**Created**: December 15, 2025  
**Expected Completion**: 60 minutes  
**Support**: GitHub Discussions
