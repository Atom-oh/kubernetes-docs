# AskDocs in the shared demo VPC

This CDK application hosts the documentation Q&A API behind CloudFront and an
internal ALB. The ALB forwards to a private API Gateway REST API through an
execute-api VPC endpoint; Lambda Web Adapter streams the Lambda response.
The existing `AskDocsData` stack stores the document index and conversation state.

All demo resources use the existing `fsi-demo-vpc` in `ap-northeast-2`, as required
by the local infrastructure policy. `AskDocsDemoNetwork` imports that VPC and its
isolated subnets. It creates AskDocs security groups and an execute-api endpoint,
and does not create or modify the shared VPC, subnets, routes, internet gateway,
or existing S3, DynamoDB and Bedrock endpoints.

## Configuration and prerequisites

The seven `demo*` settings in `cdk.json` are intentionally empty. Supply their
real values from read-only inventory of the existing `fsi-demo-vpc`; do not
commit VPC, subnet, route-table or endpoint security-group identifiers, or the
demo CIDR. Do not replace missing infrastructure by creating another VPC.
Keep real values in a permission-restricted JSON file outside the repository
and pass them explicitly as CDK `-c key=value` arguments. The tracked
`cdk.context.json` is not a private configuration file and must not be edited to
store these values.

| Context | Used for |
| --- | --- |
| `account` | Account for all stacks |
| `demoVpcId`, `demoVpcCidr` | Existing demo VPC and its IPv4 CIDR |
| `demoIsolatedSubnetA`, `demoIsolatedSubnetB` | Existing isolated subnets, respectively in `ap-northeast-2a` and `ap-northeast-2b` |
| `demoIsolatedRouteTableA`, `demoIsolatedRouteTableB` | Route tables associated with those subnets, in the same order |
| `demoBedrockEndpointSg` | Security group attached to the existing Bedrock runtime interface endpoint |
| `appZoneId` | Existing `aws.atomai.click` hosted zone for the Seoul origin certificate and DNS |
| `publicZoneId` | Existing `atomai.click` hosted zone for the CloudFront certificate and site DNS |
| `modelId` | Backend model identifier, currently `global.anthropic.claude-haiku-5-5` |

The existing account and hosted-zone settings remain in `cdk.json`. The demo
inputs are required even when synthesizing the edge stack because CDK constructs
the network/data/app stacks before selecting the requested output.

`bin/app.ts` pins the network/data/app stacks to `ap-northeast-2` and the edge
stack to `us-east-1`; changing the `region` context alone does not move them.
The network uses Seoul managed-prefix-list constants in `network-stack.ts`.
Its `s3PrefixListId` and `cloudfrontOriginFacingPrefixListId` context entries do
not override those constants. Bedrock IAM model ARNs in `app-stack.ts` also
remain fixed to Haiku 5.5; changing `modelId` alone does not update that policy.
Other account/domain-specific names in the stacks must be reviewed together
before adapting this application to another environment.

Verify these existing-network prerequisites:

- Both subnet and route-table pairs belong to the supplied VPC and expected AZs.
  Isolated subnet route tables have no internet-gateway or NAT default route.
- An internet gateway is attached to the VPC for CloudFront VPC origins. It is
  not used to route CloudFront traffic to the private origin.
- S3 and DynamoDB gateway endpoints are associated with both route tables, and
  their endpoint policies permit the Lambda role's required operations.
- The Bedrock runtime interface endpoint has private DNS enabled and its
  supplied security group admits TCP 443 from the Lambda workload. The code
  assumes the shared endpoint already admits the VPC's private CIDR; it does not
  add or broaden that ingress rule.
- The Bedrock endpoint policy, IAM permissions, account model access, quotas and
  cross-region permissions allow the configured global inference profile.
- Private subnets have enough free IPv4 addresses for the ALB, Lambda and
  endpoint ENIs. NACLs permit the required return traffic, including CloudFront
  VPC-origin ephemeral TCP ports.
- The ALB is internal. Its security group admits TCP 443 only from the
  CloudFront origin-facing managed prefix list. The execute-api endpoint admits
  TCP 443 only from that ALB security group.

The named hosted zones, certificates' DNS-validation permissions, existing CDK
bootstrap resources in both regions and GitHub OIDC provider are also required.
Offline synth does not verify any of these deployed resources.

## Local validation

From `infra/ask-docs`, use the locked dependencies and write generated assets
outside the source tree. These explicit **synthetic fixtures** are only for
offline validation; they do not identify real resources and must never be used
for deployment:

```sh
npm ci
npm run build
npm run synth -- --no-lookups --quiet --output /tmp/ask-docs-base-synth \
  -c account=111111111111 \
  -c demoVpcId=vpc-0123456789abcdef0 \
  -c demoVpcCidr=10.123.0.0/16 \
  -c demoIsolatedSubnetA=subnet-01111111111111111 \
  -c demoIsolatedSubnetB=subnet-02222222222222222 \
  -c demoIsolatedRouteTableA=rtb-01111111111111111 \
  -c demoIsolatedRouteTableB=rtb-02222222222222222 \
  -c demoBedrockEndpointSg=sg-03333333333333333
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s test -p 'test_*.py' -v
```

The Python tests mock AWS clients and use a localhost HTTP server; they do not
invoke Bedrock or modify AWS resources. `--no-lookups` prevents CDK resource
lookups. These checks do not establish deployed connectivity or streaming.
Running synth without the seven context values fails with a required-context
error. These offline commands also override the account with a synthetic
account number; no fixture account or network is queried.
Do not commit `node_modules`, `cdk.out`, generated index archives or personal
`.codex/config.toml` settings. Preserve the executable Git mode of `lambda/ask/run.sh`.

## Private context for a deployment review

Create a JSON file outside every Git worktree, readable only by its owner
(mode `0600`). Its keys are the seven required `demo*` keys from the table above;
values come from verified read-only inventory, not the offline fixtures.
This file and any synthesized templates containing its values are local
deployment inputs: do not add them to Git, PR text, shared logs or public
reports. `--no-lookups` does not remove identifiers from synthesized templates.

The following example reads such a file and passes each value as a separate
explicit CDK context argument. The wrapper does not print those values itself
or edit tracked configuration. It performs synth only. Keep its child process's
stdout and stderr private as well: a CDK diagnostic can contain resource identifiers.

```sh
ASK_DOCS_CONTEXT_FILE=/absolute/path/outside/git/ask-docs-context.json
python3 - "$ASK_DOCS_CONTEXT_FILE" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

keys = (
    "demoVpcId", "demoVpcCidr",
    "demoIsolatedSubnetA", "demoIsolatedSubnetB",
    "demoIsolatedRouteTableA", "demoIsolatedRouteTableB",
    "demoBedrockEndpointSg",
)
values = json.loads(Path(sys.argv[1]).read_text())
args = [
    "npx", "cdk", "synth",
    "AskDocsDemoNetwork", "AskDocsData", "AskDocsAppDemo",
    "--no-lookups", "--quiet", "--output", "/tmp/ask-docs-private-synth",
]
for key in keys:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Missing private context: {key}")
    args.extend(["-c", f"{key}={value}"])
try:
    subprocess.run(args, check=True)
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"CDK synth failed (exit {exc.returncode}); keep diagnostics private.") from None
PY
```

Keep that output directory private as well. Explicit CLI arguments may be
visible to local process inspection; the input file is not a secret store.
Add deployment/edge arguments only in the separately authorized operator
workflow, keeping actual origin identifiers out of published artifacts.

## Migration and rollback

`AskDocsDemoNetwork` and `AskDocsAppDemo` are new stack identities. They coexist
with any previously deployed `AskDocsNetwork` and `AskDocsApp`; renaming them
does not migrate or delete those stacks. `AskDocsData` keeps its existing
identity and resources. Do not introduce a second Data stack or copy its
account-specific bucket into a new stack.

For a separately authorized deployment, first review the live stack inventory
and CDK diff, then use this order:

1. Deploy the new `AskDocsDemoNetwork` into the verified shared VPC.
2. Reuse the existing `AskDocsData`; review any proposed changes before applying
   them. Deploy `AskDocsAppDemo` against that Data stack and the new network.
3. Verify the new internal ALB, private API and Lambda path, and obtain the new
   app stack's `AlbArn`, `AlbSecurityGroupId` and `VpcId` outputs. Obtain that
   ALB's DNS name from read-only inventory; it is not currently a stack output.
4. Pass all four edge context values below from the new ALB. The edge stack is
   instantiated only when all four are supplied. First synth and review its
   diff; then deploy the edge change after the new origin is active.
5. Verify `docs.atomai.click` serves the site and that streamed answers,
   citations and conversation follow-ups work through CloudFront. Preserve the
   previous stack and distribution configuration until cutover is accepted.

For an offline check of that edge code, use the same seven synthetic network
inputs and four synthetic ALB inputs. This command also performs synth only:

```sh
npx cdk synth AskDocsEdge --no-lookups --quiet --output /tmp/ask-docs-edge-synth \
  -c account=111111111111 \
  -c demoVpcId=vpc-0123456789abcdef0 \
  -c demoVpcCidr=10.123.0.0/16 \
  -c demoIsolatedSubnetA=subnet-01111111111111111 \
  -c demoIsolatedSubnetB=subnet-02222222222222222 \
  -c demoIsolatedRouteTableA=rtb-01111111111111111 \
  -c demoIsolatedRouteTableB=rtb-02222222222222222 \
  -c demoBedrockEndpointSg=sg-03333333333333333 \
  -c albArn=arn:aws:elasticloadbalancing:ap-northeast-2:111111111111:loadbalancer/app/ask-fixture/1111111111111111 \
  -c albSecurityGroupId=sg-04444444444444444 \
  -c albDnsName=internal-ask-fixture.ap-northeast-2.elb.amazonaws.com \
  -c vpcId=vpc-0123456789abcdef0
```

For a real edge review, the private-context wrapper must instead select
`AskDocsEdge` and append explicit `-c` arguments for `albArn`,
`albSecurityGroupId`, `albDnsName` and `vpcId` from the verified new app.
Do not use synthetic values for cutover.

The new origin certificate and DNS name are
`ask-origin-demo.aws.atomai.click`. `DemoVpcOrigin` is a new CloudFront VPC-origin
resource, while the distribution retains its identity and switches its
reference to that new origin. This avoids editing the old VPC origin while it
is associated with the distribution. The previous origin may be removed during
the edge update after disassociation; do not assume it remains available as a
rollback target.

Before an edge cutover, rollback means leaving the existing edge configuration
unchanged and keeping the previous App/Network stacks. After cutover, rollback
requires a reviewed edge template that restores the previous ALB and its origin
domain/certificate; if its VPC-origin resource has been deleted, recreate it
before switching the distribution. Simply passing an old ALB ARN to the current
template is insufficient because its origin DNS/certificate assumptions are
for the new demo ALB.

Old App/Network retirement is a separate operation after successful cutover.
Inspect CloudFormation exports/imports and other consumers first. This change
does not authorize deleting old stacks, shared network resources, or Data.

AWS references:

- [CloudFront VPC-origin prerequisites and updates](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [API Gateway Lambda response streaming](https://docs.aws.amazon.com/apigateway/latest/developerguide/response-transfer-mode-lambda.html)
- [Claude Haiku 5.5 model and inference-profile support](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html)
