# Cuestionario sobre configuración de red de EKS Hybrid Nodes

> **Documento relacionado**: [Configuración de red](../../eks-hybrid-nodes/02-network-configuration.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Qué enfoque proporciona la ruta de red híbrida bidireccional requerida?

- A) Solo acceso a Internet pública
- B) Un diseño revisado de Direct Connect/VPN con rutas reales y acceso de firewall
- C) Solo un túnel SSH
- D) Solo un proxy HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un diseño revisado de Direct Connect/VPN con rutas reales y acceso de firewall**

**Explicación:**
El plano de control debe poder alcanzar kubelet y los endpoints de Pod pertinentes, y los nodos deben poder acceder a AWS. Un endpoint público de la API de Kubernetes no elimina ese requisito de una ruta privada de retorno. Direct Connect no cifra de forma inherente todas las conexiones ni garantiza la latencia. Confirme el estado real del túnel de VPN; no se limite al estado `available` del recurso. La guía relacionada establece la cuenta/contexto y el `WORK_DIR` privado para estos diagnósticos de solo lectura.

```bash
: "${VPN_ID:?Select the reviewed VPN connection}"
: "${TUNNEL_IP:?Select its actual AWS tunnel outside IP}"
check_account
# Select telemetry only: do not dump customer gateway configuration or pre-shared keys.
aws ec2 describe-vpn-connections --region "$AWS_REGION" --vpn-connection-ids "$VPN_ID" \
  --query 'VpnConnections[].{id:VpnConnectionId,state:State,telemetry:VgwTelemetry}' \
  --output json > "$WORK_DIR/vpn-state.json"
jq -e --arg ip "$TUNNEL_IP" 'length==1 and any(.[0].telemetry[]?; .OutsideIpAddress==$ip)' \
  "$WORK_DIR/vpn-state.json" >/dev/null
export VPN_ID TUNNEL_IP
python3 - <<'PY'
import ipaddress, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
ipaddress.ip_address(os.environ["TUNNEL_IP"])
now = datetime.now(timezone.utc)
end = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
body = {"Namespace": "AWS/VPN", "MetricName": "TunnelState",
        "Dimensions": [{"Name": "VpnId", "Value": os.environ["VPN_ID"]},
                       {"Name": "TunnelIpAddress", "Value": os.environ["TUNNEL_IP"]}],
        "StartTime": (end - timedelta(minutes=15)).isoformat(), "EndTime": end.isoformat(),
        "Period": 300, "Statistics": ["Minimum", "Maximum"]}
(Path(os.environ["WORK_DIR"]) / "vpn-metric-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/vpn-metric-request.json" --output json \
  > "$WORK_DIR/vpn-metric-result.json"
jq '{label:.Label,datapoints:(.Datapoints|sort_by(.Timestamp))}' "$WORK_DIR/vpn-metric-result.json"
```

</details>

### 2. ¿Qué puerto se usa para la conexión del nodo a la API de Kubernetes?

- A) TCP 22
- B) TCP 443
- C) TCP 8080 de forma predeterminada
- D) TCP 3306

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TCP 443**

**Explicación:**
La conexión inversa del plano de control a kubelet usa TCP 10250 seguro. Los webhooks y las API agregadas usan los puertos que tengan configurados. No abra el puerto 10255 sin autenticación como requisito actual. Verifique la CA del clúster y el nombre de host; HTTP 401/403 puede indicar que se alcanzó TLS pero falta autorización, no que la aplicación esté sana.

```bash
set -euo pipefail
endpoint=$(jq -er '.cluster.endpoint' "$WORK_DIR/cluster.json")
case "$endpoint" in https://*) ;; *) printf 'HTTPS endpoint required.\n' >&2; exit 1;; esac
jq -er '.cluster.certificateAuthority.data' "$WORK_DIR/cluster.json" |
  base64 --decode > "$WORK_DIR/cluster-ca.pem"
openssl x509 -in "$WORK_DIR/cluster-ca.pem" -noout >/dev/null
curl --silent --show-error --connect-timeout 5 --max-time 15 \
  --cacert "$WORK_DIR/cluster-ca.pem" --output "$WORK_DIR/api-response.txt" \
  --write-out '{"httpCode":%{http_code},"remoteIP":"%{remote_ip}","dnsTotalSeconds":%{time_namelookup},"connectTotalSeconds":%{time_connect},"tlsTotalSeconds":%{time_appconnect},"totalSeconds":%{time_total}}\n' \
  "$endpoint/readyz" > "$WORK_DIR/api-timing.json"
cat "$WORK_DIR/api-timing.json"
```

</details>

### 3. Para la parte de descarga de imágenes de ECR privado en un diseño sin Internet, ¿qué servicios son pertinentes?

- A) ecr.api, ecr.dkr y una ruta privada adecuada para acceder a las capas en S3
- B) Solo Lambda, DynamoDB y SNS
- C) Solo los metadatos de EC2
- D) Solo un endpoint de administración de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) ecr.api, ecr.dkr y una ruta privada adecuada para acceder a las capas en S3**

**Explicación:**
Los proveedores de credenciales, la administración de EKS, la API de Kubernetes y los servicios de las cargas de trabajo tienen requisitos independientes. Los endpoints privados de ECR no convierten ECR público/CloudFront en servicios privados. Los endpoints de interfaz de S3 admiten DNS privado; el modo que usa solo un Resolver entrante necesita el endpoint de gateway de S3 para el tráfico dentro de la VPC. Un endpoint de interfaz de administración de EKS no es el endpoint de la API de Kubernetes, y un alias DNS no puede corregir un nombre de host TLS que no corresponda.

</details>

### 4. ¿Qué elemento no es un requisito del plan de direccionamiento de Pods híbridos?

- A) Evitar la superposición con los rangos de nodos remotos/VPC/Service
- B) Dimensionar según la demanda real de nodos/Pods
- C) Cada grupo de Pods debe ser un /8
- D) Separación correcta entre clústeres y enrutamiento de retorno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cada grupo de Pods debe ser un /8**

**Explicación:**
Se admiten rangos IPv4 RFC1918 o CGNAT, sujetos a los límites documentados de CIDR remotos. Un despliegue de Cilium con `cluster-pool` configura su grupo en Cilium, no asignando un único CIDR de Pods de todo el clúster mediante la configuración de kubelet. Este ejemplo de grupo nuevo no instruye a modificar uno que ya tiene asignaciones. Lea las asignaciones reales de CiliumNode; no se garantiza el orden de los bloques ni la capacidad utilizable de Pods.

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```

</details>

### 5. ¿Cómo se debe determinar la dirección DNS del clúster?

- A) Usar siempre 8.8.8.8
- B) Inspeccionar el Service real `kube-dns` o el diseño de DNS local configurado intencionalmente
- C) Suponer siempre que es 10.100.0.10
- D) Usar la dirección de metadatos de EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspeccionar el Service real `kube-dns` o el diseño de DNS local configurado intencionalmente**

**Explicación:**
`10.100.0.10` es un ejemplo para un CIDR de Service específico. Compruebe las IP reales de Service, los EndpointSlices y la configuración del resolver de los nodos. La ubicación de DNS por sí sola no garantiza el enrutamiento local; deben configurarse Service Traffic Distribution y un plano de datos compatible. Una preferencia flexible de distribución no demuestra que exista una disposición 2+2 de CoreDNS.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get service kube-dns -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,clusterIP:.spec.clusterIP,
       clusterIPs:.spec.clusterIPs,ports:.spec.ports,trafficDistribution:.spec.trafficDistribution}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get endpointslices -l kubernetes.io/service-name=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,addressType,ports,
       endpoints:[.endpoints[]?|{addresses,nodeName,zone,conditions,hints}]}]'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get pods -l k8s-app=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,node:.spec.nodeName,phase:.status.phase,
       ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported")}]'
```

</details>

### 6. ¿Cómo se deben interpretar las recomendaciones de AWS sobre latencia de red híbrida?

- A) 500 ms es un límite garantizado
- B) Un RTT de unos 200 ms o menos es una recomendación general que debe validarse para la carga de trabajo
- C) 100 ms es un requisito universal estricto
- D) Direct Connect siempre garantiza menos de 10 ms

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un RTT de unos 200 ms o menos es una recomendación general que debe validarse para la carga de trabajo**

**Explicación:**
AWS también da 100 Mbps como recomendación general, no como umbral de aceptación independiente de la carga de trabajo. Las categorías anteriores de <50/50–100/100–200/>200 ms y la afirmación de <10 ms para Direct Connect eran heurísticas no verificadas. Los tiempos DNS/conexión/TLS de curl son fases acumuladas, no un RTT puro; que ICMP no responda no demuestra que la API haya fallado. Mida el comportamiento real de la aplicación, la API, las imágenes y la telemetría.

</details>

## Referencias

- [Redes de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [PrivateLink de EKS](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [DNS privado de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [Métricas de VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
