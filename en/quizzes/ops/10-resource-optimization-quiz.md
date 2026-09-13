# Resource optimization quiz

> **Related document**: [Resource optimization](../../ops/10-resource-optimization.md)

## 1. Which statement correctly describes eviction under memory pressure?

- A) QoS class alone determines the order
- B) Usage above requests, Pod Priority and relative usage matter
- C) Guaranteed pods can never be evicted
- D) PDBs prevent every node-pressure eviction

<details>
<summary>Show answer</summary>

**Answer: B**

QoS is useful but not an absolute eviction ordering. Distinguish container-limit OOM, memory-pressure eviction and DiskPressure.

</details>

## 2. What does the CPU throttled-period ratio measure?

- A) The exact fraction of lost CPU time
- B) The fraction of quota periods containing throttling
- C) CPU request utilization
- D) Average memory utilization

<details>
<summary>Show answer</summary>

**Answer: B**

Threads share the quota. The period ratio alone does not determine lost time or prove that a higher limit is the right fix.

</details>

## 3. Which statement about JVM heap and container memory is correct?

- A) 75% is always optimal
- B) Measure non-heap memory and RSS when choosing a ratio
- C) MaxRAMPercentage always follows live Pod limit changes immediately
- D) Kernel SIGKILL always produces a heap dump

<details>
<summary>Show answer</summary>

**Answer: B**

Metaspace, stacks, direct buffers and JNI need memory. Distinguish JVM ergonomics from cgroup limits, and Java OOME from SIGKILL.

</details>

## 4. Why might setting JAVA_OPTS not apply JVM options?

- A) It is a security option the JVM must reject
- B) The JVM does not automatically read it unless the entrypoint passes it
- C) Kubernetes does not support environment variables
- D) Java 21 cannot run in containers

<details>
<summary>Show answer</summary>

**Answer: B**

Use JAVA_TOOL_OPTIONS or explicit java arguments and verify the actual VM.flags output.

</details>

## 5. Which statement about VPA upperBound is correct?

- A) Always copy it to the container memory limit
- B) It is part of the request recommendation range, not the container limit
- C) It is the HPA maximum replica count
- D) It is the amount of memory that guarantees no OOM

<details>
<summary>Show answer</summary>

**Answer: B**

Distinguish target, lowerBound, upperBound and uncappedTarget. Initial mode can still affect HPA's denominator through new requests.

</details>

## 6. Which statement about Go 1.25+ default GOMAXPROCS is correct?

- A) It always uses host CPUs and requires an external library
- B) Subject to language-version/compatibility defaults, it considers quota and affinity; explicit settings disable automatic updates
- C) It uses CPU requests alone
- D) 500m always produces 1 in every environment

<details>
<summary>Show answer</summary>

**Answer: B**

The example was tested with Go 1.27.1 and go.mod 1.25+. Quota rounding and minimum-value conditions matter.

</details>

## 7. What limitation do GOMEMLIMIT and Node's old-space limit share?

- A) They do not completely bound process RSS
- B) They forcibly free all native memory
- C) They guarantee prevention of container OOM
- D) They automatically change Pod requests

<details>
<summary>Show answer</summary>

**Answer: A**

Go's value is a runtime-managed soft limit; Node's option controls V8 old space. Account separately for native allocations and multiple workers.

</details>

## 8. How should Gunicorn/Tokio worker counts be chosen?

- A) A fixed multiple of host CPU count is sufficient
- B) Verify actual settings and test quota, memory and workload behavior
- C) Rust needs no concurrency limits because it has no GC
- D) Thread/process counts do not affect memory

<details>
<summary>Show answer</summary>

**Answer: B**

The configuration must actually read WEB_CONCURRENCY. Explicit Tokio worker_threads overrides the environment; the blocking pool is separate.

</details>

## 9. How should OOM reason and Pending phase metrics be interpreted?

- A) Apply increase to the reason gauge for an exact OOM count
- B) Count all Pending series to obtain the current Pending count
- C) Evaluate 0/1 values and preserve the last-state limitation of reason gauges
- D) Pending always means insufficient CPU

<details>
<summary>Show answer</summary>

**Answer: C**

Zero-valued Pending series exist. Combining recent restarts and the last OOM reason does not reconstruct every OOM in the interval.

</details>

## 10. Which statement about Auto Mode bin-packing and placeholder pods is correct?

- A) A 4-vCPU instance always fits four CPU of application requests
- B) A placeholder is an EC2 Capacity Reservation
- C) Account for allocatable, overhead and scheduling constraints; placeholders do not guarantee capacity
- D) preemptionPolicy Never prevents the pod from being preempted

<details>
<summary>Show answer</summary>

**Answer: C**

Never prevents this pod from preempting others. NodePool uses karpenter.sh/v1; the Auto Mode NodeClass group is eks.amazonaws.com.

</details>
