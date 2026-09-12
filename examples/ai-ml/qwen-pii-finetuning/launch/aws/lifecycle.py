"""Private ownership journal and bounded cleanup for this experiment.

No legacy inventory migration is automatic. A lost create response requires
manual reconciliation against CloudTrail/resource identity before cleanup.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from botocore.exceptions import ClientError


class RecoveryRequired(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryRequired(message)


def atomic_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if exclusive else path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(target, flags, 0o600), "w") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if not exclusive:
        os.replace(target, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def initialize(path, fields):
    # Exclusive creation prevents a second process from replacing ownership.
    value = dict(fields, schema_version=2, ownership_token=uuid.uuid4().hex,
                 resources={}, eks_clusters=[])
    for key, kind, name in [
        ("bucket", "bucket", fields.get("bucket_name")),
        ("execution_role", "role", fields.get("execution_role_name")),
        ("mlflow_role", "role", fields.get("mlflow_role_name")),
        ("mlflow_app", "app", fields.get("experiment_id")),
        ("project", "project", fields.get("experiment_id")),
    ]:
        value["resources"][key] = dict(kind=kind, name=name, state="planned", created=False)
    atomic_json(path, value, exclusive=True)


def sdk_clients(region):
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=region)
    config = Config(retries={"mode": "adaptive", "total_max_attempts": 4},
                    connect_timeout=10, read_timeout=30,
                    user_agent_extra="QwenLifecycle/2")
    return {name: session.client(name, config=config) for name in
            ("sts", "s3", "iam", "sagemaker", "datazone", "eks", "cloudformation")}


def validate_inputs(clients, env):
    names = ("EXPECTED_ACCOUNT_ID", "DATAZONE_DOMAIN_ID",
             "DATAZONE_PROJECT_PROFILE_ID", "DATAZONE_OWNER_GROUP_ID")
    require(all(env.get(n) for n in names),
            "Supply EXPECTED_ACCOUNT_ID and explicit DATAZONE_DOMAIN_ID, "
            "DATAZONE_PROJECT_PROFILE_ID, DATAZONE_OWNER_GROUP_ID before provisioning.")
    require(re.fullmatch(r"\d{12}", env["EXPECTED_ACCOUNT_ID"]), "Invalid expected account")
    account = clients["sts"].get_caller_identity()["Account"]
    require(account == env["EXPECTED_ACCOUNT_ID"], "AWS account mismatch")
    dz = clients["datazone"]
    domain = dz.get_domain(identifier=env["DATAZONE_DOMAIN_ID"])
    require(domain["id"] == env["DATAZONE_DOMAIN_ID"]
            and domain["status"] == "AVAILABLE", "DataZone domain is not AVAILABLE")
    profile = dz.get_project_profile(
        domainIdentifier=domain["id"], identifier=env["DATAZONE_PROJECT_PROFILE_ID"])
    require(profile["id"] == env["DATAZONE_PROJECT_PROFILE_ID"]
            and profile["status"] == "ENABLED", "DataZone project profile is not ENABLED")
    group = dz.get_group_profile(
        domainIdentifier=domain["id"], groupIdentifier=env["DATAZONE_OWNER_GROUP_ID"])
    require(group["id"] == env["DATAZONE_OWNER_GROUP_ID"]
            and group["status"] == "ASSIGNED", "DataZone owner group is not ASSIGNED")
    return account


def absent_call(call, codes, **kwargs):
    try:
        return call(**kwargs)
    except ClientError as error:
        if error.response["Error"]["Code"] in codes:
            return None
        raise


class Lifecycle:
    def __init__(self, path, clients=None, sleep=time.sleep):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text())
        require(self.data.get("schema_version") == 2
                and re.fullmatch(r"\d{12}", self.data.get("account_id", ""))
                and self.data.get("ownership_token") and isinstance(self.data.get("resources"), dict),
                "Refusing legacy/unowned inventory. Do not add ownership flags by hand. "
                "Reconcile actual identities and creation evidence; perform documented manual recovery.")
        self.clients = clients if clients is not None else sdk_clients(self.data["region"])
        self.sleep = sleep

    def save(self):
        atomic_json(self.path, self.data)

    def account(self):
        require(self.clients["sts"].get_caller_identity()["Account"] == self.data["account_id"],
                "AWS account differs from ownership inventory")

    def tags(self):
        return [{"Key": "ExperimentId", "Value": self.data["experiment_id"]},
                {"Key": "OwnershipToken", "Value": self.data["ownership_token"]},
                {"Key": "Experiment", "Value": "qwen-pii-finetuning"}]

    def tagged(self, tags):
        actual = {t["Key"]: t["Value"] for t in tags}
        return all(actual.get(t["Key"]) == t["Value"] for t in self.tags())

    def own_buckets(self):
        s3 = self.clients["s3"]
        return {b["Name"] for page in s3.get_paginator("list_buckets").paginate()
                for b in page["Buckets"]}

    def create(self, key, request):
        self.account()
        resource = self.data["resources"][key]
        require(resource["state"] == "planned" and not resource["created"],
                "Create already attempted; reconcile the journal before retrying")
        kind, name = resource["kind"], resource["name"]
        if kind == "role":
            require(request["RoleName"] == name, "Role name mismatch")
            require(absent_call(self.clients["iam"].get_role, {"NoSuchEntity"},
                                RoleName=name) is None, "Role already exists; not owned")
            request["Tags"] = self.tags()
            call = self.clients["iam"].create_role
        elif kind == "bucket":
            require(request["Bucket"] == name, "Bucket name mismatch")
            require(name not in self.own_buckets(), "Bucket already exists; not owned")
            call = self.clients["s3"].create_bucket
        elif kind == "app":
            require(request["Name"] == name, "App name mismatch")
            request["Tags"] = self.tags()
            call = self.clients["sagemaker"].create_mlflow_app
        elif kind == "project":
            require(request["name"] == name
                    and request["domainIdentifier"] == self.data["unified_domain_id"]
                    and request["projectProfileId"] == self.data["project_profile_id"]
                    and request["membershipAssignments"] == [{
                        "member": {"groupIdentifier": self.data["project_owner_group_id"]},
                        "designation": "PROJECT_OWNER"}], "Project input mismatch")
            call = self.clients["datazone"].create_project
        else:
            raise RecoveryRequired("Unsupported creation kind")
        resource["state"] = "creating"
        self.save()
        try:
            response = call(**request)
            if kind == "role":
                role = response["Role"]
                resource["identity"] = {"Arn": role["Arn"], "RoleId": role["RoleId"]}
                self.data[key + "_arn"] = role["Arn"]
            elif kind == "app":
                resource["identity"] = {"Arn": response["Arn"]}
                self.data["mlflow_app_arn"] = response["Arn"]
            elif kind == "project":
                resource["identity"] = {"id": response["id"], "createdAt": str(response["createdAt"])}
                self.data["project_id"] = response["id"]
            else:
                resource["identity"] = {"name": name}
            resource.update(state="owned", created=True)
            self.save()
            if kind == "bucket":
                # Failure here leaves confirmed creation, but unverified tags block deletion.
                self.clients["s3"].put_bucket_tagging(
                    Bucket=name, ExpectedBucketOwner=self.data["account_id"],
                    Tagging={"TagSet": self.tags()})
            return response
        except BaseException:
            if not resource["created"]:
                resource["state"] = "unknown"
                self.save()
            raise

    def probe(self, resource):
        """Return absent/present; all unknown and ownership errors propagate."""
        kind, name = resource["kind"], resource["name"]
        identity = resource.get("identity", {})
        if kind == "role":
            response = absent_call(self.clients["iam"].get_role, {"NoSuchEntity"}, RoleName=name)
            if response is None:
                return False
            role = response["Role"]
            require(all(role[k] == identity[k] for k in ("Arn", "RoleId"))
                    and self.tagged(role.get("Tags", [])), "Role ownership mismatch")
        elif kind == "bucket":
            if name not in self.own_buckets():
                return False
            tags = self.clients["s3"].get_bucket_tagging(
                Bucket=name, ExpectedBucketOwner=self.data["account_id"])["TagSet"]
            require(self.tagged(tags), "Bucket ownership tags missing/mismatched")
        elif kind == "app":
            sm = self.clients["sagemaker"]
            response = absent_call(sm.describe_mlflow_app, {"ResourceNotFound"}, Arn=identity["Arn"])
            if response is None or response["Status"] == "Deleted":
                return False
            require(self.tagged(sm.list_tags(ResourceArn=identity["Arn"])["Tags"]),
                    "MLflow App ownership mismatch")
        elif kind == "project":
            response = absent_call(self.clients["datazone"].get_project, {"ResourceNotFoundException"},
                                  domainIdentifier=self.data["unified_domain_id"],
                                  identifier=identity["id"])
            if response is None:
                return False
            require(response["id"] == identity["id"] and response["name"] == name
                    and str(response["createdAt"]) == identity["createdAt"],
                    "DataZone project ownership mismatch")
        elif kind == "eks":
            cluster = absent_call(self.clients["eks"].describe_cluster,
                                  {"ResourceNotFoundException"}, name=name)
            if cluster is not None:
                c = cluster["cluster"]
                require(c["arn"] == identity["arn"] and str(c["createdAt"]) == identity["createdAt"]
                        and self.tagged([{"Key": k, "Value": v} for k, v in c.get("tags", {}).items()]),
                        "EKS ownership mismatch")
            stacks_present = False
            for stack in identity["stacks"]:
                current = self.stack(stack["StackId"])
                if current and current["StackStatus"] != "DELETE_COMPLETE":
                    require(current["StackId"] == stack["StackId"]
                            and str(current["CreationTime"]) == stack["CreationTime"],
                            "EKS stack identity mismatch")
                    stacks_present = True
                elif current:
                    # DELETE_COMPLETE can coexist with retained resources.
                    rows = self.stack_resources(stack["StackId"])
                    require(all(row["ResourceStatus"] == "DELETE_COMPLETE" for row in rows),
                            "Deleted EKS stack has retained/unconfirmed resources; manual recovery required")
            return cluster is not None or stacks_present
        else:
            raise RecoveryRequired("Unknown resource kind")
        return True

    def training_jobs(self, stop=False):
        jobs = []
        for path in sorted(self.path.parent.glob("*-job.json")):
            request_path = path.with_name(path.name[:-9] + "-request.json")
            require(request_path.is_file(), "Job journal without request; manual recovery required")
            request = json.loads(request_path.read_text())
            tags = {t["Key"]: t["Value"] for t in request["Tags"]}
            if tags.get("ExperimentId") != self.data["experiment_id"]:
                continue
            journal = json.loads(path.read_text())
            name = journal["training_job_name"]
            require(journal["region"] == self.data["region"]
                    and request["TrainingJobName"] == name
                    and request["RoleArn"] == self.data.get("execution_role_arn"),
                    "Training journal ownership mismatch")
            require(journal["state"] in {"submitted", "stop_requested", "stop_unconfirmed",
                                        "Completed", "Failed", "Stopped", "terminal"},
                    "Training state %s requires manual reconciliation" % journal["state"])
            sm = self.clients["sagemaker"]
            desc = sm.describe_training_job(TrainingJobName=name)
            expected = "arn:aws:sagemaker:%s:%s:training-job/%s" % (
                self.data["region"], self.data["account_id"], name)
            actual_tags = {t["Key"]: t["Value"] for page in
                           sm.get_paginator("list_tags").paginate(ResourceArn=desc["TrainingJobArn"])
                           for t in page["Tags"]}
            require(desc["TrainingJobArn"] == expected
                    and desc["RoleArn"] == request["RoleArn"]
                    and actual_tags.get("ExperimentId") == self.data["experiment_id"],
                    "Training job ownership mismatch")
            terminal = {"Completed", "Failed", "Stopped"}
            if stop and desc["TrainingJobStatus"] not in terminal:
                sm.stop_training_job(TrainingJobName=name)
                journal["state"] = "stop_requested"
                atomic_json(path, journal)
                for _ in range(60):
                    desc = sm.describe_training_job(TrainingJobName=name)
                    if desc["TrainingJobStatus"] in terminal:
                        break
                    self.sleep(10)
                require(desc["TrainingJobStatus"] in terminal,
                        "Training stop unconfirmed; retain bucket and roles")
                journal["state"] = desc["TrainingJobStatus"]
                atomic_json(path, journal)
            jobs.append((name, desc))
        return jobs

    def empty_bucket(self):
        s3 = self.clients["s3"]
        params = {"Bucket": self.data["bucket_name"], "ExpectedBucketOwner": self.data["account_id"]}
        previous = None
        for _ in range(10000):
            page = s3.list_object_versions(**params, MaxKeys=1000)
            objects = [{"Key": x["Key"], "VersionId": x["VersionId"]}
                       for field in ("Versions", "DeleteMarkers") for x in page.get(field, [])]
            if not objects:
                require(not page.get("IsTruncated"), "Empty truncated S3 page; manual recovery required")
                break
            require(objects != previous, "S3 deletion made no progress")
            previous = objects
            result = s3.delete_objects(**params, Delete={"Objects": objects, "Quiet": True})
            require(not result.get("Errors"), "S3 per-object deletion errors; retain inventory")
        else:
            raise RecoveryRequired("S3 deletion batch limit reached")
        for page in s3.get_paginator("list_multipart_uploads").paginate(**params):
            for upload in page.get("Uploads", []):
                s3.abort_multipart_upload(**params, Key=upload["Key"], UploadId=upload["UploadId"])

    def delete(self, resource):
        if not self.probe(resource):
            resource["state"] = "deleted"
            self.save()
            return
        kind, name = resource["kind"], resource["name"]
        if kind == "role":
            iam = self.clients["iam"]
            # Attached policies/profiles were not created by these scripts.
            attached = [p for page in iam.get_paginator("list_attached_role_policies").paginate(RoleName=name)
                        for p in page["AttachedPolicies"]]
            profiles = [p for page in iam.get_paginator("list_instance_profiles_for_role").paginate(RoleName=name)
                        for p in page["InstanceProfiles"]]
            require(not attached and not profiles, "Role acquired external attachments; manual recovery required")
            policies = [p for page in iam.get_paginator("list_role_policies").paginate(RoleName=name)
                        for p in page["PolicyNames"]]
            allowed = {self.data["experiment_id"] + "-execution", self.data["experiment_id"] + "-mlflow-s3"}
            require(set(policies) <= allowed, "Role acquired external inline policies")
            for policy in policies:
                iam.delete_role_policy(RoleName=name, PolicyName=policy)
            iam.delete_role(RoleName=name)
        elif kind == "bucket":
            self.empty_bucket()
            self.clients["s3"].delete_bucket(Bucket=name, ExpectedBucketOwner=self.data["account_id"])
        elif kind == "app":
            self.clients["sagemaker"].delete_mlflow_app(Arn=resource["identity"]["Arn"])
        elif kind == "project":
            self.clients["datazone"].delete_project(
                domainIdentifier=self.data["unified_domain_id"], identifier=resource["identity"]["id"])
        else:
            raise RecoveryRequired("Use eks-delete with a verified export to delete EKS")
        for _ in range(80):
            if not self.probe(resource):
                resource["state"] = "deleted"
                self.save()
                return
            self.sleep(15)
        raise RecoveryRequired("Deletion timeout; state remains pending")

    def teardown(self, discard_artifacts=False):
        self.account()
        jobs = self.training_jobs(stop=True)
        for r in self.data["resources"].values():
            require(r["state"] not in {"creating", "unknown"},
                    "unknown/partial creation; reconcile the private journal manually before deletion")
        require(not jobs or discard_artifacts,
                "Training jobs are terminal. Export SageMaker artifacts first; then explicitly pass "
                "--discard-training-artifacts to acknowledge deletion of this experiment bucket.")
        # Validate every owned identity before the first deletion.
        for r in self.data["resources"].values():
            if r["created"]:
                present = self.probe(r)
                require(r["kind"] != "eks" or not present,
                        "EKS remains: export/recover it with run.sh before deleting shared storage")
        for key in ("mlflow_app", "project", "bucket", "execution_role", "mlflow_role"):
            r = self.data["resources"][key]
            if r["created"]:
                self.delete(r)
        report = self.verify()
        require(report["clean"], "Cleanup verification remains incomplete")
        self.data["deleted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()

    def verify(self):
        report = {"remaining": [], "unknown": [], "clean": False,
                  "scope": "recorded owned resources and training jobs; not an account-wide audit"}
        try:
            self.account()
            jobs = self.training_jobs()
            report["remaining"].extend("training:" + name for name, desc in jobs
                                       if desc["TrainingJobStatus"] not in {"Completed", "Failed", "Stopped"})
        except Exception as error:
            report["unknown"].append("account/training: " + type(error).__name__)
        for key, r in self.data["resources"].items():
            try:
                require(r["state"] not in {"creating", "unknown"}, "unconfirmed creation")
                if r["created"] and self.probe(r):
                    report["remaining"].append(key)
            except Exception as error:
                report["unknown"].append(key + ": " + type(error).__name__)
        report["clean"] = not report["remaining"] and not report["unknown"]
        atomic_json(self.path.parent / "teardown-report.json", report)
        return report

    def stack(self, name):
        try:
            return self.clients["cloudformation"].describe_stacks(StackName=name)["Stacks"][0]
        except ClientError as error:
            # ValidationError alone is not absence.
            detail = error.response["Error"]
            if detail["Code"] == "ValidationError" and "does not exist" in detail["Message"]:
                return None
            raise

    def stack_resources(self, stack_id):
        return [row for page in self.clients["cloudformation"].get_paginator(
            "list_stack_resources").paginate(StackName=stack_id)
                for row in page["StackResourceSummaries"]]

    def eks_plan(self, name, kubeconfig):
        self.account()
        require(name.startswith(self.data["experiment_id"] + "-")
                and re.fullmatch(r"[A-Za-z0-9-]{1,100}", name), "Invalid EKS name")
        require("eks:" + name not in self.data["resources"], "EKS attempt already journaled; manual recovery required")
        require(absent_call(self.clients["eks"].describe_cluster, {"ResourceNotFoundException"},
                            name=name) is None, "EKS cluster already exists")
        stacks = ["eksctl-" + name + "-cluster", "eksctl-" + name + "-nodegroup-gpu"]
        require(all(self.stack(n) is None for n in stacks), "Pre-existing EKS stack; refuse creation")
        self.data["resources"]["eks:" + name] = {
            "kind": "eks", "name": name, "state": "creating", "created": False,
            "stack_names": stacks, "kubeconfig": str(Path(kubeconfig).resolve()),
        }
        self.data["eks_clusters"].append(name)
        self.save()

    def eks_confirm(self, name):
        self.account()
        r = self.data["resources"]["eks:" + name]
        require(r["state"] == "creating", "Unexpected EKS state")
        c = self.clients["eks"].describe_cluster(name=name)["cluster"]
        require(self.tagged([{"Key": k, "Value": v} for k, v in c.get("tags", {}).items()]),
                "EKS creation ownership not confirmed; manual recovery required")
        stacks = []
        for n in r["stack_names"]:
            s = self.stack(n)
            require(s and s["StackStatus"] == "CREATE_COMPLETE"
                    and self.tagged(s.get("Tags", [])), "Partial/unowned EKS stack; manual recovery required")
            rows = self.stack_resources(s["StackId"])
            stacks.append({"StackId": s["StackId"], "CreationTime": str(s["CreationTime"]),
                           "resources": [{"type": row["ResourceType"],
                                          "id": row.get("PhysicalResourceId")}
                                         for row in rows]})
        r.update(created=True, state="owned",
                 identity={"arn": c["arn"], "createdAt": str(c["createdAt"]),
                           "endpoint": c["endpoint"], "stacks": stacks})
        self.save()

    def eks_delete(self, name, archive, mode):
        # Hash verification is local and precedes any destructive request.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eks"))
        from verify_export import verify_archive
        verify_archive(Path(archive), mode)
        self.account()
        r = self.data["resources"]["eks:" + name]
        require(r["created"] and r["state"] == "owned", "EKS is not confirmed owned")
        require(self.probe(r), "EKS unexpectedly absent; inspect residual stacks")
        env = dict(os.environ, KUBECONFIG=r["kubeconfig"])
        subprocess.run(["eksctl", "delete", "cluster", "--name", name,
                        "--region", self.data["region"], "--wait", "--timeout", "45m"],
                       env=env, check=True, timeout=2800)
        require(not self.probe(r), "EKS or its stacks remain after deletion")
        r["state"] = "deleted"
        r["export_archive"] = str(Path(archive).resolve())
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inputs", "init", "create", "teardown", "verify",
                                            "eks-plan", "eks-confirm", "eks-delete", "check"])
    parser.add_argument("inventory", nargs="?")
    parser.add_argument("resource", nargs="?")
    parser.add_argument("--kubeconfig")
    parser.add_argument("--archive")
    parser.add_argument("--mode", choices=["smoke", "full"])
    parser.add_argument("--discard-training-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        if args.command in {"create", "eks-plan"}:
            subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2]
                                                / "src/runtime_contract.py"),
                            "--check-execution"], check=True)
        if args.command in {"inputs", "init"}:
            # Require explicit inputs before creating SDK clients (including STS).
            required = ("EXPECTED_ACCOUNT_ID", "DATAZONE_DOMAIN_ID",
                        "DATAZONE_PROJECT_PROFILE_ID", "DATAZONE_OWNER_GROUP_ID")
            require(all(os.environ.get(k) for k in required), "Explicit account/DATAZONE IDs are required")
            account = validate_inputs(sdk_clients("ap-northeast-2"), os.environ)
            if args.command == "inputs":
                print(account)
                return 0
            fields = {k.lower(): os.environ[k] for k in
                      ("EXPERIMENT_ID", "BUCKET_NAME", "EXECUTION_ROLE_NAME", "MLFLOW_ROLE_NAME")}
            fields.update(account_id=account, region="ap-northeast-2",
                          unified_domain_id=os.environ["DATAZONE_DOMAIN_ID"],
                          project_profile_id=os.environ["DATAZONE_PROJECT_PROFILE_ID"],
                          project_owner_group_id=os.environ["DATAZONE_OWNER_GROUP_ID"])
            fields["source_s3_uri"] = "s3://%s/qwen-pii/%s/source/source.tar.gz" % (
                fields["bucket_name"], fields["experiment_id"])
            initialize(args.inventory, fields)
            return 0
        require(args.inventory and Path(args.inventory).is_file(), "Inventory is required")
        # One operation at a time; fail rather than queue a stale destructive plan.
        with open(args.inventory + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lc = Lifecycle(args.inventory)
            if args.command == "create":
                print(json.dumps(lc.create(args.resource, json.load(sys.stdin)), default=str))
            elif args.command == "teardown":
                lc.teardown(args.discard_training_artifacts)
            elif args.command == "verify":
                return 0 if lc.verify()["clean"] else 1
            elif args.command == "eks-plan":
                lc.eks_plan(args.resource, args.kubeconfig)
            elif args.command == "eks-confirm":
                lc.eks_confirm(args.resource)
            elif args.command == "eks-delete":
                lc.eks_delete(args.resource, args.archive, args.mode)
            else:
                lc.account()
                require(lc.data["resources"]["bucket"]["created"]
                        and lc.probe(lc.data["resources"]["bucket"]), "Owned bucket is unavailable")
        return 0
    except Exception as error:
        # No raw AWS responses, signed URLs or workload logs in console output.
        print("Lifecycle incomplete (%s): %s" % (
            type(error).__name__, str(error) if isinstance(error, RecoveryRequired)
            else "inspect the private journal and reconcile; no success is asserted"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
