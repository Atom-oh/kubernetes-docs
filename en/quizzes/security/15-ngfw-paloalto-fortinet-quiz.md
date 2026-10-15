# Palo Alto and Fortinet NGFW Quiz

> **Last Updated**: October 15, 2026

[Read the chapter and primary sources](../../security/15-ngfw-paloalto-fortinet.md)

### 1. Does generic GENEVE support establish AWS GWLB compatibility?

- A) Yes, UDP 6081 is sufficient
- B) No; verify supported vendor integration and required AWS metadata
- C) Yes, with any management IP as peer
- D) Only the product logo matters

<details>
<summary>Show Answer</summary>

**Answer: B) No; verify supported vendor integration and required AWS metadata**

**Explanation:** Match release, interfaces, policy and metadata processing to the official deployment mode.

</details>

### 2. What does a successful appliance health check prove?

- A) All IPS signatures are active
- B) TLS decryption works for all clients
- C) The configured health endpoint responded, not complete inspection
- D) N-1 business capacity is sufficient

<details>
<summary>Show Answer</summary>

**Answer: C) The configured health endpoint responded, not complete inspection**

**Explanation:** Use inspection canaries, policy/license checks and application measurements alongside health.

</details>

### 3. How should vendor health-check examples be used?

- A) HTTP 80 is universal
- B) Any response port is interchangeable
- C) GENEVE data and health must use the same protocol
- D) Match the actual template, target group and appliance response

<details>
<summary>Show Answer</summary>

**Answer: D) Match the actual template, target group and appliance response**

**Explanation:** The manual guide contains conflicting HTTP prohibition/profile wording. Verify TCP/HTTPS support and actual responses in the selected version/template instead of automating the ambiguity.

</details>

### 4. What is necessary for encrypted payload inspection?

- A) Supported decryption/termination and a tested trust/compatibility policy
- B) GWLB deployment alone
- C) GENEVE VNI alone
- D) A healthy target alone

<details>
<summary>Show Answer</summary>

**Answer: A) Supported decryption/termination and a tested trust/compatibility policy**

**Explanation:** GENEVE is not encryption or TLS termination. Validate mTLS, pinning, CA trust, protocol support and exemptions.

</details>

### 5. Does an ALB HTTPS target group validate the backend certificate?

- A) Always
- B) No; AWS documents that ALB does not validate target certificates
- C) Only when GWLB is enabled
- D) Only when the WAF action is Block

<details>
<summary>Show Answer</summary>

**Answer: B) No; AWS documents that ALB does not validate target certificates**

**Explanation:** Transport encryption and required backend identity validation are separate design properties.

</details>

### 6. Which address can an appliance observe after node SNAT?

- A) An immutable workload identity
- B) Always the original Pod address
- C) The node address, requiring CNI/IPAM correlation for Pod attribution
- D) Always the user's browser address

<details>
<summary>Show Answer</summary>

**Answer: C) The node address, requiring CNI/IPAM correlation for Pod attribution**

**Explanation:** Record translation points and timestamps. Even preserved Pod addresses are not permanent identities.

</details>

### 7. Does adding independent GWLB targets replicate firewall session state?

- A) Always
- B) Only because GENEVE uses UDP
- C) Only because targets share an AZ
- D) No; state sharing requires a supported vendor design and testing

<details>
<summary>Show Answer</summary>

**Answer: D) No; state sharing requires a supported vendor design and testing**

**Explanation:** Flow reassignment and state replication differ. Test old/new sessions during failure, scaling and upgrades.

</details>

### 8. Which benchmark fairly compares appliance designs?

- A) Measured business traffic with actual security/decryption profiles, N-1 capacity and latency/errors
- B) Only maximum datasheet throughput
- C) Only EC2 instance price
- D) Only successful health checks

<details>
<summary>Show Answer</summary>

**Answer: A) Measured business traffic with actual security/decryption profiles, N-1 capacity and latency/errors**

**Explanation:** Control traffic mix, licensing, features, AZ paths and session conditions. No performance result was measured in this documentation update.

</details>
