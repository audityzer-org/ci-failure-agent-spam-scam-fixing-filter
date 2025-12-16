# Cost Optimization & Scaling Strategy

**Current State:** $0 Year 1 (AWS Free Tier), ~$15-20 Year 2

## Cost Breakdown Year 2+
- EC2 t3.micro: $9/month ($108/year)
- RDS db.t3.micro: $50/month ($600/year) *Single AZ
- Render.com UI: Free tier ($0)
- Data transfer: ~$5/month ($60/year)
- **Total: ~$768/year (~$64/month)**

## Scaling Timeline

### Phase 1: Current (0-50K users)
- 1x EC2 t3.micro
- 1x RDS db.t3.micro single AZ
- Redis: 100MB max
- Cost: $64/month

### Phase 2: Growth (50K-500K users)
- 2-3x EC2 t3.small (behind ALB)
- RDS db.t3.small with read replica
- Redis 1GB cluster
- Cost: $300-400/month

### Phase 3: Scale (500K+ users)
- 5-10x EC2 t3.medium
- RDS db.t3.large multi-AZ
- Redis 5GB cluster
- CloudFront CDN
- Cost: $1000-1500/month

## Optimization Strategies
1. Use Spot Instances (70% savings)
2. Reserved Instances (30-50% savings)
3. S3 Intelligent-Tiering for logs
4. CloudFront edge caching
5. Auto-shutdown during off-hours

---
**Last Updated:** December 16, 2025
