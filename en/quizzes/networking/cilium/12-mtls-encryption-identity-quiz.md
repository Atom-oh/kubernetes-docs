# Part 12: mTLS, Transparent Encryption and Identity Quiz

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

[Return to the guide](../../../networking/cilium/12-mtls-encryption-identity.md)

1. What is the status of Cilium Mutual Authentication (SPIFFE/SPIRE, `authentication.mode: required`) in 1.20 and 1.21?
   - A) Removed in 1.20, absent in 1.21
   - B) Beta in 1.20, stable in 1.21
   - C) Deprecated in 1.20, removed in 1.21
   - D) Deprecated in 1.21, removed in 1.22
<details>
<summary>Show Answer</summary>

**Answer: C) Deprecated in 1.20, removed in 1.21**

The 1.20 upgrade notes call it deprecated (the docs page is still titled "Beta") and point to ztunnel. The 1.21 upgrade notes say it was removed after deprecation. The policy `authentication` field is kept for CRD compatibility but is unused in 1.21.

</details>

2. What is the numeric ID of the reserved identity `reserved:world`?
   - A) 1
   - B) 6
   - C) 8
   - D) 2
<details>
<summary>Show Answer</summary>

**Answer: D) 2**

1 is `host`, 2 is `world`, 6 is `remote-node` and 8 is `ingress`. IDs 9 and 10 split world into IPv4 and IPv6 variants.

</details>

3. How are workloads enrolled in Cilium's ztunnel mTLS?
   - A) Annotate each Pod with `istio.io/dataplane-mode=ambient`
   - B) Label the namespace `io.cilium/mtls-enabled=true`
   - C) Add `authentication.mode: required` to a CiliumNetworkPolicy
   - D) Label each Pod `io.cilium/mtls-enabled=true`
<details>
<summary>Show Answer</summary>

**Answer: B) Label the namespace `io.cilium/mtls-enabled=true`**

Enrollment is namespace-level only; Pod-level enrollment is not supported. The Istio ambient label belongs to Istio, and `authentication.mode` was the removed Mutual Authentication mechanism.

</details>

4. Which TCP port carries HBONE traffic between ztunnel proxies, and is the only port an L4 policy can target for enrolled workloads?
   - A) 15008
   - B) 4250
   - C) 15006
   - D) 15001
<details>
<summary>Show Answer</summary>

**Answer: A) 15008**

Traffic is encrypted before it leaves the Pod, so L4 policy cannot see inner ports; only the HBONE port 15008 can be targeted. 15001 and 15006 are the in-Pod outbound and plaintext inbound redirect ports, and 4250 was the removed Mutual Authentication handshake port.

</details>

5. What is the default value of `encryption.ztunnel.ca.type`?
   - A) `spire`
   - B) `istiod`
   - C) `internal`
   - D) `cert-manager`
<details>
<summary>Show Answer</summary>

**Answer: C) `internal`**

`internal` uses Cilium's built-in CA. `spire`, added in 1.20, uses an external SPIRE server and the operator registers entries for enrolled namespaces.

</details>

6. Which UDP port does the Cilium WireGuard tunnel endpoint use on each node?
   - A) 51820
   - B) 51871
   - C) 4789
   - D) 8472
<details>
<summary>Show Answer</summary>

**Answer: B) 51871**

Cilium uses 51871, not the WireGuard default 51820. Node security groups must allow it between nodes by referencing the node security group, never a public CIDR. 4789 and 8472 are VXLAN ports.

</details>

7. Which transparent-encryption strict mode option works only with WireGuard?
   - A) `encryption.strictMode.ingress.enabled`
   - B) `encryption.strictMode.egress.allowRemoteNodeIdentities`
   - C) `encryption.strictMode.egress.enabled`
   - D) `encryption.strictMode.egress.cidr`
<details>
<summary>Show Answer</summary>

**Answer: A) `encryption.strictMode.ingress.enabled`**

Ingress strict mode drops cluster-internal ingress that did not arrive through the WireGuard tunnel, so it is not supported with IPsec. The old flat flags (`encryption.strictMode.enabled` and friends) were removed in 1.20 in favour of the `egress.*` names.

</details>

8. In the IPsec key Secret, what forces per-tunnel derived keys?
   - A) Setting `encryption.ipsec.interface`
   - B) Using key ID 0
   - C) Enabling `encryption.nodeEncryption`
   - D) A `+` after the key ID, as in `3+ rfc4106(gcm(aes)) ...`
<details>
<summary>Show Answer</summary>

**Answer: D) A `+` after the key ID, as in `3+ rfc4106(gcm(aes)) ...`**

Global keys were deprecated in 1.16 (GHSA-pwqm-x5x6-5586). `encryption.ipsec.interface` was removed in 1.20, and key IDs run from 1 to 15.

</details>

9. In what order does the Double Write identity migration from kvstore to CRD proceed?
   - A) `doublewrite-readkvstore`, then `doublewrite-readcrd`, then `crd`
   - B) `crd`, then `doublewrite-readcrd`, then `kvstore`
   - C) `kvstore`, then `crd`, then `doublewrite-readcrd`
   - D) `doublewrite-readcrd`, then `doublewrite-readkvstore`, then `crd`
<details>
<summary>Show Answer</summary>

**Answer: A) `doublewrite-readkvstore`, then `doublewrite-readcrd`, then `crd`**

Both stores are written to throughout; reads move from kvstore to CRD, then the kvstore is dropped. Watch the `cilium_operator_doublewrite_*` metrics until the `*_only_identities` values reach zero before each step.

</details>

10. What happens in Cilium 1.20 when you apply a CiliumNetworkPolicy that has neither `spec` nor `specs`?
    - A) It is accepted and the agent logs a warning
    - B) It is rejected at admission by a CEL validation rule
    - C) It is accepted and treated as allow-all
    - D) It is accepted but never selects any endpoint
<details>
<summary>Show Answer</summary>

**Answer: B) It is rejected at admission by a CEL validation rule**

The CRD carries `has(self.spec) || has(self.specs)` with the message "spec or specs must be provided". Existing empty policies are unaffected until they are updated.

</details>
