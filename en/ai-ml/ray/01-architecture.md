# Part 1: Ray Architecture

> **Review baseline**: Ray 2.58.0 · 2026-09-12

## Lab Environment Setup

The local example was checked with Python 3.12, `ray==2.58.0`, and `numpy==2.2.6`. Its task, actor, and ObjectRef checks require no GPU, trained model, or Kubernetes. Check the relevant extra dependencies separately when enabling features such as the dashboard.

The example explicitly configures two logical CPUs and an 80 MiB object store, then shuts Ray down. Ray resource settings are not operating-system limits on total CPU/RAM; control and worker processes require additional memory.

## What Is Ray?

Ray Core provides remote functions (tasks), stateful remote instances (actors), ObjectRefs, and per-node object stores. Train, Tune, and Serve build on that foundation. Sharing Core does not eliminate their own controllers, retries, checkpoints, or framework communication logic.

## Core Primitives

### Tasks

After applying `@ray.remote`, submit through **`f.remote(...)`**. Calling it as an ordinary `f(...)` is incorrect. A single-return example produces an `ObjectRef`, which can be read with `ray.get()`.

Calling a task stateless does not guarantee a pure function without side effects. File/database mutations need an idempotency strategy for retries. Workers can be reused; a module-global cache surviving incidentally is different from explicit state management.

Ray tracks dependencies. Passing an upstream ObjectRef as a top-level argument to another task creates a dependency on that value becoming ready. Tasks are not necessarily independent of one another.

### Actors

`Actor.remote()` creates a handle to a remote instance; `handle.method.remote()` submits a method to it. Counters, connections, or models in that instance's memory can be reused across calls.

This is not automatic durable storage. In 2.58.0, `max_restarts` defaults to 0. Configuring restarts reruns the constructor; it does not automatically restore application state. Design checkpoints and recovery separately, and distinguish synchronous, async, and threaded actor concurrency/ordering.

### Object Store

Remote values are immutable and can be stored or replicated in node-local object stores. References to one value do not make every node share one physical memory region. Cross-node access can involve transport and serialization costs.

**NumPy arrays on the same node** can be read through read-only shared-memory views. Copy them before mutation. This does not imply zero-copy behavior for all Python objects, cross-node transfers, or GPU tensors/model weights. Small and large values can also use different transfer paths.

## Small Local Example

This checks API behavior, not training performance or a benchmark.

```python
import ray
import numpy as np

try:
    ray.init(address="local", num_cpus=2, include_dashboard=False,
             object_store_memory=80 * 1024 * 1024)

    @ray.remote(num_cpus=1)
    def twice(value):
        return value * 2

    first = twice.remote(2)
    second = twice.remote(first)  # ObjectRef dependency
    assert ray.get(second, timeout=15) == 8

    @ray.remote(num_cpus=1)
    class Counter:
        def __init__(self):
            self.value = 0
        def increment(self):
            self.value += 1
            return self.value

    counter = Counter.remote()
    assert ray.get([counter.increment.remote(),
                    counter.increment.remote()], timeout=15) == [1, 2]
    ref = ray.put(np.arange(256_000, dtype=np.int64))
    array = ray.get(ref, timeout=15)
    assert not array.flags.writeable
finally:
    ray.shutdown()
```

A small single-node exercise does not establish multi-node fault recovery, GPU memory sharing, or network performance.

## Cluster Architecture: Head Node and Worker Nodes

The head runs cluster-control components including the **Global Control Service (GCS)**. Raylets, worker processes, and local object stores participate in execution and data movement on the head and workers. A head can advertise zero logical CPUs to restrict user-task placement; it need not contribute the same compute resources as a worker.

The driver executes the top-level application. It does not have to run on the head; placement depends on the submission method. An autoscaler is also a configured deployment component, not a promise that every local `ray.init()` automatically provisions more workers.

The GCS manages cluster metadata such as actors, nodes, and placement groups. **Do not describe it as the centralized owner of all object metadata.** The process that creates the original ObjectRef is the object owner, and can differ from the worker computing the value.

### Resource Placement

Ray considers cluster state when selecting candidates, but **each task/actor must fit on one feasible node**. Two nodes with one free CPU each do not jointly execute a single two-CPU task. Feasibility, availability, data locality, and placement/label/affinity constraints all matter.

Logical CPU/GPU resources guide admission and scheduling. `num_cpus=1` does not force every OS thread in the process onto one physical core. Configure container requests/limits and library thread counts separately.

![The Ray head's GCS is distinct from per-node raylets, local object stores, and task/actor execution. Driver ObjectRef dependencies and cross-node object transfers are shown; object ownership metadata is not all centralized in the GCS.](../../.gitbook/assets/en-ai-ml-ray-01-architecture-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-01-architecture-0.html)

## Fault Recovery and Higher-Level Libraries

The GCS is in-memory by default; recovery after head failure requires additional durable-backend configuration. The 2.58.0 documentation distinguishes supported external Redis from embedded RocksDB **alpha**. Recovering GCS metadata does not restore every actor's application state or object value.

Object recovery depends on ownership, lineage, and retry/reconstruction eligibility. Do not equate `ray.put()` values with recomputable task outputs, or object spilling with long-term backup.

Train, Tune, and Serve reuse Core while adding policies such as training checkpoints, trial scheduling, and serving controllers. Framework collectives and other training communication cannot all be described as traffic through one object-store path.

## Why This Matters on Kubernetes

KubeRay reconciles CRs such as RayCluster, RayJob, and RayService into Ray Pods and related resources. Ray task/actor scheduling, Kubernetes Pod placement, and actual EC2 provisioning by tools such as Karpenter are separate layers. KubeRay is not a dispatcher that automatically selects Train, Tune, or Serve for an application.

## Primary Sources

- [Ray 2.58.0 release](https://github.com/ray-project/ray/releases/tag/ray-2.58.0)
- [Objects](https://docs.ray.io/en/releases-2.58.0/ray-core/objects.html)
- [Serialization and NumPy zero-copy](https://docs.ray.io/en/releases-2.58.0/ray-core/objects/serialization.html)
- [Scheduling](https://docs.ray.io/en/releases-2.58.0/ray-core/scheduling/index.html)
- [Logical resources](https://docs.ray.io/en/releases-2.58.0/ray-core/scheduling/resources.html)
- [Actor fault tolerance](https://docs.ray.io/en/releases-2.58.0/ray-core/fault_tolerance/actors.html)
- [Object fault tolerance](https://docs.ray.io/en/releases-2.58.0/ray-core/fault_tolerance/objects.html)
- [GCS fault tolerance](https://docs.ray.io/en/releases-2.58.0/ray-core/fault_tolerance/gcs.html)

[Next: KubeRay](02-kuberay-operator.md) · [Main Page](README.md) · [Quiz](../../quizzes/ai-ml/ray/01-architecture-quiz.md)
