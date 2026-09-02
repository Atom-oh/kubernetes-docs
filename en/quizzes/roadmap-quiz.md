# Guidebook Roadmap Quiz

1. In the domain map, which layer do the Storage and Database domains belong to?
   - A) Foundations
   - B) Connectivity
   - C) State
   - D) Cross-cutting
<details>
<summary>Show Answer</summary>

**Answer: C) State**

**Explanation:**
In the domain-map table, Storage (EBS gp2 vs gp3, measured with fio) and Database (the operator landscape and a 100M-row ClickHouse benchmark) both sit in the "State" layer. Foundations holds Linux & Container; Connectivity holds Networking and Service Mesh; Cross-cutting holds Security & Policy, GitOps, Platform Engineering, Container Registry, Observability, and the Operations Guide.

</details>

2. Which ordering of layers matches the roadmap's learning-flow map?
   - A) Orchestration → Foundations → Connectivity → State → Data & AI → Cross-cutting
   - B) Foundations → Orchestration → Connectivity → State → Data & AI → Cross-cutting
   - C) Foundations → Connectivity → Orchestration → Data & AI → State → Cross-cutting
   - D) Cross-cutting → Foundations → Orchestration → Connectivity → State → Data & AI
<details>
<summary>Show Answer</summary>

**Answer: B) Foundations → Orchestration → Connectivity → State → Data & AI → Cross-cutting**

**Explanation:**
The learning-flow map shows the guidebook's fifteen domains "flowing from foundations (Linux/Container) through orchestration (Kubernetes/EKS), connectivity (Networking/Service Mesh), state (Storage/Database), data and AI (Data Pipeline/AI-ML), to cross-cutting concerns (Security/GitOps/Platform/Container Registry/Observability/Operations)". It is one continuous story that starts at the Linux kernel and covers the whole cloud-native stack.

</details>

3. Which of these domains is **not** part of the roadmap's measured-benchmark series?
   - A) Service Mesh (Istio sidecar vs ambient)
   - B) Storage (EBS gp2 vs gp3)
   - C) Database (ClickHouse on EKS)
   - D) GitOps (ArgoCD, Flux)
<details>
<summary>Show Answer</summary>

**Answer: D) GitOps (ArgoCD, Flux)**

**Explanation:**
The measured-benchmark series consists of "documents built on numbers measured on real AWS resources, not spec sheets": Istio sidecar vs ambient (P50/P99 latency per mTLS data plane and 503 rates during rollouts), the EBS gp2 vs gp3 benchmark (a 10x IOPS gap at identical capacity and the gp2 burst-credit cliff), the ClickHouse on EKS benchmark (100M-row ingest throughput, compression ratios, query latency), and the Kafka on EKS benchmark (RF3 ingest ceiling of ≈130–135 MiB/s, among others) — four documents. GitOps is a cross-cutting domain but has no measured page in the series.

</details>

4. What is the reading order of recommended path ③, "Data & AI platform"?
   - A) AI/ML → Data Pipeline → Database → Storage
   - B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)
   - C) Data Pipeline → Storage → AI/ML → Database
   - D) Database → Storage → AI/ML → Data Pipeline
<details>
<summary>Show Answer</summary>

**Answer: B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)**

**Explanation:**
Path ③ runs "Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)", and adds that if you need GPUs and scheduling control, you should include the Custom Scheduler parts under Kubernetes Core Concepts. It climbs from the State layer into the Data & AI layer.

</details>

5. In recommended path ①, "Infrastructure onboarding", how does the roadmap tell you to check your understanding?
   - A) With each document's quiz, working through the labs in parallel
   - B) By reading the entire measured-benchmark series first
   - C) By exporting a diagram Share Card
   - D) By handing the llms.txt URL to an LLM and asking for a summary
<details>
<summary>Show Answer</summary>

**Answer: A) With each document's quiz, working through the labs in parallel**

**Explanation:**
Path ① reads "Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts (pods/services/storage/configuration) → EKS Cluster Creation → Network Fundamentals" and says to "check yourself with each document's quiz, and work through the labs in parallel" — the labs start at `labs/README.md`. The measured-benchmark series is introduced as the evidence for path ②, Platform / SRE.

</details>

6. You want to post a diagram to LinkedIn where the flow actually moves in the feed. Which procedure matches the roadmap's 30-second recipe?
   - A) Capture the viewer with a screen recorder and convert it to a GIF
   - B) Make sure the toolbar Live/Still toggle reads Live, then Export (`E`) → WebM to download the 6-second trace animation
   - C) Export → SVG and upload it to LinkedIn as a video
   - D) Resolve a path with Route Probe (`R`) and use Copy diagram to put it on the clipboard
<details>
<summary>Show Answer</summary>

**Answer: B) Make sure the toolbar Live/Still toggle reads Live, then Export (`E`) → WebM to download the 6-second trace animation**

**Explanation:**
Every interactive diagram opens at `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`, and the **Export** button in the viewer toolbar (shortcut `E`) produces share-ready files on the spot — "No screenshot tooling — the diagram page is all you need." The recipe is: (1) open the diagram; (2) check that the **Live/Still** toggle reads Live, since the motion flowing along the arrows is what the recording captures; (3) **Export → WebM** for a moving post, or **Export → Share Card** for a static 1200×630 preview; (4) post it together with the source document's URL. WebM shows "Recording 6 seconds of motion…" before the file downloads, and it needs a trace-animated diagram plus MediaRecorder support in the browser. SVG is the dual-theme vector meant for slides.

</details>

7. Which statement about the Export menu's **Route Share Card** is correct?
   - A) It is always shown on every diagram and infers routes automatically between shapes that sit close together
   - B) It appears only after a Route Probe (`R`) has resolved a path between two nodes, and it follows only authored, directed relationships
   - C) It shows a node's upstream/downstream reachability as a blast-radius analysis
   - D) It supports clipboard copy only, not download
<details>
<summary>Show Answer</summary>

**Answer: B) It appears only after a Route Probe (`R`) has resolved a path between two nodes, and it follows only authored, directed relationships**

**Explanation:**
In the Export menu table, the Route Share Card is a 1200×630 PNG (download only) that "Appears only after a Route Probe (`R`) has resolved a path between two nodes". The truth-boundary section adds that "A Route Share Card follows only authored, directed relationships. It never infers a route from geometry, and it refuses to export a stale or unreachable route." Upstream/downstream reachability belongs to the separate Reach Share Card — and even that must not be presented as impact analysis, blast radius, breakage, or runtime causality.

</details>

8. What position does the roadmap's "truth boundary" take on exported files such as the Share Card?
   - A) Exports are communication assets — not evidence that an architecture was validated — and the Share Card never claims validation
   - B) The Share Card carries an automatic "validated" badge and can serve as validation evidence
   - C) Exports are the official deliverable and replace the published HTML
   - D) The Reach Share Card measures runtime failure propagation and can go straight into an incident report
<details>
<summary>Show Answer</summary>

**Answer: A) Exports are communication assets — not evidence that an architecture was validated — and the Share Card never claims validation**

**Explanation:**
The first bullet of the section states: "Exports are communication assets. They are not evidence that an architecture was validated, and they do not replace the published HTML or the author's own validation. The Share Card never claims validation." Likewise, a Reach Share Card shows only *authored reachability*, so it must not be presented as impact analysis, blast radius, breakage, or runtime causality.

</details>
