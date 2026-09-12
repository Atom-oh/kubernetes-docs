import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

from launch.aws.lifecycle import Lifecycle, RecoveryRequired
from test_lifecycle_safety import Client, error, lifecycle

EKS = Path(__file__).resolve().parents[1] / "launch/eks"
sys.path.insert(0, str(EKS))
from verify_export import ARTIFACTS, verify_archive


def archive(tmp_path, corrupt=False, extra=False):
    data = {name: b'{"synthetic":"fixture"}' for name in ARTIFACTS}
    manifest = {
        "run_id": "a" * 32, "run_name": "eks-smoke", "status": "FINISHED",
        "params": {"run_environment": "eks"},
        "artifacts": [{"path": name, "bytes": len(value),
                       "sha256": hashlib.sha256(value).hexdigest()} for name, value in data.items()],
    }
    if corrupt:
        data[ARTIFACTS[-1]] += b"x"
    data["export.json"] = json.dumps(manifest).encode()
    if extra:
        data["../unexpected"] = b"x"
    path = tmp_path / "export.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name, value in data.items():
            info = tarfile.TarInfo(name)
            info.size = len(value)
            tar.addfile(info, io.BytesIO(value))
    return path


def test_archive_all_required_artifacts_round_trip(tmp_path):
    receipt = verify_archive(archive(tmp_path), "smoke")
    assert receipt["verified"] and len(receipt["sha256"]) == 64


@pytest.mark.parametrize("entrypoint", ["module", "script", "import"])
def test_export_verifier_in_fresh_python_process(tmp_path, entrypoint):
    import subprocess
    path = archive(tmp_path)
    if entrypoint == "module":
        command = [sys.executable, "-m", "launch.eks.verify_export", str(path), "--mode", "smoke"]
    elif entrypoint == "script":
        command = [sys.executable, str(EKS / "verify_export.py"), str(path), "--mode", "smoke"]
    else:
        command = [sys.executable, "-c",
                   "from launch.eks.verify_export import verify_archive; "
                   "import json,sys; print(json.dumps(verify_archive(sys.argv[1], 'smoke')))",
                   str(path)]
    result = subprocess.run(command, cwd=EKS.parents[1], capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["verified"] is True


@pytest.mark.parametrize("kwargs", [{"corrupt": True}, {"extra": True}])
def test_archive_rejects_bad_content(tmp_path, kwargs):
    with pytest.raises(ValueError):
        verify_archive(archive(tmp_path, **kwargs), "smoke")


def test_archive_rejects_other_mode(tmp_path):
    with pytest.raises(ValueError):
        verify_archive(archive(tmp_path), "full")


def test_preexisting_cluster_blocks_plan(tmp_path):
    lc = lifecycle(tmp_path, eks=Client(describe_cluster={"cluster": {"arn": "existing"}}))
    with pytest.raises(RecoveryRequired, match="exists"):
        lc.eks_plan("qwen-pii-fixture-smoke-eks", tmp_path / "kubeconfig")
    assert not lc.data["eks_clusters"]


def test_unknown_cluster_read_blocks_plan(tmp_path):
    lc = lifecycle(tmp_path, eks=Client(describe_cluster=error("AccessDenied")))
    with pytest.raises(Exception):
        lc.eks_plan("qwen-pii-fixture-smoke-eks", tmp_path / "kubeconfig")
    assert not lc.data["eks_clusters"]


def test_partial_create_intent_is_persistent(tmp_path):
    lc = lifecycle(tmp_path, eks=Client(describe_cluster=error("ResourceNotFoundException")))
    lc.stack = lambda name: None
    name = "qwen-pii-fixture-smoke-eks"
    lc.eks_plan(name, tmp_path / "kubeconfig")
    saved = json.loads(lc.path.read_text())["resources"]["eks:" + name]
    assert saved["state"] == "creating" and saved["created"] is False
    assert len(saved["stack_names"]) == 2
    with pytest.raises(RecoveryRequired):
        lc.teardown()


def test_bad_export_cannot_reach_cloud_delete(tmp_path):
    lc = lifecycle(tmp_path)
    with pytest.raises(ValueError):
        lc.eks_delete("not-even-recorded", archive(tmp_path, corrupt=True), "smoke")
    assert lc.clients["sts"].calls == []


def test_eks_delete_failure_is_nonzero_and_preserves_owned_state(tmp_path, monkeypatch):
    import subprocess
    lc = lifecycle(tmp_path)
    name = "qwen-pii-fixture-smoke-eks"
    lc.data["resources"]["eks:" + name] = {
        "created": True, "state": "owned", "kubeconfig": str(tmp_path / "kubeconfig"),
    }
    lc.probe = lambda _: True
    def fail(*args, **kwargs):
        assert kwargs["env"]["KUBECONFIG"] == str(tmp_path / "kubeconfig")
        assert "--wait" in args[0]
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        lc.eks_delete(name, archive(tmp_path), "smoke")
    assert lc.data["resources"]["eks:" + name]["state"] == "owned"


def test_deleted_stack_with_retained_resource_is_unknown(tmp_path):
    lc = lifecycle(tmp_path, eks=Client(describe_cluster=error("ResourceNotFoundException")))
    lc.stack = lambda _: {"StackStatus": "DELETE_COMPLETE"}
    lc.stack_resources = lambda _: [{"ResourceStatus": "DELETE_SKIPPED"}]
    with pytest.raises(RecoveryRequired, match="retained"):
        lc.probe({"kind": "eks", "name": "fixture", "identity": {"stacks": [{"StackId": "saved-id"}]}})


@pytest.mark.parametrize("action,code", [("exit 17", 17), ('kill -TERM "$$"', 143),
                                       ('kill -INT "$$"', 130)])
def test_provision_finalizer_handles_explicit_exit_and_signals(action, code):
    import subprocess
    text = (EKS.parent / "aws/provision.sh").read_text()
    start = text.index("finalize() {")
    end = text.index("jq -nc --arg bucket", start)
    program = ('set -euo pipefail\nTEARDOWN=mock_cleanup\nINVENTORY=fixture\n'
               'mock_cleanup(){ echo CLEANUP_CALLED; return 1; }\n'
               + text[start:end] + action)
    result = subprocess.run(["bash", "--noprofile", "--norc", "-c", program],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == code
    assert "CLEANUP_CALLED" in result.stdout
    assert "Cleanup incomplete" in result.stderr
