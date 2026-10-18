# 6. Automatización de redes y evaluación final

> **Última actualización**: 15 de septiembre de 2026

**Requisitos previos:** Los capítulos 1, 2 y 4 aportan las habilidades comunes de observación. Añada el capítulo 3 para un proyecto final de EVPN/fabric o el capítulo 5 para nube. El proyecto final de host Linux usa el experimento acotado del capítulo 4. El ejercicio del validador solo requiere Python 3.9 o posterior y un directorio nuevo de su propiedad.

**Objetivo:** Separar la intención de las observaciones y entregar estados normales, prohibidos, fallidos y recuperados que se puedan reproducir. La automatización no debe convertir la falta de evidencia en un resultado correcto.

## 1. Revisar la intención antes de cambiar nada {#intent}

| Área | Definir antes del cambio | Verificar después |
|---|---|---|
| Accesibilidad | ¿Quién debe acceder a qué servicio? | Respuesta real y punto de observación |
| Aislamiento | ¿Qué flujos deben prohibirse? | Evidencia de políticas junto con la sonda |
| Política de enrutamiento | ¿Qué prefijos se deben anunciar a qué peer/VRF? | Estado anunciado, seleccionado y reenviado dentro de ese mismo alcance |
| Resiliencia | ¿Qué debe sobrevivir a un único fallo? | Continuidad del servicio e intervalo de convergencia/recuperación |
| Límite operativo | Acceso de administración, alcance del cambio y criterios de detención | Ningún cambio fuera de alcance y estado restaurado |

Cambiar los valores esperados solo para que coincidan con una salida nueva puede ocultar regresiones. Revise primero la intención y registre su revisión/hash. Los adaptadores de observación conservan unidades, alcance y tiempo mientras normalizan la salida real.

Por ejemplo, los anuncios de un peer FRR, toda la FIB de un host Linux y una tabla de rutas TGW son conjuntos de datos diferentes. El contrato de prefijos siguiente compara **el conjunto anunciado a un peer especificado**. La preferencia, el número de rutas ECMP, la instalación en la FIB y el reenvío real necesitan evidencia independiente.

## 2. Ejercicio breve de validación {#record-validator}

Los datos siguientes son **sintéticos**. No configuran una red ni transmiten paquetes. El validador comprueba la coherencia entre la intención proporcionada y los registros; no certifica la autenticidad de PCAP ni de contadores.

Cree un directorio nuevo en la VM del laboratorio o en su terminal local de estudio.

```bash
EVIDENCE_DIR=$(mktemp -d /tmp/network-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE_DIR"
```

Guarde este JSON como `intent.json` en ese directorio. En una automatización real, se mantiene como entrada revisada por separado.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "maximum_window_seconds": 60,
  "exported_prefixes": ["203.0.113.0/24"],
  "flows": {"a-to-web": "allow", "b-to-a": "deny"}
}
```

Guarde lo siguiente como `observations.json`. Las direcciones, los tiempos y los nombres de artefactos son ilustrativos.

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "evidence_kind": "synthetic",
  "window": {"start": "2026-09-15T00:00:00Z", "end": "2026-09-15T00:00:10Z"},
  "exported_prefixes": ["203.0.113.0/24"],
  "route_artifact": "synthetic:advertised-routes",
  "flows": {
    "a-to-web": {
      "verdict": "allow",
      "artifacts": {"probe": "synthetic:http-response"}
    },
    "b-to-a": {
      "verdict": "deny",
      "artifacts": {"probe": "synthetic:blocked-probe", "policy": "synthetic:policy-decision"}
    }
  }
}
```

Guarde este código Python como `check_record.py` en el mismo directorio.

```python
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def prefixes(values):
    require(isinstance(values, list), "prefixes must be a list")
    return {str(ipaddress.ip_network(value, strict=True)) for value in values}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp needs a timezone")
    return parsed


require(len(sys.argv) == 3, "usage: check_record.py intent.json observations.json")
intent, seen = load(sys.argv[1]), load(sys.argv[2])
for record in (intent, seen):
    require(type(record.get("schema")) is int and record["schema"] == 1, "schema")
for key in ("scenario", "phase", "route_scope"):
    require(intent[key] == seen[key], "scope mismatch: " + key)
require(seen["evidence_kind"] in {"synthetic", "supplied", "measured"}, "evidence kind")
duration = (timestamp(seen["window"]["end"]) - timestamp(seen["window"]["start"])).total_seconds()
require(0 < duration <= intent["maximum_window_seconds"], "invalid observation window")
require(prefixes(intent["exported_prefixes"]), "empty intended prefix scope")
require(prefixes(seen["exported_prefixes"]) == prefixes(intent["exported_prefixes"]), "prefix mismatch")
require(isinstance(seen.get("route_artifact"), str) and seen["route_artifact"].strip(), "route evidence missing")
require(intent["flows"] and set(intent["flows"]) == set(seen["flows"]), "flow coverage mismatch")
for name, wanted in intent["flows"].items():
    require(wanted in {"allow", "deny"}, "unsupported intent")
    actual = seen["flows"][name]
    require(actual["verdict"] == wanted, "flow mismatch: " + name)
    needed = {"probe"} if wanted == "allow" else {"probe", "policy"}
    artifacts = actual["artifacts"]
    require(all(isinstance(artifacts.get(k), str) and artifacts[k].strip() for k in needed),
            "evidence missing: " + name)
print("CONSISTENT_RECORD kind=" + seen["evidence_kind"] + "; live behavior not attested")
```

Ejecútelo:

```bash
python3 "${EVIDENCE_DIR:?}/check_record.py" \
  "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json"
```

La salida esperada es `CONSISTENT_RECORD kind=synthetic; live behavior not attested`. Significa que se cumplieron las condiciones requeridas de este registro, no que el tráfico de red haya tenido éxito ni que se apruebe una implementación operativa. Las excepciones explícitas mantienen activas las comprobaciones cuando la optimización de Python eliminaría las instrucciones `assert`.

### Entradas que deben fallar

Conserve los originales y cambie la copia `observations-bad.json` **de un elemento a la vez**. Ejecute el mismo comando con esa copia como argumento final.

| Cambio | Resultado esperado |
|---|---|
| Eliminar la observación `b-to-a` | `flow coverage mismatch` |
| Establecer `b-to-a.verdict` en `unknown` o `allow` | `flow mismatch` |
| Eliminar el artefacto `policy` del flujo prohibido | `evidence missing` |
| Añadir `0.0.0.0/0` a los anuncios o dejar la lista vacía | `prefix mismatch` |
| Poner la hora de fin antes de la hora de inicio | `invalid observation window` |
| Cambiar `phase` | `scope mismatch` |

No normalice una salida vacía ni un tiempo de espera como `deny`. Un resultado prohibido requiere evidencia de política/aplicación vinculada a la sonda. Nombrar un artefacto no demuestra que exista ni que se haya recopilado en el punto de observación correcto.

Al extender este ejercicio a un recolector real, compruebe la existencia de los archivos, los hashes, el intervalo temporal y la identidad del recolector y del dispositivo/cuenta frente a la evidencia original. Valide por separado los atributos que se pierden al normalizar en conjuntos, como los atributos de ruta o el estado de disponibilidad de cada endpoint.

## 3. Diseñar una canalización de cambios {#pipeline}

Defina la entrada, la salida y el responsable del fallo de cada etapa.

| Etapa | Comprobación | Resultado que se pasa a la siguiente etapa |
|---|---|---|
| Revisión de intención | Flujos permitidos/prohibidos, rutas, acceso de administración y límite de fallo | Versión de la intención revisada |
| Validación estática | Sintaxis, funciones compatibles, direcciones superpuestas y alcance de políticas | Resultados para versiones exactas de herramientas/proveedores |
| Vista previa del cambio | Destino, impacto, diferencia esperada y capacidad de recuperación | Plan de cambios revisable por personas |
| Aplicación en laboratorio | Un cambio, tiempo/recursos acotados y acceso de administración preservado | Estado anterior/posterior y registro de ejecución |
| Comprobaciones de comportamiento | Permitido, prohibido, fallido, recuperado y evidencia faltante | Resultados estructurados vinculados a los originales |
| Decisión operativa | Alcance de validación, incertidumbres y condiciones de implementación/reversión | Aprobación o rechazo mediante un procedimiento operativo independiente |

Este curso no proporciona una canalización automática de aprobación para producción. Lea de antemano los comandos de recuperación y establezca acceso de recuperación independiente, como una consola, cuando pueda verse afectada la conectividad de administración.

## 4. Elegir un proyecto final {#capstones}

### A. Enrutamiento/fabric

Use un laboratorio preparado del [capítulo 2](02-routing-policy-convergence.md) o del [capítulo 3](03-datacenter-evpn.md).

1. Defina los prefijos permitidos y las rutas/los flujos prohibidos para un peer/VRF específico.
2. Registre los anuncios, la selección, la FIB y las sondas de servicio en estado normal.
3. Elija un fallo recuperable de política/ruta de ese capítulo.
4. Separe el tiempo del cambio en el plano de control del tiempo de recuperación real del servicio.
5. Restaure la configuración original y vuelva a comprobar tanto la accesibilidad como el aislamiento.

No sustituya la convergencia del servicio por el tiempo que tarda una sesión en llegar a Established. Registre la sincronización/incertidumbre al comparar los relojes de dispositivos diferentes, o use el eje temporal de un único observador.

### B. Linux/nube/SRE

Elija un experimento acotado de host del [capítulo 4](04-linux-performance.md) o evidencia aprobada de nube del [capítulo 5](05-cloud-cni-design.md).

1. Marque las rutas de ida y vuelta y al menos dos puntos de observación.
2. Seleccione una hipótesis sobre latencia, pérdida, colas o políticas y defina cómo refutarla.
3. Vincule las observaciones con el origen/espacio de nombres, el tiempo y las unidades.
4. Si realizó un experimento, restáurelo exactamente y repita las mismas comprobaciones.
5. Si solo analizó un diseño/evidencia proporcionada, limite la conclusión en consecuencia.

Si no dispone de equipo ni de una cuenta, entregue un análisis de diseño o de evidencia proporcionada. Marque **ejecución práctica completada** solo si incluye los originales y evidencia de recuperación de su propio experimento acotado.

## 5. Evaluación {#assessment}

Evalúe cada elemento como `cumplido / no cumplido / no observado`. No oculte dentro de una puntuación agregada la falta de evidencia obligatoria.

| Elemento | Criterio de aprobación |
|---|---|
| Alcance/reproducibilidad | Se pueden reconstruir la topología, el entorno, los permisos, la versión/revisión, las entradas y el tiempo |
| Razonamiento sobre protocolos | Se explican las relaciones entre paquetes, rutas y aplicaciones; se refuta al menos una hipótesis |
| Comprobaciones positivas/negativas | El tráfico permitido y el aislamiento se evalúan por separado; nunca se cuenta la ausencia como éxito |
| Fallo/recuperación | El impacto del cambio único y el estado recuperado se comprueban con los mismos criterios |
| Calidad de la automatización | Se rechazan el alcance incorrecto, las omisiones, las incertidumbres y las discrepancias de intención; se puede rastrear el origen |
| Conclusiones honestas | Se distingue entre evidencia medida, proporcionada, sintética, de diseño y no observada |

Vuelva al capítulo pertinente cuando no se cumpla un elemento obligatorio. No declare completa la validación en vivo si hay elementos no observados. Un revisor debe poder reconstruir la conclusión a partir de la misma evidencia.

## Limpieza y continuación

Inspeccione los archivos que creó antes de limpiar el ejercicio del validador.

```bash
ls -la -- "${EVIDENCE_DIR:?}"
rm -- "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json" \
  "${EVIDENCE_DIR:?}/check_record.py"
```

Si creó copias, elimine **solo las copias verificadas** y después ejecute `rmdir -- "${EVIDENCE_DIR:?}"`. Los originales de experimentos reales están sujetos a una política de retención aprobada independiente; no son este ejemplo sintético temporal.

Añada experimentos donde su cartera sea más débil: [protocolos](01-protocol-projects.md), [enrutamiento](02-routing-policy-convergence.md), [EVPN](03-datacenter-evpn.md), [rendimiento de Linux](04-linux-performance.md) o [diseño de nube](05-cloud-cni-design.md).

Referencias: [JSON de Python](https://docs.python.org/3/library/json.html), [ipaddress](https://docs.python.org/3/library/ipaddress.html), [datetime](https://docs.python.org/3/library/datetime.html).

[Anterior: Nube/CNI](05-cloud-cni-design.md) · [Cuestionario](../../quizzes/networking/expert/06-automation-capstone-quiz.md) · [Curso](README.md)
