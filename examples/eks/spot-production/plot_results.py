#!/usr/bin/env python3
"""Render the published E2 evidence; optional dependency: matplotlib==3.9.4."""
import argparse
import csv
from datetime import datetime
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads((args.results_dir / "results.json").read_text())
    observations = json.loads((args.results_dir / "e2-node-pod-timeline.json").read_text())
    events = observations["events"]
    parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    origin = parse(next(e["utc"] for e in events if e["event"] == "FIS action start"))
    shutdown = next(e["secondsFromFisAction"] for e in events
                    if e["event"] == "Kubelet reports node shutdown")
    pod_ready = next(e["secondsFromFisAction"] for e in events
                     if e["event"] == "Replacement Pod Ready")
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 13,
                         "axes.labelsize": 12, "legend.fontsize": 10,
                         "svg.fonttype": "none"})
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.2, 1]})
    colors = {"baseline": "#3366a1", "mixed": "#8057a3", "spot-only": "#d06a1f"}
    styles = {"baseline": "--", "mixed": "-", "spot-only": ":"}
    labels = {"baseline": "On-Demand control", "mixed": "Mixed: 1 OD + 2 Spot",
              "spot-only": "Same 2 Spot Pods only"}
    for service in colors:
        with (args.results_dir / "e2-interruption" / f"{service}-timeline.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        x = [(parse(r["utc"]) - origin).total_seconds() for r in rows]
        style = {"color": colors[service], "linestyle": styles[service]}
        axes[0].plot(x, [int(r["errors"]) for r in rows],
                     label=labels[service], linewidth=1.3, **style)
        axes[1].plot(x, [float(r["p99_ms"]) if r["p99_ms"] else float("nan")
                        for r in rows], linewidth=1, alpha=.85, **style)
        ready = observations["readyPodObservations"]
        axes[2].step([(parse(r["utc"]) - origin).total_seconds() for r in ready],
                     [r[service] for r in ready], where="post", linewidth=1.4, **style)
    for ax in axes:
        ax.axvspan(shutdown, pod_ready, color="#d06a1f", alpha=.09)
        ax.axvline(0, color="#475569", linestyle=":", linewidth=1)
        ax.axvline(shutdown, color="#ab3e37", linestyle="--", linewidth=1)
        ax.axvline(pod_ready, color="#41774d", linestyle="-.", linewidth=1)
        ax.grid(alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Failed requests / s")
    axes[0].legend(loc="upper right")
    axes[1].set_ylabel("1-second p99 (ms)")
    axes[1].set_yscale("log")
    axes[2].set_ylabel("Ready backend Pods")
    axes[2].set_yticks([0, 1, 2, 3])
    axes[2].set_ylim(-.1, 3.4)
    time_label = origin.strftime("%H:%M:%S.%f")[:-3]
    axes[2].set_xlabel(f"Seconds from FIS action start (UTC {time_label})")
    axes[0].set_title(
        "FIS async completion is not service recovery | dashed: shutdown; dash-dot: replacement Pod Ready",
        loc="left",
    )
    fig.suptitle(
        "Single Spot reclamation: measured synthetic ClusterIP HTTP traffic\n"
        f"20 RPS per path, fresh connections, empty response; one run on {data['date']}",
        fontsize=15,
    )
    fig.tight_layout(rect=(0, 0, 1, .94))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    fig.savefig(args.output.with_suffix(".svg"))
    plt.close(fig)


if __name__ == "__main__":
    main()
