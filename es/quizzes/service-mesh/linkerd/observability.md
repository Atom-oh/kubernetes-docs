# Cuestionario de observabilidad de Linkerd

Basado en la [guía de observabilidad](../../../service-mesh/linkerd/05-observability.md), revisada el 11 de septiembre de 2026.

### 1. ¿Cuál no es una de las tres métricas HTTP principales de los servicios en Linkerd?

- A. Tasa de éxito
- B. Tasa de solicitudes
- C. Latencia
- D. Uso de CPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** Las tres métricas son la tasa de éxito clasificada por el proxy, la tasa de solicitudes y la latencia. CPU y capacidad son información operativa adicional; esto no significa que el proxy u otro recolector no pueda exponer métricas de proceso o recursos. El TCP opaco no proporciona automáticamente métricas HTTP de los servicios.

</details>

### 2. ¿Cuál no es una columna estándar de la tabla `linkerd viz stat`?

- A. SUCCESS
- B. RPS
- C. LATENCY_P99
- D. ERROR_TYPE

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** La versión seleccionada incluye MESHED, SUCCESS, RPS, percentiles y TCP_CONN. La salida amplia agrega tasas de bytes de transporte, no un inventario de versiones del proxy. Para investigar errores, usa las políticas, Tap, los registros y las métricas que correspondan.

</details>

### 3. ¿Qué proporciona `linkerd viz tap`?

- A. Captura completa de paquetes de red
- B. Un flujo de observación en vivo de las solicitudes compatibles
- C. Cambios automáticos en las políticas del proxy
- D. Renovación de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Tap ofrece observación limitada o muestreada del tráfico; no es una auditoría completa. `max-rps` limita la tasa de solicitudes observadas por Tap y no limita todo el tráfico de la aplicación. La versión actual de Tap no tiene las opciones `--from` ni `--show-headers`; usa los selectores admitidos y protege el acceso a los metadatos de las solicitudes.

</details>

### 4. ¿Qué permiten los nombres de ruta de un ServiceProfile heredado?

- A. Contabilizar la E/S del disco
- B. Obtener métricas por ruta
- C. Generar automáticamente trazas distribuidas completas
- D. Hacer reintentos obligatorios en todos los métodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Los ServiceProfile admiten métricas por ruta y la vista `viz routes`. Siguen siendo una interfaz de compatibilidad y pueden prevalecer sobre la configuración de confiabilidad de una HTTPRoute de salida actual. Agregar un perfil para observar métricas no debe habilitar reintentos inseguros ni anular silenciosamente una política existente.

</details>

### 5. ¿Cómo accede localmente la guía al Prometheus de Viz que ya está instalado?

- A. Exponer un NodePort sin autenticación
- B. Crear un LoadBalancer público
- C. Usar `kubectl port-forward` enlazado a la interfaz de loopback
- D. Suponer que hay una URL pública

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El ejemplo reenvía el Service de Prometheus existente a `127.0.0.1`. No instala Prometheus ni configura autenticación pública. Para acceder desde otras cargas de trabajo también hay que configurar los ajustes de red y autorización de Linkerd que correspondan.

</details>

### 6. ¿Qué par corresponde al contexto de trazas W3C que usan los ejemplos de la aplicación?

- A. x-request-id y Authorization
- B. x-b3-traceid y x-b3-spanid
- C. traceparent y tracestate
- D. x-linkerd-proxy y Cookie

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Linkerd admite W3C y B3, y prefiere W3C cuando están presentes ambos formatos. `x-request-id` es un identificador de correlación, no un formato de traza obligatorio. Propagar encabezados no crea spans de aplicación ni configura el muestreo o la exportación; para esas tareas se necesita una biblioteca de trazas adecuada.

</details>

### 7. ¿Qué resume `linkerd viz top`?

- A. Los Pods ordenados por uso de CPU
- B. Las rutas o los recorridos de solicitudes observados en vivo
- C. Todos los mensajes de error históricos
- D. Los registros de contenedor más recientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `top` resume el tráfico en vivo y admite límites de muestreo y tasa, además de filtros compatibles. `hide-sources` controla la columna de origen, no los encabezados. Estas observaciones no sustituyen las métricas de Prometheus retenidas ni una auditoría completa de las solicitudes.

</details>

### 8. ¿Qué anotación cambia el nivel de los registros de diagnóstico del proxy?

- A. config.linkerd.io/log-level
- B. config.linkerd.io/proxy-log-level
- C. linkerd.io/proxy-log
- D. proxy.linkerd.io/log-level

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `proxy-log-level` controla el filtro de diagnóstico y `proxy-log-format` controla el formato de esos registros. El registro de acceso HTTP se habilita por separado con `config.linkerd.io/access-log:json` o `apache`. Una plantilla parcial de Pod es un fragmento o parche, no un Deployment completo.

</details>

### 9. ¿Cómo se calcula una proporción de éxito durante un intervalo?

- A. Dividir los contadores acumulados de éxitos y del total desde el inicio sin calcular una tasa
- B. Usar el contador inventado `success_total`
- C. Dividir la tasa de respuestas exitosas por la tasa total, con el mismo ámbito, el tratamiento de éxitos ausentes y un total positivo
- D. Calcular el promedio de una métrica inventada `success_rate`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Usa una sola dirección de observación y un ámbito de carga de trabajo y clúster coherente. Aunque no haya una serie de éxitos en un intervalo en que todas las respuestas fallaron, el resultado debe ser 0; los datos ausentes o inactivos no deben convertirse en un 100 % de éxito. La clasificación HTTP del proxy puede contar las respuestas 400 como exitosas, así que define la SLI de acuerdo con el objetivo de negocio.

</details>

### 10. ¿Qué función puede cumplir Jaeger en la configuración actual de trazas?

- A. Sustituir el descubrimiento de métricas de Kubernetes
- B. Agregar únicamente registros de acceso de las aplicaciones
- C. Recopilar, almacenar y consultar trazas distribuidas como backend administrado por separado
- D. Dividir el tráfico automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La extensión de Linkerd para Jaeger se eliminó en la versión 2.19. Linkerd ahora configura un recolector compatible con OpenTelemetry y, en la ruta de instalación de Helm mostrada, la identidad de malla para ese recolector. Que haya una interfaz de backend no demuestra que lleguen spans de la aplicación o del proxy ni que formen trazas completas.

</details>

### 11. ¿Qué información se debe obtener con `kubectl logs` o con un sistema de registros, en vez de suponer que Viz muestra los registros de contenedores?

- A. La topología de las cargas de trabajo
- B. Las métricas de Deployment
- C. Los registros de los contenedores de los Pods
- D. Las métricas de ruta de ServiceProfile

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Viz ofrece vistas de cargas de trabajo y tráfico, topología y Tap. Los registros de diagnóstico y de acceso son datos independientes. Aunque un flujo de trabajo consulte esas vistas, todavía necesita determinar la causa, aplicar una solución y verificarla; las vistas no resuelven un incidente por sí solas.

</details>

### 12. ¿Qué opción enlaza Viz con una instancia externa de Grafana a la que se accede desde el navegador?

- A. grafana.external:true
- B. grafana.externalUrl:https://grafana.example.com/
- C. grafana.enabled:false
- D. monitoring:external

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Viz no instala Grafana actualmente. `externalUrl` proporciona el enlace externo; `grafana.url` configura la opción de proxy inverso dentro del clúster, junto con los ajustes adicionales de raíz o subruta. Ninguna de las dos opciones crea Grafana, configura su origen de datos ni concede acceso a Prometheus.

</details>
