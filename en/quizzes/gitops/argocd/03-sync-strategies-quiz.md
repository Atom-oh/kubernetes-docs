# ArgoCD Sync Strategies Quiz

This quiz tests your understanding of ArgoCD synchronization strategies and options.

1. What is the difference between a "Sync" and a "Refresh" in ArgoCD?
   - A) They are the same operation
   - B) Refresh compares the current state to Git; Sync applies changes to make them match
   - C) Sync is manual, Refresh is automatic
   - D) Refresh deletes resources, Sync creates them

<details>
<summary>Show Answer</summary>

**Answer: B) Refresh compares the current state to Git; Sync applies changes to make them match**

**Explanation:**
A Refresh operation fetches the latest manifests from Git and compares them to the live state, updating the Application status. A Sync operation actually applies changes to the cluster to bring the live state in line with the desired state in Git.

</details>

2. What does enabling `automated` sync policy do?
   - A) Automatically deletes the application
   - B) Enables automatic synchronization when the desired state differs from live state
   - C) Enables automatic rollback
   - D) Automatically creates backups

<details>
<summary>Show Answer</summary>

**Answer: B) Enables automatic synchronization when the desired state differs from live state**

**Explanation:**
When `syncPolicy.automated` is enabled, Argo CD applies OutOfSync changes according to policy. Live-only drift needs selfHeal, deletion needs prune, and identical failed commits are not unconditionally retried forever.

</details>

3. What is the purpose of the `prune` option in automated sync?
   - A) To clean up old Git branches
   - B) To automatically delete resources that are no longer defined in Git
   - C) To remove failed deployments
   - D) To delete the application itself

<details>
<summary>Show Answer</summary>

**Answer: B) To automatically delete resources that are no longer defined in Git**

**Explanation:**
When `prune: true` is set in automated sync, Argo CD deletes tracked resources belonging to this Application that disappear from the desired source, not every unmanaged resource in the cluster.

</details>

4. What does `selfHeal: true` do in a sync policy?
   - A) Automatically fixes YAML syntax errors
   - B) Automatically syncs when live state deviates from desired state due to manual changes
   - C) Restarts unhealthy pods
   - D) Repairs corrupted Git repositories

<details>
<summary>Show Answer</summary>

**Answer: B) Automatically syncs when live state deviates from desired state due to manual changes**

**Explanation:**
With automated sync enabled, selfHeal reconciles compared live-only drift, subject to windows, authorization and ignore rules. It does not restore lost data or repair YAML errors.

</details>

5. Which sync option would you use to replace resources instead of applying patches?
   - A) Force=true
   - B) Replace=true
   - C) Recreate=true
   - D) Update=true

<details>
<summary>Show Answer</summary>

**Answer: B) Replace=true**

**Explanation:**
The `Replace=true` sync option tells ArgoCD to use `kubectl replace` instead of `kubectl apply`, which completely replaces the resource rather than patching it. replace/create does not automatically bypass immutable-field restrictions. Force=true with Replace=true can delete/recreate resources and is not a PVC migration shortcut.

</details>
