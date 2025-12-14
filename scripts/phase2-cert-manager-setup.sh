#!/bin/bash

# Phase 2: Cert-Manager & SSL/TLS Setup for Kubernetes
# Installs cert-manager for automatic certificate management and domain configuration
# Supports Let's Encrypt ACME challenges for production certificates

set -e

CLUSTER_NAME="predictive-propositions-prod"
REGION="us-east-1"
NAMESPACE="cert-manager"
HELM_VERSION="1.13.0"

echo "=== Phase 2: Cert-Manager & SSL/TLS Setup ==="
echo ""

# Color codes for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Step 1: Verify cluster connectivity
print_status "Step 1: Verifying cluster connectivity..."
kubectl cluster-info > /dev/null 2>&1 || {
    print_error "Failed to connect to cluster. Please configure kubeconfig."
    exit 1
}
print_success "Cluster connectivity verified"

# Step 2: Create cert-manager namespace
print_status "Step 2: Creating cert-manager namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f - || true
kubectl label namespace ${NAMESPACE} cert-manager-managed=true --overwrite || true
print_success "Cert-manager namespace created"

# Step 3: Add Helm repositories
print_status "Step 3: Adding Helm repositories..."
helm repo add jetstack https://charts.jetstack.io || true
helm repo update
print_success "Helm repositories added"

# Step 4: Install cert-manager CRDs
print_status "Step 4: Installing cert-manager CRDs..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v${HELM_VERSION}/cert-manager.crds.yaml || true
print_success "Cert-manager CRDs installed"

# Step 5: Install cert-manager via Helm
print_status "Step 5: Installing cert-manager Helm chart..."
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace ${NAMESPACE} \
  --set installCRDs=false \
  --set global.leaderElection.namespace=${NAMESPACE} \
  --set serviceAccount.create=true \
  --set serviceAccount.name=cert-manager \
  --version ${HELM_VERSION} \
  --wait \
  --timeout 5m
print_success "Cert-manager installed"

# Step 6: Wait for cert-manager to be ready
print_status "Step 6: Waiting for cert-manager deployment to be ready..."
kubectl rollout status deployment/cert-manager -n ${NAMESPACE} --timeout=5m
kubectl rollout status deployment/cert-manager-webhook -n ${NAMESPACE} --timeout=5m
print_success "Cert-manager deployments are ready"

# Step 7: Apply cert-manager ACME issuers and config
print_status "Step 7: Applying cert-manager ACME issuers..."
kubectl apply -f k8s/cert-manager-setup.yaml
print_success "ACME issuers configured"

# Step 8: Verify cert-manager installation
print_status "Step 8: Verifying cert-manager installation..."
kubectl get pods -n ${NAMESPACE}
kubectl get clusterissuers
print_success "Cert-manager installation verified"

# Step 9: Configure DNS and domain validation
print_status "Step 9: Domain configuration information..."
echo ""
echo "To complete SSL/TLS setup:"
echo "1. Point your domain to the Load Balancer IP"
echo "2. Run: kubectl get svc ingress-nginx-controller -n ingress-nginx"
echo "3. Certificate validation will occur automatically via ACME HTTP01 challenge"
echo ""

# Step 10: Health check
print_status "Step 10: Final health checks..."
CERT_MANAGER_READY=$(kubectl get deployment cert-manager -n ${NAMESPACE} -o jsonpath='{.status.conditions[?(@.type=="Available")].status}')
if [ "$CERT_MANAGER_READY" = "True" ]; then
    print_success "Cert-manager is operational"
else
    print_error "Cert-manager deployment status check failed"
    exit 1
fi

echo ""
echo "=== Phase 2 Complete ==="
echo "\nNext Steps:"
echo "1. Configure domain DNS records to point to ingress controller"
echo "2. Create Certificate resources for your domains"
echo "3. Monitor certificate renewal: kubectl describe certificate <name> -n <namespace>"
echo "4. Proceed to Phase 3: Monitoring Stack Setup"
echo ""
echo "Estimated runtime: 5-10 minutes"
