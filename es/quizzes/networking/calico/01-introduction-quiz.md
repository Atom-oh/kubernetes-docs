# Cuestionario de introducción a Calico

> **Documento relacionado**: [Introducción a Calico](../../../networking/calico/01-introduction.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿En qué año se inició originalmente Project Calico?
   - A) 2012
   - B) 2014
   - C) 2016
   - D) 2018

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 2014**

**Explicación:**
Project Calico se inició en 2014 en Metaswitch. Desde entonces, se ha convertido en uno de los plugins CNI de Kubernetes más utilizados a nivel mundial. En 2016, se fundó Tigera para comercializar Calico y, en 2019, se lanzó Calico Enterprise.

</details>

2. ¿Qué empresa fundó Tigera y comercializó Calico?
   - A) Google
   - B) Red Hat
   - C) Fundadores de Metaswitch
   - D) VMware

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Fundadores de Metaswitch**

**Explicación:**
Tigera fue fundada en 2016 por los creadores originales de Project Calico de Metaswitch. Actualmente, Tigera mantiene tanto el proyecto Calico de código abierto como productos comerciales, incluidos Calico Enterprise y Calico Cloud.

</details>

3. ¿Cuál de las siguientes NO es una característica principal de Calico?
   - A) Enrutamiento basado en BGP
   - B) Service mesh integrado con inyección de sidecar
   - C) Políticas de red estándar y extendidas de Kubernetes
   - D) Compatibilidad con eBPF dataplane

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Service mesh integrado con inyección de sidecar**

**Explicación:**
Calico proporciona redes de alto rendimiento con enrutamiento basado en BGP, potentes políticas de red (tanto las estándar de Kubernetes como las extendidas de Calico) y compatibilidad con eBPF dataplane. Sin embargo, a diferencia de Cilium, Calico no incluye un service mesh integrado. La funcionalidad de service mesh está disponible por separado a través de Calico Enterprise o mediante la integración con otras soluciones de service mesh como Istio.

</details>

4. ¿Cuál es la principal ventaja de las redes basadas en BGP de Calico en comparación con las redes overlay tradicionales?
   - A) Configuración más sencilla
   - B) Mejor cifrado de seguridad
   - C) Enrutamiento directo sin sobrecarga de encapsulación
   - D) Resolución de DNS integrada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Enrutamiento directo sin sobrecarga de encapsulación**

**Explicación:**
Las redes basadas en BGP de Calico permiten el enrutamiento directo de paquetes entre nodos sin la sobrecarga de encapsulación (como VXLAN o IPIP). Esto produce un mejor rendimiento de red, menor latencia y una integración más sencilla con la infraestructura de red existente. Las redes overlay tradicionales añaden encabezados de encapsulación que aumentan el tamaño de los paquetes y la sobrecarga de procesamiento.

</details>

5. ¿Qué entornos admite Calico?
   - A) Solo cloud
   - B) Solo on-premises
   - C) Cloud, on-premises e híbrido
   - D) Solo Kubernetes, sin compatibilidad con VM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cloud, on-premises e híbrido**

**Explicación:**
Calico es una solución de redes versátil que admite múltiples entornos, incluidos cloud público (AWS, Azure, GCP), centros de datos on-premises y despliegues híbridos. También se puede utilizar con máquinas virtuales y cargas de trabajo bare-metal, no solo con contenedores de Kubernetes.

</details>

6. ¿Qué opciones de dataplane admite Calico?
   - A) Solo iptables
   - B) Solo eBPF
   - C) iptables y eBPF
   - D) Solo IPVS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) iptables y eBPF**

**Explicación:**
Calico admite los dataplanes iptables y eBPF. El dataplane iptables es la opción tradicional y más madura, mientras que el modo eBPF se introdujo en 2020 y ofrece un rendimiento mejorado con un menor uso de CPU. Los usuarios pueden elegir el dataplane que mejor se adapte a sus requisitos y a la compatibilidad con la versión del kernel.

</details>

7. ¿Qué es calicoctl?
   - A) Una interfaz gráfica de usuario para Calico
   - B) Una herramienta de línea de comandos para gestionar recursos de Calico
   - C) Un operador de Kubernetes para Calico
   - D) Un panel de monitorización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una herramienta de línea de comandos para gestionar recursos de Calico**

**Explicación:**
calicoctl es una herramienta de interfaz de línea de comandos para gestionar recursos de Calico, como políticas de red, grupos de IP, configuraciones de BGP y nodos. Proporciona acceso directo al almacén de datos de Calico y es esencial para la resolución de problemas, el diagnóstico y las tareas de configuración avanzada que podrían no realizarse fácilmente solo mediante kubectl.

</details>

8. ¿Cuál es la relación entre Calico OSS y Calico Enterprise?
   - A) Son productos completamente independientes sin código compartido
   - B) Calico Enterprise es la versión comercial construida sobre Calico OSS
   - C) Calico OSS está obsoleto en favor de Calico Enterprise
   - D) Calico Enterprise solo funciona con Calico Cloud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico Enterprise es la versión comercial construida sobre Calico OSS**

**Explicación:**
Calico Enterprise es la oferta comercial de Tigera que se basa en el proyecto Calico de código abierto. Añade características empresariales como detección avanzada de amenazas, informes de cumplimiento, gestión multiclúster y soporte comercial. La funcionalidad principal de redes y políticas se comparte entre ambas versiones.

</details>

9. ¿En qué año introdujo Calico la compatibilidad con eBPF dataplane?
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 2020**

**Explicación:**
Calico introdujo la compatibilidad con eBPF dataplane en 2020. Fue un hito significativo que permitió a Calico ofrecer un rendimiento mejorado con características como Direct Server Return (DSR), balanceo de carga en el momento de la conexión y la capacidad de reemplazar kube-proxy, todo ello mientras utiliza menos CPU que el dataplane iptables.

</details>

10. ¿Qué es Calico Cloud?
    - A) Un servicio gestionado de Kubernetes
    - B) Una plataforma SaaS para la seguridad de red de Calico
    - C) Una solución de almacenamiento cloud
    - D) Un servicio CDN para Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una plataforma SaaS para la seguridad de red de Calico**

**Explicación:**
Calico Cloud, lanzado en 2022, es una oferta SaaS (Software como servicio) de Tigera que proporciona características de Calico Enterprise como servicio gestionado. Simplifica el despliegue y la gestión de características avanzadas de seguridad de red, observabilidad y cumplimiento sin la sobrecarga operativa de autogestionar los componentes empresariales.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/01-introduction.md) | [Siguiente cuestionario: Arquitectura](./02-architecture-quiz.md)
