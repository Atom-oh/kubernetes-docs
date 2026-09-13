terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = set(string) }
variable "private_route_table_ids" { type = set(string) }
variable "client_security_group_ids" {
  type        = set(string)
  description = "Existing node/Pod/management security groups allowed to reach interface endpoints."
}
variable "interface_service_names" {
  type        = map(string)
  description = "Stable logical name => exact service name verified in the target Region. Include only required APIs."
  default     = {}
}
variable "s3_endpoint_policy_json" {
  type        = string
  description = "Reviewed gateway endpoint policy for ECR layer buckets and other required buckets; endpoint policy is not an IAM grant."
}

resource "aws_security_group" "endpoints" {
  name_prefix = "eks-private-endpoints-"
  description = "HTTPS from explicitly approved client security groups"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  for_each                     = var.client_security_group_ids
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "Approved endpoint client"
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = var.interface_service_names
  vpc_id              = var.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags = {
    Name = "vpce-${each.key}"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids
  policy            = var.s3_endpoint_policy_json
  tags = {
    Name = "vpce-s3"
  }
}
