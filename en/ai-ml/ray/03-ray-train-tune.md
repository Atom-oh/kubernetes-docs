# Part 3: Ray Train and Ray Tune

> **Review baseline**: Ray 2.58.0 · 2026-09-12

## Lab Environment Setup

Validation used Python 3.12 and `ray[train,tune]==2.58.0`. These extras install Ray's Train/Tune dependencies; **frameworks such as PyTorch are separate**. Check the PyTorch, CUDA, and driver pairing for the actual workload.

The checks here cover configuration, callback/checkpoint APIs, and a small CPU scalar Tune example. They are not PyTorch training, GPU, distributed-gradient, or EKS autoscaling tests.

## Ray Train V2 and Training-Code Responsibilities

In 2.58.0, V2 is the default when `RAY_TRAIN_V2_ENABLED` is unset. The `ray.train.torch.TorchTrainer` import selects its V2 implementation accordingly. Do not assume identical contracts when an environment variable selects the older implementation.

The Trainer coordinates workers and underlying distributed process groups. It does not automatically author models, optimizers, loss/data loops, data partitioning, or state save/restore logic. With PyTorch, use appropriate helpers such as `prepare_model` and `prepare_data_loader` for device/DDP/sampler setup, then verify data duplication, gradient synchronization, and evaluation. Framework collectives cannot all be described as Ray object-store transfers.

## ScalingConfig and Resource Demand

`ScalingConfig` specifies worker counts and per-worker logical CPU/GPU resources. Supported elastic configurations also exist, so check the actual mode and its data/recovery requirements. Setting legacy `trainer_resources` raises a deprecation error in 2.58.0 V2. Distinguish the V2 controller, training workers, and Tune trial-driver resources.

Placement groups and worker bundles need adequate capacity before framework processes can initialize. This neither replaces Kubernetes scheduling nor guarantees atomic scheduling of every Pod. Insufficient GPUs can cause waits, timeouts, or failure; Ray/KubeRay bounds, quotas, image readiness, and EC2 availability matter too.

## Checkpoints and Reporting

`Checkpoint.from_directory()` constructs a checkpoint reference from files you prepare. It does not capture model, optimizer, RNG, scheduler, or dataset position automatically. Save the required state explicitly, then load the checkpoint returned by `train.get_checkpoint()` inside the worker.

**The 2.58.0 V2 `train.report` call is a barrier that every worker must reach the same number of times.** Even if only rank 0 saves files, other ranks participate with `checkpoint=None`. Skipping reports on some workers can stall training. Metrics are not automatically averaged across workers; compute required aggregates in training code.

Checkpoint upload defaults to synchronous mode. If using asynchronous upload or validation, check completion, temporary-file lifetime, and feature-specific constraints. Avoid filename collisions when several workers save shards.

For multiple nodes, set `train.RunConfig(storage_path=...)` to persistent storage accessible by all workers. A local Pod directory does not guarantee recovery after node/Pod deletion. S3 paths still need IAM, networking, and retention configuration.

### Failure Classes and Retries

The 2.58.0 V2 `FailureConfig` defaults are `max_failures=0` for training-worker errors, `controller_failure_limit=-1` for controller errors, and `max_preemption_failures=-1` for preemption. **Setting only `max_failures=0` does not disable every retry class.** Configure each limit together with RayJob/operational deadlines. Retries cannot recover progress from a missing or incomplete checkpoint.

## Ray Tune: Searchers and Schedulers

Tune manages trial configurations and execution. Searchers select parameter candidates; trial schedulers use intermediate metrics to stop, pause, or continue trials. Grid/random search does not necessarily adapt its next candidate from previous metrics.

Review `max_concurrent_trials`, trial resources, placement groups, and cluster capacity together. Avoid trial drivers occupying all resources needed by their nested Train workers. Summed CPU/GPU counts alone do not guarantee each worker bundle can be placed.

## Small Tune Example

This runs **two scalar-objective trials**, not model training. The actual check collected both results and selected `x=3` with score 0.

```python
from pathlib import Path
import ray
from ray import tune

def objective(config):
    for step in range(2):
        tune.report({"score": -(config["x"] - 3) ** 2, "step": step})

try:
    ray.init(address="local", num_cpus=2, include_dashboard=False,
             object_store_memory=80 * 1024 * 1024)
    tuner = tune.Tuner(
        tune.with_resources(objective, {"cpu": 1}),
        param_space={"x": tune.grid_search([1, 3])},
        tune_config=tune.TuneConfig(
            metric="score", mode="max", max_concurrent_trials=1),
        run_config=tune.RunConfig(
            storage_path=str(Path(".tune-demo").resolve()),
            name="scalar-example", verbose=0),
    )
    results = tuner.fit()
    assert len(results) == 2 and not results.errors
    best = results.get_best_result()
    assert best.config["x"] == 3 and best.metrics["score"] == 0
finally:
    ray.shutdown()
```

Ray logical resources and object-store size are not OS limits on the whole process. Decide whether you intend a new run or recovery before reusing a result directory.

## Current Train/Tune Integration

**Do not present passing a V2 Trainer instance directly to `Tuner` as the current recommended path.** The native check raised `TuneError` for a V2 DataParallelTrainer instance. Distinguish older BaseTrainer compatibility/deprecation handling from V2.

The current documented pattern uses a **function trainable** that constructs a framework Trainer and calls `.fit()`. Pass trial parameters through `train_loop_config` and use unique Train run names and storage paths per trial.

To forward intermediate metrics and checkpoint paths, attach `ray.tune.integration.ray_train.TuneReportCallback` through the Train `RunConfig(callbacks=[...])`. Construct it inside a Tune session. The 2.58.0 implementation forwards the first worker metric dictionary, without averaging. It adds an existing checkpoint path to metrics instead of uploading the checkpoint again.

Use `tune.RunConfig` for Tuner and `train.RunConfig` for the Trainer. Keep their failure, storage, and callback settings separate. This integration needs explicit wiring and resource planning.

![Tune trial functions create separate Train runs, whose workers use framework communication. Checkpoints go to shared persistent storage; a callback forwards metrics and checkpoint paths to Tune.](../../.gitbook/assets/en-ai-ml-ray-03-ray-train-tune-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-03-ray-train-tune-0.html)

## EKS Operational Checks

Inspect Ray resource/placement demand, KubeRay worker-group bounds, Kubernetes Pod placement, and physical node supply separately. Even with capacity available, image pulls, dataset access, framework initialization/communication, and checkpoint permissions can delay startup.

Autoscaling does not provide instant GPUs or an automatic cost/completion bound. Coordinate trial concurrency, workers, max replicas, retry classes, and operational deadlines. Verify result/checkpoint preservation before deleting a RayJob or cluster.

## Primary Sources

- [Train overview](https://docs.ray.io/en/releases-2.58.0/train/overview.html)
- [Train + Tune](https://docs.ray.io/en/releases-2.58.0/train/user-guides/hyperparameter-optimization.html)
- [Checkpoints](https://docs.ray.io/en/releases-2.58.0/train/user-guides/checkpoints.html)
- [Persistent storage](https://docs.ray.io/en/releases-2.58.0/train/user-guides/persistent-storage.html)
- [Failures/preemption](https://docs.ray.io/en/releases-2.58.0/train/user-guides/fault-tolerance.html)
- [PyTorch preparation](https://docs.ray.io/en/releases-2.58.0/train/getting-started-pytorch.html)
- [2.58.0 report implementation](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/train/v2/api/train_fn_utils.py)

[Next: Ray Serve](04-ray-serve.md) · [Main Page](README.md) · [Quiz](../../quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
