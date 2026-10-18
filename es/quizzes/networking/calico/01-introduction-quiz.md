# Cuestionario de introducción a Calico

> **Documento relacionado**: [Introducción a Calico](../../../networking/calico/01-introduction.md)
> **Última actualización**: 12 de septiembre de 2026

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
Los orígenes de Project Calico se remontan a 2014 en Metaswitch. Tigera se fundó en 2016. No confundas el origen del proyecto con lanzamientos posteriores de productos o fechas de lanzamiento de Calico.

</details>

2. ¿Qué empresa es la principal responsable del mantenimiento de Calico y ofrece Calico Enterprise y Calico Cloud?
   - A) Google
   - B) Red Hat
   - C) Tigera
   - D) VMware

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Tigera**

**Explicación:**
Tigera mantiene Calico junto con colaboradores de la comunidad y ofrece productos comerciales. «Fundadores de Metaswitch» describe a personas, no el nombre de la empresa por la que se pregunta. Que el proyecto aparezca en el CNCF Landscape no significa que la CNCF lo gobierne.

</details>

3. ¿Cuál de estas afirmaciones NO es cierta sobre la instalación predeterminada de Calico?
   - A) Enrutamiento basado en BGP
   - B) Inyecta automáticamente sidecars de Istio en todos los Pods
   - C) Políticas de red estándar y extendidas de Kubernetes
   - D) Compatibilidad con el plano de datos eBPF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inyecta automáticamente sidecars de Istio en todos los Pods**

**Explicación:**
Calico proporciona redes, políticas y planos de datos que se pueden seleccionar. Las integraciones con mallas de servicios son funciones y configuraciones independientes; la instalación de este laboratorio no inyecta automáticamente sidecars de Istio. Las funciones de malla de Cilium también requieren su propia configuración; una comparación de CNI no debe dar a entender que todas las funciones de malla estén habilitadas de forma predeterminada.

</details>

4. ¿Qué puede ofrecer una topología Calico sin encapsulación, si BGP y las rutas de la red subyacente están configurados correctamente?
   - A) Una configuración más sencilla
   - B) Un cifrado de seguridad mejor
   - C) Enrutamiento sin encabezados de encapsulación overlay, cuando la red subyacente admite rutas de Pods
   - D) Resolución DNS integrada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Enrutamiento sin encabezados de encapsulación overlay, cuando la red subyacente admite rutas de Pods**

**Explicación:**
BGP distribuye rutas. Si la red subyacente puede enrutar direcciones de Pods y la encapsulación está deshabilitada, los paquetes no necesitan una envoltura IPIP/VXLAN. BGP también puede coexistir con IPIP, así que habilitar BGP por sí solo no elimina la encapsulación. Tampoco cifra el tráfico ni garantiza una latencia menor para todas las cargas de trabajo.

</details>

5. ¿En qué entornos se pueden usar las configuraciones y ediciones de producto de Calico adecuadas?
   - A) Solo en la nube
   - B) Solo en instalaciones locales
   - C) En la nube, en instalaciones locales y en entornos híbridos
   - D) Solo con Kubernetes, sin compatibilidad con máquinas virtuales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) En la nube, en instalaciones locales y en entornos híbridos**

**Explicación:**
Calico se usa en entornos de nube, locales e híbridos, pero siguen aplicándose las limitaciones de plataforma, kernel, plano de datos y edición. GKE Dataplane V2 usa específicamente Cilium, no Calico. Las capacidades para máquinas virtuales y Windows no son idénticas a las de Kubernetes en Linux.

</details>

6. ¿Qué lista incluye las opciones compatibles del plano de datos de Calico para Linux?
   - A) Solo iptables
   - B) Solo eBPF
   - C) iptables, nftables y eBPF
   - D) Solo IPVS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) iptables, nftables y eBPF**

**Explicación:**
Calico admite estas opciones del plano de datos para Linux. Los modos de encapsulación, como VXLAN/IPIP, son una elección distinta; e IPVS es un backend de kube-proxy, no un plano de datos completo de Calico. Elige según los requisitos del kernel, la plataforma y las funciones; el laboratorio usa explícitamente iptables.

</details>

7. ¿Qué es calicoctl?
   - A) Una interfaz gráfica de usuario para Calico
   - B) Una herramienta de línea de comandos para administrar recursos de Calico
   - C) Un operador de Kubernetes para Calico
   - D) Un panel de monitorización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una herramienta de línea de comandos para administrar recursos de Calico**

**Explicación:**
calicoctl administra recursos de Calico y ofrece diagnósticos, como operaciones de IPAM/BGP. Usa una versión de cliente compatible. Muchas operaciones habituales con recursos también se pueden realizar mediante kubectl y el servidor de API de Calico. calicoctl node status requiere un entorno de nodo adecuado; un kubeconfig de portátil por sí solo no basta.

</details>

8. ¿Qué relación hay entre Calico OSS y Calico Enterprise?
   - A) Son productos completamente separados, sin código compartido
   - B) Calico Enterprise es la versión comercial basada en Calico OSS
   - C) Calico OSS está obsoleto y ha sido sustituido por Calico Enterprise
   - D) Calico Enterprise solo funciona con Calico Cloud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico Enterprise es la versión comercial basada en Calico OSS**

**Explicación:**
Enterprise amplía la tecnología de Calico con funciones y soporte comerciales. El código abierto también incluye niveles de políticas y observabilidad con Goldmane/Whisker, y se puede ejecutar en producción. Consulta la matriz de funciones vigente en lugar de suponer que todas las funciones avanzadas son de pago o que OSS solo sirve para clústeres pequeños.

</details>

9. ¿En qué año incorporó Calico la compatibilidad con el plano de datos eBPF?
   - A) 2018
   - B) 2019
   - C) 2020
   - D) 2022

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 2020**

**Explicación:**
El anuncio oficial del 25 de febrero de 2020 presentó el nuevo plano de datos como vista previa tecnológica para Calico 3.13. No fue un anuncio de disponibilidad general. eBPF se ejecuta en el kernel de Linux y puede sustituir partes del procesamiento convencional de paquetes, no el kernel en sí. El rendimiento depende de la carga de trabajo medida.

</details>

10. ¿Qué es Calico Cloud?
   - A) Un servicio administrado de Kubernetes
   - B) Una plataforma SaaS para la seguridad de red de Calico
   - C) Una solución de almacenamiento en la nube
   - D) Un servicio CDN para Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una plataforma SaaS para la seguridad de red de Calico**

**Explicación:**
Calico Cloud es la oferta SaaS de Tigera para seguridad y observabilidad de red. No es un servicio de alojamiento de Kubernetes, un almacén de objetos ni una CDN. Sus funciones y responsabilidades difieren de las de Enterprise autoadministrado; aun así, se requiere integrar y configurar el clúster. La fecha de lanzamiento de 2022, que carecía de respaldo en la versión anterior, no es necesaria para esta definición.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/01-introduction.md) | [Siguiente cuestionario: Arquitectura](02-architecture-quiz.md)
