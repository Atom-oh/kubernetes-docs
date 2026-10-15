# DNS and Connectivity Quiz

> **Last Updated**: September 15, 2026

Use the [lesson](../../../networking/beginner/04-dns-connectivity.md) to distinguish observation from inference. The internal lab has client `192.0.2.10/24` and server `192.0.2.20/24`; no DNS service runs on the server.

## Questions

1. `/etc/hosts` maps `server.netlab.test` to `.20`. `getent ahostsv4` succeeds, but `dig @192.0.2.20` times out. Which interpretation fits?
   - A) All name resolution is broken
   - B) Local NSS lookup works, while the queried server is not providing the expected DNS service
   - C) The management default route must be deleted
   - D) A hosts entry automatically creates a DNS listener on the server

<details>
<summary>Show Answer</summary>

**Answer: B) Local NSS lookup works, while the queried server is not providing the expected DNS service**

**Explanation:** getent follows system name-service sources; dig sends a DNS query to the selected server. The lab intentionally has no DNS listener at `.20`. A timeout is no usable response within the limit, not an NXDOMAIN answer. Keep the working hosts mapping rather than pointing system DNS at `.20`.

</details>

2. On Ubuntu, `dig @127.0.0.53 server.netlab.test. A` returns the address from `/etc/hosts`. What happened?
   - A) Dig directly read the queried name from NSS
   - B) A public authoritative server learned the local hosts entry
   - C) The client became a router
   - D) Dig queried resolved's stub, which can answer using local hosts data

<details>
<summary>Show Answer</summary>

**Answer: D) Dig queried resolved's stub, which can answer using local hosts data**

**Explanation:** Dig itself does not resolve the queried name through NSS. However, systemd-resolved normally reads hosts data and can expose that result through its DNS stub. Querying a local stub and querying an unrelated upstream server are different experiments; inspect configuration if that local behavior is disabled.

</details>

3. A DNS reply contains `status: NXDOMAIN`, while another query times out. What is the difference?
   - A) NXDOMAIN is a negative DNS answer; a timeout means no usable response arrived within the limit
   - B) Both prove the queried name does not exist
   - C) NXDOMAIN proves all IP routes are missing
   - D) A timeout proves the authoritative server deleted the record

<details>
<summary>Show Answer</summary>

**Answer: A) NXDOMAIN is a negative DNS answer; a timeout means no usable response arrived within the limit**

**Explanation:** Investigate spelling, resolver view and cached negative data for NXDOMAIN. Investigate route, resolver reachability and policy for timeouts. Dig may exit 0 after receiving NXDOMAIN, so read DNS status and answer content rather than relying only on shell exit status.

</details>

4. A record has TTL 300. You lower its authoritative TTL and clear resolved's local cache. What can you conclude?
   - A) Every client instantly sees the new record
   - B) The record can traverse exactly 300 routers
   - C) DNS TTL is a cache lifetime; other caches can retain earlier data, and IP TTL is unrelated
   - D) `/etc/hosts` was also erased

<details>
<summary>Show Answer</summary>

**Answer: C) DNS TTL is a cache lifetime; other caches can retain earlier data, and IP TTL is unrelated**

**Explanation:** Clearing one local service's DNS cache does not clear application or upstream caches. Changing the authoritative TTL does not rewrite a previously cached lifetime. IP TTL limits forwarding hops; the units and mechanism differ from DNS TTL seconds.

</details>

5. The client's `ip route get 192.0.2.20` shows `dev LAB_NIC src 192.0.2.10` and no `via`. What is established?
   - A) The server's HTTP application is healthy
   - B) Local routing selects the lab interface and source for an on-link peer; reachability is still untested
   - C) No default route exists anywhere on the VM
   - D) DNS selected the peer's MAC address

<details>
<summary>Show Answer</summary>

**Answer: B) Local routing selects the lab interface and source for an on-link peer; reachability is still untested**

**Explanation:** Route lookup is local and sends no probe. An on-link `/24` peer needs no next-hop router. The separate management default route can remain. Check neighbor discovery, peer/return-path behavior and application tests separately.

</details>

6. Pinging the client's own `192.0.2.10` succeeds, but its neighbor entry for `.20` becomes `FAILED`. What should you check first?
   - A) Install public DNS on the lab NIC
   - B) Treat self-ping as proof of the virtual cable
   - C) Flush the management route table
   - D) Both internal-network attachments, peer address, carrier and possible address conflicts

<details>
<summary>Show Answer</summary>

**Answer: D) Both internal-network attachments, peer address, carrier and possible address conflicts**

**Explanation:** A request to a local address is normally handled locally. It does not test the virtual link. A failed neighbor entry suggests next-hop MAC resolution did not succeed, so inspect link/address evidence before application DNS. `STALE`, in contrast, is not itself a failed mapping.

</details>

7. Traceroute prints `*`, but a client HTTP request to the same server succeeds. Which statement is justified?
   - A) The probe received no matching response in time; ordinary application forwarding may still work
   - B) The starred hop drops every packet
   - C) The HTTP result must be cached by traceroute
   - D) Every virtual switch must appear as an IP hop

<details>
<summary>Show Answer</summary>

**Answer: A) The probe received no matching response in time; ordinary application forwarding may still work**

**Explanation:** Probe protocols and control-response policies differ from application traffic. Filtering, response rate limiting and return paths can hide replies. An Ethernet switch does not decrement IP TTL as a router does. A star alone is not a measurement of application packet loss.

</details>

8. `nc -z` or `ncat -z` connects to port 18080, but no HTTP request has been made. What has passed?
   - A) DNS authority verification
   - B) HTTP authentication and page rendering
   - C) TCP connection establishment to that endpoint
   - D) A complete HTTPS certificate check

<details>
<summary>Show Answer</summary>

**Answer: C) TCP connection establishment to that endpoint**

**Explanation:** The zero-I/O connection probe does not send the intended HTTP request or validate its response. Follow it with curl to inspect status, headers and body. Even a successful TCP connection does not establish that the service speaks the expected protocol.

</details>

9. The server's self-request returns 200, its listener is bound to `.20:18080`, and the client's TCP request times out. What is the best report?
   - A) End-to-end HTTP is fully working
   - B) The local service works; remote routing, neighbor/return-path evidence and host policy still need investigation
   - C) DNS must be broken even though the client used a numeric address
   - D) Disable the server firewall globally

<details>
<summary>Show Answer</summary>

**Answer: B) The local service works; remote routing, neighbor/return-path evidence and host policy still need investigation**

**Explanation:** A server self-request cannot prove client access. A firewall is one candidate, not a conclusion from a timeout alone. Preserve the evidence for chapter 06's scoped policy work. Do not substitute local success for a blocked remote test or bypass the firewall to force success.

</details>

10. Curl returns HTTP 404 for `/missing-page` and exits 0. What does this mean?
   - A) No TCP connection existed
   - B) The server name has no DNS record
   - C) Curl necessarily ignored the server response
   - D) HTTP returned a missing-resource response; without `--fail`, curl can still exit successfully

<details>
<summary>Show Answer</summary>

**Answer: D) HTTP returned a missing-resource response; without `--fail`, curl can still exit successfully**

**Explanation:** Transport worked sufficiently to exchange HTTP, while the requested resource was absent. Read the HTTP status line and investigate the path/application. Do not change DNS to repair this deliberate application-level failure.

</details>

11. Numeric HTTP succeeds, named HTTP fails, and adding `--resolve server.netlab.test:18080:192.0.2.20` makes the named request succeed. What is the next step?
   - A) Inspect ordinary name lookup with getent/NSS; the override affected only that curl invocation
   - B) Delete the permanent route to `.20`
   - C) Assume the public DNS zone was updated by curl
   - D) Disable TLS verification everywhere

<details>
<summary>Show Answer</summary>

**Answer: A) Inspect ordinary name lookup with getent/NSS; the override affected only that curl invocation**

**Explanation:** The override preserves the hostname in the request while supplying the known address to curl. It changes no hosts file or DNS record and needs no rollback. For HTTPS, hostname/SNI/certificate behavior also matters; this HTTP exercise is not a reason to bypass certificate validation.

</details>

12. Which completion/cleanup statement is correct?
   - A) Public DNS must succeed before the isolated lab can pass
   - B) Remove every file under `/tmp` and reset the entire hosts file
   - C) Stop the owned server, remove its exact file/directory and marked hosts entries, preserve the static lab addresses, and treat public DNS as optional
   - D) Change the management NIC to public DNS so all observations match

<details>
<summary>Show Answer</summary>

**Answer: C) Stop the owned server, remove its exact file/directory and marked hosts entries, preserve the static lab addresses, and treat public DNS as optional**

**Explanation:** Cleanup follows ownership: the foreground server has a five-minute limit, its temporary directory was recorded, and the hosts block is marked. Preserve unrelated edits and chapter 03's addresses for SSH. Public queries depend on existing external access/policy and are not evidence about the isolated peer path.

</details>

---

[Back to the lesson](../../../networking/beginner/04-dns-connectivity.md) · [Next lesson: SSH access](../../../networking/beginner/05-ssh-access.md)
