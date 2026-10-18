# Cuestionario sobre Landing Zone, OUs y control organizativo

> Este cuestionario evalúa su comprensión de [Landing Zone, OUs y control organizativo](../../governance/01-landing-zone-and-ou.md).

---

1. ¿Qué precede a la activación de IdentityCenterBaseline en Control Tower 4.0?
   - A) Ninguna baseline
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

2. ¿Qué afirmación describe la Security OU de Control Tower 4.0?
   - A) Todas las OUs son Security OUs
   - B) La OU que contiene las Accounts de integración de servicios se designa como Security OU
   - C) Se eliminaron las Security OUs
   - D) Todas las Accounts generales de esa OU reciben todas las baselines

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La OU que contiene las Accounts de integración de servicios se designa como Security OU**

**Explicación:**
Las Accounts de integración comparten una OU principal y se administran mediante la landing zone. AWSControlTowerBaseline/ConfigBaseline no se aplican a esa Security OU. La ubicación separada de las Accounts de operaciones generales es una decisión de diseño.

</details>

---

3. ¿Por qué los paquetes de SCP en capas pueden ahorrar cuota de asociaciones directas?
   - A) Desaparecen los límites de tamaño de los documentos
   - B) Las políticas heredadas no consumen las asociaciones directas de la OU secundaria
   - C) Los permisos de la OU secundaria prevalecen sobre las denegaciones de la principal
   - D) La raíz no tiene cuota

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las políticas heredadas no consumen las asociaciones directas de la OU secundaria**

**Explicación:**
El límite de asociaciones directas es de 10 SCP por entidad. La herencia no consume estas ranuras, pero siguen aplicándose las restricciones efectivas de las políticas principales.

</details>

---

4. ¿Qué afirmación describe correctamente las asociaciones e herencia de RCP?
   - A) Conceden permisos directamente
   - B) No se pueden heredar
   - C) RCPFullAWSAccess ocupa una de cinco ranuras; diseñe conjuntamente las ranuras directas restantes y la herencia
   - D) Su límite de tamaño es igual al de las SCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) RCPFullAWSAccess ocupa una de cinco ranuras; diseñe conjuntamente las ranuras directas restantes y la herencia**

**Explicación:**
Quedan cuatro ranuras directas y los documentos admiten 5,120 caracteres. Este presupuesto no impide la herencia en capas. Compruebe los recursos compatibles y las excepciones de principal.

</details>
