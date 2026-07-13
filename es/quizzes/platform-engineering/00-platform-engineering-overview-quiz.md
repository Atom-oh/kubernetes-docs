# Cuestionario de descripción general de Platform Engineering

> Este cuestionario evalúa tu comprensión del documento [Descripción general de Platform Engineering](../../platform-engineering/00-platform-engineering-overview.md).

---

1. ¿Cuál es el objetivo principal de Platform Engineering?
   - A) Capacitar a todos los desarrolladores para gestionar la infraestructura directamente
   - B) Crear una Internal Developer Platform (IDP, plataforma interna para desarrolladores) para el autoservicio de los desarrolladores
   - C) Reemplazar por completo el rol del equipo de operaciones con automatización
   - D) Migrar todas las aplicaciones a serverless

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear una Internal Developer Platform (IDP, plataforma interna para desarrolladores) para el autoservicio de los desarrolladores**

**Explicación:**
Platform Engineering es la disciplina de crear una IDP que permite a los desarrolladores desplegar aplicaciones de forma rápida y segura sin tratar directamente con la complejidad de la infraestructura. El objetivo no es enseñar a los desarrolladores la gestión de infraestructura, sino proporcionar interfaces de autoservicio abstraídas.

</details>

---

2. En el modelo de madurez de AWS CAF, ¿qué etapa corresponde a "automatización de infraestructura mediante IaC" y "entrega de productos de autoservicio"?
   - A) START
   - B) ADVANCE
   - C) EXCEL
   - D) Común en todas las etapas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ADVANCE**

**Explicación:**
En el modelo de madurez de AWS CAF, la etapa ADVANCE se centra en ampliar la automatización y crear observabilidad centralizada. La automatización de infraestructura (IaC, productos de autoservicio) es una capacidad de ADVANCE construida sobre la base de START. START cubre la construcción de la base, mientras que EXCEL cubre la optimización continua.

</details>

---

3. ¿Qué afirmación describe correctamente la relación entre Platform Engineering, DevOps y SRE?
   - A) Los tres son enfoques mutuamente excluyentes
   - B) Platform Engineering reemplaza DevOps y SRE
   - C) Platform Engineering empaqueta los principios de DevOps y las prácticas de SRE como un producto
   - D) SRE es un superconjunto que abarca Platform Engineering y DevOps

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Platform Engineering empaqueta los principios de DevOps y las prácticas de SRE como un producto**

**Explicación:**
Los tres enfoques son complementarios. DevOps proporciona cultura y metodología, SRE proporciona prácticas de ingeniería operativa, y Platform Engineering las empaqueta en un producto llamado Internal Developer Platform.

</details>

---

4. En la arquitectura de referencia de IDP basada en Kubernetes, ¿a qué capa pertenecen ArgoCD, FluxCD y KRO?
   - A) Capa de interfaz para desarrolladores
   - B) Capa de integración/orquestación
   - C) Capa de recursos
   - D) Capa de infraestructura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Capa de integración/orquestación**

**Explicación:**
La capa de integración/orquestación gestiona la administración del estado declarativo y la automatización del despliegue. ArgoCD y FluxCD proporcionan despliegue basado en GitOps, y KRO proporciona orquestación de grafos de recursos. La capa de interfaz para desarrolladores es para UIs/CLIs como Backstage, la capa de recursos es para ACK/Helm/Operators, y la capa de infraestructura es para EKS/VPC/IAM.

</details>

---

5. ¿Qué afirmación sobre Golden Paths (rutas doradas) NO es correcta?
   - A) Son rutas de despliegue recomendadas proporcionadas por el equipo de plataforma
   - B) Son reglas obligatorias que los desarrolladores deben seguir
   - C) Guían a los desarrolladores para comenzar rápidamente usando métodos validados
   - D) Los desarrolladores pueden desviarse cuando sea necesario, pero son la opción óptima en la mayoría de los casos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Son reglas obligatorias que los desarrolladores deben seguir**

**Explicación:**
Golden Paths son "recomendados", no "impuestos". Proporcionan métodos de despliegue que el equipo de plataforma ha validado y optimizado, pero los desarrolladores pueden elegir enfoques diferentes cuando sea necesario. El objetivo es diseñar Golden Paths de modo que sean la opción óptima para la mayoría de los casos de uso.

</details>

---

6. En el patrón de autoservicio que combina ResourceGraphDefinition (RGD) de KRO y ACK, ¿qué combinación de recursos se crea automáticamente cuando un desarrollador envía un único manifest?
   - A) Deployment + ConfigMap + PVC
   - B) Deployment + Service + RDS Instance + IAM Role
   - C) StatefulSet + Service + DynamoDB Table
   - D) Pod + Ingress + S3 Bucket

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Deployment + Service + RDS Instance + IAM Role**

**Explicación:**
En el patrón de autoservicio KRO RGD + ACK, el único manifest WebApplication de un desarrollador hace que KRO cree automáticamente recursos nativos de Kubernetes (Deployment + Service) y recursos de AWS mediante ACK (RDS Instance, IAM Role). Este es el valor central de una IDP: abstraer la complejidad de la infraestructura.

</details>

---

7. En el modelo de madurez de AWS CAF, ¿a qué etapa y área de capacidad pertenecen las métricas DORA?
   - A) START - Gestión de costos
   - B) ADVANCE - Observabilidad central
   - C) EXCEL - Métricas de plataforma
   - D) Común en todas las etapas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) EXCEL - Métricas de plataforma**

**Explicación:**
Las métricas DORA (Deployment Frequency, Lead Time, MTTR, Change Failure Rate) pertenecen a la capacidad "Métricas de plataforma" en la etapa EXCEL. Esto representa el nivel de madurez más alto, que logra la optimización continua mediante métricas alineadas con los objetivos de la organización.

</details>

---

8. Entre los valores centrales de una IDP, ¿cuál incorpora seguridad y cumplimiento de forma predeterminada para que los desarrolladores puedan trabajar en un entorno seguro sin configuración explícita de seguridad?
   - A) Self-Service
   - B) Guardrails
   - C) Estandarización
   - D) Automatización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Guardrails**

**Explicación:**
Los Guardrails incorporan seguridad y cumplimiento en la plataforma de forma predeterminada. Incluso sin que los desarrolladores configuren explícitamente la seguridad, la plataforma aplica automáticamente políticas de seguridad (Pod Security Standards, network policies, image scanning, etc.). Self-Service se relaciona con el aprovisionamiento directo, la estandarización con Golden Paths, y la automatización con eliminar tareas repetitivas.

</details>
