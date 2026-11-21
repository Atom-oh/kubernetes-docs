#!/bin/sh
# Runs inside each copy of the "orders" app. Every 3 seconds it asks STS who it
# is and reads one S3 object, then prints one JSON line. No credentials or
# tokens are printed. The AWS CLI picks credentials with its default chain:
# IRSA (web identity) and Pod Identity (container provider) come before IMDS,
# so the copy switches source as soon as EKS injects the new variables.
while :; do
  src=imds
  [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ] && src=irsa
  [ -n "${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ] && src=pod-identity
  if arn=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null); then
    role=${arn#*:assumed-role/}
    role=${role%%/*}
  else
    role=no-credentials
  fi
  if aws s3api get-object --bucket "$BUCKET" --key "$KEY" /tmp/object >/tmp/s3 2>&1; then
    s3=allowed
  else
    case "$(cat /tmp/s3)" in
      *AccessDenied*|*'(403)'*) s3=denied ;;
      *'Unable to locate credentials'*) s3=no-creds ;;
      *) s3=error ;;
    esac
  fi
  printf '{"t":"%s","src":"%s","role":"%s","s3":"%s"}\n' "$(date -u +%H:%M:%S)" "$src" "$role" "$s3"
  sleep 3
done
