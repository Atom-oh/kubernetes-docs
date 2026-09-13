"""Offline contracts: real pinned Helm renders, no cluster or credential access.

Set PROMETHEUS_CHART and DATADOG_CHART to the downloaded, pinned archives.
TMPDIR/HELM_*_HOME may point at an ignored evidence directory.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import yaml

HERE = Path(__file__).resolve().parent
PINNED = {
    "PROMETHEUS_CHART": "04b90a3f4aab4b40572585095331259bc8f00328e40f9ec588e54cdb9aa6a55f",
    "DATADOG_CHART": "09083b7414d595080b874878f9ee7a576f9181ee245619deb0cab5b4bef13228",
}


def render(profile, archive, release, namespace):
    chart = Path(os.environ[archive])
    if hashlib.sha256(chart.read_bytes()).hexdigest() != PINNED[archive]:
        raise AssertionError("Wrong chart archive: " + archive)
    result = subprocess.run(
        ["helm", "template", release, str(chart), "--namespace", namespace,
         "--kube-version", "1.36.2", "-f", str(HERE / profile)],
        check=True, capture_output=True, text=True,
    )
    return list(filter(None, yaml.safe_load_all(result.stdout)))


def workloads(documents):
    return [d for d in documents if d["kind"] in ("Deployment", "DaemonSet")]


def containers(workload):
    spec = workload["spec"]["template"]["spec"]
    return spec.get("containers", []) + spec.get("initContainers", [])


def env(container):
    return {v["name"]: v for v in container.get("env", [])}


def postrender(documents):
    return subprocess.run(
        [sys.executable, "-B", str(HERE / "datadog_postrender.py")],
        input=yaml.safe_dump_all(documents, sort_keys=False),
        text=True, capture_output=True,
    )


class Profiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prom = render("prometheus-values.yaml", "PROMETHEUS_CHART",
                          "kube-prom", "monitoring")
        cls.dd = render("datadog-values.yaml", "DATADOG_CHART",
                        "datadog", "datadog")

    def test_grafana_keeps_file_expression_not_password_in_environment(self):
        workload = next(d for d in workloads(self.prom)
                        if d["metadata"]["name"] == "metrics-demo-grafana")
        for container in containers(workload):
            self.assertFalse(container.get("envFrom"))
            for entry in container.get("env", []):
                self.assertNotIn("secretKeyRef", entry.get("valueFrom", {}))
                self.assertFalse(entry["name"].endswith("__FILE"))
        grafana = next(c for c in containers(workload) if c["name"] == "grafana")
        self.assertEqual(env(grafana)["GF_SECURITY_ADMIN_PASSWORD"]["value"],
                         "$__file{/mnt/grafana-secrets/admin-password}")
        mount = next(m for m in grafana["volumeMounts"]
                     if m["mountPath"] == "/mnt/grafana-secrets")
        self.assertTrue(mount["readOnly"])
        self.assertFalse(mount.get("subPath"))
        spec = workload["spec"]["template"]["spec"]
        volume = next(v for v in spec["volumes"] if v["name"] == mount["name"])
        self.assertEqual(volume["csi"]["driver"], "secrets-store.csi.k8s.io")
        self.assertEqual(volume["csi"]["volumeAttributes"]["secretProviderClass"],
                         "metrics-grafana-admin")
        self.assertEqual(spec["securityContext"]["fsGroup"], 472)
        config = next(d["data"]["grafana.ini"] for d in self.prom
                      if d["kind"] == "ConfigMap" and "grafana.ini" in d.get("data", {}))
        self.assertIn("admin_password = $__file{/mnt/grafana-secrets/admin-password}", config)
        self.assertFalse(any(d["kind"] == "Secret" and
                             "admin-password" in d.get("data", {}) for d in self.prom))

    def test_sidecar_startup_and_provisioning_do_not_require_admin_credentials(self):
        workload = next(d for d in workloads(self.prom)
                        if d["metadata"]["name"] == "metrics-demo-grafana")
        spec = workload["spec"]["template"]["spec"]
        initial = {c["name"] for c in spec.get("initContainers", [])}
        self.assertIn("grafana-init-sc-datasources", initial)
        self.assertIn("grafana-init-sc-dashboard", initial)
        for container in containers(workload):
            if "sc-" in container["name"]:
                self.assertFalse({"REQ_PASSWORD", "REQ_USERNAME", "REQ_URL"} & env(container).keys())
                self.assertFalse(any(m["name"] == "grafana-secrets"
                                     for m in container["volumeMounts"]))

    def test_csi_source_is_aws_file_only_and_matches_grafana_mount(self):
        spc = yaml.safe_load((HERE / "grafana-secret-provider.yaml").read_text())
        self.assertEqual(spc["metadata"]["namespace"], "monitoring")
        self.assertEqual(spc["metadata"]["name"], "metrics-grafana-admin")
        self.assertEqual(spc["spec"]["provider"], "aws")
        self.assertNotIn("secretObjects", spc["spec"])
        obj = yaml.safe_load(spc["spec"]["parameters"]["objects"])[0]
        self.assertEqual(obj["objectType"], "secretsmanager")
        self.assertEqual(obj["jmesPath"][0]["objectAlias"], "admin-password")
        self.assertEqual(obj["jmesPath"][0]["filePermission"], "0440")

    def test_unprocessed_datadog_has_the_original_seven_unsafe_references(self):
        references = [e for w in workloads(self.dd) for c in containers(w)
                      for e in c.get("env", [])
                      if "secretKeyRef" in e.get("valueFrom", {})]
        self.assertEqual(len(references), 7)
        # The sentinel Secret is deliberately absent: omitting the renderer fails closed.
        self.assertFalse(any(d["kind"] == "Secret" for d in self.dd))

    def test_all_rendered_pod_templates_including_jobs_avoid_secret_environments(self):
        result = postrender(self.dd)
        self.assertEqual(result.returncode, 0, result.stderr)
        documents = self.prom + list(yaml.safe_load_all(result.stdout))
        count = 0
        for document in documents:
            spec = document.get("spec", {})
            if document["kind"] == "CronJob":
                spec = spec["jobTemplate"]["spec"]
            pod = spec if document["kind"] == "Pod" else spec.get("template", {}).get("spec", {})
            for group in ("containers", "initContainers", "ephemeralContainers"):
                for container in pod.get(group, []):
                    count += 1
                    self.assertFalse(container.get("envFrom"))
                    for variable in container.get("env", []):
                        self.assertNotIn("secretKeyRef", variable.get("valueFrom", {}))
                        self.assertFalse(variable["name"].endswith("__FILE"))
        self.assertGreater(count, 6)  # Includes more than the Datadog consumers alone.

    def test_datadog_resolves_identical_handles_in_each_consumer(self):
        result = postrender(self.dd)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = list(yaml.safe_load_all(result.stdout))
        expected = {
            "agent": {"DD_API_KEY", "DD_CLUSTER_AGENT_AUTH_TOKEN"},
            "trace-agent": {"DD_API_KEY", "DD_CLUSTER_AGENT_AUTH_TOKEN"},
            "init-config": {"DD_API_KEY"},
            "cluster-agent": {"DD_API_KEY", "DD_CLUSTER_AGENT_AUTH_TOKEN"},
            "init-volume": set(),
        }
        count = 0
        for workload in workloads(output):
            for container in containers(workload):
                entries = env(container)
                actual = set(entries) & {"DD_API_KEY", "DD_CLUSTER_AGENT_AUTH_TOKEN"}
                self.assertEqual(actual, expected[container["name"]])
                for key in actual:
                    reference = ("api-key" if key == "DD_API_KEY" else "cluster-token")
                    self.assertEqual(entries[key], {
                        "name": key, "value": "ENC[observability/datadog;" + reference + "]"})
                    count += 1
                for entry in entries.values():
                    self.assertNotIn("secretKeyRef", entry.get("valueFrom", {}))
                    self.assertFalse(entry["name"].endswith("__FILE"))
                if actual:
                    self.assertEqual(entries["DD_SECRET_BACKEND_TYPE"]["value"], "aws.secrets")
                    self.assertEqual(json.loads(entries["DD_SECRET_BACKEND_CONFIG"]["value"]),
                                     {"aws_session": {"aws_region": "ap-northeast-2"}})
                    self.assertEqual(entries["AWS_EC2_METADATA_DISABLED"]["value"], "true")
        self.assertEqual(count, 7)
        # Replacing only credential references must preserve collection, commands, mounts and RBAC.
        restored = copy.deepcopy(output)
        original_by_key = {(d["kind"], d["metadata"]["name"]): d for d in self.dd}
        for workload in workloads(restored):
            original = original_by_key[(workload["kind"], workload["metadata"]["name"])]
            for c, previous in zip(containers(workload), containers(original)):
                for i, entry in enumerate(c.get("env", [])):
                    if entry["name"] in {"DD_API_KEY", "DD_CLUSTER_AGENT_AUTH_TOKEN"}:
                        c["env"][i] = copy.deepcopy(env(previous)[entry["name"]])
        self.assertEqual(restored, self.dd)

    def test_helm_invokes_the_executable_postrenderer(self):
        result = subprocess.run(
            ["helm", "template", "datadog", os.environ["DATADOG_CHART"],
             "--namespace", "datadog", "--kube-version", "1.36.2",
             "-f", str(HERE / "datadog-values.yaml"),
             "--post-renderer", str(HERE / "datadog_postrender.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Independent Helm renders generate a new install-info UUID/timestamp.
        # Compare the resulting consumers; same-input preservation is checked above.
        self.assertEqual(workloads(list(yaml.safe_load_all(result.stdout))),
                         workloads(list(yaml.safe_load_all(postrender(self.dd).stdout))))

    def assert_rejected(self, documents):
        result = postrender(documents)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_rejects_missing_or_duplicate_credential_and_wrong_secret(self):
        for change in ("missing", "duplicate", "wrong-secret"):
            with self.subTest(change=change):
                docs = copy.deepcopy(self.dd)
                c = next(c for w in workloads(docs) for c in containers(w) if c["name"] == "agent")
                entry = env(c)["DD_API_KEY"]
                if change == "missing":
                    c["env"].remove(entry)
                elif change == "duplicate":
                    c["env"].append(copy.deepcopy(entry))
                else:
                    entry["valueFrom"]["secretKeyRef"]["name"] = "unexpected"
                self.assert_rejected(docs)

    def test_rejects_missing_backend_static_aws_credentials_or_imds_fallback(self):
        for key, value in [
            ("DD_SECRET_BACKEND_TYPE", ""),
            ("DD_SECRET_BACKEND_CONFIG", '{"aws_session":{"aws_access_key_id":"FAKE"}}'),
            ("AWS_EC2_METADATA_DISABLED", "false"),
        ]:
            with self.subTest(key=key):
                docs = copy.deepcopy(self.dd)
                c = next(c for w in workloads(docs) for c in containers(w)
                         if c["name"] == "cluster-agent")
                env(c)[key]["value"] = value
                self.assert_rejected(docs)

    def test_rejects_chart_image_and_identity_drift(self):
        for change in ("chart", "image", "identity", "role"):
            with self.subTest(change=change):
                docs = copy.deepcopy(self.dd)
                workload = workloads(docs)[0]
                if change == "chart":
                    workload["metadata"]["labels"]["helm.sh/chart"] = "datadog-999.0.0"
                elif change == "image":
                    containers(workload)[0]["image"] = "unreviewed:latest"
                elif change == "identity":
                    workload["spec"]["template"]["spec"]["serviceAccountName"] = "default"
                else:
                    account = next(d for d in docs if d["kind"] == "ServiceAccount"
                                   and d["metadata"]["name"] == "datadog")
                    account["metadata"].pop("annotations")
                self.assert_rejected(docs)

    def test_rejects_other_secret_environment_sources_and_new_consumers(self):
        for change in ("envFrom", "extra", "plaintext", "aws-key", "file-export", "sidecar"):
            with self.subTest(change=change):
                docs = copy.deepcopy(self.dd)
                workload = workloads(docs)[0]
                c = containers(workload)[0]
                if change == "envFrom":
                    c["envFrom"] = [{"secretRef": {"name": "leak"}}]
                elif change == "extra":
                    c.setdefault("env", []).append(
                        {"name": "OTHER_PASSWORD", "valueFrom": {
                            "secretKeyRef": {"name": "leak", "key": "password"}}})
                elif change in ("plaintext", "aws-key", "file-export"):
                    variable = {"plaintext": "OTHER_PASSWORD",
                                "aws-key": "AWS_SECRET_ACCESS_KEY",
                                "file-export": "DD_API_KEY__FILE"}[change]
                    c.setdefault("env", []).append({"name": variable, "value": "FAKE_ONLY"})
                else:
                    workload["spec"]["template"]["spec"]["containers"].append(
                        {"name": "unreviewed", "image": "example:latest"})
                self.assert_rejected(docs)

    def test_invalid_input_produces_no_partial_manifest_or_secret_diagnostic(self):
        for text in ("kind: Pod\nkind: Secret\n", "not: [valid", "null\n", "[]\n"):
            result = subprocess.run(
                [sys.executable, "-B", str(HERE / "datadog_postrender.py")],
                input=text, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
