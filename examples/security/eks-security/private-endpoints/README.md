# Private endpoint example

[main.tf](main.tf) creates explicitly selected interface endpoints, an endpoint
security group and an S3 gateway endpoint in an existing VPC. It does not create
a VPC, subnets, NAT, workload security groups or a Kubernetes API endpoint.
This example has not been deployed by the documentation validation.

## Operator inputs

For demo execution, use only the administrator-approved existing
`fsi-demo-vpc` in `ap-northeast-2`. Verify the account, VPC ID and subnet
membership; a matching VPC name alone does not establish approval.

Start from [terraform.tfvars.example](terraform.tfvars.example). It contains
placeholders, not deployment IDs. Copy it to a private variable file outside
the checkout, replace every placeholder, and provide:

| Input | Required preparation |
| --- | --- |
| `vpc_id` | The approved existing demo VPC ID. |
| `private_subnet_ids` | Approved private subnets in that VPC, with the intended availability zone placement. |
| `private_route_table_ids` | Existing route tables associated with the private subnets that need the S3 gateway endpoint. |
| `client_security_group_ids` | Existing, explicitly approved node/Pod/management client security groups; their outbound rules must also permit the intended traffic. |
| `s3_endpoint_policy_json` | A reviewed JSON policy string covering the required ECR layer buckets and other permitted buckets. An endpoint policy does not grant the client's IAM permissions. |
| `interface_service_names` | Logical map keys to exact service names verified in the target Region, including only required APIs. The default is empty and creates no interface endpoints. |

`region` defaults to `ap-northeast-2`. Keep the selected service names and
resource IDs consistent with the approved account, Region and VPC.
Pass the private variable file to an authorized Terraform review with
`-var-file=/absolute/private/path/demo.tfvars`. Arrange approved private state
storage before applying; operator variable files, state and generated provider
cache directories (`.terraform/`) must not be committed.

## Network prerequisites

The interface endpoint security group permits TCP 443 from the supplied client
security groups. Verify client egress, DNS support/hostnames, private DNS,
subnet placement, routes, endpoint policies and the actual required APIs.
Review existing endpoints and their ownership before proposing duplicates.
The S3 gateway endpoint is associated only with the supplied route tables.

An EKS service endpoint does not configure the Kubernetes API endpoint.
Review cluster API private/public access and node/management reachability
separately. Private subnet placement also does not provide internet access.

For the [Qwen EKS launcher](../../../ai-ml/qwen-pii-finetuning/launch/eks/README.md),
AWS endpoints do not replace access to its current `ghcr.io` image, pip packages,
model/tokenizer source or the management host's NVIDIA Helm chart. Verify
approved NAT/egress or prepare private mirrors and configure those consumers.
Do not treat this endpoint example as a complete isolated-cluster configuration.

Formatting, schema and mocked tests do not establish live DNS, route,
security-group or endpoint reachability. Deployments and changes to the shared
VPC require the existing ownership and approval process.
