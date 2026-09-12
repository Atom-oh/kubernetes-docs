# Cross-Org VPC Connectivity Quiz

Distinguish reported measurements from AWS platform requirements.

## 1. What is required for TGW sharing with an account outside the owner’s Organization?

- A. Merge both Organizations
- B. Allow external principals on the share and accept the RAM invitation in the receiving account
- C. Connect the management accounts with a VPN
- D. Obtain a support-ticket approval

<details>
<summary>Show answer</summary>

B. The share must permit the external account, and the recipient must accept the invitation before using the shared resources. CreateResourceShare defaults allowExternalPrincipals to true; the literal --allow-external-principals flag is therefore not always required. Check the effective configuration and IAM/sharing restrictions.

</details>

## 2. With AutoAcceptSharedAttachments disabled, what is needed for a valid cross-account VPC attachment to a shared TGW?

- A. No acceptance is needed
- B. The TGW owner must accept the pending shared attachment
- C. Such attachments cannot exist across Organizations
- D. It always activates after 24 hours

<details>
<summary>Show answer</summary>

B. Automatic shared-attachment acceptance is disabled by default. RAM share acceptance and VPC-attachment acceptance are separate steps. If automatic acceptance is enabled, the second workflow changes. The TGW owner controls TGW route tables; the receiving account still controls its own VPC routes and security settings.

</details>

## 3. What does the report’s TCP_RR comparison M3−M2 establish?

- A. Every TGW hop always adds the same one-way latency
- B. Those reported path medians differ by 0.619−0.048 = 0.571 ms
- C. A guaranteed AWS latency SLA
- D. The throughput of GPU training

<details>
<summary>Show answer</summary>

B. It is an observed difference between reported round-trip medians, not a pure component measurement or per-hop constant. The two-TGW path has a lower TCP_RR median than the single-TGW path in that campaign. Raw samples, uncertainty and workload measurements are needed for broader conclusions; the review did not reproduce the benchmark.

</details>

## 4. What should be checked in the target SG for the tested Lattice HTTP-service/VPC-association path?

- A. Open every inbound and outbound port
- B. Allow the correct regional/IP-family managed prefix lists on the actual target and health-check ports
- C. Replace security groups with NACLs
- D. Allow only TCP 443 regardless of the backend

<details>
<summary>Show answer</summary>

B. Lattice traffic can arrive from addresses in its managed prefix lists, so allowing only the client VPC CIDR is insufficient. The historical 169.254.171.0/24 example is not the full universal address definition. Use the documented lists and configured ports; endpoint/resource-gateway paths have their own controls.

</details>

## 5. Which of the compared patterns can expose services across overlapping VPC CIDRs without direct routing between the overlapping ranges?

- A. Direct VPC peering
- B. Unmodified direct TGW routing
- C. PrivateLink service access or VPC Lattice service access
- D. No architecture can ever handle overlap

<details>
<summary>Show answer</summary>

C. These provide service access rather than unrestricted bidirectional VPC routing. Direct VPC peering cannot connect overlapping CIDRs, and routed designs need an unambiguous address plan. NAT and address redesign are additional options, so PrivateLink/Lattice are not the only possible architectures.

</details>

## 6. Which routing statement is correct for direct TGW-to-TGW peering?

- A. Peering automatically propagates all routes through BGP
- B. Configure static peer routes and the needed VPC routes explicitly
- C. Only the VPC tables matter
- D. Acceptance automatically creates every required route

<details>
<summary>Show answer</summary>

B. The peering attachment uses static routes; automation can manage them. TGW routing first uses the most-specific prefix, and static routes beat propagated routes for the same prefix. Accept the pending peering request from the accepter Region using its attachment ID; NotFound alone does not prove that requester/accepter IDs must differ.

</details>

[Return to the guide](../../networking/05-cross-org-vpc-connectivity.md)
