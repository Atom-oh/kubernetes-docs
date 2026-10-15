#!/usr/bin/env python3
"""Observe IPv4 routing, ICMP and PMTU in temporary Docker bridge networks."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import uuid

IMAGE = "nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70"
SOCKET = "unix:///var/run/docker.sock"
LEFT = "192.0.2.0/29"
RIGHT = "198.51.100.0/29"
CLIENT = "192.0.2.2"
ROUTER_LEFT = "192.0.2.3"
ROUTER_RIGHT = "198.51.100.2"
SERVER = "198.51.100.3"


class LabError(RuntimeError):
    pass


class Docker:
    def __init__(self):
        self.env = os.environ.copy()
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
            self.env.pop(key, None)
        self.history = []

    def argv(self, args):
        return ["docker", "--host", SOCKET, *args]

    def call(self, *args, check=True, record=True):
        entry = {"args": list(args), "exitCode": None}
        if record:
            self.history.append(entry)
        try:
            result = subprocess.run(self.argv(args), env=self.env, capture_output=True,
                                    text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as error:
            entry["error"] = str(error)
            raise
        entry.update({"exitCode": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr})
        if check and result.returncode:
            detail = (result.stderr.strip() or result.stdout.strip())[-2000:]
            raise LabError(f"Docker {args[0]} failed ({result.returncode}): {detail}")
        return result

    def execute(self, container, *args, check=True):
        return self.call("exec", "--env", "LC_ALL=C", container, *args, check=check)


class Resources:
    """Track returned IDs, so cleanup cannot remove an unrelated named object."""
    def __init__(self, docker):
        self.docker = docker
        self.containers = []
        self.networks = []
        self.cleanup_errors = []

    def network(self, name, subnet, label):
        result = self.docker.call(
            "network", "create", "--subnet", subnet,
            "--opt", "com.docker.network.bridge.enable_ip_masquerade=false",
            "--label", label, name)
        identifier = result.stdout.strip()
        self.networks.append(identifier)
        return identifier

    def container(self, name, network, address, label, forward=False):
        args = ["create", "--name", name, "--network", network, "--ip", address,
                "--label", label, "--memory", "128m", "--cpus", "0.5",
                "--pids-limit", "64", "--cap-drop", "ALL",
                "--cap-add", "NET_ADMIN", "--cap-add", "NET_RAW",
                "--security-opt", "no-new-privileges"]
        if forward:
            args += ["--sysctl", "net.ipv4.ip_forward=1"]
        args += [IMAGE, "sleep", "300"]
        identifier = self.docker.call(*args).stdout.strip()
        # Record before start: a failed start must still clean up the created ID.
        self.containers.append(identifier)
        self.docker.call("start", identifier)
        return identifier

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        for kind, identifiers in (("container", self.containers), ("network", self.networks)):
            for identifier in reversed(identifiers):
                try:
                    args = ("rm", "--force", identifier) if kind == "container" else (
                        "network", "rm", identifier)
                    result = self.docker.call(*args, check=False)
                    if result.returncode:
                        self.cleanup_errors.append(f"{kind} {identifier}: {result.stderr.strip()}")
                except (OSError, subprocess.SubprocessError) as error:
                    self.cleanup_errors.append(f"{kind} {identifier}: {error}")
        if self.cleanup_errors:
            raise LabError("Cleanup incomplete: " + "; ".join(self.cleanup_errors)) from exc


def check_subnets(routes, docker_networks):
    reserved = [ipaddress.ip_network(LEFT), ipaddress.ip_network(RIGHT)]
    occupied = []
    for route in routes:
        prefix = route.get("dst")
        if prefix and prefix != "default":
            occupied.append(ipaddress.ip_network(prefix, strict=False))
    for network in docker_networks:
        for config in network.get("IPAM", {}).get("Config", []) or []:
            if config.get("Subnet"):
                occupied.append(ipaddress.ip_network(config["Subnet"], strict=False))
    for candidate in reserved:
        for existing in occupied:
            if candidate.version == existing.version and candidate.overlaps(existing):
                raise LabError(f"Lesson subnet {candidate} overlaps existing route/network {existing}")


def preflight(docker):
    if sys.platform != "linux" or not Path("/var/run/docker.sock").exists():
        raise LabError("Use a Linux lab host with a local Docker Engine Unix socket")
    if docker.call("info", "--format", "{{.OSType}}").stdout.strip() != "linux":
        raise LabError("This lesson requires Linux containers")
    if docker.call("image", "inspect", IMAGE, check=False).returncode:
        raise LabError(f"Pull the pinned image first: docker --host {SOCKET} pull {IMAGE}")
    routes = json.loads(subprocess.check_output(
        ["ip", "-j", "-4", "route", "show", "table", "all"], text=True))
    identifiers = docker.call("network", "ls", "--quiet", record=False).stdout.split()
    networks = json.loads(docker.call("network", "inspect", *identifiers,
                                      record=False).stdout) if identifiers else []
    check_subnets(routes, networks)


def capture_probe(docker, router, capture_filter, probe):
    args = ["exec", "--env", "LC_ALL=C", router, "timeout", "10", "tcpdump",
            "-l", "-nn", "-i", "any", "-c", "1", capture_filter]
    process = subprocess.Popen(docker.argv(args), env=docker.env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = threading.Event()
    errors = []

    def read_stderr():
        for line in process.stderr:
            errors.append(line)
            if "listening on" in line:
                ready.set()

    reader = threading.Thread(target=read_stderr, daemon=True)
    reader.start()
    try:
        if not ready.wait(timeout=5):
            raise LabError("Packet capture did not become ready: " + "".join(errors))
        observation = probe()
        process.wait(timeout=12)
        output = process.stdout.read()
        reader.join(timeout=2)
        if process.returncode:
            raise LabError("Expected ICMP message was not captured: " + "".join(errors))
        return {"probeExit": observation.returncode, "probeOutput": observation.stdout + observation.stderr,
                "capture": output, "captureStderr": "".join(errors)}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        reader.join(timeout=2)
        process.stdout.close()
        process.stderr.close()


def traceroute_reaches_expected_hops(output):
    """Validate numbered replies from this lab's fixed Linux -n -I -q 1 trace."""
    replies = {}
    for line in output.splitlines():
        if not re.match(r"^\s*[12]\s+", line):
            continue
        match = re.fullmatch(r"\s*([12])\s+(\S+)\s+\d+(?:\.\d+)?\s+ms\s*", line)
        # Timeout stars, unreachable annotations and duplicate rows are not a
        # clean reply. The heading and diagnostics never enter this map.
        if not match or int(match[1]) in replies:
            return False
        replies[int(match[1])] = match[2]
    return replies == {1: ROUTER_LEFT, 2: SERVER}


def run_lab(docker):
    preflight(docker)
    prefix = "network-lesson-" + uuid.uuid4().hex[:10]
    docker.run_prefix = prefix
    label = "org.atomoh.network-lesson=" + prefix
    result = {"image": IMAGE, "scope": "Temporary local IPv4 bridges; no masquerading, published ports, or container default routes",
              "prefix": prefix, "observations": {}}
    with Resources(docker) as resources:
        left = resources.network(prefix + "-left", LEFT, label)
        right = resources.network(prefix + "-right", RIGHT, label)
        client = resources.container(prefix + "-client", left, CLIENT, label)
        router_name = prefix + "-router"
        router = resources.container(router_name, left, ROUTER_LEFT, label, forward=True)
        server = resources.container(prefix + "-server", right, SERVER, label)
        docker.call("network", "connect", "--ip", ROUTER_RIGHT, right, router)
        defaults = {}
        for name, container in (("client", client), ("router", router), ("server", server)):
            # Inside this run's container only; retain its connected subnet routes.
            for _ in range(8):
                remaining = json.loads(docker.execute(container, "ip", "-j", "route", "show", "default").stdout)
                if not remaining:
                    break
                docker.execute(container, "ip", "route", "del", "default")
            defaults[name] = json.loads(docker.execute(container, "ip", "-j", "route", "show", "default").stdout)
            if defaults[name]:
                raise LabError(f"Could not remove {name}'s default routes")
        docker.execute(client, "ip", "route", "add", RIGHT, "via", ROUTER_LEFT)
        docker.execute(server, "ip", "route", "add", LEFT, "via", ROUTER_RIGHT)
        observations = result["observations"]
        observations["defaultRoutes"] = defaults
        observations["route"] = json.loads(docker.execute(client, "ip", "-j", "route", "get", SERVER).stdout)
        observations["dns"] = docker.execute(client, "dig", "+short", "+tries=1", "+time=1",
                                             router_name, "A").stdout
        docker.execute(client, "ping", "-n", "-c", "2", "-W", "1", SERVER)
        observations["nextHopNeighbor"] = json.loads(
            docker.execute(client, "ip", "-j", "neigh", "show", "to", ROUTER_LEFT).stdout)
        observations["remoteNeighbor"] = json.loads(
            docker.execute(client, "ip", "-j", "neigh", "show", "to", SERVER).stdout)
        observations["ttlOne"] = capture_probe(
            docker, router, "icmp[0] == 11",
            lambda: docker.execute(client, "ping", "-n", "-c", "1", "-W", "1",
                                   "-t", "1", SERVER, check=False))
        observations["traceroute"] = docker.execute(
            client, "traceroute", "-n", "-I", "-m", "4", "-q", "1", "-w", "1", SERVER).stdout
        destination_route = json.loads(docker.execute(router, "ip", "-j", "route", "get", SERVER).stdout)[0]
        device = destination_route["dev"]
        docker.execute(router, "ip", "link", "set", "dev", device, "mtu", "1280")
        observations["pmtu"] = capture_probe(
            docker, router, "icmp[0] == 3 and icmp[1] == 4",
            lambda: docker.execute(client, "ping", "-n", "-c", "1", "-W", "1",
                                   "-M", "do", "-s", "1372", SERVER, check=False))
        observations["smallerPacket"] = docker.execute(
            client, "ping", "-n", "-c", "1", "-W", "1", "-M", "do", "-s", "1200", SERVER).stdout
        observations["routeAfterFeedback"] = json.loads(
            docker.execute(client, "ip", "-j", "route", "get", SERVER).stdout)
        result["checks"] = {
            "noContainerDefaultRoutes": not any(defaults.values()),
            "routeUsesRouter": observations["route"][0].get("gateway") == ROUTER_LEFT,
            "dockerNameResolves": ROUTER_LEFT in observations["dns"].split(),
            "neighborIsNextHop": any(n.get("lladdr") for n in observations["nextHopNeighbor"]),
            "noRemoteL2Neighbor": not observations["remoteNeighbor"],
            "ttlOneExpires": observations["ttlOne"]["probeExit"] != 0 and
                "time exceeded" in observations["ttlOne"]["capture"].lower(),
            "tracerouteReachesBothHops": traceroute_reaches_expected_hops(observations["traceroute"]),
            "pmtuFeedback": observations["pmtu"]["probeExit"] != 0 and
                bool(re.search(r"(unreachable|fragmentation|need to frag)", observations["pmtu"]["capture"], re.I)),
        }
        if not all(result["checks"].values()):
            raise LabError("An observation did not meet its criterion: " + json.dumps(result["checks"]))
    result["cleanup"] = "All IDs created by this run were removed"
    result["status"] = "passed"
    result["commands"] = docker.history
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new JSON evidence file")
    args = parser.parse_args()
    output = None
    if args.output:
        output = os.fdopen(os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w")
    docker = Docker()
    exit_code = 0
    result = {"status": "failed", "error": "Lab did not complete"}
    try:
        result = run_lab(docker)
    except (LabError, OSError, ValueError, subprocess.SubprocessError) as error:
        result = {"status": "failed", "error": str(error),
                  "prefix": getattr(docker, "run_prefix", None), "commands": docker.history}
        exit_code = 1
    except KeyboardInterrupt:
        result = {"status": "interrupted", "prefix": getattr(docker, "run_prefix", None),
                  "commands": docker.history}
        exit_code = 130
    finally:
        if output:
            json.dump(result, output, indent=2)
            output.write("\n")
            output.close()
    print(json.dumps({k: v for k, v in result.items() if k != "commands"}, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
