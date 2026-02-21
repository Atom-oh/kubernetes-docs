# Resource Optimization Quiz

> **Related Document**: [Resource Optimization](../../ops/10-resource-optimization.md)

## Multiple Choice Questions

### 1. What is the difference between resource requests and limits in Kubernetes?

- A) Requests are for CPU only, limits are for memory only
- B) Requests are guaranteed resources for scheduling; limits are maximum allowed
- C) Requests and limits are the same thing
- D) Limits are guaranteed, requests are optional

<details>
<summary>Show Answer</summary>

**Answer: B) Requests are guaranteed resources for scheduling; limits are maximum allowed**

**Explanation:**
Requests are the resources Kubernetes guarantees to a container and uses for scheduling decisions. Limits are the maximum resources a container can use. Exceeding CPU limits causes throttling; exceeding memory limits can cause OOM kills.

</details>

### 2. Which QoS class gets the highest priority during node resource pressure?

- A) BestEffort
- B) Burstable
- C) Guaranteed
- D) All classes have equal priority

<details>
<summary>Show Answer</summary>

**Answer: C) Guaranteed**

**Explanation:**
Guaranteed pods (requests=limits for both CPU and memory) have the highest priority and are last to be evicted during resource pressure. BestEffort pods (no requests/limits) are evicted first, followed by Burstable pods.

</details>

### 3. What causes CPU throttling in Kubernetes containers?

- A) Not enough memory
- B) Container exceeding its CPU limit during a CFS period
- C) Network congestion
- D) Disk I/O bottleneck

<details>
<summary>Show Answer</summary>

**Answer: B) Container exceeding its CPU limit during a CFS period**

**Explanation:**
The Linux CFS (Completely Fair Scheduler) enforces CPU limits over 100ms periods. If a container uses its quota early in the period, it's throttled (paused) until the next period begins. This is tracked in `cpu.cfs_throttled_us`.

</details>

### 4. What is the recommended JVM MaxRAMPercentage setting for containers?

- A) 100%
- B) 90%
- C) 75%
- D) 50%

<details>
<summary>Show Answer</summary>

**Answer: C) 75%**

**Explanation:**
Setting MaxRAMPercentage to 75% leaves 25% of container memory for non-heap usage: metaspace, thread stacks, native memory, and OS overhead. Using higher values risks OOM kills when non-heap memory grows unexpectedly.

</details>

### 5. In VPA, what does the "Initial" update mode do?

- A) Updates pods continuously
- B) Only sets resources when pods are first created
- C) Deletes all existing pods
- D) Disables VPA completely

<details>
<summary>Show Answer</summary>

**Answer: B) Only sets resources when pods are first created**

**Explanation:**
"Initial" mode applies VPA recommendations only at pod creation time, not to running pods. This is useful with HPA since it avoids conflicts - VPA sets initial sizing, HPA handles scaling, and existing pods aren't disrupted.

</details>

### 6. What Go runtime setting should be configured based on container CPU limits?

- A) GOGC
- B) GOMAXPROCS
- C) GOPATH
- D) GOROOT

<details>
<summary>Show Answer</summary>

**Answer: B) GOMAXPROCS**

**Explanation:**
GOMAXPROCS controls the number of OS threads executing Go code. By default, Go uses all host CPUs, not container limits. Setting GOMAXPROCS to match container CPU limits (using automaxprocs library) prevents excessive context switching.

</details>

### 7. What is GOMEMLIMIT used for in Go applications?

- A) Setting minimum memory allocation
- B) Providing a soft memory limit hint to the garbage collector
- C) Limiting the number of goroutines
- D) Configuring swap memory

<details>
<summary>Show Answer</summary>

**Answer: B) Providing a soft memory limit hint to the garbage collector**

**Explanation:**
GOMEMLIMIT tells the Go garbage collector the target memory ceiling. The GC triggers earlier as memory approaches this limit, reducing the risk of OOM kills while still utilizing available memory efficiently.

</details>

### 8. For Python Gunicorn workers in containers, what's the recommended worker count formula?

- A) 2 * CPU_CORES + 1
- B) Based on container CPU limit, not host cores
- C) Always use 1 worker
- D) Use 100 workers for maximum throughput

<details>
<summary>Show Answer</summary>

**Answer: B) Based on container CPU limit, not host cores**

**Explanation:**
The classic formula (2*cores+1) uses host CPU count, which oversubscribes in containers. Worker count should be based on container CPU limits (e.g., 2-4 workers per CPU limit) to avoid resource contention and OOM issues.

</details>

### 9. What happens to a container that exceeds its memory limit?

- A) It gets CPU throttled
- B) It is OOM killed by the kernel
- C) It automatically scales horizontally
- D) Memory is borrowed from other containers

<details>
<summary>Show Answer</summary>

**Answer: B) It is OOM killed by the kernel**

**Explanation:**
Unlike CPU (which is throttled), memory limits are hard enforced. When a container exceeds its memory limit, the Linux OOM killer terminates processes in the container. Kubernetes then restarts the container based on its restart policy.

</details>

### 10. What is the purpose of the VPA Recommender component?

- A) To restart pods with new resources
- B) To analyze resource usage and generate resource recommendations
- C) To manage node scaling
- D) To validate resource configurations

<details>
<summary>Show Answer</summary>

**Answer: B) To analyze resource usage and generate resource recommendations**

**Explanation:**
The VPA Recommender watches actual resource usage of containers over time and generates recommendations for requests and limits. It considers CPU and memory usage patterns, peaks, and variance to suggest appropriate values.

</details>
