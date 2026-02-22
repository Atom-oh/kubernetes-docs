# Platform Engineering Overview Quiz

> This quiz tests your understanding of the [Platform Engineering Overview](../../platform-engineering/00-platform-engineering-overview.md) document.

---

1. What is the core goal of Platform Engineering?
   - A) Training all developers to manage infrastructure directly
   - B) Building an Internal Developer Platform (IDP) for developer self-service
   - C) Completely replacing the operations team's role with automation
   - D) Migrating all applications to serverless

<details>
<summary>Show Answer</summary>

**Answer: B) Building an Internal Developer Platform (IDP) for developer self-service**

**Explanation:**
Platform Engineering is the discipline of building an IDP that enables developers to deploy applications quickly and securely without dealing directly with infrastructure complexity. The goal is not to teach developers infrastructure management, but to provide abstracted self-service interfaces.

</details>

---

2. In the AWS CAF maturity model, which stage corresponds to "infrastructure automation through IaC" and "self-service product delivery"?
   - A) START
   - B) ADVANCE
   - C) EXCEL
   - D) Common across all stages

<details>
<summary>Show Answer</summary>

**Answer: B) ADVANCE**

**Explanation:**
In the AWS CAF maturity model, the ADVANCE stage focuses on expanding automation and building centralized observability. Infrastructure automation (IaC, self-service products) is an ADVANCE capability built on top of the START foundation. START covers foundation building, while EXCEL covers continuous optimization.

</details>

---

3. Which statement correctly describes the relationship between Platform Engineering, DevOps, and SRE?
   - A) The three are mutually exclusive approaches
   - B) Platform Engineering replaces DevOps and SRE
   - C) Platform Engineering packages DevOps principles and SRE practices as a product
   - D) SRE is a superset that encompasses Platform Engineering and DevOps

<details>
<summary>Show Answer</summary>

**Answer: C) Platform Engineering packages DevOps principles and SRE practices as a product**

**Explanation:**
The three approaches are complementary. DevOps provides culture and methodology, SRE provides operational engineering practices, and Platform Engineering packages these into a product called the Internal Developer Platform.

</details>

---

4. In the Kubernetes-based IDP reference architecture, which layer do ArgoCD, FluxCD, and KRO belong to?
   - A) Developer Interface Layer
   - B) Integration/Orchestration Layer
   - C) Resource Layer
   - D) Infrastructure Layer

<details>
<summary>Show Answer</summary>

**Answer: B) Integration/Orchestration Layer**

**Explanation:**
The Integration/Orchestration Layer handles declarative state management and deployment automation. ArgoCD and FluxCD provide GitOps-based deployment, and KRO provides resource graph orchestration. The Developer Interface Layer is for UIs/CLIs like Backstage, the Resource Layer is for ACK/Helm/Operators, and the Infrastructure Layer is for EKS/VPC/IAM.

</details>

---

5. Which statement about Golden Paths is NOT correct?
   - A) They are recommended deployment paths provided by the platform team
   - B) They are mandatory rules that developers must follow
   - C) They guide developers to get started quickly using validated methods
   - D) Developers can deviate when needed, but they're the optimal choice in most cases

<details>
<summary>Show Answer</summary>

**Answer: B) They are mandatory rules that developers must follow**

**Explanation:**
Golden Paths are "recommended," not "enforced." They provide deployment methods that the platform team has validated and optimized, but developers can choose different approaches when needed. The goal is to design Golden Paths so they are the optimal choice for most use cases.

</details>

---

6. In the self-service pattern combining KRO's ResourceGraphDefinition (RGD) and ACK, what combination of resources is automatically created when a developer submits a single manifest?
   - A) Deployment + ConfigMap + PVC
   - B) Deployment + Service + RDS Instance + IAM Role
   - C) StatefulSet + Service + DynamoDB Table
   - D) Pod + Ingress + S3 Bucket

<details>
<summary>Show Answer</summary>

**Answer: B) Deployment + Service + RDS Instance + IAM Role**

**Explanation:**
In the KRO RGD + ACK self-service pattern, a developer's single WebApplication manifest triggers KRO to automatically create Kubernetes native resources (Deployment + Service) and AWS resources via ACK (RDS Instance, IAM Role). This is the core value of an IDP: abstracting infrastructure complexity.

</details>

---

7. In the AWS CAF maturity model, which stage and capability area do DORA metrics belong to?
   - A) START - Cost Management
   - B) ADVANCE - Central Observability
   - C) EXCEL - Platform Metrics
   - D) Common across all stages

<details>
<summary>Show Answer</summary>

**Answer: C) EXCEL - Platform Metrics**

**Explanation:**
DORA metrics (Deployment Frequency, Lead Time, MTTR, Change Failure Rate) belong to the "Platform Metrics" capability in the EXCEL stage. This represents the highest maturity level, achieving continuous optimization through metrics aligned with organizational goals.

</details>

---

8. Among the core values of an IDP, which one embeds security and compliance by default so developers can work in a secure environment without explicit security configuration?
   - A) Self-Service
   - B) Guardrails
   - C) Standardization
   - D) Automation

<details>
<summary>Show Answer</summary>

**Answer: B) Guardrails**

**Explanation:**
Guardrails embed security and compliance into the platform by default. Even without developers explicitly configuring security, the platform automatically applies security policies (Pod Security Standards, network policies, image scanning, etc.). Self-Service relates to direct provisioning, Standardization to Golden Paths, and Automation to eliminating repetitive tasks.

</details>
