"""Validate the private MLflow archive without extracting untrusted paths."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import uuid

if __package__:
    from .export_mlflow import ARTIFACTS
else:
    from export_mlflow import ARTIFACTS


def digest(stream):
    sha = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        sha.update(chunk)
    return sha.hexdigest()


def verify_archive(path, mode, expected_provenance):
    if mode not in {"smoke", "full"}:
        raise ValueError("Invalid run mode")
    keys = {"experiment_id", "cluster_name", "execution_id"}
    if (not isinstance(expected_provenance, dict) or set(expected_provenance) != keys
            or any(not isinstance(v, str) or not v for v in expected_provenance.values())):
        raise ValueError("Expected inventory provenance is required")
    if str(uuid.UUID(expected_provenance["execution_id"])) != expected_provenance["execution_id"]:
        raise ValueError("Execution ID must be a canonical UUID")
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Export archive must not be a symlink")
    with tarfile.open(path, "r:gz") as archive:
        expected = set(ARTIFACTS) | {"export.json"}
        members = []
        total = 0
        for member in archive:
            members.append(member)
            total += member.size
            if len(members) > len(expected) or total > 16 * 1024 ** 3:
                raise ValueError("Export archive exceeds bounded member/size limits")
        if (len(members) != len(expected)
                or {m.name for m in members} != expected
                or any(not m.isfile() or m.size <= 0 for m in members)):
            raise ValueError("Unexpected, missing, duplicate or nonregular export member")
        manifest_member = archive.getmember("export.json")
        if manifest_member.size > 2 * 1024 * 1024:
            raise ValueError("Oversized export manifest")
        manifest = json.load(archive.extractfile(manifest_member))
        if manifest.get("provenance") != expected_provenance:
            raise ValueError("Archive provenance does not match the recorded execution")
        if (manifest["run_name"] != "eks-" + mode or manifest["status"] != "FINISHED"
                or manifest["params"]["run_environment"] != "eks"):
            raise ValueError("Export is not the expected completed EKS run")
        entries = manifest["artifacts"]
        if len(entries) != len(ARTIFACTS) or {e["path"] for e in entries} != set(ARTIFACTS):
            raise ValueError("Unexpected artifact manifest")
        for entry in entries:
            member = archive.getmember(entry["path"])
            if member.size != entry["bytes"] or digest(archive.extractfile(member)) != entry["sha256"]:
                raise ValueError("Artifact size/hash mismatch: " + member.name)
    with path.open("rb") as stream:
        return {"archive": str(path.resolve()), "sha256": digest(stream),
                "run_id": manifest["run_id"], "mode": mode, "verified": True,
                "provenance": expected_provenance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--mode", choices=["smoke", "full"], required=True)
    parser.add_argument("--expected-provenance", type=Path, required=True,
                        help="Private JSON projection of the inventory's expected_export")
    args = parser.parse_args()
    expected = json.loads(args.expected_provenance.read_text())
    print(json.dumps(verify_archive(args.archive, args.mode, expected), sort_keys=True))


if __name__ == "__main__":
    main()
