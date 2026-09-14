# Network foundations examples

These examples connect HTTP message structure to Linux sockets, routing and
packet observations. They support the [English guide](../../../en/networking/07-linux-network-diagnostics.md)
and [한국어 가이드](../../../ko/networking/07-linux-network-diagnostics.md).

## HTTP messages on loopback

Python 3.9 or newer is sufficient; no extra package or cloud account is needed.
From the repository root, run this in one terminal:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

In another terminal:

```bash
curl --disable --noproxy '*' --http1.1 --max-time 5 -i \
  http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --http1.1 --max-time 5 -I \
  http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --http1.1 --max-time 5 -i \
  --data-binary 'topic=network' http://127.0.0.1:18080/echo
```

`GET /lesson` returns the six bytes `hello\n`; HEAD supplies the corresponding
length without response content. POST echoes at most 4096 bytes with
`application/octet-stream`. Its response media type need not match the request's.
The server counts **bytes**, including the newline, rather than characters.
Responses use Content-Length so another request can reuse the TCP connection.

The listener is fixed to `127.0.0.1`. Port 0 selects an available port and prints
it; an occupied requested port produces an error. The process stops after the
chosen duration (at most 600 seconds) or Ctrl+C. It serves no files and does not
log request content. This is a small educational HTTP/1.1 implementation, not a
TLS service, proxy, complete RFC implementation, or production server.

## Routing, ICMP and PMTU

Use a Linux lab host with a local Docker Engine at `/var/run/docker.sock`,
permission to use that socket, and the host `ip` command. The script selects that
Unix socket explicitly and does not inherit a remote `DOCKER_HOST` or
`DOCKER_CONTEXT`.

Pull the immutable multi-architecture Netshoot image before running the lab:

```bash
docker --host unix:///var/run/docker.sock pull \
  nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
NETWORK_LAB_OUTPUT=$(mktemp -d /tmp/network-lesson.XXXXXX)
python3 examples/networking/foundations/routing_lab.py \
  --output "$NETWORK_LAB_OUTPUT/routing.json"
```

The topology is:

```text
client                  router                         server
192.0.2.2/29 --- 192.0.2.3/29 | 198.51.100.2/29 --- 198.51.100.3/29
       left bridge          |              right bridge
```

The prefixes are RFC 5737 documentation ranges, used here only in temporary
local networks. The script checks all IPv4 routing tables and rejects overlapping non-default host routes and
existing Docker IPAM ranges before creating resources. It creates two dedicated
bridges with IP masquerading disabled, then removes default IPv4 routes inside
the three containers and installs only the lesson routes. Docker manages the
temporary host bridges and associated rules as usual; the script does not edit
host routes, MTU, sysctls or firewall rules directly.

These are **not Docker `--internal` networks**: internal-network filtering can
prevent the cross-subnet forwarded traffic this exercise needs. The lesson's
containers have no published ports, no default IPv4 route, and no host-network
mode. This routing arrangement is a lab scope, not proof of an air gap or a
production security boundary.

Containers are limited to 128 MiB, 0.5 CPU and 64 PIDs. They run with
`NET_ADMIN`/`NET_RAW`, all other capabilities dropped, and no-new-privileges.
They do not receive a Docker socket or host-directory mount. The router's IP
forwarding sysctl and egress MTU change apply to its own network namespace.

The recorded checks cover:

1. `ip route get` selects the router as the next hop.
2. Docker's embedded DNS resolves the router name; this is not public DNS recursion.
3. The client's ARP/neighbor entry belongs to the next hop, not the remote server.
4. A TTL-1 probe generates an actual captured ICMP Time Exceeded message.
5. ICMP traceroute reaches the router and then the destination.
6. Lowering the router's outgoing MTU to 1280 produces captured IPv4
   Fragmentation Needed feedback for a 1400-byte DF packet.
7. A 1228-byte IP packet still succeeds; the sender's route lookup exposes
   the learned PMTU in the tested environment.

The ping sizes above include 20 bytes of IPv4 and 8 bytes of ICMP headers.
They do not measure TCP MSS. Timing, learned-route formatting, MAC addresses
and other output details depend on the host and tools.

Returned container/network **IDs** are recorded and removed on normal completion,
failure or handled interruption. A failed container start is still cleaned up.
Cleanup errors cause failure instead of a success report. Docker API failure or
abrupt host/process loss can still prevent complete cleanup: inspect resources bearing the
`org.atomoh.network-lesson` label and the run's recorded prefix; never use a
global prune as this lesson's cleanup procedure.

## Validation

Run the loopback HTTP and resource-ownership tests without Docker or root:

```bash
python3 -B -m unittest discover \
  -s examples/networking/foundations -p 'test_*.py' -v
```

These tests run in PR and Pages validation. The real Docker/packet-capture
experiment is a separate invocation of `routing_lab.py`; its measured
[September 14, 2026 result](results/2026-09-14.json) is retained with script hashes.
It is functional evidence for that local environment, not an AWS, Kubernetes,
throughput, latency or general compatibility benchmark.
