# 04. DNS and Connectivity Diagnosis

> **Supported Versions**: Ubuntu Server 24.04 LTS (primary), Rocky Linux 9 (alternative)
> **Last Updated**: September 15, 2026

“The server is unreachable” can mean that a name did not resolve, a packet took the wrong route, a firewall rejected a connection, or an application returned an error. Each test below answers one smaller question. Record the result and its limits before choosing the next test.

## Prerequisites and outcomes

Complete [persistent configuration](03-persistent-configuration.md). The [course lab](README.md) has a client at `192.0.2.10/24` and server at `192.0.2.20/24` on the same internal virtual network. It has **no DHCP, gateway, DNS server or uplink**. Each guest's separate NAT/DHCP management NIC remains unchanged.

Use guest consoles and identify lab NICs by matching their hypervisor MACs to `ip -br link`. The primary lesson runs without public DNS or Internet access. The separately marked public-query exercise is optional.

| Tools already prepared in the guests | Purpose |
|---|---|
| `ip`, `ping`, `getent`, `grep`, `timeout`, editor and sudo | Local configuration, names and bounded probes |
| `dig` | Inspect DNS protocol responses; supplied by BIND utilities |
| `tracepath` and/or Linux `traceroute` | Observe responses to hop-limited probes |
| `python3` (3.9+), `curl`, `ss` | Serve a disposable page and observe HTTP/listening sockets |
| Ubuntu OpenBSD `nc`, or Rocky `ncat` | Make one TCP connection test |
| `resolvectl` where systemd-resolved is active | Inspect that resolver; not a requirement on Rocky |

Check availability with `command -v ip ping getent timeout dig tracepath traceroute python3 curl ss nc ncat`. Missing optional alternatives are normal; a missing tool needed for your selected exercise means return to preparation. This chapter contains no package-install commands.

You will distinguish NSS lookup from DNS, explain authoritative answers and caching, inspect the selected route, interpret ICMP and trace results, separate TCP from HTTP, and write a failure report with a justified next step.

## 1. Names, DNS and the operating system

DNS is a distributed database. An **A** record contains an IPv4 address; **AAAA** contains IPv6; **CNAME** points an alias at another name; **PTR** is used for reverse lookup. None of these records proves that the destination application is running.

A **recursive resolver** seeks an answer for its client, using cached information or querying other DNS servers. An **authoritative server** holds a zone's published data. A cache can reuse positive and negative answers for their permitted lifetime. DNS **TTL** is measured in seconds; IP TTL is a hop limit and is unrelated. Reducing a DNS TTL now does not instantly remove copies already cached with an earlier TTL. See [DNS concepts](https://www.rfc-editor.org/rfc/rfc1034.html) and [negative caching](https://www.rfc-editor.org/rfc/rfc2308.html).

Linux applications may ask the C library for a name through **NSS**, the Name Service Switch. NSS selects sources using `/etc/nsswitch.conf`: `files` reads `/etc/hosts`; `dns` uses DNS; `resolve` talks to systemd-resolved if installed/configured. Other modules and bracketed return rules can change the search path. Applications with their own resolvers, such as a browser using DNS over HTTPS, may behave differently.

| Tool | Question it answers |
|---|---|
| `getent ahostsv4 NAME` | What IPv4 addresses does this system's NSS/getaddrinfo path return? |
| `getent hosts NAME` | What does the NSS hosts lookup return? Its address-family behavior differs from `ahostsv4` |
| `getent -s files hosts NAME` | Does the files source alone contain this name? |
| `dig @SERVER NAME A` | What DNS response does that server return? It does not use NSS to look up the queried name |
| `resolvectl query NAME` | What does systemd-resolved return through its own resolver interface? |

On the **client**, inspect without editing:

```bash
grep '^hosts:' /etc/nsswitch.conf
cat /etc/hosts
ls -l /etc/resolv.conf
cat /etc/resolv.conf
systemctl is-active systemd-resolved
```

For example, `hosts: files dns` tries the hosts file before DNS. Do not replace your real line with this example. `/etc/resolv.conf` may be a symlink to a generated stub file, a generated upstream list, or a differently managed file. A `nameserver 127.0.0.53` entry identifies a local loopback stub, not your router.

On an **Ubuntu client with active systemd-resolved**:

```bash
resolvectl status
resolvectl statistics
```

Inspect per-link DNS servers/search domains and the cache statistics. The course lab NIC should not supply DNS; management DNS may still appear. On a **Rocky client managed by NetworkManager**, use `nmcli -f GENERAL,IP4,IP6 device show` and the resolver-file inspection above. Do not install resolved or rewrite the symlink just to match Ubuntu's layout. Any durable correction belongs in the confirmed owner from chapter 03.

## 2. Give the two VMs local names

On the **client**, use `/etc/hosts` so the local lab needs no external resolver. These names are local aliases; they do not rename the guests, create DNS records, or configure the server remotely. `.test` is reserved for testing; avoid using `.local`, which has special multicast-DNS behavior.

First check for conflicts:

```bash
grep -nE 'netlab\.test|BEGIN network-beginner-04|END network-beginner-04' /etc/hosts
```

No output with exit status 1 is the expected first-run result. If any entries exist, inspect them before continuing; do not append duplicate mappings. Create a new recovery directory and backup:

```bash
sudo mkdir -m 700 /root/network-beginner-04
sudo cp -a /etc/hosts /root/network-beginner-04/hosts-before
sudoedit /etc/hosts
```

If the directory already exists, stop and inspect the earlier attempt. Add only this block at the end; preserve all existing localhost and guest-hostname entries:

```text
# BEGIN network-beginner-04
192.0.2.10 client.netlab.test
192.0.2.20 server.netlab.test
# END network-beginner-04
```

Now compare files-only lookup and normal application lookup:

```bash
getent -s files hosts server.netlab.test
timeout 5s getent ahostsv4 server.netlab.test
timeout 5s getent hosts server.netlab.test
```

The first two should include `192.0.2.20`. `ahostsv4` may repeat it for `STREAM`, `DGRAM` and `RAW`; these describe socket types, not three servers. `hosts` may make an IPv6 lookup before IPv4 and can take a different path or longer. A timeout (status 124) is a bounded observation, not proof that DNS says the name does not exist.

If files-only succeeds but normal lookup fails, inspect the NSS order/modules and compare the exact spelling/address family. Do not change the route to repair a name lookup. The server needs its own hosts entries only if it will use these names itself; repeating this section there requires its own backup.

### Compare with dig without an external dependency

On the **Ubuntu client**, after the hosts entry works and resolved is active:

```bash
resolvectl --network=no -4 query server.netlab.test
dig -r @127.0.0.53 server.netlab.test. A +time=2 +tries=1
```

`--network=no` prevents resolved from asking the network, making a local source/cache sufficient or returning a local failure. `dig -r` skips personal `.digrc` settings, `@127.0.0.53` selects the stub, the final dot makes the DNS name absolute, and the options bound waiting/retries. A normal resolved setup reads `/etc/hosts` and can return `.20` to **both** commands. Dig still sent a DNS query; the stub synthesized the answer from local data. Thus “dig never returns hosts-file entries” would be misleading.

If the stub is disabled or resolved's hosts-file reading is disabled, that branch need not succeed. Inspect the current resolver setup rather than enabling a service. On **either distribution**, contrast hosts lookup with a DNS query to the lab server:

```bash
dig -r @192.0.2.20 server.netlab.test. A +time=2 +tries=1
```

This is an **intentional failure probe**: the course server runs no DNS service, so expect refusal or timeout, not an answer. A hosts entry on the client does not make the server a DNS server. An unexpected answer requires inspecting what is listening on the server's port 53. Keep normal applications using the hosts mapping; do not point system DNS at `.20`.

Without `@SERVER`, dig reads `/etc/resolv.conf`, so an apparently local test could ask the management network's upstream resolver. The commands above select their target explicitly.

### Reading a DNS response

The following is an **illustrative response from a hypothetical authoritative lab DNS service**, not captured output or a service created in this lesson:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1234
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; ANSWER SECTION:
server.netlab.test. 300 IN A 192.0.2.20
;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)
```

| Field/status | Interpretation |
|---|---|
| `SERVER` | The server that answered this query, not necessarily the authoritative origin |
| `300 IN A 192.0.2.20` | TTL seconds, Internet class, IPv4 type and address |
| `aa` | Answer marked authoritative for the relevant queried name; not a connectivity or identity guarantee |
| `rd` / `ra` when present | Recursion requested / recursion available; neither proves a fresh upstream lookup |
| `NOERROR` and expected answer | DNS query succeeded; check the data itself |
| `NOERROR` with no requested data | May be NODATA; inspect Authority/CNAME/referral context before concluding |
| `NXDOMAIN` | DNS response says the queried name does not exist; can also come from cache/policy |
| `SERVFAIL` | Resolver failed, for example due to upstream or validation problems |
| `REFUSED` | Server policy refused the query |
| Timeout | No usable response in the waiting period; not NXDOMAIN |

`dig +short` hides useful status and server information, so use full output while diagnosing. Dig can exit 0 after receiving an `NXDOMAIN` response; exit status alone does not mean an address was found.

Caching can occur in an application, a local service and an upstream recursive resolver. A fast second lookup alone does not prove a cache hit. On resolved, compare `resolvectl statistics`; hosts-derived answers need not behave like cached DNS records. `sudo resolvectl flush-caches` clears resolved's local DNS cache, not `/etc/hosts`, application caches or upstream caches. It changes ephemeral state that repopulates through queries and has no meaningful “restore cache” operation. It is not needed for this lab; record evidence before considering it in a separate cache investigation.

## 3. Inspect the selected route, then probe IP

On the **client**, match the lab MAC again and substitute the name:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -br link
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
```

An illustrative route result is:

```text
192.0.2.20 dev LAB_NIC src 192.0.2.10 uid 1000
```

`dev` selects the output interface, `src` the chosen source address, and `via` would name a next-hop router. Here the peer is on-link, so no `via` is needed. `LAB_NIC` is an explanatory label, not a literal device name. `ip route get` performs a local route lookup; it sends no ping and proves neither peer availability nor a working return path.

If lookup selects the management NIC, stop the peer probes and inspect the lab address/prefix and saved configuration. Do not delete the management default route. On the **server**, `ip -4 route get 192.0.2.10` should select its lab NIC with source `.20`; replies need a valid return path too.

On the **client**, compare loopback, its own address and the peer:

```bash
ping -n -c 3 -W 2 127.0.0.1
ping -n -c 3 -W 2 192.0.2.10
ping -n -c 3 -W 2 192.0.2.20
```

`-n` suppresses reverse name lookup, `-c 3` sends three Echo Requests, and `-W 2` bounds response waiting when no replies arrive. A numeric destination removes forward-name lookup from this test. `time` is round-trip time, not bandwidth. The printed reply `ttl` is the received packet's remaining TTL; without knowing its initial value it is not an exact hop count.

Loopback success tests the local stack. Pinging your own lab address is normally handled locally and does not test the virtual cable. Peer replies show bidirectional ICMP Echo exchange at that moment, not TCP-port access. Three missing replies are evidence about three probes; filtering, response rate limits, wrong addressing and return-path failures need investigation.

After the peer probe, inspect the **client's** neighbor entry:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip neigh show to 192.0.2.20 dev "$LAB_IF"
```

A MAC with `REACHABLE` or `STALE` indicates a known neighbor mapping; `STALE` is not a failure. `INCOMPLETE`/`FAILED` suggests ARP resolution has not succeeded. Check both adapters' internal-network attachment, peer address, carrier and duplicate-IP possibility. DNS does not supply the Ethernet destination MAC.

## 4. Read traceroute and tracepath carefully

On the **client**, run whichever tools were prepared:

```bash
traceroute -4 -n -m 4 -q 1 -w 1 192.0.2.20
timeout 15s tracepath -4 -n -m 4 192.0.2.20
```

Linux traceroute normally uses UDP probes. `-m 4` limits the maximum TTL, `-q 1` uses one probe per TTL, and `-w 1` limits waiting per probe. Tracepath uses UDP and also reports path-MTU information; the outer `timeout` bounds its total run. With a direct peer and permitted replies, expect the destination at TTL 1. A virtual Ethernet switch is not an IP router and does not add a traceroute hop.

Routers can return ICMP Time Exceeded when a probe's TTL expires. A destination can return ICMP Port Unreachable for a probe to a closed UDP port. These control responses reveal parts of a path; they are not a recording of every packet's route.

A traceroute `*` or tracepath `no reply` means no matching response arrived before the timeout. It does **not** prove that this hop dropped ordinary application traffic. Filtering, rate limiting, different probe protocols and asymmetric return paths can explain missing replies. Later hops or the application can still respond.

For an optional **ICMP comparison** to the same peer, if the installed Linux traceroute supports it:

```bash
sudo traceroute -4 -I -n -m 4 -q 1 -w 1 192.0.2.20
```

`-I` uses ICMP Echo probes; sudo permits raw probes where needed. Different results can reflect protocol-specific policy. These commands change no persistent configuration. Do not disable a firewall to make the trace display prettier.

## 5. Distinguish TCP from HTTP with one local service

There is no assumption that SSH or a web server is already installed. We create a temporary HTTP service with existing Python, bound only to the **server lab address**.

### Start a bounded service on the server

In **server terminal A**, confirm `.20` belongs to the lab NIC and that no existing TCP listener uses port 18080:

```bash
ip -br address
ss -ltn 'sport = :18080'
```

If a listener exists, identify it; do not kill another service. Select a free port and consistently adapt this section, or finish that earlier lab first.

In the same **server terminal A**, create a fresh directory and serve it as the ordinary user:

```bash
LAB_HTTP_DIR=$(mktemp -d /tmp/network-beginner-04.XXXXXX)
printf '%s\n' "$LAB_HTTP_DIR"
printf 'network lab ok\n' > "${LAB_HTTP_DIR:?missing lab directory}/index.html"
timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"
```

Stop if `mktemp` fails. `${variable:?message}` prevents use of an empty path variable. Record the printed directory path. Only the new directory contains the served file; do not serve your home directory or add symlinks to it. `--bind` avoids a wildcard listener, `--directory` selects the content root, and `timeout` terminates the server after five minutes. Ctrl+C stops it earlier. A timeout exit status of 124 is expected when the time limit ends.

Python's built-in HTTP server is an exercise tool. It has no authentication/TLS here and is not a production deployment. No system service or boot activation is created.

In **server terminal B**, while A is running:

```bash
ss -ltn 'sport = :18080'
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
```

Expect a listener at `192.0.2.20:18080`, HTTP 200 and `network lab ok`. HTTP/1.0 in the response is normal for this Python server, including Rocky's Python 3.9 path. This self-request validates local application behavior, not the path from the client. If binding says “Cannot assign requested address”, inspect the server's address from chapter 03. If it reports a permission denial, inspect that failure instead of disabling SELinux.

### Test TCP from the client

On the **Ubuntu client with OpenBSD netcat**:

```bash
nc -n -z -v -w 3 192.0.2.20 18080
```

On the **Rocky client with Ncat**, the equivalent is:

```bash
ncat -n -z -v -w 3 192.0.2.20 18080
```

`-n` avoids DNS, `-z` tests connection establishment without an application payload, `-v` reports the result and `-w 3` limits connection waiting. Success proves a TCP connection could be made to that endpoint, not that HTTP works. Refusal usually means a closed port or an active rejection; timeout can mean filtering, unresolved neighbors, a down peer or a return-path problem.

A guest firewall, particularly a configured Rocky firewalld policy, can block this new port. Compare the server's listener/self-request with client route/neighbor/TCP evidence and record a **candidate policy boundary**. This chapter does not alter firewall rules; [chapter 06](06-firewalls-host-security.md) teaches scoped policy changes. If the remote test is blocked, complete the HTTP observations in server terminal B and retain the client failure for that later lesson. Do not report remote HTTP success from the server's self-request.

### Test HTTP, then compare names

On the **client**, while the service is alive:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://server.netlab.test:18080/
```

The first option, `--disable`, skips default curl configuration; `--noproxy '*'` avoids an inherited HTTP proxy. `--connect-timeout` bounds connection setup, `--max-time` the whole operation, and `-i` includes response headers. The second command uses the client's name lookup. If the numeric URL works but the named one fails, compare `getent ahostsv4` and curl's error before touching routes.

To isolate lookup for this **single curl invocation**, keep the hostname but supply the known lab address:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve server.netlab.test:18080:192.0.2.20 \
  -i http://server.netlab.test:18080/
```

`--resolve` changes only curl's mapping for that hostname/port; no hosts file or DNS record is changed, and it needs no rollback. The HTTP Host header still uses the name. For real HTTPS, name-based certificate checks and TLS SNI also matter; replacing a hostname with an IP is not always an equivalent application test. Do not bypass certificate checks to label TLS “fixed”.

Create a harmless application-level failure by requesting a file that was never created:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/missing-page
```

Expect HTTP **404** if the server is reachable. The name/IP path and TCP transport worked sufficiently to return an HTTP error; the requested page is absent. Without `--fail`, curl can exit 0 for an HTTP 404, so read the status line. `curl -I` would send **HEAD**, not GET with its body merely hidden.

## 6. Choose the next test from evidence

Use this decision table in order, but return to an earlier row when new evidence contradicts an assumption. Examples describe candidates, not automatic diagnoses.

| Observation | What is established | Next discriminating check |
|---|---|---|
| Files-only lookup lacks `.20` | Local mapping missing/wrong | Exact spelling, `/etc/hosts` block and duplicate entries |
| Files-only works; normal getent fails | Sources behave differently | NSS order/return rules, modules and address family |
| getent works; dig to `.20` fails | Local naming works; no expected DNS service at `.20` | Use the hosts entry; inspect real resolver only if DNS is required |
| DNS `NXDOMAIN` | A negative DNS response arrived | Query spelling, resolver/view, authoritative data and negative cache |
| DNS timeout | No usable DNS answer within the limit | `ip route get` to resolver, port 53 reachability, resolver service/policy |
| Route selects management NIC or wrong source | Local forwarding choice is wrong for this lab | Lab address/prefix, persistent owner, route/rule inventory |
| Correct route; neighbor `FAILED` | Next-hop MAC resolution failed | Hypervisor network/cable, peer address, link state and conflicts |
| Neighbor exists; ping fails | MAC known, ICMP reply absent | Server return route, ICMP policy, then intended TCP port |
| Ping works; TCP refused | ICMP works; TCP actively rejected | Server `ss`, service lifetime/bind address, rejection policy |
| Server self-HTTP works; client TCP times out | Local service works; remote path unproven | Both routes, neighbors and host policy; record evidence for chapter 06 |
| TCP connects; HTTP stalls or is invalid | Connection establishment works | Right protocol/port, application logs and response behavior |
| HTTP 404/403/500 | HTTP endpoint returned an application result | Requested path, application permissions or service error; not a DNS fix |
| Numeric HTTP works; named HTTP fails | Known endpoint works without ordinary lookup | getent result, curl resolution error, per-request `--resolve` comparison |
| Traceroute has `*`; HTTP works | Those probes lacked replies; application succeeded | Probe protocol/rate limits; no basis to declare total packet loss |

Useful curl exit codes include **6** (could not resolve host), **7** (could not connect), and **28** (operation timed out). They locate a stage, not necessarily a root cause. Record the command, execution VM, timestamp (`date -Is`), destination, output, exit status (`echo $?` immediately afterward), expected result, and the next test. Separate “observed” from “suspected”.

## 7. Optional public DNS observation

**External dependency:** run only if the client's existing, unchanged management network already provides permitted Internet access and permits queries to the selected resolver. This is not a completion requirement, and failure says nothing by itself about the isolated `.10` ↔ `.20` lab. Do not add an uplink or public DNS server to the lab NIC.

```bash
ip -4 route get 1.1.1.1
dig -r @1.1.1.1 example.com. A +time=2 +tries=1
dig -r @1.1.1.1 example.com. AAAA +time=2 +tries=1
dig -r @1.1.1.1 example.com. NS +time=2 +tries=1
```

Inspect the route before sending the queries; it should use the preexisting management path. If policy requires a different approved resolver, substitute its known address consistently. Observe the DNS status, server, record types and TTL without expecting fixed public IPs. Repeat the A query once and compare TTL, but do not infer cache location from timing alone. `+tcp` optionally compares DNS over TCP to the usual UDP A query. Do not query private/internal names through public resolvers.

An NS answer identifies authority information; a recursive answer from `1.1.1.1` is not thereby an authoritative response from the zone. `dig +trace` follows DNS delegations, not IP router hops like traceroute, and adds external dependencies; it is outside this local exercise.

## 8. Cleanup and completion

In **server terminal A**, stop the Python process with Ctrl+C or let its timer expire. In terminal B, verify that this lesson's listener is gone with `ss -ltn 'sport = :18080'`.

In the **same terminal A shell that created the directory**, inspect and remove only its file and empty directory:

```bash
printf '%s\n' "$LAB_HTTP_DIR"
ls -la -- "${LAB_HTTP_DIR:?missing lab directory}"
rm -i -- "${LAB_HTTP_DIR:?missing lab directory}/index.html"
rmdir -- "${LAB_HTTP_DIR:?missing lab directory}"
unset LAB_HTTP_DIR
```

If that shell was closed, set `LAB_HTTP_DIR` to the exact path you recorded and verify its contents before this block. Never guess it with a broad wildcard. `rmdir` refuses a nonempty directory, helping expose unexpected files.

On each guest where you edited `/etc/hosts`, use `sudoedit /etc/hosts` to remove only the lines between `# BEGIN network-beginner-04` and `# END network-beginner-04`, including the two marker lines. Compare with `sudo diff -u /root/network-beginner-04/hosts-before /etc/hosts`; no output means the original contents are restored when no unrelated edits occurred. Preserve any legitimate intervening edits instead of overwriting them with the backup.

Verify `getent -s files hosts server.netlab.test` no longer returns the lesson mapping. Do not demand that every resolver forget the name instantly. The chapter 03 static addresses and management settings stay in place for SSH.

Before continuing, you should be able to:

- Explain getent/NSS, dig and resolved using the actual sources on your guest.
- Resolve `.20` locally without public DNS and explain the intentional dig failure.
- Interpret a DNS response, including TTL, authoritative status and negative results.
- Show the selected lab route/source and distinguish loopback, neighbor and peer evidence.
- Explain why trace stars do not establish application packet loss.
- Compare a TCP test, HTTP 200 and HTTP 404, identifying which VM produced each result.
- Classify any blocked remote test with evidence and a next check; do not substitute local success.
- Remove the temporary server, its files and hosts entries without changing network/firewall settings.

## Primary sources and further reading

- [Ubuntu Server: names and NSS](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/), [getent manual](https://manpages.ubuntu.com/manpages/noble/en/man1/getent.1.html)
- [BIND dig manual](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility), [resolvectl on Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/en/man1/resolvectl.1.html)
- [DNS concepts: RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html), [negative caching: RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html), [test names: RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)
- [ping](https://manpages.ubuntu.com/manpages/noble/en/man8/ping.8.html), [tracepath](https://manpages.ubuntu.com/manpages/noble/en/man8/tracepath.8.html), [Linux traceroute manual shipped by Ubuntu](https://manpages.ubuntu.com/manpages/noble/en/man1/traceroute.db.1.html)
- [OpenBSD nc](https://man.openbsd.org/nc), [Ncat](https://nmap.org/book/ncat-man.html), [curl manual](https://curl.se/docs/manpage.html), [Python HTTP server](https://docs.python.org/3.12/library/http.server.html)
- Continue later with [Linux network diagnostics](../07-linux-network-diagnostics.md) for packet, TCP queue and MTU interpretation.

[Previous: persistent configuration](03-persistent-configuration.md) · [Quiz](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) · [Next: SSH access](05-ssh-access.md)
