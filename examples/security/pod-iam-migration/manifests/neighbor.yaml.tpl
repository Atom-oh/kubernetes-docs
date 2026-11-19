# "Noisy neighbour": a pod that was never granted AWS access.
# With only a node instance profile it still inherits the node role via IMDS.
apiVersion: v1
kind: Pod
metadata:
  name: neighbor
  namespace: default
spec:
  restartPolicy: Never
  containers:
    - name: aws
      image: public.ecr.aws/aws-cli/aws-cli:latest
      command: ["/bin/sh", "-c", "sleep 3600"]
      env:
        - { name: DEMO_BUCKET, value: "${DEMO_BUCKET}" }
        - { name: AWS_REGION,  value: "${AWS_REGION}" }
