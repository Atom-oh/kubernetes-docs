# ArgoCD ApplicationSets Quiz

This quiz tests your understanding of ArgoCD ApplicationSets for templated application generation.

1. What is the primary purpose of an ApplicationSet?
   - A) To group existing Applications
   - B) To automatically generate multiple Applications from templates
   - C) To create application backups
   - D) To manage application secrets

<details>
<summary>Show Answer</summary>

**Answer: B) To automatically generate multiple Applications from templates**

**Explanation:**
ApplicationSets use generators and templates to automatically create and manage multiple ArgoCD Applications. They're ideal for deploying applications across multiple clusters or environments.

</details>

2. Which generator would you use to create Applications for each cluster registered in ArgoCD?
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>Show Answer</summary>

**Answer: C) Cluster generator**

**Explanation:**
The Cluster generator automatically generates Applications for each cluster registered in ArgoCD. It can use label selectors to target specific clusters.

</details>

3. What does the Git directory generator do?
   - A) Creates Applications based on Git branches
   - B) Creates Applications for each directory in a specified path
   - C) Syncs Git credentials
   - D) Manages Git webhooks

<details>
<summary>Show Answer</summary>

**Answer: B) Creates Applications for each directory in a specified path**

**Explanation:**
The Git directory generator scans a specified directory in a Git repository and creates an Application for each directory matching its configured glob and exclusion rules. This is useful for monorepo setups.

</details>

4. How do you combine multiple generators in an ApplicationSet?
   - A) Using the Merge generator
   - B) Using the Matrix generator
   - C) Using the Combine generator
   - D) Both A and B

<details>
<summary>Show Answer</summary>

**Answer: D) Both A and B**

**Explanation:**
The Matrix generator creates combinations (Cartesian product) of parameters from exactly two child generators. The Merge generator combines parameters from multiple generators, merging matching entries. Both can be used to combine generators.

</details>

5. What is the purpose of the `goTemplate` field in ApplicationSet templates?
   - A) To enable Go programming
   - B) To use Go template syntax for more complex templating
   - C) To compile Go applications
   - D) To enable debugging

<details>
<summary>Show Answer</summary>

**Answer: B) To use Go template syntax for more complex templating**

**Explanation:**
Setting `goTemplate: true` enables Go template syntax, which provides more powerful templating capabilities like conditionals, loops, and functions compared to default simple substitution. Each string field is evaluated independently; control statements cannot span YAML fields, and boolean/object fields cannot be templated directly.

</details>

6. Which generator would you use to create Applications based on pull requests?
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>Show Answer</summary>

**Answer: B) Pull Request generator**

**Explanation:**
The Pull Request generator creates Applications for each open pull request in a repository, enabling preview environments for code review. It supports GitHub, GitLab, Bitbucket, and Gitea.

</details>

7. What happens by default when you delete an ApplicationSet?
   - A) Nothing, generated Applications remain
   - B) All generated Applications are deleted
   - C) Applications are orphaned
   - D) A backup is created

<details>
<summary>Show Answer</summary>

**Answer: B) All generated Applications are deleted**

**Explanation:**
By default, ApplicationSets have a cascading delete policy, meaning when you delete an ApplicationSet, all Applications it generated will also be deleted. `preserveResourcesOnDeletion` controls deployed-resource cleanup, not whether Application objects are garbage-collected.

</details>

8. How can you prevent an ApplicationSet from deleting generated Applications when the ApplicationSet is removed?
   - A) Delete with `kubectl delete applicationset NAME --cascade=orphan`
   - B) Only set `syncPolicy.preserveResourcesOnDeletion: true`
   - C) Set the deletion policy annotation
   - D) Scale the ApplicationSet controller to zero

<details>
<summary>Show Answer</summary>

**Answer: A) Delete with `kubectl delete applicationset NAME --cascade=orphan`**

**Explanation:**
`--cascade=orphan` leaves generated Application objects when removing their parent. `preserveResourcesOnDeletion: true` prevents adding the deployed-resource deletion finalizer; it does not preserve Application objects from garbage collection. An orphaned Application with an existing finalizer can still delete its resources when later removed.

</details>
