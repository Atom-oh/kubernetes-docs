# Cuestionario de integración con MWAA

Comprueba los límites de administración y la conectividad con EKS de MWAA 3.3.1/Python 3.12 aprovisionado.

1. ¿Se puede usar `kubectl` en el clúster EKS del cliente para inspeccionar el scheduler de MWAA?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Usa infraestructura Fargate administrada por AWS que se conecta a subredes privadas de la VPC del cliente.

**Explicación:** Esto no significa que MWAA no esté relacionado con la VPC. Los usuarios siguen administrando los DAG, IAM, la red, las opciones de capacidad y las actualizaciones.

</details>

2. ¿Qué tres límites se deben comprobar cuando MWAA envía pods a EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Alcance de red, autenticación de EKS basada en IAM y RBAC de Kubernetes.

**Explicación:** Un kubeconfig y `in_cluster=False` no proporcionan por sí mismos conectividad con el endpoint ni permisos de espacio de nombres.

</details>

3. ¿Añadir una asignación a `aws-auth` concede acceso cuando EKS usa el modo de autenticación API?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. En este modo, usa una entrada de acceso.

**Explicación:** Las entradas de acceso también funcionan con `API_AND_CONFIG_MAP`. Asocia el grupo al RoleBinding real e inspecciona otras concesiones.

</details>

4. ¿MWAA prohíbe instalar runtimes de Linux o dependencias del sistema?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Se pueden instalar runtimes admitidos mediante scripts de inicio.

**Explicación:** Los ejemplos oficiales incluyen `sudo`. Valida el tiempo de inicio, la red y las restricciones de versión; esto no equivale a poder reemplazar libremente la imagen base administrada.

</details>

5. ¿Git → CI → S3 → MWAA garantiza la ejecución inmediata después de una fusión?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Deben terminar la sincronización de archivos y el análisis de DAG.

**Explicación:** La configuración base documentada con S3 no demuestra por sí sola que falte compatibilidad con todas las funciones de bundles de Airflow. Comprueba que la versión elegida admita una configuración independiente.

</details>

6. Según la tabla de compatibilidad revisada el 12 de septiembre de 2026, ¿cuál era la versión más reciente de Airflow y desde cuándo estaba disponible en MWAA?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Airflow 3.3.1, disponible desde el 1 de septiembre de 2026, con Python 3.12.

**Explicación:** La versión 3.3.1 de upstream se publicó el 12 de agosto de 2026, por lo que no es correcto asumir un retraso fijo de tres meses. Comprueba por separado las versiones que ya estén instaladas en el entorno.

</details>

7. ¿MWAA solo es adecuado para canalizaciones de poca importancia o que usan exclusivamente PyPI?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Puede ejecutar imágenes de cargas de trabajo externas de EKS; decide según los requisitos operativos, funcionales y de recuperación.

**Explicación:** Una imagen secundaria de KPO es distinta del runtime propio de MWAA. Distingue también el MWAA aprovisionado de MWAA Serverless, que usa YAML.

</details>

8. ¿Se debería usar un ahorro fijo de entre el 30 % y el 60 % por alojamiento propio al comparar costos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No, salvo que haya pruebas y se comparen condiciones equivalentes.

**Explicación:** Compara los mismos objetivos de rendimiento y latencia, e incluye los rangos de workers, EKS, la base de datos, el almacenamiento, NAT, los registros y el trabajo de ingeniería.

</details>

9. ¿Cómo se fija la versión del proveedor de Kubernetes para el entorno del capítulo con Airflow 3.3.1/Python 3.12?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Usa las restricciones de Airflow/Python correspondientes y `apache-airflow-providers-cncf-kubernetes==10.21.0`.

**Explicación:** Primero inspecciona la imagen base. Después de cargar el archivo en S3, verifica la versión del objeto de requisitos del entorno y los registros de instalación.

</details>

10. ¿Qué se debe comprobar antes de entregar a MWAA un kubeconfig generado localmente?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Comprueba el clúster, el contexto, la CA, `exec.command` y la selección de credenciales de IAM; elimina las referencias locales a `AWS_PROFILE`.

**Explicación:** No incrustes tokens estáticos ni claves de larga duración. Verifica que se ejecute `aws get-token` y que se pueda acceder al endpoint de destino desde MWAA.

</details>

11. ¿Qué asociación conecta un grupo de Kubernetes con un Role solo dentro de `data-processing`?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Usa un RoleBinding en ese espacio de nombres.

**Explicación:** Un ClusterRoleBinding no expresa el límite del espacio de nombres. Otras concesiones son aditivas; crear pods también implica considerar la selección de cuentas de servicio.

</details>

12. Si nunca aparece `MWAA_EKS_OK` y el pod secundario presenta `ImagePullBackOff`, ¿se deberían ampliar primero los permisos de S3 del rol de MWAA?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Inspecciona la identidad de extracción de imágenes del nodo de EKS o Fargate, la conectividad con el registro y la disponibilidad de la imagen.

**Explicación:** El pod secundario no hereda automáticamente el rol de ejecución de MWAA. Configura por separado los permisos de datos reales de la carga de trabajo.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/airflow/04-mwaa-integration.md)
