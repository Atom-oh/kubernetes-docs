# IAM Authentication Flow Quiz

This quiz tests your understanding of the four-stage Lattice IAM Auth flow, SigV4 signing pitfalls, and 403 diagnosis.

## Multiple Choice Questions

1. Which service name is used when signing VPC Lattice data plane requests with SigV4?
   - A) `vpc-lattice`
   - B) `vpc-lattice-svcs`
   - C) `lattice`
   - D) `execute-api`

<details>

<summary>Show Answer</summary>

**Answer: B) `vpc-lattice-svcs`**

**Explanation:**
`vpc-lattice-svcs` is the signing service name for data plane requests. It is easy to confuse with `vpc-lattice`, which is the service name for the Lattice control plane API (creating services, listeners, and so on). The service name is an input to signing key derivation (secret key → date → region → service name → terminating string, four chained HMAC-SHA256 operations), so getting it wrong means the signature will not verify. It is consistent with the service DNS name itself, which takes the form `...vpc-lattice-svcs.<region>.on.aws`.
</details>

2. What is the most common cause of a 403 under Lattice IAM Auth?
   - A) The principal is missing from the Lattice service's auth policy
   - B) The calling IAM Role's identity-based policy lacks `vpc-lattice-svcs:Invoke`
   - C) The node Security Group does not allow the Lattice prefix list
   - D) The Target Group health check is failing

<details>

<summary>Show Answer</summary>

**Answer: B) The calling IAM Role's identity-based policy lacks `vpc-lattice-svcs:Invoke`**

**Explanation:**
It is natural to think "the service's auth policy allows this Role, so we're done," but the calling Role itself also needs Invoke permission — a resource policy alone does not get you through. The actual error message ends with `because no identity-based policy allows the vpc-lattice-svcs:Invoke action`, telling you the cause, so read that clause first when you hit a 403. Note that C would manifest as a connection failure or timeout, not a 403.
</details>

3. If 403s begin right after introducing a custom domain, what should you check first?
   - A) The Target Group's protocol setting
   - B) The `Host` header — in SigV4 the Host header is always signed, so the Host used when signing must match the actual request's Host header
   - C) Whether Lattice quotas were exceeded
   - D) The VPC's DNS resolution settings

<details>

<summary>Show Answer</summary>

**Answer: B) The `Host` header — in SigV4 the Host header is always signed, so the Host used when signing must match the actual request's Host header**

**Explanation:**
SigV4 always includes the `Host` header in the signature. When you attach a custom domain, clients send requests to that domain and must sign with that value — if the signing logic still uses the Lattice-generated domain, the signature does not match. This problem surfaces at the moment you attach the custom domain rather than at the start of migration, which is why it is easy to miss. Introducing a custom domain requires settling SNI control, the signed Host value, and certificate management together.
</details>

4. If "only Pods on one particular node get intermittent 403s," what is the most likely cause?
   - A) A Security Group misconfiguration on that node
   - B) Clock synchronization on that node — `x-amz-date` is signed and SigV4's tolerance is about 5 minutes
   - C) The Gateway API Controller is not running on that node
   - D) That node's kubelet version is too old

<details>

<summary>Show Answer</summary>

**Answer: B) Clock synchronization on that node — `x-amz-date` is signed and SigV4's tolerance is about 5 minutes**

**Explanation:**
Because `x-amz-date` is signed, the verifying side rejects requests whose timestamp differs too much from current time — which makes node clock synchronization a precondition for authentication. On EC2/EKS nodes using the Amazon Time Sync Service this is rarely an issue, but it occurs on on-premises or hybrid nodes with misconfigured NTP, or nodes resuming after a long suspend. The failure being intermittent and node-scoped is the diagnostic clue. Note that 5 minutes is standard SigV4 behavior, not a Lattice-specific value.
</details>

5. Why does the rule "sign at the last hop" matter when signing via an egress proxy?
   - A) Multiple proxies increase latency
   - B) The signature is bound to request content (path, query, Host, payload hash), so any proxy that modifies those after signing breaks verification
   - C) A proxy cannot cache credentials
   - D) An IAM Role can only be attached to one proxy

<details>

<summary>Show Answer</summary>

**Answer: B) The signature is bound to request content (path, query, Host, payload hash), so any proxy that modifies those after signing breaks verification**

**Explanation:**
The canonical request includes the method, normalized path, sorted query string, signed headers, and payload hash. A proxy that rewrites paths, changes the Host, adds or reorders query parameters, or compresses/decompresses the payload after signing will cause a mismatch. The aws-samples reference implementation runs a `sigv4proxy` sidecar on 8080 with an init container using iptables to redirect only `169.254.171.0/24`-bound traffic, so the signed request goes straight out to Lattice with nothing in between.
</details>

6. Why might an auth policy not take effect for traffic inside the cluster?
   - A) Auth policies do not support IPv6 traffic
   - B) If the client calls the Kubernetes Service DNS directly, it bypasses Lattice and the auth policy is never evaluated
   - C) Auth policies apply only to cross-account calls
   - D) The Gateway API Controller has not yet reconciled the policy

<details>

<summary>Show Answer</summary>

**Answer: B) If the client calls the Kubernetes Service DNS directly, it bypasses Lattice and the auth policy is never evaluated**

**Explanation:**
The AWS Gateway API Controller documentation states this explicitly: `IAMAuthPolicy` performs authorization only for traffic traveling through Gateways, HTTPRoutes, and GRPCRoutes. Sending to `http://svc.ns.svc.cluster.local` bypasses Lattice, so no policy is evaluated. During migration, when both paths coexist, there are simultaneously paths where authorization applies and paths where it does not — compensating controls such as NetworkPolicy are needed. Another common cause is authType being `NONE` instead of `AWS_IAM`.
</details>

7. How do the "scope" and "directionality" of authentication change from AS-IS (App Mesh + SPIRE mTLS) to TO-BE (Lattice IAM Auth)?
   - A) Connection-scoped bidirectional → request-scoped bidirectional
   - B) Connection-scoped bidirectional mutual authentication → request-scoped unidirectional (client proof) plus a TLS server certificate
   - C) Request-scoped unidirectional → connection-scoped bidirectional
   - D) Neither scope nor directionality changes

<details>

<summary>Show Answer</summary>

**Answer: B) Connection-scoped bidirectional mutual authentication → request-scoped unidirectional (client proof) plus a TLS server certificate**

**Explanation:**
mTLS verifies each side's SVID once at connection setup — a bidirectional model. Lattice IAM Auth verifies the client's SigV4 signature on every request, so client proof actually becomes finer-grained (blocking the hijacked-connection scenario and enabling path/method/header conditions). But server-side identity proof drops to the level of a TLS server certificate, and there is no longer a step that confirms "is this really that team's service" within a workload identity system.
</details>
