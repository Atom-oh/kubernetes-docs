# Part 13: Versions, Install/Upgrade and Cluster Mesh Quiz

> **Cilium 1.20.2 · 2026-10-15**

1. **Which upgrade path does upstream test, for both upgrade and rollback?**
   - A) Consecutive minors only (for example 1.19 to 1.20 and back), after moving to the latest patch of the current minor
   - B) Any N to N+2 minor, as long as the latest patch is installed
   - C) Any minor to the latest minor if the pre-flight chart passes
   - D) Agent-only upgrades, with the operator following a minor later

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Consecutive minors only (for example 1.19 to 1.20 and back), after moving to the latest patch of the current minor**

   Skipping minors is untested, and all components must run the same version. Updating to the latest patch first ensures a rollback target that has all fixes.

   </details>

2. **Why must you not run `helm upgrade --reuse-values` when moving to a new minor version?**
   - A) It deletes the Cilium CRDs
   - B) It resets `upgradeCompatibility` to the new version
   - C) It forces the OCI chart to be replaced by the classic repository chart
   - D) It reuses the old release's values and ignores new chart defaults, which can render broken manifests

   <details>
   <summary>Show Answer</summary>

   **Answer: D) It reuses the old release's values and ignores new chart defaults, which can render broken manifests**

   Save the values with `helm get values`, review renamed or removed keys, and pass them with `-f`. `--reuse-values` is acceptable only when the chart version is unchanged, such as applying the Cluster Mesh values at the same version.

   </details>

3. **What is the default `maxConnectedClusters`, and what does setting it to 511 cost?**
   - A) 255; KVStoreMesh must be disabled
   - B) 255; the maximum number of cluster-local identities drops from 65535 to 32767
   - C) 127; the cluster name length limit is halved
   - D) 511; the identity range is unchanged but only overlay mode works

   <details>
   <summary>Show Answer</summary>

   **Answer: B) 255; the maximum number of cluster-local identities drops from 65535 to 32767**

   The cluster ID takes bits from the numeric identity. The value must be identical in all clusters and set only at install time, because changing it on a live cluster can disrupt connections and mis-enforce policy.

   </details>

4. **What is the default for `clustermesh.apiserver.tls.authMode` in 1.20 versus the 1.21 pre-release?**
   - A) `legacy` in 1.20 and `migration` in 1.21
   - B) `cluster` in 1.20 and `cluster-strict` in 1.21
   - C) `migration` in 1.20 and `cluster` in 1.21 (with a new `cluster-strict` option)
   - D) `migration` in both

   <details>
   <summary>Show Answer</summary>

   **Answer: C) `migration` in 1.20 and `cluster` in 1.21 (with a new `cluster-strict` option)**

   In `cluster` mode each cluster authenticates as `remote-<cluster-name>` and a shared CA is required. With user-provided certificates and `tls.auto.enabled=false`, re-issue the remote certificate with the new CN or set `authMode` back to `migration`.

   </details>

5. **In Cilium 1.19 and later, which endpoints does a policy selector without a cluster label match in a Cluster Mesh?**
   - A) Endpoints of all connected clusters
   - B) Nothing, the policy is rejected
   - C) Only endpoints in global namespaces of remote clusters
   - D) Endpoints of the local cluster only

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Endpoints of the local cluster only**

   `policy-default-local-cluster` (Helm `clustermesh.policyDefaultLocalCluster`) defaults to true in 1.19. Select a remote cluster with the label `io.cilium.k8s.policy.cluster`, or use the `Exists` expression for any cluster. Up to 1.18 the default was all clusters.

   </details>

6. **Which clustermesh-apiserver container makes agents read remote cluster state from a local cache?**
   - A) `kvstoremesh`, which pulls remote state into the local etcd
   - B) `apiserver`, which mirrors remote clusters
   - C) `etcd`, which pulls from remote etcd instances directly
   - D) The cilium-agent, which keeps one connection per remote etcd

   <details>
   <summary>Show Answer</summary>

   **Answer: A) `kvstoremesh`, which pulls remote state into the local etcd**

   The `apiserver` container only syncs the local cluster's state into the local etcd. KVStoreMesh has been on by default since 1.16 and is unconditionally enabled in the 1.21 pre-release.

   </details>

7. **Cilium 1.20 requires which Gateway API CRD version, and what is the TLSRoute trap?**
   - A) v1.6.1; the Helm chart installs the CRDs and replaces TLSRoute automatically
   - B) v1.4; TLSRoute is not supported at all
   - C) v1.6.1; installing the standard-channel TLSRoute v1.6 makes existing `v1alpha2` TLSRoute objects unreadable, so use the experimental v1.6.1 TLSRoute if you already use them
   - D) v1.3.0; TLSRoute requires the `bpf.tproxy` flag

   <details>
   <summary>Show Answer</summary>

   **Answer: C) v1.6.1; installing the standard-channel TLSRoute v1.6 makes existing `v1alpha2` TLSRoute objects unreadable, so use the experimental v1.6.1 TLSRoute if you already use them**

   The chart does not install Gateway API CRDs. Back up TLSRoute objects before changing channels and apply CRDs with `kubectl apply --server-side`.

   </details>

8. **Can Cilium be used as the CNI on EKS Auto Mode?**
   - A) Yes, with `cni.chainingMode=aws-cni`
   - B) No, AWS states Auto Mode does not support alternate CNI or network policy plugins
   - C) Yes, but only in overlay mode
   - D) Yes, if `aws-node` is patched to a non-matching node selector

   <details>
   <summary>Show Answer</summary>

   **Answer: B) No, AWS states Auto Mode does not support alternate CNI or network policy plugins**

   Use managed or self-managed node groups. The `aws-node` patch and ENI mode apply to standard node groups, not Auto Mode.

   </details>

9. **What does `cilium_drift_checker_config_delta > 0` mean?**
   - A) The agent cannot reach the Kubernetes API server
   - B) A CiliumNodeConfig failed validation
   - C) The `cilium-config` ConfigMap contains keys the running agent has not applied, so an agent restart is needed
   - D) The operator and agent run different image versions

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The `cilium-config` ConfigMap contains keys the running agent has not applied, so an agent restart is needed**

   The drift checker compares the watched ConfigMap with the settings the agent started with. `cilium config set --restart=false` is one way to create a pending change that the metric then reports.

   </details>

10. **What is the order of `identity-allocation-mode` values in the Double Write migration from KVStore to CRD?**
    - A) `crd`, then `doublewrite-readcrd`, then `kvstore`
    - B) `doublewrite-readcrd`, then `doublewrite-readkvstore`, then `crd`
    - C) `kvstore`, then `crd`, with `doublewrite-readkvstore` only as a rollback state
    - D) `kvstore`, then `doublewrite-readkvstore`, then `doublewrite-readcrd`, then `crd`

    <details>
    <summary>Show Answer</summary>

    **Answer: D) `kvstore`, then `doublewrite-readkvstore`, then `doublewrite-readcrd`, then `crd`**

    Redeploy the operator first and then the agents for the two Double Write steps; for the final `crd` step redeploy the agents first and then the operator. The feature is beta, and the one-shot `migrate-identity` tool is deprecated in the 1.21 pre-release.

    </details>
