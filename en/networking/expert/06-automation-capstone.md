# 6. Network Automation and Final Assessment

> **Last Updated**: September 15, 2026

**Prerequisites:** Chapters 1, 2 and 4 provide the common observation skills. Add chapter 3 for an EVPN/fabric capstone or chapter 5 for cloud. The Linux host capstone uses chapter 4's bounded experiment. The validator exercise needs only Python 3.9+ and a new directory you own.

**Goal:** Separate intent from observations and submit reproducible normal, forbidden, failed and recovered states. Automation must not turn missing evidence into success.

## 1. Review intent before changing anything {#intent}

| Area | Define before the change | Verify afterward |
|---|---|---|
| Reachability | Who should access which service? | Actual response and observation point |
| Isolation | Which flows must be forbidden? | Policy evidence together with the probe |
| Routing policy | Which prefixes should be advertised to which peer/VRF? | Advertised, selected and forwarded state in that same scope |
| Resilience | What must survive a single failure? | Service continuity and convergence/recovery interval |
| Operational boundary | Management access, change scope and stop criteria | No out-of-scope change and restored state |

Changing expected values merely to match new output can conceal regressions. Review intent first and record its revision/hash. Observation adapters preserve units, scope and time while normalizing actual output.

For example, a FRR peer's advertisements, a Linux host's entire FIB and a TGW route table are different datasets. The prefix contract below compares **the set advertised to a specified peer**. Preference, ECMP count, FIB installation and actual forwarding need separate evidence.

## 2. A small validator exercise {#record-validator}

The following data is **synthetic**. It does not configure a network or transmit packets. The validator checks consistency between supplied intent and records; it does not attest to the authenticity of PCAPs or counters.

Create a fresh directory on your lab VM or local study terminal.

```bash
EVIDENCE_DIR=$(mktemp -d /tmp/network-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE_DIR"
```

Save this JSON as `intent.json` in that directory. Real automation keeps it as a separately reviewed input.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "maximum_window_seconds": 60,
  "exported_prefixes": ["203.0.113.0/24"],
  "flows": {"a-to-web": "allow", "b-to-a": "deny"}
}
```

Save the following as `observations.json`. Addresses, times and artifact names are illustrative.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "evidence_kind": "synthetic",
  "window": {"start": "2026-09-15T00:00:00Z", "end": "2026-09-15T00:00:10Z"},
  "exported_prefixes": ["203.0.113.0/24"],
  "route_artifact": "synthetic:advertised-routes",
  "flows": {
    "a-to-web": {
      "verdict": "allow",
      "artifacts": {"probe": "synthetic:http-response"}
    },
    "b-to-a": {
      "verdict": "deny",
      "artifacts": {"probe": "synthetic:blocked-probe", "policy": "synthetic:policy-decision"}
    }
  }
}
```

Save this Python as `check_record.py` in the same directory.

```python
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def prefixes(values):
    require(isinstance(values, list), "prefixes must be a list")
    return {str(ipaddress.ip_network(value, strict=True)) for value in values}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp needs a timezone")
    return parsed


require(len(sys.argv) == 3, "usage: check_record.py intent.json observations.json")
intent, seen = load(sys.argv[1]), load(sys.argv[2])
for record in (intent, seen):
    require(type(record.get("schema")) is int and record["schema"] == 1, "schema")
for key in ("scenario", "phase", "route_scope"):
    require(intent[key] == seen[key], "scope mismatch: " + key)
require(seen["evidence_kind"] in {"synthetic", "supplied", "measured"}, "evidence kind")
duration = (timestamp(seen["window"]["end"]) - timestamp(seen["window"]["start"])).total_seconds()
require(0 < duration <= intent["maximum_window_seconds"], "invalid observation window")
require(prefixes(intent["exported_prefixes"]), "empty intended prefix scope")
require(prefixes(seen["exported_prefixes"]) == prefixes(intent["exported_prefixes"]), "prefix mismatch")
require(isinstance(seen.get("route_artifact"), str) and seen["route_artifact"].strip(), "route evidence missing")
require(intent["flows"] and set(intent["flows"]) == set(seen["flows"]), "flow coverage mismatch")
for name, wanted in intent["flows"].items():
    require(wanted in {"allow", "deny"}, "unsupported intent")
    actual = seen["flows"][name]
    require(actual["verdict"] == wanted, "flow mismatch: " + name)
    needed = {"probe"} if wanted == "allow" else {"probe", "policy"}
    artifacts = actual["artifacts"]
    require(all(isinstance(artifacts.get(k), str) and artifacts[k].strip() for k in needed),
            "evidence missing: " + name)
print("CONSISTENT_RECORD kind=" + seen["evidence_kind"] + "; live behavior not attested")
```

Run it:

```bash
python3 "${EVIDENCE_DIR:?}/check_record.py" \
  "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json"
```

The expected output is `CONSISTENT_RECORD kind=synthetic; live behavior not attested`. It means this record's required conditions passed, not that network traffic succeeded or an operational rollout is approved. Explicit exceptions keep checks active when Python optimization would remove `assert` statements.

### Inputs that must fail

Keep the originals and change an `observations-bad.json` copy **one item at a time**. Run the same command with that copy as the final argument.

| Change | Expected result |
|---|---|
| Remove the `b-to-a` observation | `flow coverage mismatch` |
| Set `b-to-a.verdict` to `unknown` or `allow` | `flow mismatch` |
| Remove the forbidden flow's `policy` artifact | `evidence missing` |
| Add `0.0.0.0/0` to advertisements or empty the list | `prefix mismatch` |
| Put end time before start time | `invalid observation window` |
| Change `phase` | `scope mismatch` |

Do not normalize empty output or a timeout to `deny`. A forbidden outcome needs policy/enforcement evidence tied to the probe. Naming an artifact does not prove it exists or was collected at the correct observation point.

When extending this exercise into a real collector, check file existence, hashes, time range, collector and device/account identity against original evidence. Separately validate attributes lost when normalizing to sets, such as path attributes or per-endpoint readiness.

## 3. Design a change pipeline {#pipeline}

Define each stage's input, output and failure owner.

| Stage | Check | Result passed onward |
|---|---|---|
| Intent review | Allowed/forbidden flows, routes, management access and failure boundary | Reviewed intent revision |
| Static validation | Syntax, supported features, overlapping addresses and policy scope | Results for exact tool/provider versions |
| Change preview | Target, impact, expected difference and recoverability | Human-reviewable change plan |
| Lab application | One change, bounded time/resources, preserved management | Before/after state and execution record |
| Behavior checks | Allowed, forbidden, failed, recovered and missing evidence | Structured results tied to originals |
| Operational decision | Validation scope, unknowns and rollout/rollback conditions | Approval or rejection through a separate operational procedure |

This course does not provide an automatic production-approval pipeline. Read the recovery commands beforehand and establish independent recovery access, such as a console, when management connectivity could be affected.

## 4. Choose a capstone {#capstones}

### A. Routing/fabric

Use one prepared lab from [chapter 2](02-routing-policy-convergence.md) or [chapter 3](03-datacenter-evpn.md).

1. Define permitted prefixes and forbidden routes/flows for a specific peer/VRF.
2. Record healthy advertisements, selection, FIB and service probes.
3. Choose one recoverable policy/path fault from that chapter.
4. Separate control-plane change time from actual service recovery.
5. Restore the original configuration and recheck both reachability and isolation.

Do not substitute the time a session becomes Established for service convergence. Record synchronization/uncertainty when comparing different devices' clocks, or use one observer's time axis.

### B. Linux/cloud/SRE

Choose a bounded host experiment from [chapter 4](04-linux-performance.md) or approved cloud evidence from [chapter 5](05-cloud-cni-design.md).

1. Mark forward/return paths and at least two observation points.
2. Select a hypothesis about delay, loss, queuing or policy and define falsification.
3. Connect observations to source/namespace, time and units.
4. If you performed an experiment, restore it exactly and repeat the same checks.
5. If you only analyzed design/supplied evidence, limit the conclusion accordingly.

Without equipment or an account, submit design or supplied-evidence analysis. Mark **practical execution complete** only with originals and recovery evidence from your own bounded experiment.

## 5. Assessment {#assessment}

Evaluate each item as `met / unmet / unobserved`. Do not conceal missing mandatory evidence inside an aggregate score.

| Item | Passing criterion |
|---|---|
| Scope/reproducibility | Topology, environment, permissions, version/revision, inputs and time can be reconstructed |
| Protocol reasoning | Packet, route and application relationships explained; at least one hypothesis falsified |
| Positive/negative checks | Allowed traffic and isolation evaluated separately; absence never counted as success |
| Failure/recovery | Single-change impact and recovered state checked against the same criteria |
| Automation quality | Wrong scope, omissions, unknowns and intent mismatches rejected; originals traceable |
| Honest conclusions | Measured, supplied, synthetic, design and unobserved evidence distinguished |

Return to the relevant chapter when a mandatory item is unmet. Do not declare live validation complete for an unobserved item. A reviewer must be able to reconstruct the conclusion from the same evidence.

## Cleanup and continuation

Inspect the files you created before cleaning up the validator exercise.

```bash
ls -la -- "${EVIDENCE_DIR:?}"
rm -- "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json" \
  "${EVIDENCE_DIR:?}/check_record.py"
```

If you made copies, remove **only the verified copies**, then run `rmdir -- "${EVIDENCE_DIR:?}"`. Actual experiment originals have a separate approved retention policy; they are not this temporary synthetic example.

Add experiments where your portfolio is weakest: [protocols](01-protocol-projects.md), [routing](02-routing-policy-convergence.md), [EVPN](03-datacenter-evpn.md), [Linux performance](04-linux-performance.md), or [cloud design](05-cloud-cni-design.md).

References: [Python JSON](https://docs.python.org/3/library/json.html), [ipaddress](https://docs.python.org/3/library/ipaddress.html), [datetime](https://docs.python.org/3/library/datetime.html).

[Previous: Cloud/CNI](05-cloud-cni-design.md) · [Quiz](../../quizzes/networking/expert/06-automation-capstone-quiz.md) · [Course](README.md)
