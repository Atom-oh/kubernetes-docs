# Infrastructure Advanced Quiz

> **Related Document**: [Infrastructure Advanced](../../ops/02-infrastructure-advanced.md)

## Multiple Choice Questions

### 1. What does an NLB weight ratio of 5:5 mean?

- A) Create five nodes in each cluster
- B) Configure an equal relative distribution of new flows
- C) Move every existing connection within five seconds
- D) It is invalid because the total is not 100

<details>
<summary>Show Answer</summary>

**Answer: B) Configure an equal relative distribution of new flows**

NLB weights are relative integers 0–999. Observed bytes/requests can differ with flow size, stickiness, and the observation window.

</details>

### 2. What matters when lowering an NLB group weight to zero?

- A) Existing connections must survive until natural closure
- B) The current guide says existing connections also close after a short period, so test reconnection
- C) Deregistration delay guarantees all transition times
- D) A successful API response means all traffic already moved

<details>
<summary>Show Answer</summary>

**Answer: B) The current guide says existing connections also close after a short period, so test reconnection**

Distinguish ordinary weight changes from zero transitions. Configuration acceptance and data-plane convergence are separate; inspect new/active flows, errors, and latency.

</details>

### 3. If blue and green DNS names point to the same shared NLB, what can DNS weights do?

- A) Independently select its target groups
- B) Pin requests to an AZ by hostname alone
- C) Select the same LB; they do not choose cluster-specific target groups
- D) Automatically select the same database replica

<details>
<summary>Show Answer</summary>

**Answer: C) Select the same LB; they do not choose cluster-specific target groups**

DNS-based selection needs distinct real LB endpoints leading to the intended clusters. Listener weights and DNS record weights operate at different layers.

</details>

### 4. How do you place workloads on Auto Mode nodes in a chosen AZ?

- A) Pod nodeSelector creates nodes by itself
- B) Put subnet_ids in the NodePool
- C) Align Pod selection, NodePool requirements, NodeClass subnet selection, and tolerations
- D) Name the cluster blue

<details>
<summary>Show Answer</summary>

**Answer: C) Align Pod selection, NodePool requirements, NodeClass subnet selection, and tolerations**

NodeSelector/affinity selects eligible nodes; provisioning constraints and taints/tolerations must also align. Distinguish worker placement from the regional managed control plane.

</details>

### 5. Which TGB ownership model does this externally managed TG example use?

- A) Built-in Auto Mode always has identical deletion behavior
- B) A separately installed LBC with elbv2.k8s.aws/v1beta1, distinct from built-in Auto Mode
- C) Only an ARN, with no Service or targetPort prerequisites
- D) Permanent Pod IPs registered through Terraform

<details>
<summary>Show Answer</summary>

**Answer: B) A separately installed LBC with elbv2.k8s.aws/v1beta1, distinct from built-in Auto Mode**

Built-in Auto Mode uses eks.amazonaws.com/v1 and documents TG deletion behavior. This recipe uses a separate controller for dynamic registration and networking rules.

</details>

### 6. What does a single PostgreSQL StatefulSet plus a Retain PVC guarantee?

- A) Cross-cluster replication
- B) Zero-downtime DB failover across AZs
- C) Every connection remains open
- D) It does not by itself guarantee HA, backup, or recovery

<details>
<summary>Show Answer</summary>

**Answer: D) It does not by itself guarantee HA, backup, or recovery**

Retain is a reclamation policy. Replication, backup, writer ownership, and recovery procedures are separate. NLB weights do not relocate EBS volumes across AZs.

</details>

### 7. Why separate alarm-input and decision-notification SNS topics?

- A) Prevent notifications from returning as new input and causing extra executions/errors
- B) Allow publishing without IAM permission
- C) Retry Lambda forever
- D) Eliminate DNS TTL

<details>
<summary>Show Answer</summary>

**Answer: A) Prevent notifications from returning as new input and causing extra executions/errors**

This handler accepts the SNS envelope. Direct CloudWatch Lambda events differ, so do not wire both invocation paths. A notification failure must not replay an already successful listener mutation.

</details>

### 8. What does the default automatic_failover=false do?

- A) Immediately shift all traffic to Green
- B) Propose changes without granting ModifyListener permission
- C) Skip health checks
- D) Modify every available listener

<details>
<summary>Show Answer</summary>

**Answer: B) Propose changes without granting ModifyListener permission**

Enable automatic mode only after capacity, SLO, reconnection, and writer coordination are tested. Reserved concurrency=1 does not serialize external Terraform or manual writers.

</details>

### 9. What should a manual transition script do?

- A) Evaluate raw user strings as Bash arithmetic
- B) Always assume an initial 100/0 state
- C) Validate weights and destination health, then show and approve the full plan
- D) Repeat a timer loop with STEP=0

<details>
<summary>Show Answer</summary>

**Answer: C) Validate weights and destination health, then show and approve the full plan**

Validate numeric bounds first and use the intended variables/backend. Check real SLOs and data compatibility between stages. API/apply success alone does not prove transition completion.

</details>

### 10. Which statement about Route 53 weight and TTL is correct?

- A) Weights are integers 0–255; TTL alone is not a recovery-time guarantee
- B) Weights are always 0–999
- C) A 60-second TTL is a 60-second recovery SLA
- D) If all choices are unhealthy, DNS must return no answer

<details>
<summary>Show Answer</summary>

**Answer: A) Weights are integers 0–255; TTL alone is not a recovery-time guarantee**

Alias records inherit target TTL. Consider health, resolver caches, connection lifetimes, and fallback behavior. All-zero weights are not a reliable traffic-stop mechanism.

</details>
