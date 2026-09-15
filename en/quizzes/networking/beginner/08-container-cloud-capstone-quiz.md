# Capstone, Containers and Cloud Quiz

[Lesson](../../../networking/beginner/08-container-cloud-capstone.md)

Six questions. Explain each answer in your own words.

1. An IP request returns HTTP 200, but getent fails for the service name. What do you investigate first?

   - A) CPU congestion-control algorithms
   - B) The name-resolution path
   - C) Only HTTP file permissions
   - D) Every CNI implementation

<details>
<summary>Show Answer</summary>

**Answer: B) The name-resolution path**

**Explanation:** IP connectivity and an application response are established, so investigate how the name is resolved. Identifying a particular DNS server as the cause needs more evidence.

</details>

2. The server returns HTTP 404. What has this request established?

   - A) Every port is open
   - B) The routing table is empty
   - C) An HTTP response was exchanged with the server
   - D) The entire internet is healthy

<details>
<summary>Show Answer</summary>

**Answer: C) An HTTP response was exchanged with the server**

**Explanation:** 404 is an HTTP-layer response. Compare paths and server logs; resetting the entire firewall is unsupported by this evidence.

</details>

3. ss shows only a 127.0.0.1:8000 listener and the server-local request succeeds. What is central to investigating remote failure?

   - A) Check whether the listener binds to the remote request destination address
   - B) Assume client localhost is the same as server localhost
   - C) Always increase DNS TTL
   - D) Disable SELinux

<details>
<summary>Show Answer</summary>

**Answer: A) Check whether the listener binds to the remote request destination address**

**Explanation:** Loopback belongs to its network namespace. Receiving traffic on the server lab IP requires a listener bound appropriately and suitable access rules.

</details>

4. You removed only UFW's independent TCP 8000 allow. New key-only SSH still works, but HTTP fails. Which recovery preserves the intended policy?

   - A) Append an HTTP allow after the remaining lab deny
   - B) Delete the lab deny and all SSH rules
   - C) Disable UFW and assume an old SSH session proves recovery
   - D) Insert the original scoped HTTP allow ahead of the deny, then verify rule order, HTTP 200, and a fresh key-only SSH connection

<details>
<summary>Show Answer</summary>

**Answer: D) Insert the original scoped HTTP allow ahead of the deny, then verify rule order, HTTP 200, and a fresh key-only SSH connection**

**Explanation:** SSH and HTTP have separate allows, so the HTTP fault must leave TCP 22 and default policies untouched. UFW placement matters: an allow appended behind a matching deny is ineffective. Test a new, non-multiplexed key login before, during, and after the fault; allow the encrypted key's passphrase prompt rather than assuming an unlocked agent. In the firewalld branch, only runtime HTTP is removed/restored and its permanent rule remains present. If HTTP never fails after removal, inspect other accepts and zone behavior instead of claiming a block.

</details>

5. What does curl --resolve lesson.test:8000:192.0.2.20 change?

   - A) DNS servers on every VM
   - B) The host/port mapping for that curl invocation
   - C) The persistent /etc/hosts file
   - D) A Kubernetes Service IP

<details>
<summary>Show Answer</summary>

**Answer: B) The host/port mapping for that curl invocation**

**Explanation:** The override is scoped to this invocation. It does not edit the system resolver or mappings used by other programs.

</details>

6. Which principle should you retain when moving from VM practice to CNI?

   - A) Docker bridge and all CNIs are the same implementation
   - B) Service IP and localhost are identical
   - C) Identify namespaces, addresses, routes, policies and observation points again
   - D) A tiny HTTP request proves maximum cloud throughput

<details>
<summary>Show Answer</summary>

**Answer: C) Identify namespaces, addresses, routes, policies and observation points again**

**Explanation:** The diagnostic questions transfer, but implementation and boundaries differ. Distinguish cluster abstractions from the real packet path.

</details>
