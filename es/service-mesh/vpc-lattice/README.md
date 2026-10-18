# Introducción detallada a VPC Lattice

> **Alcance**: API de servicios y recursos de VPC Lattice y AWS Gateway API Controller; verifica la versión seleccionada y las CRD instaladas.
> **Última actualización**: 12 de octubre de 2026

## Contenido de esta sección

- Qué cambia realmente al pasar de una malla de servicios con proxy sidecar (App Mesh, Istio) a un **plano de datos administrado** (VPC Lattice)
- Cómo afectan al recorrido de la solicitud el direccionamiento documentado de Lattice, la firma SigV4 y las políticas de autorización aplicables
- Las diferencias estructurales que surgen al migrar la identidad de cargas de trabajo de SPIFFE/SPIRE a IAM, y por qué son cuestiones que deberá evaluar el comité de revisión

## Por qué esta sección es independiente

Esta sección trata de **entender los conceptos**. La creación de recursos de Lattice
y la instalación de AWS Gateway API Controller ya se explican en [VPC Lattice](../../networking/02-vpc-lattice.md), y la comparación de funciones con Istio está en [Istio frente a VPC Lattice](../istio/comparison/02-istio-vs-lattice.md). Esos documentos no cubren lo que aborda esta sección: **por qué se diseñó de esta manera y qué consecuencias tiene ese diseño**.

Hay urgencia. **El soporte de AWS App Mesh terminó el 30 de septiembre de 2026** y la consola y los recursos de App Mesh ya no son accesibles. La incorporación de nuevos clientes se había cerrado el 24 de septiembre de 2024. Para cualquier organización que usara App Mesh, esta migración ya no es opcional: el plazo venció.

Pero App Mesh y Lattice **no son dos implementaciones de lo mismo**. El plano de
datos está en un lugar distinto (dentro del pod o en la infraestructura de AWS), la
identidad se demuestra con diferente granularidad (conexión frente a solicitud) y
la raíz de confianza pertenece a otra entidad (la CA del cliente o AWS IAM/STS). Si intentas
migrar sustituyendo nombres de recursos uno por uno, descubrirás brechas funcionales
y fallos en las revisiones de seguridad cuando la migración ya esté avanzada. El
objetivo de esta sección es exponer esas brechas **desde el principio**.

## Público y supuestos

- Arquitectos de AWS e ingenieros de infraestructura del cliente
- Suponemos que ya conoces EKS y Kubernetes
- Suponemos que VPC Lattice y el funcionamiento interno de las mallas de servicios son nuevos para ti
- Se incluyen pocos ejemplos de código y manifiestos. No es una guía de laboratorio práctico

## Estructura de los documentos

| # | Documento | Pregunta que responde |
|---|----------|---------------------|
| 1 | [Arquitectura de App Mesh frente a VPC Lattice](./01-appmesh-vs-lattice.md) | Cuando el plano de datos pasa del pod a la infraestructura, ¿qué permanece y qué desaparece? |
| 2 | [Análisis del impacto en la latencia](./02-latency.md) | Hay factores que la empeoran y que la mejoran. ¿Cuál predomina en nuestro entorno? |
| 3 | [Flujo detallado de autenticación de IAM](./03-auth-flow.md) | ¿Qué ocurre en las cuatro etapas desde la firma hasta la autorización de una solicitud? |
| 4 | [Fundamentos: enlace local y SNI](./04-networking-basics.md) | ¿Cómo se intercepta el tráfico sin sidecar? ¿Qué se pierde al no terminar TLS? |
| 5 | [Migración de identidad de cargas de trabajo: de SPIFFE a IAM](./05-spiffe-to-iam.md) | ¿Puede IAM hacer lo que hacía SPIRE? ¿Qué no reemplaza? |
| 6 | [Restricciones y puntos de decisión](./06-constraints.md) | ¿Qué decisiones de capacidad, confianza, costo y recuperación se deben resolver? |
| 7 | [Plano de datos del kernel](./07-kernel-datapath.md) | ¿Cómo afectan al recorrido el enrutamiento de pods, las reglas de proxy y el seguimiento de conexiones? |

Se recomienda leer los documentos en orden desde el 1. El documento 4 (enlace
local, SNI) proporciona conocimientos previos necesarios para las restricciones de
los documentos 3 y 6. Aunque está más adelante, si no conoces los fundamentos de
redes, léelo primero.

## Nota sobre la precisión

Las afirmaciones fácticas de esta sección se basan en la documentación oficial de
AWS, la documentación de AWS Gateway API Controller, la implementación de
referencia `aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice` y la
documentación de SPIFFE/SPIRE.

Lo que no se haya confirmado con documentación oficial no se presenta como un
hecho; se marca con un bloque `Needs verification`. Lattice sigue incorporando
funciones y, en particular, **las cuotas y los precios varían según la región y con
el tiempo**. Antes de finalizar un diseño, comprueba los valores actuales
directamente en la consola de Service Quotas y en la [página de precios de VPC Lattice](https://aws.amazon.com/vpc/lattice/pricing/).

## Documentos relacionados

- [VPC Lattice](../../networking/02-vpc-lattice.md): configuración de recursos de Lattice e instalación de Gateway API Controller
- [Gateway API](../../networking/04-gateway-api.md): estándar de Kubernetes Gateway API
- [Istio frente a VPC Lattice](../istio/comparison/02-istio-vs-lattice.md): comparación de funciones, costos y complejidad operativa
- [Seguridad de Istio: mTLS](../istio/security/01-mtls.md): cómo funciona la autenticación mutua basada en sidecar
- [Prueba comparativa de redes de pods](../../networking/06-pod-network-benchmark.md): valores medidos de referencia para la latencia en la misma AZ y entre AZ
