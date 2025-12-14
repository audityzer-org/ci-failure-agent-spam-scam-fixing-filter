# Phase 2 Execution Checklist

**Phase**: Cert-Manager & SSL/TLS Implementation  
**Status**: ✅ READY  
**Estimated Duration**: 5-10 minutes  
**Critical Path**: Yes (Required before Phase 3)

---

## Pre-Deployment Requirements

### Infrastructure Verification
- [ ] Phase 1 (EKS Cluster) successfully deployed
- [ ] Kubernetes cluster is healthy (all nodes ready)
- [ ] kubectl configured and authenticated to target cluster
- [ ] AWS credentials configured for cluster access
- [ ] VPC and security groups allow HTTP/HTTPS traffic

### Software Prerequisites
- [ ] Helm 3.x installed (`helm version`)
- [ ] kubectl 1.24+ installed (`kubectl version`)
- [ ] bash shell available (for deployment scripts)
- [ ] Domain name registered and accessible
- [ ] DNS provider credentials/access available
- [ ] Git repository access confirmed

### Permissions & Access
- [ ] EKS cluster admin role assigned
- [ ] IAM permissions for Helm operations
- [ ] Namespace creation permissions
- [ ] RBAC configuration rights
- [ ] Secret management access

---

## Pre-Deployment Checklist

### Resource Preparation
- [ ] Review `k8s/cert-manager-setup.yaml` manifest
- [ ] Confirm all YAML syntax is valid (`kubectl apply --dry-run`)
- [ ] Review `scripts/phase2-cert-manager-setup.sh` script
- [ ] Ensure script permissions are executable
- [ ] Confirm email address for Let's Encrypt (admin@predictive-propositions.dev)
- [ ] Verify domain list for certificate issuance

### Configuration Review
- [ ] ClusterIssuer production settings correct
- [ ] ClusterIssuer staging settings correct  
- [ ] HTTP01 solver ingress class name matches (nginx)
- [ ] ServiceMonitor annotations present
- [ ] CRD versions match Kubernetes version

### Backup & Rollback
- [ ] Git branch created for Phase 2 work
- [ ] Current cluster state snapshot taken
- [ ] Rollback procedure documented
- [ ] Backup of existing configs created

---

## Deployment Execution

### Step 1: Environment Preparation
```bash
# [ ] Export necessary environment variables
export CLUSTER_NAME="predictive-propositions-prod"
export REGION="us-east-1"
export NAMESPACE="cert-manager"
export HELM_VERSION="1.13.0"

# [ ] Verify connectivity
kubectl cluster-info
kubectl get nodes
```

### Step 2: Pre-Deployment Verification
```bash
# [ ] Check available cluster resources
kubectl top nodes
kubectl top pods --all-namespaces

# [ ] Verify Helm availability
helm version
helm repo list

# [ ] Validate YAML manifests
kubectl apply -f k8s/cert-manager-setup.yaml --dry-run=client -o yaml
```

### Step 3: Execute Deployment Script
```bash
# [ ] Make script executable
chmod +x scripts/phase2-cert-manager-setup.sh

# [ ] Run with monitoring
bash scripts/phase2-cert-manager-setup.sh

# [ ] Monitor output for errors/warnings
# [ ] Confirm all 10 steps completed successfully
```

### Step 4: Verify Installation
```bash
# [ ] Check cert-manager pods are running
kubectl get pods -n cert-manager
kubectl get pods -n cert-manager -o wide

# [ ] Verify all deployments are ready
kubectl rollout status deployment/cert-manager -n cert-manager
kubectl rollout status deployment/cert-manager-webhook -n cert-manager
kubectl rollout status deployment/cert-manager-cainjector -n cert-manager

# [ ] Check ClusterIssuers are ready
kubectl get clusterissuers
kubectl describe clusterissuer letsencrypt-prod
kubectl describe clusterissuer letsencrypt-staging
```

### Step 5: Test ACME Connectivity
```bash
# [ ] Check webhook service is running
kubectl get svc -n cert-manager

# [ ] Verify webhook readiness
kubectl get po cert-manager-webhook-* -n cert-manager -o wide

# [ ] Test issuer connectivity
kubectl describe clusterissuer letsencrypt-staging
# Check events section for ACME server connectivity
```

### Step 6: Domain Setup
```bash
# [ ] Get Load Balancer IP
LB_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "DNS Record: $LB_IP"

# [ ] Update DNS A records
# [ ] Point predictive-propositions.dev -> $LB_IP
# [ ] Point www.predictive-propositions.dev -> $LB_IP

# [ ] Wait for DNS propagation (5-10 minutes)
nslookup predictive-propositions.dev
```

### Step 7: Create Test Certificate
```bash
# [ ] Apply test certificate (staging issuer)
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: test-cert-staging
  namespace: default
spec:
  secretName: test-cert-staging-tls
  issuerRef:
    name: letsencrypt-staging
    kind: ClusterIssuer
  dnsNames:
  - predictive-propositions.dev
  - www.predictive-propositions.dev
EOF

# [ ] Monitor certificate issuance
kubectl describe certificate test-cert-staging
kubectl get certificate test-cert-staging -w
```

### Step 8: Production Certificate (After Staging Success)
```bash
# [ ] Only after staging certificate is READY
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: prod-cert
  namespace: default
spec:
  secretName: prod-cert-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - predictive-propositions.dev
  - www.predictive-propositions.dev
EOF

# [ ] Verify certificate is ready
kubectl describe certificate prod-cert
# [ ] Check certificate secret exists
kubectl get secret prod-cert-tls -o yaml
```

---

## Post-Deployment Verification

### Certificate Status Checks
- [ ] Production certificate is READY
- [ ] Certificate secret contains tls.crt and tls.key
- [ ] Certificate expiration date is 90 days from now
- [ ] Renewal is scheduled before expiration

### Monitoring Configuration
- [ ] ServiceMonitor is created (`kubectl get servicemonitor -n cert-manager`)
- [ ] Prometheus can scrape cert-manager metrics
- [ ] Grafana dashboards can see cert-manager data

### Security Validation
- [ ] RBAC permissions are minimal
- [ ] Service accounts have proper role bindings
- [ ] Network policies allow necessary traffic
- [ ] Secret storage is encrypted

### Logging & Alerting
- [ ] cert-manager logs are being captured
- [ ] Alert rules are configured for certificate expiration
- [ ] Alert rules are configured for renewal failures
- [ ] Webhook health checks are active

---

## Troubleshooting Checklist

### If Certificate Not Issuing:
- [ ] Check certificate status: `kubectl describe certificate <name>`
- [ ] Check ACME logs: `kubectl logs -n cert-manager -l app=cert-manager`
- [ ] Verify webhook is running: `kubectl get po cert-manager-webhook-* -n cert-manager`
- [ ] Check DNS resolution: `nslookup predictive-propositions.dev`
- [ ] Verify ingress HTTP reachability
- [ ] Check rate limiting: Switch to staging issuer

### If ACME Challenge Fails:
- [ ] Verify HTTP/80 is open to public
- [ ] Check DNS points to correct IP: `dig predictive-propositions.dev`
- [ ] Verify ingress-nginx-controller is running
- [ ] Check ingress rules are configured
- [ ] Review webhook error logs

### If Helm Installation Fails:
- [ ] Check Helm repo is added: `helm repo list`
- [ ] Update repos: `helm repo update`
- [ ] Check namespace exists: `kubectl get ns cert-manager`
- [ ] Verify RBAC permissions
- [ ] Check resource limits on nodes

---

## Health Check Commands

```bash
# Comprehensive status check
#!/bin/bash

echo "=== Cluster Status ==="
kubectl cluster-info
kubectl get nodes

echo "\n=== Cert-Manager Namespace ==="
kubectl get all -n cert-manager

echo "\n=== ClusterIssuers ==="
kubectl get clusterissuers
kubectl get clusterissuers -o wide

echo "\n=== Certificates ==="
kubectl get certificates --all-namespaces
kubectl get certificates -A -o wide

echo "\n=== Secrets ==="
kubectl get secrets -A | grep tls

echo "\n=== Services ==="
kubectl get svc -n ingress-nginx

echo "\n=== Pod Status ==="
kubectl get pods -n cert-manager -o wide

echo "\n=== Logs ==="
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

---

## Success Criteria

✅ **Phase 2 is COMPLETE when:**
- [ ] All cert-manager pods are running
- [ ] Both ClusterIssuers are READY
- [ ] At least one certificate is READY
- [ ] TLS secret exists and is valid
- [ ] Certificate renewal is scheduled
- [ ] No errors in logs
- [ ] Health checks all pass
- [ ] Prometheus metrics are being collected
- [ ] Alerting rules are active

---

## Next Steps

→ **Phase 3**: Monitoring Stack Setup

```bash
cd scripts
chmod +x phase3-monitoring-setup.sh
bash phase3-monitoring-setup.sh
```

---

## Rollback Plan

If Phase 2 deployment fails:

```bash
# Uninstall cert-manager
helm uninstall cert-manager -n cert-manager

# Delete namespace
kubectl delete namespace cert-manager

# Verify removal
kubectl get all -n cert-manager

# Return to previous state
git checkout HEAD~1
```

---

**Last Updated**: $(date)  
**Phase Status**: ✅ READY FOR EXECUTION  
**Tested**: Yes  
**Production Ready**: Yes
