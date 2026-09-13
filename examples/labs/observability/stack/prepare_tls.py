"""Create private, disposable lab PKI and Grafana provisioning files."""

import argparse
import datetime
import ipaddress
import os
import re
import secrets
from pathlib import Path

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def write_private(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(value)


def secret(name, namespace, values):
    return {
        "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
        "metadata": {"name": name, "namespace": namespace},
        "stringData": values,
    }


def generate(output, collector_dns, prometheus_dns):
    for hostname in (collector_dns, prometheus_dns):
        if len(hostname) > 253 or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in hostname.split(".")
        ):
            raise ValueError("Supply DNS names, without scheme, port or wildcard")
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise ValueError("Use a DNS name whose certificate SAN can match the endpoint")
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Disposable observability lab CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    ca_pem = ca.public_bytes(serialization.Encoding.PEM).decode()
    write_private(output / "ca.key", ca_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode())

    def leaf(name, dns_names=None):
        key = ec.generate_private_key(ec.SECP256R1())
        builder = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
            .issuer_name(ca_name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH if dns_names else ExtendedKeyUsageOID.CLIENT_AUTH,
            ]), critical=False)
        )
        if dns_names:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(n) for n in dict.fromkeys(dns_names)]),
                critical=False,
            )
        certificate = builder.sign(ca_key, hashes.SHA256())
        return {
            "ca.crt": ca_pem,
            "tls.crt": certificate.public_bytes(serialization.Encoding.PEM).decode(),
            "tls.key": key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).decode(),
        }

    collector = leaf("lab-collector", [
        collector_dns, "lab-collector.monitoring.svc.cluster.local",
    ])
    prometheus = leaf("lab-prometheus", [
        prometheus_dns, "lab-monitoring-prometheus.monitoring.svc.cluster.local",
    ])
    client = leaf("lab-telemetry-client")
    datasources = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus", "uid": "prometheus", "type": "prometheus",
                "access": "proxy", "isDefault": True,
                "url": "https://lab-monitoring-prometheus.monitoring.svc.cluster.local:9090",
                "jsonData": {
                    "httpMethod": "POST", "timeInterval": "15s",
                    "tlsAuth": True, "tlsAuthWithCACert": True, "tlsSkipVerify": False,
                    "exemplarTraceIdDestinations": [{"name": "trace_id", "datasourceUid": "tempo"}],
                },
                "secureJsonData": {
                    "tlsCACert": client["ca.crt"], "tlsClientCert": client["tls.crt"],
                    "tlsClientKey": client["tls.key"],
                },
            },
            {
                "name": "Loki", "uid": "loki", "type": "loki", "access": "proxy",
                "url": "http://lab-loki.monitoring.svc.cluster.local:3100",
                "jsonData": {"derivedFields": [{
                    "name": "trace_id", "datasourceUid": "tempo",
                    "matcherRegex": r'"trace_id"\s*:\s*"([a-f0-9]{32})"',
                    "url": "$${__value.raw}",
                }]},
            },
            {
                "name": "Tempo", "uid": "tempo", "type": "tempo", "access": "proxy",
                "url": "http://lab-tempo.monitoring.svc.cluster.local:3200",
                "jsonData": {
                    "tracesToLogsV2": {
                        "datasourceUid": "loki",
                        "spanStartTimeShift": "-1m", "spanEndTimeShift": "1m",
                        "tags": [{"key": "service.name", "value": "service_name"}],
                        "filterByTraceID": True, "filterBySpanID": False,
                    },
                    "serviceMap": {"datasourceUid": "prometheus"},
                    "nodeGraph": {"enabled": True},
                },
            },
        ],
    }
    management = [
        secret("lab-collector-tls", "monitoring", collector),
        secret("lab-prometheus-tls", "monitoring", prometheus),
        secret("lab-prometheus-client", "monitoring", client),
        secret("lab-grafana-admin", "monitoring", {
            "admin-user": "lab-admin", "admin-password": secrets.token_urlsafe(24),
        }),
        secret("lab-grafana-datasources", "monitoring", {
            "lab.yaml": yaml.safe_dump(datasources, sort_keys=False),
        }),
    ]
    write_private(output / "management-secrets.yaml", yaml.safe_dump_all(management, sort_keys=False))
    write_private(output / "service-observability-secrets.yaml", yaml.safe_dump(
        secret("lab-collector-tls", "observability", client), sort_keys=False,
    ))
    write_private(output / "service-monitoring-secrets.yaml", yaml.safe_dump(
        secret("lab-prometheus-client", "monitoring", client), sort_keys=False,
    ))
    write_private(output / "collector-endpoint-values.yaml", yaml.safe_dump({
        "extraEnvs": [{"name": "MANAGEMENT_OTLP_ENDPOINT", "value": f"https://{collector_dns}:4318"}],
    }, sort_keys=False))
    write_private(output / "prometheus-endpoint-values.yaml", yaml.safe_dump({
        "prometheus": {"prometheusSpec": {"remoteWrite": [{
            "url": f"https://{prometheus_dns}:9090/api/v1/write", "sendExemplars": True,
            "tlsConfig": {
                "caFile": "/etc/prometheus/secrets/lab-prometheus-client/ca.crt",
                "certFile": "/etc/prometheus/secrets/lab-prometheus-client/tls.crt",
                "keyFile": "/etc/prometheus/secrets/lab-prometheus-client/tls.key",
            },
        }]}},
    }, sort_keys=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--collector-dns", required=True)
    parser.add_argument("--prometheus-dns", required=True)
    args = parser.parse_args()
    generate(args.output_directory, args.collector_dns, args.prometheus_dns)
    print("Private lab files created. No cluster resources or DNS/routes were changed.")


if __name__ == "__main__":
    main()
