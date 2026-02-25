# Docker Hub Quiz
> **Last Updated**: February 25, 2025

1. What is the anonymous pull rate limit for Docker Hub?
   - A) 50 pulls per 6 hours per IP address
   - B) 100 pulls per 6 hours per IP address
   - C) 200 pulls per 6 hours per IP address
   - D) Unlimited pulls

<details>
<summary>Show Answer</summary>

**Answer: B) 100 pulls per 6 hours per IP address**

**Explanation:**
Docker Hub enforces rate limits for anonymous users at 100 pulls per 6 hours based on IP address. Authenticated free users get 200 pulls per 6 hours, while paid subscriptions (Pro, Team, Business) have higher or unlimited limits.

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
A pull-through cache (like Harbor's proxy cache or a registry mirror) caches images locally after the first pull. Subsequent pulls from cluster nodes hit the local cache instead of Docker Hub, dramatically reducing the number of requests to Docker Hub and avoiding rate limit issues.

</details>

4. How do you configure imagePullSecrets to be automatically applied to all Pods in a namespace?
   - A) Add the secret to the kube-system namespace
   - B) Patch the default ServiceAccount in the namespace with imagePullSecrets
   - C) Set a cluster-wide ConfigMap
   - D) Modify the kubelet configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Patch the default ServiceAccount in the namespace with imagePullSecrets**

**Explanation:**
By adding `imagePullSecrets` to the default ServiceAccount in a namespace, all Pods that don't explicitly specify a ServiceAccount will automatically inherit those credentials. This avoids having to specify imagePullSecrets in every Pod spec.

</details>

5. What distinguishes Docker Official Images from other images on Docker Hub?
   - A) They are maintained by Docker and follow best practices for security and documentation
   - B) They are always free to use
   - C) They have no rate limits
   - D) They are automatically updated daily

<details>
<summary>Show Answer</summary>

**Answer: A) They are maintained by Docker and follow best practices for security and documentation**

**Explanation:**
Docker Official Images are curated by Docker and maintained with specific security and documentation standards. They undergo regular security scans, have clear documentation, and follow Dockerfile best practices. However, they still follow the same rate limit and pricing rules as other images.

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
   - B) Pro tier
   - C) Team tier
   - D) Both Team and Business tiers

<details>
<summary>Show Answer</summary>

**Answer: D) Both Team and Business tiers**

**Explanation:**
Docker Hub Team and Business subscription tiers provide unlimited private repositories. The Free tier offers limited private repositories, and the Pro tier offers unlimited private repositories for individual users. Team and Business are designed for organizations requiring collaboration features.

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
   - A) `kubectl create secret docker-registry my-secret --docker-server=docker.io --docker-username=USER --docker-password=PASS`
   - B) `kubectl create configmap my-secret --docker-server=docker.io`
   - C) `kubectl apply secret docker my-secret`
   - D) `kubectl set image secret my-secret`

<details>
<summary>Show Answer</summary>

**Answer: A) `kubectl create secret docker-registry my-secret --docker-server=docker.io --docker-username=USER --docker-password=PASS`**

**Explanation:**
The `kubectl create secret docker-registry` command creates a Secret of type `kubernetes.io/dockerconfigjson` with the provided registry credentials. The `--docker-server` flag specifies the registry URL (docker.io for Docker Hub), and credentials are provided via `--docker-username` and `--docker-password` flags.

</details>

10. When configuring automated builds on Docker Hub, which trigger source is NOT supported?
    - A) GitHub repository webhooks
    - B) Bitbucket repository webhooks
    - C) GitLab repository webhooks
    - D) Manual API triggers

<details>
<summary>Show Answer</summary>

**Answer: C) GitLab repository webhooks**

**Explanation:**
Docker Hub's automated builds feature natively supports GitHub and Bitbucket as source repositories for webhook-triggered builds. GitLab is not directly supported for automated builds on Docker Hub. For GitLab repositories, you would typically use GitLab CI/CD to build and push images to Docker Hub or another registry.

</details>
