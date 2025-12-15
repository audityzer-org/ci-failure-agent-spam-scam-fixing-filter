# 🚀 AWS DEPLOYMENT EXECUTION CHECKLIST
## 60-Minute Timer to Live System

**START TIME**: December 15, 2025, 6:30 PM EET  
**TARGET END TIME**: 7:30 PM EET  
**GOAL**: Production-ready CI/CD failure agent LIVE on AWS for $0  

---

## ⏱️ STEP 1: Create AWS Free Tier Account (10 minutes)
**START**: ___:___ | END: ___:___

- [ ] Open https://aws.amazon.com/free in browser
- [ ] Click "Create a Free Account"
- [ ] Enter email address
- [ ] Create password (make it strong!)
- [ ] Enter AWS account name: `ci-failure-agent`
- [ ] Enter credit card (for verification only, NO charges)
- [ ] Verify phone number (SMS code)
- [ ] Select Basic Support Plan
- [ ] Click "Complete Sign Up"

✅ **MILESTONE 1 COMPLETE**: AWS Account Created

---

## ⏱️ STEP 2: Set Up EC2 Instance (15 minutes)
**START**: ___:___ | END: ___:___

- [ ] Log in to AWS Console: https://console.aws.amazon.com
- [ ] Go to Services → EC2
- [ ] Click "Launch Instance"
- [ ] Name: `ci-failure-agent-server`
- [ ] AMI: Ubuntu 22.04 LTS (FREE tier eligible)
- [ ] Instance Type: t3.micro (FREE tier eligible)
- [ ] Create Key Pair:
  - [ ] Name: `ci-failure-agent-key`
  - [ ] Type: RSA
  - [ ] Format: .pem
  - [ ] **DOWNLOAD & SAVE** the .pem file!
- [ ] Create Security Group: `ci-failure-agent-sg`
- [ ] Inbound Rules:
  - [ ] SSH (22) - 0.0.0.0/0
  - [ ] HTTP (80) - 0.0.0.0/0
  - [ ] HTTPS (443) - 0.0.0.0/0
  - [ ] TCP (8000) - 0.0.0.0/0
  - [ ] TCP (3000) - 0.0.0.0/0
  - [ ] TCP (9090) - 0.0.0.0/0
- [ ] Storage: 20 GB
- [ ] Click "Launch Instance"
- [ ] Wait for green checkmark (instance running)

✅ **MILESTONE 2 COMPLETE**: EC2 Instance Running

---

## ⏱️ STEP 3: Connect to Your Server (10 minutes)
**START**: ___:___ | END: ___:___

- [ ] Go to EC2 Instances dashboard
- [ ] Copy your instance's **Public IPv4 address**: `_________`
- [ ] On your computer, open Terminal/PowerShell
- [ ] Navigate to Downloads folder (where .pem file is)
- [ ] **Linux/Mac:**
  ```bash
  chmod 400 ci-failure-agent-key.pem
  ssh -i ci-failure-agent-key.pem ubuntu@YOUR_PUBLIC_IP
  ```
- [ ] **Windows (PowerShell):**
  ```powershell
  icacls "ci-failure-agent-key.pem" /grant:r "$($env:USERNAME):(R)" /inheritance:r
  ssh -i "ci-failure-agent-key.pem" ubuntu@YOUR_PUBLIC_IP
  ```
- [ ] Type "yes" when asked about host key verification
- [ ] You should see: `ubuntu@ip-172-...~$`

✅ **MILESTONE 3 COMPLETE**: Connected to Server

---

## ⏱️ STEP 4: Install Docker & Deploy App (20 minutes)
**START**: ___:___ | END: ___:___

**Run these commands on your server:**

- [ ] Update system:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
  (Wait for completion - 2-3 minutes)

- [ ] Install Docker:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  ```
  (Wait for completion - 2-3 minutes)

- [ ] Add user to Docker group:
  ```bash
  sudo usermod -aG docker ubuntu
  exit
  ```
  (Reconnect via SSH again)

- [ ] Install Docker Compose:
  ```bash
  sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  docker-compose --version
  ```

- [ ] Clone your repository:
  ```bash
  git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
  cd ci-failure-agent-spam-scam-fixing-filter
  ```

- [ ] Copy environment file:
  ```bash
  cp .env.example .env
  ```

- [ ] Start application:
  ```bash
  docker-compose up -d
  ```
  (Wait 30-60 seconds)

- [ ] Check status:
  ```bash
  docker-compose ps
  ```
  (Should show all containers as "Up")

✅ **MILESTONE 4 COMPLETE**: Application Running

---

## ⏱️ STEP 5: Verify Everything Works (5 minutes)
**START**: ___:___ | END: ___:___

**Run these tests on your server:**

- [ ] Test health endpoint:
  ```bash
  curl http://localhost:8000/health
  ```
  (Should return: `{"status": "ok"}`)

- [ ] View Docker logs:
  ```bash
  docker-compose logs app
  ```
  (Should show no errors)

✅ **MILESTONE 5 COMPLETE**: Application Verified

---

## ⏱️ STEP 6: Access Your System (5 minutes)
**START**: ___:___ | END: ___:___

**Your Public IP**: `_________`

- [ ] Open in browser: http://`YOUR_PUBLIC_IP`:8000
  - Verify you see: Swagger UI or API response
  - [ ] ✅ API is accessible

- [ ] Open in browser: http://`YOUR_PUBLIC_IP`:3000
  - Verify you see: Grafana login
  - [ ] Login: admin / admin
  - [ ] ✅ Grafana is accessible

- [ ] Open in browser: http://`YOUR_PUBLIC_IP`:9090
  - Verify you see: Prometheus dashboard
  - [ ] ✅ Prometheus is accessible

✅ **MILESTONE 6 COMPLETE**: System Accessible from Internet

---

## ⏱️ STEP 7: Final Verification & Documentation (5 minutes)
**START**: ___:___ | END: ___:___

- [ ] Test API with your IP:
  ```bash
  curl -X POST http://YOUR_PUBLIC_IP:8000/api/analyze-failure \
    -H "Content-Type: application/json" \
    -d '{"error_log": "test error"}'
  ```

- [ ] Document your system:
  - [ ] Public IP Address: `_________________`
  - [ ] Region: `_________________`
  - [ ] Instance ID: `_________________`
  - [ ] API URL: http://`YOUR_PUBLIC_IP`:8000
  - [ ] Grafana URL: http://`YOUR_PUBLIC_IP`:3000
  - [ ] Prometheus URL: http://`YOUR_PUBLIC_IP`:9090

- [ ] Set AWS Billing Alert:
  - [ ] Go to AWS Billing Dashboard
  - [ ] Enable "Receive Billing Alerts"
  - [ ] Set alert at $0.10

✅ **MILESTONE 7 COMPLETE**: Production System Live!

---

## 🎯 DEPLOYMENT COMPLETE!

### ✅ System Status:
- ✅ AWS account created
- ✅ EC2 instance running (t3.micro - $0/month)
- ✅ Docker containers deployed
- ✅ API responding from internet
- ✅ Grafana dashboard accessible
- ✅ Prometheus metrics collecting
- ✅ Total cost: $0 for 12 months

### 🔗 Your Live System:
**API**: http://`YOUR_PUBLIC_IP`:8000  
**Dashboard**: http://`YOUR_PUBLIC_IP`:3000  
**Metrics**: http://`YOUR_PUBLIC_IP`:9090  

### 📊 What's Running:
- ✅ CI/CD failure detection AI agent
- ✅ Spam/fraud detection system  
- ✅ PostgreSQL database
- ✅ Prometheus metrics
- ✅ Grafana dashboards
- ✅ Log aggregation

### 🚀 Next Steps:

1. **Get Beta Users (This Week)**
   - Share your API URL with 5-10 beta testers
   - Get feedback on CI/CD failure detection
   - Test spam blocking accuracy
   - Collect user stories

2. **Monitor & Optimize (This Month)**
   - Check AWS billing (should be $0)
   - Monitor system performance (Grafana)
   - Optimize based on user feedback
   - Plan Phase 2 features

3. **Scale When Ready (Next Month)**
   - Add RDS database (free tier)
   - Set up automated backups
   - Configure custom domain
   - Plan production hardening

---

## 🎉 CONGRATULATIONS!

Your production-grade AI system is now:
- 🌍 Accessible from anywhere on the internet
- ⚡ Running 24/7 in AWS cloud
- 💰 Costing $0 for 12 months
- 📈 Ready for real users
- 🔒 Production-grade infrastructure
- 📊 Fully monitored and logged

**Your CI/CD failure agent is LIVE!**

---

**Timeline Summary:**
- Planned: 60 minutes
- Actual: _____ minutes
- **Status**: ✅ LIVE ON AWS

**Deployment Date**: December 15, 2025  
**Deployer**: Your Team  
**System**: Production-Ready CI/CD Failure Agent  
**Cost**: $0 (Free Tier)

🚀 **System operational. Ready for users!**
