"""Translate reviewed CloudFormation outputs into exact Helm inputs."""

import argparse
import json
import os
import re
from pathlib import Path

import yaml


def generate(outputs, region, repository, tag, directory):
    values = {entry["OutputKey"]: entry["OutputValue"] for entry in outputs}
    required = [
        "EventTopicArn", "NotificationQueueUrl", "AnalyticsQueueUrl",
        "OrderRoleArn", "PaymentRoleArn", "NotificationRoleArn", "AnalyticsRoleArn",
        "KedaRoleArn", "CollectorRoleArn", "ApplicationLogGroup",
    ]
    if any(not values.get(key) for key in required):
        raise ValueError("Missing required outputs from the lab infrastructure stack")
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
        raise ValueError("Invalid AWS Region")
    if not repository or not re.fullmatch(r"[A-Za-z0-9._/-]+", repository):
        raise ValueError("Use the repository URI without a tag or URL scheme")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise ValueError("Use an explicit image tag")
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    application = {
        "image": {"repository": repository, "tag": tag},
        "region": region, "eventTopicArn": values["EventTopicArn"],
        "notificationQueueURL": values["NotificationQueueUrl"],
        "analyticsQueueURL": values["AnalyticsQueueUrl"],
        "roleArns": {
            role: values[output] for role, output in [
                ("order-service", "OrderRoleArn"), ("payment-service", "PaymentRoleArn"),
                ("notification", "NotificationRoleArn"), ("analytics", "AnalyticsRoleArn"),
            ]
        },
    }
    keda = {
        "serviceAccount": {"operator": {"name": "keda-operator"}},
        "podIdentity": {"aws": {"irsa": {
            "enabled": True, "roleArn": values["KedaRoleArn"],
            "stsRegionalEndpoints": "true",
        }}},
    }
    collector = {
        "serviceAccount": {"name": "lab-collector", "annotations": {
            "eks.amazonaws.com/role-arn": values["CollectorRoleArn"],
            "eks.amazonaws.com/sts-regional-endpoints": "true",
        }},
        "extraEnvs": [
            {"name": "AWS_REGION", "value": region},
            {"name": "APPLICATION_LOG_GROUP", "value": values["ApplicationLogGroup"]},
        ],
    }
    for name, data in [("application.yaml", application), ("keda.yaml", keda), ("collector-identity.yaml", collector)]:
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            yaml.safe_dump(data, stream, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-file", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--image-repository", required=True)
    parser.add_argument("--image-tag", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    generate(
        json.loads(Path(args.outputs_file).read_text()), args.region,
        args.image_repository, args.image_tag, args.output_directory,
    )
    print("Helm inputs created from stack outputs; no cloud or cluster changes were made.")


if __name__ == "__main__":
    main()
