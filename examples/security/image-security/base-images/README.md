# Minimal base-image build fixtures

Use this directory as the Docker build context and select Dockerfile.distroless, Dockerfile.chainguard, or Dockerfile.alpine. Each app only prints a fixed message; it is not a web server.

Base image indexes and amd64/arm64 availability were inspected on2026-09-13. These digests are reproducible starting points, not perpetual security endorsements. Rebuild and rescan when dependencies or base images change. Alpine apk repositories and future Python dependency additions also need a reproducibility/update policy.

The Go and Python source programs were checked locally. Dockerfile configuration was checked statically. No container build or runtime was executed during this documentation audit; verify build-stage/runtime ABI compatibility and registry access in your own build environment.
