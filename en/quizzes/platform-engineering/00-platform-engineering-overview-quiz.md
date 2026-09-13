# Platform Engineering Overview Quiz

[Related guide](../../platform-engineering/00-platform-engineering-overview.md)

## 1. What is the core goal of platform engineering?

<details>
<summary>Answer and explanation</summary>

Understand developer needs and provide approved self-service APIs, CLIs, portals, templates and operational support as an internal product. It does not eliminate operations teams or assume every application responsibility.
</details>

## 2. How should Start, Advance, Excel and tool mappings be interpreted?

<details>
<summary>Answer and explanation</summary>

They organize improvement tasks in AWS platform-engineering guidance. Advance discusses IaC/self-service automation; this guide’s Kubernetes mappings are teaching examples, not official certification scores or a universal sequence.
</details>

## 3. How do platform engineering, DevOps and SRE relate?

<details>
<summary>Answer and explanation</summary>

They are complementary: platforms emphasize developer experience/reusable products, DevOps collaboration/delivery, and SRE reliability/operations engineering. Team structures and hierarchy are not universal.
</details>

## 4. What are the IDP layers and the scope of a Backstage portal?

<details>
<summary>Answer and explanation</summary>

Interface, orchestration, resources and infrastructure form a reference model. A Backstage-style portal is part of the interface, not a replacement for provisioning, policy, runtime, documentation and support.
</details>

## 5. Can deviating from a Golden Path bypass mandatory security policy?

<details>
<summary>Answer and explanation</summary>

No. It is a supported recommended path, but exceptions still follow organizational approval and mandatory security/data policies. It is not guaranteed optimal for every case.
</details>

## 6. Does one WebApplication always make kro create Deployments, RDS and IAM?

<details>
<summary>Answer and explanation</summary>

No. WebApplication is an example custom API requiring an RGD/CRD. kro manages the declared Kubernetes resources; authorized ACK service controllers call AWS APIs. Resource combinations, readiness and deletion policies depend on the definitions.
</details>

## 7. What are current DORA metrics and how should they be used?

<details>
<summary>Answer and explanation</summary>

Change lead time, deployment frequency, failed deployment recovery time, change fail rate and deployment rework rate. Improve service/team delivery and stability rather than substitute generic MTTR or individual rankings. Measurement can start before Excel.
</details>

## 8. Do guardrails automatically guarantee security and compliance?

<details>
<summary>Answer and explanation</summary>

No. Enforce and verify policies, bypass/exception handling, permissions and changes, with audit and recovery. Guardrails do not replace application data-handling responsibilities or assessment of legal requirements.
</details>
