# Cuestionario de introducción a la ingeniería de plataformas

[Guía relacionada](../../platform-engineering/00-platform-engineering-overview.md)

## 1. ¿Cuál es el objetivo principal de la ingeniería de plataformas?

<details>
<summary>Respuesta y explicación</summary>

Comprender las necesidades de los desarrolladores y proporcionar APIs de autoservicio aprobadas, CLIs, portales, plantillas y soporte operativo como un producto interno. No elimina a los equipos de operaciones ni presupone toda la responsabilidad de cada aplicación.
</details>

## 2. ¿Cómo se deben interpretar las asignaciones de Start, Advance, Excel y herramientas?

<details>
<summary>Respuesta y explicación</summary>

Organizan las tareas de mejora en la guía de ingeniería de plataformas de AWS. Advance aborda la automatización de IaC/autoservicio; las asignaciones de Kubernetes de esta guía son ejemplos didácticos, no puntuaciones oficiales de certificación ni una secuencia universal.
</details>

## 3. ¿Cómo se relacionan la ingeniería de plataformas, DevOps y SRE?

<details>
<summary>Respuesta y explicación</summary>

Son complementarios: las plataformas enfatizan la experiencia del desarrollador y los productos reutilizables, DevOps la colaboración y la entrega, y SRE la confiabilidad y la ingeniería de operaciones. Las estructuras y jerarquías de los equipos no son universales.
</details>

## 4. ¿Cuáles son las capas de IDP y el alcance de un portal de Backstage?

<details>
<summary>Respuesta y explicación</summary>

La interfaz, la orquestación, los recursos y la infraestructura forman un modelo de referencia. Un portal de estilo Backstage forma parte de la interfaz, no sustituye el aprovisionamiento, las políticas, el entorno de ejecución, la documentación ni el soporte.
</details>

## 5. ¿Puede desviarse de un Golden Path eludir una política de seguridad obligatoria?

<details>
<summary>Respuesta y explicación</summary>

No. Es una ruta recomendada con soporte, pero las excepciones siguen estando sujetas a la aprobación organizacional y a las políticas obligatorias de seguridad y datos. No se garantiza que sea óptima para todos los casos.
</details>

## 6. ¿Un solo WebApplication siempre hace que kro cree Deployments, RDS e IAM?

<details>
<summary>Respuesta y explicación</summary>

No. WebApplication es un ejemplo de API personalizada que requiere un RGD/CRD. kro gestiona los recursos de Kubernetes declarados; los controladores de servicio ACK autorizados llaman a las APIs de AWS. Las combinaciones de recursos, la preparación y las políticas de eliminación dependen de las definiciones.
</details>

## 7. ¿Cuáles son las métricas DORA actuales y cómo se deben utilizar?

<details>
<summary>Respuesta y explicación</summary>

El tiempo de entrega de cambios, la frecuencia de despliegue, el tiempo de recuperación de despliegues fallidos, la tasa de fallos de cambios y la tasa de retrabajo de despliegues. Mejoran la entrega y la estabilidad del servicio o equipo, en lugar de sustituir un MTTR genérico o clasificaciones individuales. La medición puede comenzar antes de Excel.
</details>

## 8. ¿Los guardrails garantizan automáticamente la seguridad y el cumplimiento?

<details>
<summary>Respuesta y explicación</summary>

No. Aplique y verifique las políticas, la gestión de omisiones/excepciones, los permisos y los cambios, con auditoría y recuperación. Los guardrails no sustituyen las responsabilidades de la aplicación respecto al manejo de datos ni la evaluación de los requisitos legales.
</details>
