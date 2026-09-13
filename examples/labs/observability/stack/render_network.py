"""Render private NLB endpoints and source-limited ingress policies."""

import argparse
import ipaddress
import os
import re
from pathlib import Path

import yaml


def render(source_cidr, security_group, output, nlb_source_cidrs):
    network = ipaddress.ip_network(source_cidr, strict=True)
    if network.version != 4 or not network.is_private or network.prefixlen < 16:
        raise ValueError("Use the actual private service-network IPv4 CIDR, /16 or narrower")
    if not re.fullmatch(r"sg-(?:[0-9a-f]{8}|[0-9a-f]{17})", security_group):
        raise ValueError("Supply the existing, reviewed NLB security group ID")
    if not nlb_source_cidrs:
        raise ValueError("Supply the actual NLB subnet CIDRs for TCP health checks")
    nlb_networks = [ipaddress.ip_network(cidr, strict=True) for cidr in nlb_source_cidrs]
    if any(n.version != 4 or not n.is_private or n.prefixlen < 16 for n in nlb_networks):
        raise ValueError("NLB source ranges must be private IPv4 CIDRs, /16 or narrower")
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    resources = []
    for role, name, port in [
        ("collector-management", "lab-collector-ingest", 4318),
        ("prometheus-management", "lab-prometheus-ingest", 9090),
    ]:
        resources.append({
            "apiVersion": "v1", "kind": "Service",
            "metadata": {
                "name": name, "namespace": "monitoring",
                "annotations": {
                    "service.beta.kubernetes.io/aws-load-balancer-scheme": "internal",
                    "service.beta.kubernetes.io/aws-load-balancer-nlb-target-type": "ip",
                    "service.beta.kubernetes.io/aws-load-balancer-security-groups": security_group,
                    "service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules": "true",
                    "service.beta.kubernetes.io/aws-load-balancer-target-group-attributes": "preserve_client_ip.enabled=true",
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol": "TCP",
                },
            },
            "spec": {
                "type": "LoadBalancer", "loadBalancerClass": "service.k8s.aws/nlb",
                "selector": {"lab-role": role},
                "ports": [{"name": "tls", "port": port, "targetPort": port, "protocol": "TCP"}],
            },
        })
        ingress = [{
            "from": [{"ipBlock": {"cidr": str(n)}} for n in [network, *nlb_networks]],
            "ports": [{"protocol": "TCP", "port": port}],
        }]
        if role == "prometheus-management":
            ingress.append({
                "from": [
                    {"podSelector": {"matchLabels": {"lab-role": allowed}}}
                    for allowed in ("prometheus-management", "tempo", "grafana")
                ],
                "ports": [{"protocol": "TCP", "port": 9090}],
            })
        resources.append({
            "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
            "metadata": {"name": name, "namespace": "monitoring"},
            "spec": {
                "podSelector": {"matchLabels": {"lab-role": role}},
                "policyTypes": ["Ingress"], "ingress": ingress,
            },
        })
    descriptor = os.open(output / "endpoints.yaml", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        yaml.safe_dump_all(resources, stream, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-source-cidr", required=True)
    parser.add_argument("--nlb-security-group", required=True)
    parser.add_argument("--nlb-source-cidr", action="append", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    render(
        args.service_source_cidr, args.nlb_security_group,
        args.output_directory, args.nlb_source_cidr,
    )
    print("Manifests written; no AWS or Kubernetes resources were changed.")


if __name__ == "__main__":
    main()
