# Cuestionario sobre la descripción general de la gobernanza de la nube empresarial

> Este cuestionario evalúa su comprensión de la [descripción general de la gobernanza de la nube empresarial](../../governance/00-governance-overview.md).

---

1. ¿Cuál es la idea principal al evaluar de forma «independiente» los límites de Account, VPC y EKS?
   - A) Crear siempre los tres límites a la vez, según el nombre del equipo
   - B) Decidir cada límite por separado y según distintos criterios (seguridad/cuota/propiedad, red/zona de confianza y radio de impacto del runtime)
   - C) Usar una sola Account, VPC y clúster compartidos para todas las cargas de trabajo
   - D) Decidir únicamente el límite de VPC y dejar que los demás se definan automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Decidir cada límite por separado y según distintos criterios (seguridad/cuota/propiedad, red/zona de confianza y radio de impacto del runtime)**

**Explicación:**
Account se evalúa según la seguridad, las cuotas, la propiedad de los costos y el ciclo de vida; VPC, según la política de red y la zona de confianza; y EKS, según el radio de impacto del runtime. La fórmula fija que crea los tres límites juntos para cada combinación de dominio y entorno es más sencilla, pero trata límites fundamentalmente distintos como si fueran uno solo.

</details>

---

2. ¿En qué Account debe residir el rol principal de IAM de una asociación de Pod Identity?
   - A) En cualquier Account
   - B) En la misma Account que el clúster
   - C) Solo en la Account de administración
   - D) En una Account por cada Region

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En la misma Account que el clúster**

**Explicación:**
El rol principal de la asociación debe estar en la Account del clúster. La función de rol objetivo usa encadenamiento de roles, mientras que las políticas de recursos compatibles e IRSA ofrecen otras vías entre cuentas.

</details>

---

3. ¿Por qué se debe distinguir un Workload ID estable de los metadatos mutables?
   - A) Para reducir el costo de las llamadas a la API de AWS
   - B) Para que los cambios recurrentes, como las reorganizaciones y la consolidación de marcas, no se conviertan directamente en migraciones de infraestructura
   - C) Para simplificar la configuración de Kubernetes RBAC
   - D) Para consolidar todas las cargas de trabajo en una sola Account

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para que los cambios recurrentes, como las reorganizaciones y la consolidación de marcas, no se conviertan directamente en migraciones de infraestructura**

**Explicación:**
Los equipos cambian con frecuencia debido a las reorganizaciones, mientras que los dominios (capacidades empresariales) son relativamente estables. Vincular directamente los límites de Account o VPC a los nombres de equipos o marcas convierte cada reorganización en una migración. Por eso se recomienda asociar dominio, marca, equipo, CUJ y otros datos como metadatos mutables a un Workload ID estable.

</details>
