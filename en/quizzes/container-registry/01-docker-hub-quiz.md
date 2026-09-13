# Docker Hub Quiz
> **Last Updated**: September 11, 2026

1. Which boundary is used to attribute anonymous Docker Hub pulls from nodes behind NAT?
   - A) Each Kubernetes Pod
   - B) Source IPv4 address or IPv6 /64 subnet
   - C) Kubernetes namespace
   - D) Unlimited pulls

<details>
<summary>Show Answer</summary>

**Answer: B) Source IPv4 address or IPv6 /64 subnet**

**Explanation:**
Nodes sharing a NAT address may consume the same anonymous allowance. Obtain the actual limit and reset window from current policy and response headers; authenticated account attribution and abuse controls are separate.

</details>

2. Which Kubernetes resource is used to store Docker Hub credentials for pulling private images?
   - A) ConfigMap
   - B) Secret with type `kubernetes.io/dockerconfigjson`
   - C) ServiceAccount
   - D) PersistentVolumeClaim

<details>
<summary>Show Answer</summary>

**Answer: B) Secret with type `kubernetes.io/dockerconfigjson`**

**Explanation:**
Kubernetes uses Secrets of type `kubernetes.io/dockerconfigjson` to store registry credentials. This secret is then referenced in Pod specs via `imagePullSecrets` or attached to a ServiceAccount for automatic injection.

</details>

3. What is the recommended approach to mitigate Docker Hub rate limits in a Kubernetes cluster?
   - A) Use more IP addresses
   - B) Configure a pull-through cache or registry mirror
   - C) Disable image pulling
   - D) Only use local images

<details>
<summary>Show Answer</summary>

**Answer: B) Configure a pull-through cache or registry mirror**

**Explanation:**
A pull-through cache reduces repeated layer downloads. Cache misses, mutable-tag checks and refreshes still contact upstream, so caching does not eliminate rate limits.

</details>

4. How do you provide default pull credentials to new Pods using the namespace's default ServiceAccount?
   - A) Add the secret to the kube-system namespace
   - B) Patch the default ServiceAccount in the namespace with imagePullSecrets
   - C) Set a cluster-wide ConfigMap
   - D) Modify the kubelet configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Patch the default ServiceAccount in the namespace with imagePullSecrets**

**Explanation:**
Add `imagePullSecrets` to that ServiceAccount. Newly admitted Pods using it inherit the list if they do not have their own pull-secret list. Existing Pods, different ServiceAccounts and other namespaces are not retroactively updated.

</details>

5. What distinguishes Docker Official Images from other images on Docker Hub?
   - A) They belong to a curated program with reviewed upstream images and documentation
   - B) They are always free to use
   - C) They have no rate limits
   - D) They are automatically updated daily

<details>
<summary>Show Answer</summary>

**Answer: A) They belong to a curated program with reviewed upstream images and documentation**

**Explanation:**
Docker Official Images are curated with upstream/community maintainers and reviewed against program standards. The badge does not guarantee that a particular tag has no vulnerabilities; verify the selected digest and maintenance status.

</details>

6. What is the purpose of Docker Verified Publisher images?
   - A) They are free images from random contributors
   - B) They are images from commercial software vendors verified by Docker
   - C) They are deprecated legacy images
   - D) They are images that bypass security scanning

<details>
<summary>Show Answer</summary>

**Answer: B) They are images from commercial software vendors verified by Docker**

**Explanation:**
Docker Verified Publisher images come from commercial software vendors who have partnered with Docker and undergone a verification process. This provides assurance that the images are authentic and maintained by the actual software vendor, reducing supply chain security risks.

</details>

7. Which Docker Hub subscription tier provides unlimited private repositories?
   - A) Free tier
   - B) Only Pro
   - C) Only Team
   - D) Pro, Team and Business under their plan policies

<details>
<summary>Show Answer</summary>

**Answer: D) Pro, Team and Business under their plan policies**

**Explanation:**
The usage table lists unlimited private repositories for Pro, Team and Business, subject to plan and fair-use conditions. Personal includes one.

</details>

8. What supply chain security risk is associated with using public Docker Hub images?
   - A) Images may contain vulnerabilities or malicious code
   - B) Images are always outdated
   - C) Images cannot be scanned
   - D) Images are too large

<details>
<summary>Show Answer</summary>

**Answer: A) Images may contain vulnerabilities or malicious code**

**Explanation:**
Public images on Docker Hub may contain known vulnerabilities, outdated dependencies, or in rare cases, malicious code (typosquatting attacks, compromised maintainer accounts). Organizations should scan images before use, prefer Official Images or Verified Publishers, and consider maintaining their own curated base images.

</details>

9. What is the correct kubectl command to create a Docker Hub image pull secret?
   - A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`
   - B) `kubectl create configmap my-secret --docker-server=docker.io`
   - C) `kubectl apply secret docker my-secret`
   - D) `kubectl set image secret my-secret`

<details>
<summary>Show Answer</summary>

**Answer: A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`**

**Explanation:**
The command creates a Secret of type `kubernetes.io/dockerconfigjson`. The example uses Docker Hub's standard `https://index.docker.io/v1/` credential key. Replace USER/TOKEN with appropriate credentials without committing them, and create the Secret in the consuming Pod's namespace.

</details>

10. What is the appropriate guidance for Docker Hub Automated Builds as of September 2026?
    - A) Use it as the default for every new CI pipeline
    - B) It has no announced retirement
    - C) Migrate from the deprecated feature before April 1, 2027
    - D) It is available to all free accounts

<details>
<summary>Show Answer</summary>

**Answer: C) Migrate from the deprecated feature before April 1, 2027**

**Explanation:**
The official documentation marks Automated Builds deprecated and gives an April 1, 2027 retirement date. Legacy native integration uses GitHub/Bitbucket; GitLab CI can independently build and push images.

</details>
