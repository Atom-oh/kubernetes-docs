# Cuestionario sobre Landing Zone, unidades organizativas (OU) y control organizativo

> Este cuestionario evalúa su comprensión de [Landing Zone, unidades organizativas (OU) y control organizativo](../../governance/01-landing-zone-and-ou.md).

---

1. ¿Qué precede a la activación de IdentityCenterBaseline en Control Tower 4.0?
   - A) Ninguna configuración base
   - B) CentralSecurityRolesBaseline y su requisito previo, CentralConfigBaseline
   - C) BackupCentralVaultBaseline
   - D) Identity Center requiere Config en todos los entornos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CentralSecurityRolesBaseline y su requisito previo, CentralConfigBaseline**

**Explicación:**
Esta es una dependencia de la baseline administrada por Control Tower, no un requisito universal de Config para el servicio Identity Center.

</details>

---

2. ¿Qué afirmación describe la OU de seguridad de Control Tower 4.0?
   - A) Todas las OU son OU de seguridad
   - B) La OU que contiene las cuentas de integración de servicios se designa como OU de seguridad
   - C) Se eliminaron las OU de seguridad
   - D) Todas las cuentas generales de esa OU reciben todas las baselines

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La OU que contiene las cuentas de integración de servicios se designa como OU de seguridad**

**Explicación:**
Las cuentas de integración comparten una OU principal y se administran mediante la landing zone. AWSControlTowerBaseline/ConfigBaseline no se aplican a esa OU de seguridad. Ubicar por separado las cuentas de operaciones generales es una decisión de diseño.

</details>

---

3. ¿Por qué los conjuntos de SCP organizados en capas pueden ahorrar cuota de asociaciones directas?
   - A) Desaparecen los límites de los documentos
   - B) Las políticas heredadas no consumen las asociaciones directas de la OU secundaria
   - C) Los permisos de la OU secundaria prevalecen sobre las denegaciones de la principal
   - D) La raíz tiene una cuota ilimitada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las políticas heredadas no consumen las asociaciones directas de la OU secundaria**

**Explicación:**
El límite de asociaciones directas es de 10 SCP por entidad. La herencia no consume estos espacios, pero siguen aplicándose las restricciones efectivas de las políticas principales.

</details>

---

4. ¿Qué afirmación describe correctamente las asociaciones y la herencia de RCP?
   - A) Conceden permisos directamente
   - B) No se pueden heredar
   - C) RCPFullAWSAccess ocupa uno de cinco espacios; diseñe conjuntamente los espacios directos restantes y la herencia
   - D) Su límite de tamaño es igual al de las SCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) RCPFullAWSAccess ocupa uno de cinco espacios; diseñe conjuntamente los espacios directos restantes y la herencia**

**Explicación:**
Quedan cuatro espacios directos y los documentos admiten 5,120 caracteres. Este presupuesto no impide la herencia en capas. Compruebe los recursos compatibles y las excepciones relativas al principal.

</details>
