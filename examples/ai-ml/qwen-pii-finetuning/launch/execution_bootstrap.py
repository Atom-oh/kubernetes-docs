"""SageMaker code-channel entry point; never install packages on the docs host."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile


def main():
    source = Path("/opt/ml/input/data/code/source.tar.gz")
    if hashlib.sha256(source.read_bytes()).hexdigest() != os.environ["SOURCE_SHA256"]:
        raise ValueError("Code channel hash mismatch")
    code = Path("/opt/ml/code")
    code.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(code, filter="data")
    import torch
    if (torch.__version__.split("+")[0] != "2.11.0"
            or torch.version.cuda != "13.0"
            or sys.version_info[:2] != (3, 12)
            or not torch.cuda.is_available() or not torch.cuda.is_bf16_supported()):
        raise RuntimeError("Unexpected DLC / Python / CUDA / BF16 runtime")
    constraints = code / "image-constraints.txt"
    constraints.write_text("torch==" + torch.__version__ + "\n")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        "--no-cache-dir", "--only-binary=:all:", "--constraint", str(constraints),
        "--requirement", str(code / "requirements-execution.txt"),
    ], check=True, timeout=1200)
    versions = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    # The training entry requires an empty model directory. SageMaker preserves
    # this separate output channel in output.tar.gz alongside model.tar.gz.
    output = Path("/opt/ml/output/data")
    output.mkdir(parents=True, exist_ok=True)
    (output / "installed-packages.json").write_text(json.dumps(versions, indent=2, sort_keys=True))
    print(json.dumps({"event": "runtime_ready", "torch": torch.__version__,
                      "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0)}), flush=True)
    os.chdir(code)
    command = [
        sys.executable, "-m", "src.train_execution",
        "--mode", os.environ["RUN_MODE"],
        "--config", str(code / "config/execution-20260916.json"),
        "--dataset-dir", "/opt/ml/input/data/dataset",
        "--output-dir", "/opt/ml/model",
        "--steps", os.environ["RUN_STEPS"], "--eval-batch-size", "1",
    ]
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
