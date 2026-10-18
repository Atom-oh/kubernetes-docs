# Cuestionario sobre límites de datos y seguridad

> Este cuestionario evalúa su comprensión de [los límites de datos y seguridad](../../governance/05-data-security-boundaries.md).

---

1. ¿Qué se deduce de que no se pueda compartir una instantánea de un clúster de base de datos Multi-AZ?
   - A) Ninguna vía de recuperación es posible
   - B) Esa vía de uso compartido de RDS no está disponible; valide alternativas de recuperación específicas del motor
   - C) Las bases de datos deben pertenecer a las cargas de trabajo
   - D) Todos los vaults de AWS Backup se comportan igual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Esa vía de uso compartido de RDS no está disponible; valide alternativas de recuperación específicas del motor**

**Explicación:**
Una restricción de API no descarta todas las alternativas de backup lógico ni de replicación. Valide el soporte y los objetivos de RTO/RPO antes de decidir quién será el propietario.

</details>

---

2. ¿Qué se debe incluir en el RTO de una vía de recuperación que requiere una copia posterior al incidente?
   - A) Solo la nomenclatura de etiquetas
   - B) El tiempo para copiar, restaurar y validar la aplicación
   - C) Solo la retención histórica
   - D) Solo la puntuación de Security Hub

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tiempo para copiar, restaurar y validar la aplicación**

**Explicación:**
Cuando hay copias preexistentes, la frecuencia de copia afecta el RPO. Distinga las vías de restauración desde un vault aislado compartido que no necesitan una copia para el destinatario.

</details>

---

3. ¿Qué afirmación sobre autorización es correcta después de habilitar el backup entre cuentas?
   - A) Todos los usuarios omiten las denegaciones de IAM
   - B) Revisar en conjunto IAM, el vault, KMS, las condiciones del destino de copia y el uso compartido de RAM
   - C) Los vaults pasan a ser públicos
   - D) Los backups copiados se eliminan al salir de la organización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Revisar en conjunto IAM, el vault, KMS, las condiciones del destino de copia y el uso compartido de RAM**

**Explicación:**
Habilitar una función no concede permisos. La copia a un vault estándar y el uso compartido de un vault aislado son vías distintas; pruebe los destinos aprobados y la indisponibilidad del origen.

</details>

---

4. ¿Qué implica la dependencia de Config de Security Hub CSPM?
   - A) Todos los controles funcionan sin Config
   - B) La mayoría de los controles de CSPM necesitan registrar recursos; esta dependencia no corresponde al servicio Identity Center
   - C) Reemplaza GuardDuty
   - D) Todas las solicitudes de AWS MCP necesitan Config

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La mayoría de los controles de CSPM necesitan registrar recursos; esta dependencia no corresponde al servicio Identity Center**

**Explicación:**
Distinga las dependencias de las baselines administradas por Control Tower de los requisitos del servicio Identity Center. Compruebe el alcance de las capacidades de Security Hub y la cobertura de Regions.

</details>
