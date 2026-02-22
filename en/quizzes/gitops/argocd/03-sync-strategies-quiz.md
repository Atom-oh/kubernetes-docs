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
When `syncPolicy.automated` is enabled, ArgoCD will automatically sync the application whenever it detects that the live state has drifted from the desired state defined in Git.

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
When `prune: true` is set in automated sync, ArgoCD will automatically delete Kubernetes resources that exist in the cluster but are no longer defined in the Git repository.

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
Self-heal ensures that if someone makes a manual change to a resource in the cluster (outside of Git), ArgoCD will automatically revert it to match the desired state in Git.

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
The `Replace=true` sync option tells ArgoCD to use `kubectl replace` instead of `kubectl apply`, which completely replaces the resource rather than patching it. This is useful when dealing with immutable fields.

</details>
