#!/usr/bin/env bash
# Step 4 - Who am I? Run after every step and compare.
source "$(dirname "$0")/00-env.sh"

probe() { # probe <namespace> <kubectl exec target>
  local ns="$1" target="$2"
  printf '\n=== %-11s %s\n' "$ns" "$target"
  kubectl -n "$ns" exec "$target" -- sh -c '
    if   [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ];       then echo "mechanism : IRSA";
    elif [ -n "${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ]; then echo "mechanism : Pod Identity";
    else echo "mechanism : (none injected) -> IMDS / node role"; fi
    printf "identity  : "; aws sts get-caller-identity --query Arn --output text 2>&1 | tail -1
    printf "s3 ls     : "; aws s3 ls "s3://${DEMO_BUCKET}/" --region "${AWS_REGION}" >/dev/null 2>&1 && echo ALLOWED || echo DENIED
    printf "IMDS      : "; command -v curl >/dev/null || { echo "curl not in image"; exit 0; }; TOKEN=$(curl -s -m 2 -X PUT http://169.254.169.254/latest/api/token \
         -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null); [ -n "$TOKEN" ] && echo REACHABLE || echo BLOCKED
  ' 2>&1
}

probe demo-node  deploy/whoami
probe demo-irsa  deploy/whoami
probe demo-podid deploy/whoami
probe default    neighbor
