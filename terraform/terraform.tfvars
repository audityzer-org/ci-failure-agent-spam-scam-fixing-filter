# Terraform Variables - Production EKS Deployment
# For auditorsec.com and audityzer.com infrastructure

aws_region         = "us-east-1"
cluster_name       = "ci-failure-agent-cluster"
kubernetes_version = "1.28"
environment        = "production"
vpc_cidr           = "10.0.0.0/16"

# Node Group Configuration
desired_size = 3
min_size     = 2
max_size     = 10
instance_types = ["t3.medium", "t3.large"]
disk_size    = 50

# Tags
tags = {
  Project             = "CI-Failure-Agent"
  Environment         = "Production"
  ManagedBy           = "Terraform"
  CostCenter          = "Engineering"
  CreatedBy           = "CI/CD-Pipeline"
  Domains             = "auditorsec.com,audityzer.com"
  GovernmentAudit     = "enabled"
  EnergySectorMonitor = "enabled"
}
