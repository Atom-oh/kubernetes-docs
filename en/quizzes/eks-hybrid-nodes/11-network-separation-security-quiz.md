# Hybrid Nodes Network-Separation Security Review Quiz

> **Last Updated**: September 16, 2026

[Study guide: Reviewing Hybrid Nodes Network Separation with Security Teams](../../eks-hybrid-nodes/11-network-separation-security.md)

1. How should “DX and private endpoints make this compliant with network separation” be corrected?
   - A) Attaching the DX connection ID is sufficient.
   - B) Identify the applicable policy, allowed connections, permissions and data, implementation evidence, and approval conditions.
   - C) Without internet access, no external management connection exists.

<details>
<summary>Show Answer</summary>

**Answer: B**

Private routing reduces exposure. It does not decide whether the customer's policy permits the management connection.

</details>

2. What does the `com.amazonaws.<region>.eks` interface endpoint provide?
   - A) A relay for every control-plane-to-kubelet TCP 10250 connection.
   - B) An endpoint policy that replaces Kubernetes API RBAC.
   - C) Private access to AWS EKS management APIs such as `DescribeCluster`.

<details>
<summary>Show Answer</summary>

**Answer: C**

The Kubernetes API private endpoint and the AWS EKS management API PrivateLink endpoint are different.

</details>

3. A firewall permits only responses to TCP 443 sessions initiated by hybrid nodes. Does that also permit the kubelet connection used by `kubectl logs` in a conventional routed deployment?
   - A) No. Review the separate session initiated by the API server toward node TCP 10250.
   - B) Yes. Every packet in the same cluster is part of an existing session's response.
   - C) Yes. DX automatically bypasses firewall rules.

<details>
<summary>Show Answer</summary>

**Answer: A**

Stateful return permission does not allow a new inbound connection for a different TCP session.

</details>

4. Which checks establish this article's private-only assumption?
   - A) Check only `endpointPrivateAccess=true`.
   - B) Confirm private access is enabled and public access disabled, then verify DNS, routing, and actual flows.
   - C) Narrow `publicAccessCidrs`; it restricts the private endpoint identically.

<details>
<summary>Show Answer</summary>

**Answer: B**

With public and private access both enabled, hybrid nodes can use public addresses. Public-access CIDRs do not control access to the private endpoint.

</details>

5. Which encryption statement is correct for a DX deployment?
   - A) DX encrypts every Pod flow by default.
   - B) A private IP allows TLS certificate validation to be skipped.
   - C) Preserve TLS and check IPsec/MACsec support and coverage when separate link encryption is required.

<details>
<summary>Show Answer</summary>

**Answer: C**

DX does not encrypt in transit by default. MACsec link protection also differs in scope from application end-to-end TLS.

</details>

6. A business application's Pods run on-premises. Which statement about the data boundary is correct?
   - A) All business data is automatically copied to AWS.
   - B) All data necessarily remains on-premises.
   - C) Review API objects, Secrets, `logs`, management streams, and application egress separately from the business datastore.

<details>
<summary>Show Answer</summary>

**Answer: C**

Node placement does not determine every storage and transfer location. Kubernetes management operations can handle sensitive data.

</details>

7. What process is needed when EKS ENI addresses are used in firewall allowlists?
   - A) Keep the initially observed `/32` addresses forever.
   - B) Verify cluster ownership and address scope, refresh and retest after ENI changes, and record shared-subnet risks.
   - C) Allow all AWS address space.

<details>
<summary>Show Answer</summary>

**Answer: B**

ENI IPs can change. Allowing a broad shared subnet can include other resources in the permitted source range.

</details>

8. What is missing from “we removed `exec`, so all administrator-mediated data access is blocked”?
   - A) Review workload creation/modification, privileged/hostPath access, other subresources, and host management permissions too.
   - B) Cluster administrators cannot cross namespace boundaries.
   - C) NetworkPolicy invalidates all administrative permissions.

<details>
<summary>Show Answer</summary>

**Answer: A**

Restricting one command does not remove alternative access paths. Review the principal's full permissions together with admission and host controls.

</details>

9. Which statement about security-review evidence is correct?
   - A) VPC Flow Logs can reconstruct every TLS payload and `exec` input/output.
   - B) CloudTrail makes Kubernetes audit logs unnecessary.
   - C) Distinguish network records, Kubernetes audit, and CloudTrail, and test allowed and denied behavior with synthetic data.

<details>
<summary>Show Answer</summary>

**Answer: C**

The records have different scopes. Kubernetes audit does not record every streamed payload and cannot replace denial tests or data classification.

</details>

10. A policy prohibits every new cloud-initiated connection. Does moving webhooks to cloud nodes or using Hybrid Nodes Gateway automatically satisfy it?
    - A) Either change is sufficient.
    - B) No. Reassess the design, including the separate kubelet connection and the gateway's actual bidirectional paths.
    - C) Describing the architecture as PrivateLink is sufficient.

<details>
<summary>Show Answer</summary>

**Answer: B**

Moving webhooks does not remove the kubelet requirement. Hybrid Nodes Gateway is not a one-way security gateway. If policy conflicts with supported connectivity requirements, reconsider the design or formal approval conditions.

</details>
