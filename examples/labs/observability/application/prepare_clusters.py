"""Render two EKS configurations that reuse a reviewed private VPC."""

import argparse
import ipaddress
import json
import os
import re
from pathlib import Path


def generate(region, vpc_id, subnets, client_cidr, prefix, output):
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
        raise ValueError("Invalid AWS Region")
    if not re.fullmatch(r"vpc-(?:[0-9a-f]{8}|[0-9a-f]{17})", vpc_id):
        raise ValueError("Invalid VPC ID")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,24}", prefix):
        raise ValueError("Use a short unique lab cluster prefix")
    network = ipaddress.ip_network(client_cidr, strict=True)
    if network.version != 4 or network.prefixlen < 24:
        raise ValueError("Use an approved narrow public API client CIDR, /24 or narrower")
    if len(subnets) != 2 or len({s["az"] for s in subnets}) != 2:
        raise ValueError("Supply two private subnets in different Availability Zones")
    for subnet in subnets:
        if not re.fullmatch(re.escape(region) + r"[a-z]", subnet["az"]):
            raise ValueError("Subnet AZ does not match the Region")
        if not re.fullmatch(r"subnet-(?:[0-9a-f]{8}|[0-9a-f]{17})", subnet["id"]):
            raise ValueError("Invalid subnet ID")
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for role, cidr in [("managed", "172.20.0.0/16"), ("service", "172.21.0.0/16")]:
        config = {
            "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
            "metadata": {
                "name": f"{prefix}-{role}", "region": region, "version": "1.36",
                "tags": {"observability-lab": prefix},
            },
            "iam": {"withOIDC": True},
            "accessConfig": {"authenticationMode": "API"},
            "upgradePolicy": {"supportType": "STANDARD"},
            "kubernetesNetworkConfig": {"serviceIPv4CIDR": cidr},
            "vpc": {
                "id": vpc_id,
                "subnets": {"private": {s["az"]: {"id": s["id"]} for s in subnets}},
                "controlPlaneSubnetIDs": [s["id"] for s in subnets],
                "clusterEndpoints": {"publicAccess": True, "privateAccess": True},
                "publicAccessCIDRs": [str(network)],
            },
            "managedNodeGroups": [{
                "name": "lab-workers", "instanceType": "m6i.large",
                "amiFamily": "AmazonLinux2023", "privateNetworking": True,
                "desiredCapacity": 2, "minSize": 2, "maxSize": 3,
                "volumeSize": 40, "volumeType": "gp3", "volumeEncrypted": True,
            }],
        }
        descriptor = os.open(output / f"{role}.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(config, stream, indent=2)
            stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("--vpc-id", required=True)
    parser.add_argument("--subnet-a", required=True)
    parser.add_argument("--az-a", required=True)
    parser.add_argument("--subnet-b", required=True)
    parser.add_argument("--az-b", required=True)
    parser.add_argument("--client-cidr", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    generate(
        args.region, args.vpc_id,
        [{"id": args.subnet_a, "az": args.az_a}, {"id": args.subnet_b, "az": args.az_b}],
        args.client_cidr, args.prefix, args.output_directory,
    )
    print("Cluster configurations written. Verify CIDRs/routes/quotas before creation.")


if __name__ == "__main__":
    main()
