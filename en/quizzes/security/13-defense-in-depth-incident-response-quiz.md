# Defense in Depth and Incident Response Quiz

> **Last Updated**: October 15, 2026

[Read the chapter and primary sources](../../security/13-defense-in-depth-incident-response.md)

### 1. Which path did CVE-2025-1974 require reviewing beyond public WAF coverage?

- A) The admission webhook reachable from the Pod network
- B) Only the CloudFront viewer path
- C) Only database storage encryption
- D) Only DNS cache size

<details>
<summary>Show Answer</summary>

**Answer: A) The admission webhook reachable from the Pod network**

**Explanation:** Review webhook reachability and controller Secret privileges. Historical fixed versions do not resolve the later retirement of ingress-nginx.

</details>

### 2. What does the ingress-nginx retirement statement imply for a new 2026 design?

- A) A historical CVE fix is sufficient indefinitely
- B) Plan migration to a maintained implementation
- C) WAF guarantees future controller patches
- D) Disable every Kubernetes webhook

<details>
<summary>Show Answer</summary>

**Answer: B) Plan migration to a maintained implementation**

**Explanation:** After retirement, ingress-nginx does not receive further security releases. Check maintenance and migration, not just a past patch.

</details>

### 3. What is the affectedness boundary of PAN-OS CVE-2026-0322?

- A) Every Palo Alto product without exception
- B) Only unauthenticated Internet users
- C) Authenticated management-interface RCE on the listed product families
- D) A WAF body-size problem

<details>
<summary>Show Answer</summary>

**Answer: C) Authenticated management-interface RCE on the listed product families**

**Explanation:** The advisory covers PA-Series, VM-Series and Panorama and excludes Cloud NGFW/Prisma Access for this issue. Credentials and management reachability both matter.

</details>

### 4. How should Fortinet's January 28 correction be represented?

- A) All SAML IdPs are affected
- B) No Fortinet product is affected
- C) Every SSO issue has the same scope
- D) Third-party SAML IdPs/FortiAuthenticator are excluded from the specified issue

<details>
<summary>Show Answer</summary>

**Answer: D) Third-party SAML IdPs/FortiAuthenticator are excluded from the specified issue**

**Explanation:** Use the revised scope rather than the initial broader SAML statement. FortiCloud SSO affectedness must still be checked.

</details>

### 5. Which traffic is automatically covered merely by routing selected flows through central TGW inspection?

- A) All same-node Pod traffic
- B) Every PrivateLink connection
- C) All alternate peering routes
- D) Only the flows actually routed through that inspection path

<details>
<summary>Show Answer</summary>

**Answer: D) Only the flows actually routed through that inspection path**

**Explanation:** Inventory local, endpoint, peering and IPv6 paths separately; complementary CNI, IAM, SG and application controls remain necessary.

</details>

### 6. What separates patch completion from compromise removal?

- A) Only the reboot timestamp
- B) Evidence about unauthorized accounts/settings, persistent access and exposed secrets
- C) A healthy target alone
- D) A newer version string alone

<details>
<summary>Show Answer</summary>

**Answer: B) Evidence about unauthorized accounts/settings, persistent access and exposed secrets**

**Explanation:** Persistent access can remain after a patch. Investigate and recover configuration, accounts and related credentials according to vendor guidance.

</details>

### 7. What does a zero WAF-block count prove by itself?

- A) Every request was safe
- B) All routes were inspected
- C) Neither complete safety nor effective path coverage
- D) Administrator credentials were not stolen

<details>
<summary>Show Answer</summary>

**Answer: C) Neither complete safety nor effective path coverage**

**Explanation:** Correlate associations, actions, benign canaries, origin restrictions and application records. Zero blocks may also reflect missing coverage.

</details>

### 8. Which proposed recovery acceptance evidence is strongest?

- A) Version only
- B) A screenshot of the appliance
- C) A single successful login
- D) Clean configuration/credentials plus business, deny-path and logging retests

<details>
<summary>Show Answer</summary>

**Answer: D) Clean configuration/credentials plus business, deny-path and logging retests**

**Explanation:** Combine eradication evidence with legitimate functionality, restricted management, inspection and restored observability.

</details>
