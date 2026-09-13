#!/usr/bin/env python3
"""Pinned Helm postrenderer: credential references -> native in-memory resolution.

Only accepts the accompanying Linux Datadog 3.244.0 profile/release/namespace.
It never reads a credential, calls AWS, or exports a resolved value. It emits
nothing until the whole input passes validation. See README.md before use.
"""
import json
import re
import sys

import yaml

SENTINEL = "must-use-secret-postrenderer"
REFERENCES = {
    "DD_API_KEY": ("api-key", "ENC[observability/datadog;api-key]"),
    "DD_CLUSTER_AGENT_AUTH_TOKEN": ("token", "ENC[observability/datadog;cluster-token]"),
}
PUBLIC_SECRET_SETTINGS = {
    "DD_AUTH_TOKEN_FILE_PATH",
    "DD_CLUSTER_AGENT_TOKEN_NAME",
    "DD_SECRET_BACKEND_TYPE", "DD_SECRET_BACKEND_CONFIG",
    "DD_SECRET_REFRESH_INTERVAL", "DD_SECRET_REFRESH_ON_API_KEY_FAILURE_INTERVAL",
}
IMAGES = {
    "datadog": "gcr.io/datadoghq/agent@sha256:ed0bd588e955d82f661d1b8dd1cdf179c1023e74a2817e7a812c99d52f05c319",
    "datadog-cluster-agent": "gcr.io/datadoghq/cluster-agent@sha256:8e420c81e68abec34ab792c72a6513b739dcba8f7682c52e1e7e276363827b1a",
}
CONSUMERS = {
    ("DaemonSet", "datadog"): {
        "containers": {"agent": set(REFERENCES), "trace-agent": set(REFERENCES)},
        "initContainers": {"init-volume": set(), "init-config": {"DD_API_KEY"}},
    },
    ("Deployment", "datadog-cluster-agent"): {
        "containers": {"cluster-agent": set(REFERENCES)},
        "initContainers": {"init-volume": set()},
    },
}


class InvalidProfile(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidProfile(message)


class UniqueLoader(yaml.SafeLoader):
    """Reject ambiguous input rather than silently accepting the last key."""


def unique_mapping(loader, node):
    pairs = loader.construct_pairs(node, deep=True)
    result = {}
    for key, value in pairs:
        require(isinstance(key, str) and key not in result, "duplicate or non-string YAML key")
        result[key] = value
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def transform(documents):
    require(bool(documents), "empty manifest")
    resources = {}
    for document in documents:
        require(isinstance(document, dict), "expected Kubernetes resources")
        identity = (document.get("kind"), document.get("metadata", {}).get("name"))
        require(all(isinstance(v, str) and v for v in identity), "resource identity missing")
        require(identity not in resources, "duplicate resource")
        resources[identity] = document
        require(identity[0] not in {"Pod", "Job", "CronJob", "StatefulSet",
                                    "ReplicaSet", "ReplicationController", "List"},
                "unsupported workload")
        require(identity[0] != "Secret", "profile must not contain Kubernetes Secrets")
    actual = {key for key in resources if key[0] in {"DaemonSet", "Deployment"}}
    require(actual == set(CONSUMERS), "unexpected workload set")
    replacements = []
    for identity, expected_groups in CONSUMERS.items():
        workload = resources[identity]
        name = identity[1]
        meta = workload["metadata"]
        require(meta.get("namespace") == "datadog", "wrong workload namespace")
        require(meta.get("labels", {}).get("helm.sh/chart") == "datadog-3.244.0",
                "unreviewed chart version")
        pod = workload["spec"]["template"]["spec"]
        require(pod.get("serviceAccountName") == name, "unexpected workload identity")
        service_account = resources.get(("ServiceAccount", name), {})
        require(service_account.get("metadata", {}).get("namespace") == "datadog",
                "missing workload service account")
        role = service_account["metadata"].get("annotations", {}).get(
            "eks.amazonaws.com/role-arn", "")
        require(bool(re.fullmatch(r"arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+", role)),
                "IRSA role annotation required")
        require(not pod.get("ephemeralContainers"), "unreviewed ephemeral containers")
        for group, expected in expected_groups.items():
            entries = pod.get(group, [])
            require(len(entries) == len(expected)
                    and {c.get("name") for c in entries} == set(expected),
                    "unreviewed container set")
            for container in entries:
                require(container.get("image") == IMAGES[name], "unreviewed image")
                require(not container.get("envFrom"), "envFrom is not allowed")
                variables = container.get("env", [])
                require(len({v["name"] for v in variables}) == len(variables),
                        "duplicate environment entry")
                env = {v["name"]: v for v in variables}
                keys = set(env) & set(REFERENCES)
                require(keys == expected[container["name"]], "credential consumer drift")
                for variable in variables:
                    require(not variable["name"].endswith("__FILE"),
                            "entrypoint file-to-environment expansion is not allowed")
                    if variable["name"] not in REFERENCES:
                        require("secretKeyRef" not in variable.get("valueFrom", {}),
                                "unexpected secret environment reference")
                        require(variable["name"] in PUBLIC_SECRET_SETTINGS or not re.search(
                            r"PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|APP_KEY|ACCESS_KEY|PRIVATE_KEY",
                            variable["name"], re.IGNORECASE),
                            "unreviewed credential environment variable")
                    if variable["name"] == "DD_AUTH_TOKEN_FILE_PATH":
                        require(variable.get("value") == "/etc/datadog-agent/auth/token",
                                "unexpected IPC token file path")
                    if variable["name"] == "DD_CLUSTER_AGENT_TOKEN_NAME":
                        require(variable.get("value") == "datadogtoken",
                                "unexpected chart token-name metadata")
                if keys:
                    require(env.get("DD_SECRET_BACKEND_TYPE", {}).get("value") == "aws.secrets",
                            "native AWS backend required")
                    config = json.loads(env.get("DD_SECRET_BACKEND_CONFIG", {}).get("value", "{}"))
                    require(config == {"aws_session": {"aws_region": "ap-northeast-2"}},
                            "unexpected backend config; static AWS credentials are not allowed")
                    require(env.get("AWS_EC2_METADATA_DISABLED", {}).get("value") == "true",
                            "EC2 metadata fallback must be disabled")
                    for setting in ("DD_SECRET_REFRESH_INTERVAL",
                                    "DD_SECRET_REFRESH_ON_API_KEY_FAILURE_INTERVAL"):
                        require(env.get(setting, {}).get("value") == "0",
                                "profile requires explicit restart-based rotation")
                for key in keys:
                    secret_key, handle = REFERENCES[key]
                    expected_ref = {"name": SENTINEL, "key": secret_key}
                    if container["name"] == "cluster-agent" and key == "DD_API_KEY":
                        expected_ref["optional"] = True
                    require(env[key] == {"name": key, "valueFrom": {"secretKeyRef": expected_ref}},
                            "unexpected credential source")
                    replacements.append((env[key], handle))
    require(len(replacements) == 7, "credential coverage incomplete")
    for entry, handle in replacements:
        del entry["valueFrom"]
        entry["value"] = handle
    return documents


def main():
    try:
        documents = list(filter(lambda d: d is not None,
                                yaml.load_all(sys.stdin.read(), Loader=UniqueLoader)))
        result = transform(documents)
        output = yaml.safe_dump_all(result, sort_keys=False)
    except (InvalidProfile, yaml.YAMLError, ValueError, KeyError, TypeError, AttributeError):
        # Do not echo YAML or exception values: rejected input could contain a credential.
        print("Datadog secret profile rejected; check the pinned chart, identity, "
              "backend and consumer contract.", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
