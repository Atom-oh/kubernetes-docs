# Upstream policy source

`templates/k8scontainerlimits.yaml` is copied from
`open-policy-agent/gatekeeper-library` at commit `bd333d4704647b1000cef5a92017257ee46fe2c8`,
path `library/general/containerlimits/template.yaml`. Its policy body is unchanged;
a source/license comment was prepended. The Apache-2.0 license is included as
`LICENSE.gatekeeper-library`. This template intentionally retains its supported
Rego v0 syntax and fails closed on unsupported quantity representations.

The other four templates are local Rego v1 examples and explicitly set
`targets[].code[].source.version: v1`. They demonstrate a limited policy scope;
they are not a full Pod Security Standards implementation.
