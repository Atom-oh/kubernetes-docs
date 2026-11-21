#!/bin/sh
set -eu

bucket=$1
key=$2
export AWS_PAGER=""
export HOME=/tmp
arn=$(aws sts get-caller-identity --query Arn --output text)
printf 'arn=%s\n' "$arn"

if aws s3api get-object --bucket "$bucket" --key "$key" /tmp/probe.txt >/tmp/s3-result 2>&1; then
  if [ "$(cat /tmp/probe.txt)" != "eks-workload-identity" ]; then
    printf '%s\n' 'S3 returned an unexpected probe object.' >&2
    exit 1
  fi
  printf '%s\n' 's3=allowed'
else
  case "$(cat /tmp/s3-result)" in
    *'(AccessDenied)'*|*'(403)'*) printf '%s\n' 's3=denied' ;;
    *) cat /tmp/s3-result >&2; exit 1 ;;
  esac
fi
