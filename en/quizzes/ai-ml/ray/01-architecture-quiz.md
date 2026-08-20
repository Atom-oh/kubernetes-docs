# Ray Architecture Quiz

This quiz tests your understanding of Ray's core primitives (tasks, actors, the object store), Ray cluster architecture (head node, worker nodes), and how Ray's higher-level libraries build on that same foundation.

## Multiple Choice Questions

1. What is Ray, fundamentally?
   - A) A domain-specific framework built only for distributed model training
   - B) An open-source distributed computing framework for scaling Python workloads, built around a small set of general-purpose primitives
   - C) A Kubernetes-native scheduler that replaces the default kube-scheduler
   - D) A managed model-serving product with no programming API

<details>

<summary>Show Answer</summary>

**Answer: B) An open-source distributed computing framework for scaling Python workloads, built around a small set of general-purpose primitives**

**Explanation:**
Ray is not built for one workload type. It provides general-purpose primitives — tasks, actors, and the object store — that support use cases ranging from ad hoc parallel tasks to distributed training, hyperparameter tuning, and model serving.
</details>

2. What is a Ray task?
   - A) A stateful, long-lived remote object created by applying `@ray.remote` to a class
   - B) A stateless function that Ray runs remotely, created by applying `@ray.remote` to a function
   - C) The process that manages cluster metadata on the head node
   - D) A shard of the distributed object store

<details>

<summary>Show Answer</summary>

**Answer: B) A stateless function that Ray runs remotely, created by applying `@ray.remote` to a function**

**Explanation:**
A task is a stateless remote function. Calling it returns a future immediately, and Ray schedules the actual execution on some worker with available capacity. Because tasks carry no state between calls, Ray can run any call on any worker with capacity.
</details>

3. What distinguishes an actor from a task?
   - A) An actor is stateless, while a task retains state between calls
   - B) An actor is a long-lived, stateful remote instance created from a class, whose state persists across method calls
   - C) An actor can only run on the head node
   - D) An actor cannot be created with the `@ray.remote` decorator

<details>

<summary>Show Answer</summary>

**Answer: B) An actor is a long-lived, stateful remote instance created from a class, whose state persists across method calls**

**Explanation:**
Applying `@ray.remote` to a class turns it into an actor. Ray keeps the resulting instance alive as a long-lived remote process, so state stored on it — such as loaded model weights or a counter — persists across method calls, unlike a stateless task.
</details>

4. What problem does Ray's distributed object store primarily solve?
   - A) It replaces the need for a head node in a Ray cluster
   - B) It avoids unnecessary copying of large objects by letting them be read from shared memory rather than reserialized into every process that needs them
   - C) It stores the cluster's autoscaler configuration
   - D) It schedules tasks onto specific worker nodes

<details>

<summary>Show Answer</summary>

**Answer: B) It avoids unnecessary copying of large objects by letting them be read from shared memory rather than reserialized into every process that needs them**

**Explanation:**
The object store is a distributed, shared-memory store for objects passed between tasks and actors. For large objects such as datasets or model weights, this avoids the serialization and copy cost of duplicating the object into every process that needs it.
</details>

5. What runs on a Ray cluster's head node, in addition to what worker nodes run?
   - A) Only the distributed object store
   - B) The Global Control Store (GCS), the driver process (if run there), and the autoscaler
   - C) Only user-submitted tasks and actors
   - D) A separate Kubernetes control plane

<details>

<summary>Show Answer</summary>

**Answer: B) The Global Control Store (GCS), the driver process (if run there), and the autoscaler**

**Explanation:**
The head node runs the GCS (cluster metadata), the driver process if a top-level script or session runs there, and the autoscaler, in addition to contributing CPU/GPU/memory to the resource pool the way worker nodes do.
</details>

6. How does Ray schedule tasks and actors across a cluster?
   - A) Against each node's resources in isolation, requiring the user to pick a specific node for each task
   - B) Against the cluster's combined resource pool, so a task can land on any node with enough free resources
   - C) Only on the head node, with worker nodes used solely for storage
   - D) Randomly, without regard to available CPU, GPU, or memory

<details>

<summary>Show Answer</summary>

**Answer: B) Against the cluster's combined resource pool, so a task can land on any node with enough free resources**

**Explanation:**
Ray schedules work against the whole cluster's resource pool rather than per-node. A task requesting a given amount of CPU can run on whichever node in the cluster has that capacity free.
</details>

7. What do Ray Train, Ray Tune, and Ray Serve have in common architecturally?
   - A) Each implements its own separate scheduling and fault-tolerance system, independent of Ray's core
   - B) They are all built on top of the same underlying tasks, actors, and object store as Ray's core primitives
   - C) They can only run outside of a Ray cluster
   - D) They replace the need for a head node

<details>

<summary>Show Answer</summary>

**Answer: B) They are all built on top of the same underlying tasks, actors, and object store as Ray's core primitives**

**Explanation:**
Ray's higher-level libraries for training, tuning, and serving reuse the same primitives rather than reimplementing scheduling and data movement separately for each workload. This shared foundation is Ray's key architectural distinction from bundling unrelated point tools.
</details>

8. Why does running Ray on Kubernetes require something beyond Ray's own cluster concept?
   - A) Because Ray cannot run inside containers
   - B) Because Ray's head/worker cluster shape is a different layer from Kubernetes' own scheduling, so something needs to translate that shape into Kubernetes objects like Pods and Deployments
   - C) Because Kubernetes does not support autoscaling
   - D) Because Ray tasks cannot use CPU resources on Kubernetes nodes

<details>

<summary>Show Answer</summary>

**Answer: B) Because Ray's head/worker cluster shape is a different layer from Kubernetes' own scheduling, so something needs to translate that shape into Kubernetes objects like Pods and Deployments**

**Explanation:**
Ray's own notion of a cluster (head node, worker nodes, autoscaler) doesn't automatically map onto Kubernetes' scheduling model. Something has to translate a Ray cluster's shape into Pods and Deployments the Kubernetes scheduler understands — that translation is what KubeRay provides.
</details>

## Short Answer Questions

9. A teammate is deciding whether to implement a piece of logic as a Ray task or a Ray actor. They need to keep a machine learning model loaded in memory across many incoming requests, rather than reloading it every time. Which primitive should they use, and why?

<details>

<summary>Show Answer</summary>

**Answer: An actor, because it is a long-lived, stateful remote instance — the loaded model can be held in the actor's state and reused across many method calls, instead of being reloaded on every call the way a stateless task would require.**

**Explanation:**
Tasks are stateless and complete a single call; there is nowhere on a task to keep a loaded model resident between calls. An actor's instance stays alive as a remote process, so state such as loaded model weights persists across calls made through the actor handle.
</details>

10. Why does Ray implement scheduling, fault tolerance, and data movement once in its core primitives rather than once per higher-level library (Train, Tune, Serve)?

<details>

<summary>Show Answer</summary>

**Answer: Because Ray Train, Ray Tune, and Ray Serve are all built on the same tasks, actors, and object store, each library reuses that shared implementation instead of reimplementing scheduling and data movement separately for its own workload.**

**Explanation:**
This shared foundation is Ray's key architectural distinction from an ecosystem of separate point tools, each with its own execution model, that happen to be bundled together. A distributed training run and a hyperparameter sweep both, underneath, are workers running as Ray actors or tasks exchanging data through the same object store.
</details>

---

[Return to Learning Materials](../../../ai-ml/ray/01-architecture.md) | [Next Quiz: KubeRay Operator](./02-kuberay-operator-quiz.md)
