# Cuestionario de Dynatrace

> **Última actualización**: September 13, 2026

---

1. ¿Qué afirmación sobre OneAgent es incorrecta?
   - A) Puede descubrir procesos compatibles.
   - B) Puede instrumentar tecnologías compatibles.
   - C) La instalación elimina todos los requisitos de permisos, alcance y conectividad.
   - D) La cobertura depende del modo de despliegue y de la compatibilidad tecnológica.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La instalación elimina todos los requisitos de permisos, alcance y conectividad.**

El descubrimiento automático no elimina los privilegios de instalación, los requisitos de runtimes compatibles, la salida de red, la configuración de tokens, la selección de inyección ni las decisiones de privacidad de datos. No garantiza que se capture cada método/solicitud.

</details>

---

2. ¿Qué componente administra los recursos de DynaKube y las cargas de trabajo de Dynatrace en Kubernetes?
   - A) Un binario kubectl independiente.
   - B) Dynatrace Operator.
   - C) Solo el proceso OneAgent.
   - D) Una función Lambda creada automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Dynatrace Operator.**

Helm o los manifiestos instalan el Operator; no son modos de monitorización que compitan entre sí. El Operator/chart revisado es la versión 1.10.2. Su CRD publicado sirve v1beta5 y v1beta6, con v1beta6 como almacenamiento; el ejemplo antiguo de v1beta2 no es una API servida actualmente. Aún deben revisarse las versiones de los componentes y el comportamiento de actualización.

</details>

---

3. ¿Qué resultado no está implícito al habilitar la detección de problemas y el análisis de causa raíz?
   - A) Análisis de línea base y anomalías.
   - B) Investigación con conocimiento de la topología.
   - C) Los cambios de código de producción no revisados se autorizan automáticamente.
   - D) Análisis de impacto mediante evidencia recopilada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los cambios de código de producción no revisados se autorizan automáticamente.**

La terminología Davis permanece en material anterior; la documentación actual utiliza Dynatrace Intelligence. Se pueden configurar acciones/flujos de trabajo agénticos aprobados, incluidas las funcionalidades Preview, por lo que «la IA nunca puede tomar medidas» también es una afirmación demasiado amplia. La detección por sí sola no concede autoridad de remediación ni prueba que un diagnóstico sea correcto.

</details>

---

4. ¿Qué combina cloudNativeFullStack?
   - A) Solo monitorización de Windows.
   - B) Monitorización de host e inyección de módulos de código de aplicación basada en webhook.
   - C) Monitorización solo de aplicaciones sin componente de host.
   - D) Una garantía de menor sobrecarga en cada carga de trabajo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Monitorización de host e inyección de módulos de código de aplicación basada en webhook.**

El Operator publicado describe cloudNativeFullStack como la combinación de hostMonitoring y applicationMonitoring, mediante su infraestructura CSI. No es simplemente un sidecar de aplicación. classicFullStack sigue presente en la versión revisada; no debe describirse como eliminado. El modo, el sistema operativo y los permisos de CSI determinan su idoneidad.

</details>

---

5. ¿Qué capacidad se asocia con PurePath?
   - A) Compresión de logs.
   - B) Trazado distribuido con contexto a nivel de código compatible.
   - C) Un dispositivo universal de captura de paquetes.
   - D) Copia de seguridad de bases de datos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trazado distribuido con contexto a nivel de código compatible.**

La visibilidad de trazas y código depende de las tecnologías compatibles, la instrumentación, la configuración de captura/muestreo y la telemetría disponible. «Ruta completa» no prueba que se conserve cada solicitud, método o relación asíncrona.

</details>

---

6. ¿Qué medida utiliza la monitorización Full-Stack basada en host de DPS actual?
   - A) vCPU más RAM.
   - B) GiB-horas de memoria monitorizada según la tarifa aplicable.
   - C) max(RAM/16, vCPU/1.5) Host Units.
   - D) Una unidad fija por namespace de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) GiB-horas de memoria monitorizada según la tarifa aplicable.**

El proveedor documenta intervalos de facturación de 15 minutos, redondeo de RAM a 0.25 GiB y un mínimo de host de 4 GiB. La monitorización de aplicaciones solo basada en contenedores tiene reglas diferentes de memoria/mínimos. La antigua fórmula máxima de CPU/RAM no es el cálculo actual de DPS. La aritmética de uso no es una factura: importan el compromiso, la tarifa, las asignaciones y las capacidades facturadas por separado.

</details>

---

7. ¿Cuál no es una función de ActiveGate?
   - A) Enrutar telemetría.
   - B) Monitorización configurada de la API de Kubernetes.
   - C) Actuar como lakehouse de datos analíticos a largo plazo.
   - D) Proporcionar una ruta de conectividad aprobada al entorno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actuar como lakehouse de datos analíticos a largo plazo.**

El enrutamiento/la monitorización y el almacenamiento en búfer local son diferentes del almacenamiento backend a largo plazo. Algunas configuraciones de ingesta de ActiveGate en contenedores requieren un PVC. Una ruta SaaS aún necesita conectividad; un proxy no permite que una red completamente desconectada alcance SaaS.

</details>

---

8. ¿Qué selecciona oneAgent.cloudNativeFullStack.namespaceSelector?
   - A) Namespaces que se deben crear.
   - B) Namespaces elegibles para la inyección de webhook configurada.
   - C) Un límite de aislamiento de red.
   - D) El alcance completo de la monitorización de host y de la API de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Namespaces elegibles para la inyección de webhook configurada.**

El selector y las anotaciones de inyección de Pod controlan la inyección de webhook. No restringen la monitorización de host de OneAgent ni la monitorización de la API de Kubernetes de ActiveGate. El enriquecimiento de metadatos y la configuración automática del exportador OTLP tienen sus propios selectores. Proteja las etiquetas y los permisos de actualización de DynaKube; los selectores no son RBAC ni un límite de facturación.

</details>

---

9. ¿Qué transporte acepta la API OTLP nativa documentada de Dynatrace SaaS/ActiveGate?
   - A) Solo gRPC.
   - B) HTTP con Protocol Buffers binarios.
   - C) gRPC y HTTP/JSON indistintamente.
   - D) Solo un formato propietario que no es OTLP.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) HTTP con Protocol Buffers binarios.**

El endpoint nativo admite HTTP/protobuf, no gRPC ni JSON de protobuf. Un Collector puede aceptar gRPC y exportar HTTP a Dynatrace. Utilice la base /api/v2/otlp y el sufijo de señal correctos, TLS y el tipo/los alcances de token requeridos por el endpoint seleccionado. No sustituya una URL de navegador .apps.

</details>

---

10. ¿Qué proporciona Smartscape?
   - A) Un interruptor universal para silenciar alertas.
   - B) Mapeo de topología y dependencias a partir de datos observados.
   - C) Autorización automática para el escalado.
   - D) Revisión de código fuente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mapeo de topología y dependencias a partir de datos observados.**

El grafo de dependencias permite el análisis de impacto y la investigación. Su cobertura depende de las tecnologías monitorizadas y de la telemetría; las relaciones ausentes o las brechas de datos no deben considerarse prueba de que no existe ninguna dependencia.

</details>

---

[Volver a la guía](../../../observability/tracing/04-dynatrace.md)
