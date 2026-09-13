# EKS security validation examples

These files are examples for the security chapter. They are not a deployed
security system or a production certification.

- `ecr_scan_gate.py` checks the exact account/repository/digest, a successful scan
  status, a completion timestamp and an explicit severity-count map. ACTIVE alone
  is insufficient. Counts summarize the image; detailed finding pagination is
  separate. An initial scan gate does not prove indefinite safety or runtime
  protection. Exceptions and freshness requirements need an explicit policy.
- Run the Python tests with boto3 installed. Botocore Stubber and a fake clock
  prevent AWS requests and real waiting during tests.
- `private-endpoints` accepts explicit, Region-verified service names. It uses
  logical map keys for tags instead of splitting variable-length endpoint names.
  Provide existing subnets, route tables, client security groups and a reviewed
  S3 endpoint policy. No resources were provisioned.
- `tenant-baseline.yaml` targets a Kubernetes 1.35 policy baseline and a CNI that
  enforces NetworkPolicy. Confirm DNS labels and NodeLocal DNS behavior. Namespace
  workload creation can still provide indirect access to namespace credentials;
  this is not a hard boundary for mutually hostile tenants.
- The GuardDuty event pattern matches tactic-prefixed Kubernetes/Runtime finding
  types. Runtime findings can concern resources beyond EKS: validate the finding's
  actual resource metadata before choosing an EKS response. This pattern has no
  target and does not isolate a Pod.
- The GuardDuty feature payload is an account/Region configuration example. Check
  the existing detector, organization ownership, platform coverage and costs
  first. Do not enable EKS_RUNTIME_MONITORING and RUNTIME_MONITORING together.
