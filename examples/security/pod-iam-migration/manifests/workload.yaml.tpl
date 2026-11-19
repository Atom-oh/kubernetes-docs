# Rendered once per namespace by 01-baseline.sh: NAMESPACE is substituted with sed.
apiVersion: v1
kind: Namespace
metadata:
  name: NAMESPACE
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: NAMESPACE
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whoami
  namespace: NAMESPACE
  labels: { app: whoami }
spec:
  replicas: 1
  selector:
    matchLabels: { app: whoami }
  template:
    metadata:
      labels: { app: whoami }
    spec:
      serviceAccountName: s3-reader
      containers:
        - name: aws
          # Pin a digest/tag in real use. AWS CLI v2 supports both web identity (IRSA)
          # and the container credential provider (Pod Identity).
          image: public.ecr.aws/aws-cli/aws-cli:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
              while true; do
                echo "----- $(date -u +%FT%TZ) ns=NAMESPACE"
                if [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ]; then echo "source: IRSA (web identity) role=${AWS_ROLE_ARN}";
                elif [ -n "${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ]; then echo "source: Pod Identity agent ${AWS_CONTAINER_CREDENTIALS_FULL_URI}";
                else echo "source: none injected -> SDK falls through to IMDS (node instance profile)"; fi
                aws sts get-caller-identity --query Arn --output text || true
                aws s3 ls "s3://${DEMO_BUCKET}/" --region "${AWS_REGION}" || true
                sleep 30
              done
          env:
            - { name: DEMO_BUCKET, value: "${DEMO_BUCKET}" }
            - { name: AWS_REGION,  value: "${AWS_REGION}" }
          resources:
            requests: { cpu: 10m, memory: 64Mi }
            limits:   { memory: 128Mi }
