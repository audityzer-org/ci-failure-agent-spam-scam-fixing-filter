#!/bin/bash

# AWS Infrastructure Validation Script for Audityzer
# Перевіряє готовність AWS інфраструктури до розгортання

set -e

echo "========================================"
echo "AWS Infrastructure Validation for Audityzer"
echo "========================================"
echo ""

# Кольори
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функція для перевірки
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
        return 0
    else
        echo -e "${RED}✗ $1${NC}"
        return 1
    fi
}

echo "[1] Перевірка AWS CLI..."
aws --version > /dev/null
check "AWS CLI встановлено"

echo "\n[2] Перевірка AWS облікових даних..."
aws sts get-caller-identity > /dev/null
check "AWS облікові дані налаштовані"

echo "\n[3] Перевірка VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=audityzer-vpc --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" != "None" ] && [ -n "$VPC_ID" ]; then
    echo -e "${GREEN}✓ VPC знайдено: $VPC_ID${NC}"
else
    echo -e "${YELLOW}⚠ VPC не знайдено. Потрібно запустити: terraform apply${NC}"
fi

echo "\n[4] Перевірка EKS Cluster..."
EKS_CLUSTER=$(aws eks list-clusters --query 'clusters[?contains(@, `audityzer`)]' --output text)
if [ -n "$EKS_CLUSTER" ]; then
    echo -e "${GREEN}✓ EKS Cluster знайдено: $EKS_CLUSTER${NC}"
    CLUSTER_STATUS=$(aws eks describe-cluster --name audityzer-eks --query 'cluster.status' --output text)
    echo -e "  Status: ${GREEN}$CLUSTER_STATUS${NC}"
else
    echo -e "${YELLOW}⚠ EKS Cluster не знайдено${NC}"
fi

echo "\n[5] Перевірка RDS Database..."
RDS_DB=$(aws rds describe-db-instances --db-instance-identifier audityzer-db --query 'DBInstances[0].DBInstanceIdentifier' --output text 2>/dev/null)
if [ "$RDS_DB" != "None" ] && [ -n "$RDS_DB" ]; then
    echo -e "${GREEN}✓ RDS Database знайдено: $RDS_DB${NC}"
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier audityzer-db --query 'DBInstances[0].DBInstanceStatus' --output text)
    echo -e "  Status: ${GREEN}$DB_STATUS${NC}"
else
    echo -e "${YELLOW}⚠ RDS Database не знайдено${NC}"
fi

echo "\n[6] Перевірка ECR Repository..."
ECR_REPO=$(aws ecr describe-repositories --repository-names audityzer-api --query 'repositories[0].repositoryUri' --output text 2>/dev/null)
if [ "$ECR_REPO" != "None" ] && [ -n "$ECR_REPO" ]; then
    echo -e "${GREEN}✓ ECR Repository знайдено: $ECR_REPO${NC}"
else
    echo -e "${YELLOW}⚠ ECR Repository не знайдено${NC}"
fi

echo "\n[7] Перевірка IAM Roles..."
IAM_ROLE=$(aws iam get-role --role-name eks-audityzer-role --query 'Role.RoleName' --output text 2>/dev/null)
if [ "$IAM_ROLE" != "None" ] && [ -n "$IAM_ROLE" ]; then
    echo -e "${GREEN}✓ IAM Role знайдено: $IAM_ROLE${NC}"
else
    echo -e "${YELLOW}⚠ IAM Role не знайдено${NC}"
fi

echo "\n[8] Перевірка S3 Buckets..."
S3_BACKUPS=$(aws s3 ls audityzer-backups 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ S3 Backup bucket існує${NC}"
else
    echo -e "${YELLOW}⚠ S3 Backup bucket не існує${NC}"
fi

echo "\n[9] Перевірка kubectl доступу..."
kubectl cluster-info > /dev/null 2>&1
if [ $? -eq 0 ]; then
    check "kubectl доступ налаштований"
    NODES=$(kubectl get nodes --no-headers | wc -l)
    echo -e "${GREEN}  Nodes у кластері: $NODES${NC}"
else
    echo -e "${RED}✗ kubectl доступ не налаштований${NC}"
fi

echo "\n[10] Перевірка TLS Certificates..."
CERT=$(kubectl get secret audityzer-tls -n production 2>/dev/null)
if [ $? -eq 0 ]; then
    check "TLS Certificate налаштований"
else
    echo -e "${YELLOW}⚠ TLS Certificate не знайдено${NC}"
fi

echo ""
echo "========================================"
echo "Валідація завершена"
echo "========================================"

echo ""
echo "Наступні кроки:"
echo "1. Якщо якісь перевірки не пройшли, запустіть: terraform apply"
echo "2. Оновіть kubernetes config: aws eks update-kubeconfig --name audityzer-eks"
echo "3. Розгорніть додатки: kubectl apply -f k8s/"
echo "4. Перевірте статус: kubectl get all -n production"
