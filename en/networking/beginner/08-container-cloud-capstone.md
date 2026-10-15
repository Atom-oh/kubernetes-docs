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

### D. Test a firewall hypothesis with evidence {#firewall-fault}

Use **only the manager selected in lesson 6**, from the server's hypervisor console. This fault removes only the course-owned TCP 8000 allow. The TCP 22 allow, lab deny, default policies, zones/profile assignments, and management NIC stay in place. Finish the optional Fail2ban experiment first so no background ban change confounds this test.

**Server console B, normal user:** re-identify both NICs by their recorded hypervisor MACs; variables from lesson 6 are not assumed to survive.

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

Verify `.20/24` on the lab NIC, distinct NIC names, unchanged management, and the healthy `.20:8000` listener. Record the current rules as instructed below. If the server's timer expired, restart **only** `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"` in server console A with its existing directory. Do not introduce a stopped-server fault at the same time.

**Client, normal user:** recover the existing lesson-5 key directory and normal server account from your records. Do not create a new key or bypass the verified host record.

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

Define this short shell function once in that client terminal. Calling `check_lab_ssh` runs a **new** SSH connection, prints the remote account/connection, and returns to the client; it creates no file or service.

```bash
check_lab_ssh() {
  ssh -F /dev/null -b 192.0.2.10 \
    -i "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
    -o "UserKnownHostsFile=${SSH_LAB_DIR:?missing key directory}/known_hosts" \
    -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
    -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
    -o BatchMode=no -o ConnectTimeout=5 \
    "${SERVER_USER:?missing account}@192.0.2.20" \
    'whoami; printf "%s\n" "$SSH_CONNECTION"'
}
check_lab_ssh
```

The private-key **passphrase prompt is allowed**; an unlocked agent is not required. Remote account-password fallback is disabled. `-F /dev/null` avoids unrelated client configuration, and disabling multiplexing prevents reuse of an old authenticated connection. Expect the normal account and a connection from `.10` to `.20` port 22. If this **before-fault** check or healthy HTTP fails, stop before changing any rule. Also preserve/recheck any separately required management SSH path.

#### UFW: change only the saved/applied HTTP allow

**Ubuntu server console B, sudo:**

```bash
sudo ufw status numbered
sudo ufw show added
```

Proceed only with active UFW and lesson 6's three course rules in this order: **1: `.10`→`.20` TCP 22 allow on `LAB_IF`; 2: the separate TCP 8000 allow; 3: the same-interface/destination TCP `22,8000` deny**. Record their full specifications. If you still have an older combined `22,8000` allow or the order differs, reconcile the lesson-6 setup first; deleting one port is not an inverse of a multiport rule.

Remove only HTTP:

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

Confirm the TCP 22 allow remains first and the lab deny is now second. This changes both saved and applied UFW state. Leave those two rules and the default policies alone. Now perform the **during-fault checks** below.

**Restore from the same Ubuntu console:** verify the deny is still second, then insert HTTP at position 2, **ahead of that deny**:

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

Expect the original SSH allow → HTTP allow → lab deny order and original source/interface/destination scope. Appending an allow after the deny would still block HTTP; the deletion's inverse includes restoring placement. If another rule changed the positions, stop and re-establish the recorded order instead of using a stale number. Continue with the after-recovery checks below.

#### firewalld: remove HTTP only at runtime and preserve the saved policy

**Rocky server console B, normal user for assignments, sudo for firewall queries:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

Expect only the lab NIC in `network-beginner`, the original management zone, and all four queries returning `yes`. This requires lesson 6's retained permanent rules, not its expiring trial. Record both configurations and inspect any broader policy that could still accept HTTP.

Remove **only the runtime HTTP rule**:

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

Expect `no`, `yes`, `yes`, `yes`; `no` has a nonzero status and is expected here. Run the during-fault checks. Do not reload, reboot, or use `--runtime-to-permanent`: a reload would reintroduce the saved HTTP rule, while copying runtime to permanent would unintentionally persist the fault.

**Restore from the same Rocky console**, without a global reload or permanent change:

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

All four queries should again say `yes`. Compare the runtime/permanent lists with your recorded baseline: the saved rules were never changed, and runtime HTTP has been restored with the same scope. An unexpected saved-policy change needs investigation against that record, not a bulk overwrite.

#### Checks during the fault and after recovery

**Client, normal user, same terminal:** run this pair **after HTTP removal and again after restoration**, in addition to the before-fault check.

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

During the fault, the fresh key-only SSH check must still succeed. HTTP should fail under the recorded course policy while the server listener remains `.20:8000`. If SSH fails, recover only the removed HTTP permission from the server console, compare the unchanged SSH rule/path, and stop: you have not demonstrated an HTTP-only fault. If HTTP still succeeds, inspect other matching accepts, zone/default behavior, listener and packet evidence; do not claim a block merely because one rule was removed.

After recovery, require a fresh successful key-only SSH check and HTTP 200 with `healthy`. On server console B, repeat `sudo ss -ltnp 'sport = :8000'`, the relevant rule queries/listing, `ip -4 -br address show dev "$MGMT_IF"`, and `ip -4 route`; compare with the before-fault record and recheck required management access. Record observations for all three stages separately. These instructions are not a claim that guest execution was performed when writing the document.

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

For a structured continuation, follow the [expert networking path](../expert/README.md). It connects the individual guides below to a reading, experiment and assessment progression.

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
- [Ubuntu 24.04 UFW: rule order, multiport rules and deletion](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld: runtime/permanent configuration and rich-rule operations](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [OpenSSH client options and connection sharing](https://man.openbsd.org/ssh_config)
- [Docker bridge](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker overlay](https://docs.docker.com/engine/network/drivers/overlay/)
- [Kubernetes networking model](https://kubernetes.io/docs/concepts/services-networking/)

[Previous: Monitoring and performance](07-monitoring-performance.md) · [Quiz](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [Back to course](README.md)
