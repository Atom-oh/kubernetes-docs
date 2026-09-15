# 8. Capstone — From Web Service Failures to Containers and Cloud

> **Learning baseline**: Ubuntu Server 24.04 LTS, with an alternate Rocky Linux 9 path
>
> **Last Updated**: September 15, 2026

**Prerequisites:** [Lessons 1–7](README.md#course-map), both VMs' lab addresses, verified SSH key login, and a TCP 8000 rule allowing the lab client. Stop the lesson 7 web server first.

**Outcomes:** Record a small web service's healthy state, then reproduce, diagnose and recover from failures at different layers one at a time. Apply the same questions to Docker and Kubernetes afterward. Allow approximately 3–4 hours.

## Task and healthy baseline {#baseline}

The task is “the client reads `/health.txt` from the server”. No web framework or cloud account is required.

**Server console A:**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

Restart with the same command when the five-minute limit expires. Check the console so an intentionally stopped server is not mistaken for a network fault. Keep only the exercise file in this directory.

**Server console B:**

```bash
ip -br address
ip route get 192.0.2.10
sudo ss -ltnp 'sport = :8000'
```

**Client:**

```bash
ip route get 192.0.2.20
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve lesson.test:8000:192.0.2.20 \
  -i http://lesson.test:8000/health.txt
```

Both routes must use the lab NICs, the listener must be `192.0.2.20:8000`, and both requests must return HTTP 200 with `healthy` in the body. `--resolve` provides a **host/port address mapping for this curl invocation**. It changes neither system DNS nor other applications.

If the baseline fails, check configuration and rules from lessons 4–6 first. Do not introduce a new fault until the baseline works.

## Reproduce one fault at a time {#faults}

Start each experiment from the healthy baseline and repeat the healthy request after recovery. Ordinary `curl` requests can return exit status 0 even for HTTP 404, so read the HTTP status line. Automation that must treat HTTP errors as failures can explicitly select a supported option such as `--fail-with-body`.

### A. Separate name resolution from IP connectivity

On the client, compare a request without `--resolve`.

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

With no separate registration of `lesson.test`, name resolution will normally fail in this lab. If you already configured it in `/etc/hosts` or local DNS, record the actual mapping instead of expecting failure. Check whether the earlier IP and `--resolve` requests succeed in the same environment.

**Diagnosis:** If the IP request works but name lookup fails, investigate name resolution first. This does not establish a specific DNS server failure or an internet-wide outage. **Recovery:** Reuse the healthy request's `--resolve` mapping; no system resolver overwrite is needed for this temporary experiment.

### B. An application path error

Request a missing file from the client.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**Diagnosis:** Receiving HTTP 404 means that request exchanged an HTTP response with the server. There is no reason to reset all routing and firewall settings. Compare the requested path with the server log. **Recovery:** Request `/health.txt` again.

### C. The wrong listening address

Stop your server with Ctrl+C in server console A. In **the same terminal**, change only its bind address.

```bash
timeout 300 python3 -m http.server 8000 \
  --bind 127.0.0.1 --directory "$LAB_WEB"
```

Server console B:

```bash
sudo ss -ltnp 'sport = :8000'
curl --disable --noproxy '*' --max-time 5 \
  -i http://127.0.0.1:8000/health.txt
```

Check that the client's original `192.0.2.20:8000` request fails while the server's own loopback request succeeds. Firewall behavior also affects whether failure appears as refusal or timeout. The `127.0.0.1` listener shown by `ss` is the key evidence.

**Recovery:** Press Ctrl+C in console A and restart the healthy command with `--bind 192.0.2.20`. One VM's loopback is not another VM's loopback.

### D. Test a firewall hypothesis with evidence

Use the procedure for the **single firewall manager** selected in lesson 6. Record the healthy rules first, then remove **only the TCP 8000 allow rule added for this course**, using that lesson's deletion command. Leave SSH rules and default policies alone.

Repeat the healthy HTTP request from the client. Compare the server listener, selected zone/interface, current rules and lesson 7 capture. Traffic may remain allowed: if so, find another matching allow rule or the zone's default behavior and revise the hypothesis. Do not record “one rule was removed, therefore traffic was blocked”.

**Recovery:** Restore the TCP 8000 rule with the same source/interface scope from lesson 6. Verify both the effective rule and HTTP 200. If persistent rules changed too, reconcile runtime and persistent state using that manager's documented procedure.

## Report and completion criteria {#capstone-report}

Record lab addresses and results, not passwords, private keys or real user traffic.

| Field | What to record |
|---|---|
| Environment | Distribution, kernel, lab NICs, client/server addresses, firewall manager |
| Healthy state | Routes, listener, HTTP status and body |
| Symptom | Which host sent which request and received which result |
| Hypothesis | Name resolution, route, listener, firewall or HTTP |
| Evidence | Relevant command, time, address/port and observation |
| Falsification | What you would expect if the hypothesis were wrong |
| Change and recovery | The single change and exact restoration procedure |
| Recheck | Healthy HTTP 200, SSH key access, lab/management NIC state |

**Pass:** Distinguish and recover from A–C and explain whether the actual rules and observations support D. Meet all five criteria: environment identification, layered hypothesis, evidence, narrow change/recovery, and post-recovery verification. Return to the relevant lesson for any missing criterion. Faster completion is not the assessment.

## Apply the questions to Docker and Kubernetes {#container-cloud-map}

Add containers after you understand diagnosis between VMs. This table maps roles for subsequent study; it does not imply that every packet crosses each row in order.

| What you learned | Docker | Kubernetes | Cloud |
|---|---|---|---|
| Process address/port | Listener inside a container network namespace | Pod listener and networking shared within a Pod | Backend process and load-balancer target port |
| Link and route | veth, Linux bridge and environment-dependent NAT | CNI-configured Pod paths, overlay or native routing | VPC subnets, routes and connectivity boundaries |
| Name resolution | Container names on user-defined bridges | Service names and cluster DNS | Organizational/cloud DNS and private names |
| Access rules | Published ports and host forwarding rules | NetworkPolicy and implementation enforcement | Layer-specific controls such as Security Groups |
| Observation point | Host versus container namespace | Node, Pod and Service implementation | Client, load balancer, node and AZ boundaries |

A Docker **bridge** commonly connects containers on one host; an **overlay** builds a virtual network over an underlying network. Docker Swarm overlay practice requires additional preparation such as multiple hosts. Kubernetes CNI is a separate interface/plugin ecosystem: copying a Docker bridge topology does not produce a Kubernetes cluster.

Likewise, `localhost`, Pod IP, Service IP and an external entry point are different observation targets. Host firewall rules, container forwarding rules and CNI policies are not one interchangeable rule list.

## Next practical steps {#next-path}

1. Use [container technology](../../basics/03-container-technology.md) to study namespaces, bridges and published ports.
2. Measure next hops, ICMP and PMTU in [Linux network diagnostics](../07-linux-network-diagnostics.md). First read that guide's Docker prerequisites, scope and cleanup.
3. Learn the [Kubernetes introduction](../../basics/04-kubernetes-introduction.md) and [Pods/workloads](../../core/02-pods-and-workloads.md), then follow the [Service/DNS lab](../../labs/core/03-services-networking-lab.md).
4. Study [eBPF fundamentals](../../basics/05-ebpf-fundamentals.md), then compare [Cilium](../cilium/README.md) and [Calico](../calico/README.md).
5. When you need AWS, study [EKS networking](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md) and [load balancing](../03-aws-lb-controller.md). Check each guide's cost, permission and cleanup conditions separately before creating resources.
6. For performance work, read the measurement conditions in the [kernel networking stack](../../kernel/02-network-stack.md) and [Pod benchmark](../06-pod-network-benchmark.md). Do not generalize the small HTTP exercise into a cloud-throughput result.

## Cleanup

Stop the exercise server in console A, then remove its file in the same terminal.

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

Record whether lesson 6's rules will remain for subsequent practice. When ending the entire course, use each lesson's recovery procedure or return to **your VM snapshot**. Verify the management NIC and existing SSH access, then shut down the VMs normally.

## References

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [curl address mapping](https://curl.se/docs/manpage.html)
- [Docker bridge](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker overlay](https://docs.docker.com/engine/network/drivers/overlay/)
- [Kubernetes networking model](https://kubernetes.io/docs/concepts/services-networking/)

[Previous: Monitoring and performance](07-monitoring-performance.md) · [Quiz](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [Back to course](README.md)
