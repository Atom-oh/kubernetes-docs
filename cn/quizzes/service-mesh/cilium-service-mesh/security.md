# Cilium Service Mesh 安全测验

本测验用于测试你对 Cilium Service Mesh 中的 mTLS、网络策略、加密、基于 Identity 的安全性和零信任网络的理解。

## 测验问题

### 1. Cilium Service Mesh 使用什么技术来实现透明 mTLS？

A. Istio sidecar
B. SPIFFE/SPIRE 集成
C. Nginx proxy
D. HAProxy

<details>
<summary>显示答案</summary>

**答案：B. SPIFFE/SPIRE 集成**

**说明：**
Cilium Service Mesh 与 SPIFFE（Secure Production Identity Framework for Everyone）和 SPIRE 集成，以实现透明 mTLS。这样可在无需更改应用程序代码的情况下，实现 workload 之间的加密通信。

</details>

### 2. 当认证模式设为 'required' 时，CiliumNetworkPolicy 的行为是什么？

A. 无需认证即可允许所有流量
B. 仅允许通过双向认证的流量
C. 仅在认证失败时记录警告
D. 禁用 mTLS

<details>
<summary>显示答案</summary>

**答案：B. 仅允许通过双向认证的流量**

**说明：**
当认证模式设为 'required' 时，仅允许成功完成双向认证的流量。认证失败的流量会被阻止。这对于实现零信任安全模型至关重要。

</details>

### 3. 以下哪项不是 Cilium 中 WireGuard 加密的优势？

A. 在 kernel 层运行，性能高
B. 自动密钥管理
C. IETF 标准协议
D. ChaCha20Poly1305 加密

<details>
<summary>显示答案</summary>

**答案：C. IETF 标准协议**

**说明：**
WireGuard 不是标准协议。IPsec 是 IETF 标准协议。不过，WireGuard 内置于 Linux kernel 5.6+，并提供高性能、自动密钥管理和 ChaCha20Poly1305 加密。

</details>

### 4. 在 CiliumNetworkPolicy 中，使用 L7 HTTP 规则限制特定路径和方法的正确配置是什么？

A. 在 toEndpoints 中指定路径和方法
B. 在 toPorts.rules.http 中指定方法和路径
C. 直接在 ingress.http 中指定
D. 在 spec.http 中定义规则

<details>
<summary>显示答案</summary>

**答案：B. 在 toPorts.rules.http 中指定方法和路径**

**说明：**
在 CiliumNetworkPolicy 中，L7 HTTP 规则定义在 toPorts 部分的 rules.http 下。在此处可以指定方法（GET、POST 等）和路径（支持 regex），以实现细粒度访问控制。

</details>

### 5. Cilium 基于 Identity 的安全性的主要优势是什么？

A. 不受 IP 地址变化影响
B. 因基于 MAC 地址而更安全
C. 可以手动管理 ID
D. 支持 VLAN tagging

<details>
<summary>显示答案</summary>

**答案：A. 不受 IP 地址变化影响**

**说明：**
Cilium Identity 基于 Pod labels 生成，因此即使 Pod 重启且其 IP 地址发生变化，也会保持相同的 Identity。这克服了基于 IP 的安全策略的局限性。

</details>

### 6. 在 Cilium 中，使用 DNS L7 策略限制外部域名访问时使用哪些规则？

A. toFQDNs 和 dns 规则的组合
B. 仅 toEndpoints
C. 仅 toCIDR
D. 仅 toEntities

<details>
<summary>显示答案</summary>

**答案：A. toFQDNs 和 dns 规则的组合**

**说明：**
外部域名访问限制分两步配置：1) 使用 DNS L7 规则（toPorts.rules.dns）仅允许特定域名查询；2) 使用 toFQDNs 允许实际连接到这些域名。此组合可对 workload 的外部访问提供细粒度控制。

</details>

### 7. 使用 CiliumClusterwideNetworkPolicy 实施默认拒绝策略时，通常需要允许哪些流量？

A. 所有外部流量
B. DNS 查询和 host 网络流量
C. 所有互联网流量
D. 仅特定 IP 范围

<details>
<summary>显示答案</summary>

**答案：B. DNS 查询和 host 网络流量**

**说明：**
实施默认拒绝策略时，至少需要允许到 kube-dns（端口 53/UDP）的 DNS 查询和 host 网络流量（reserved:host），以使集群正常运行。否则，服务发现和 node 通信将无法进行。

</details>

### 8. SPIRE 中 workload attestation 的作用是什么？

A. 签发证书
B. 验证 workload Identity
C. 应用网络策略
D. 加密流量

<details>
<summary>显示答案</summary>

**答案：B. 验证 workload Identity**

**说明：**
Workload attestation 是 SPIRE Agent 验证 workload Identity 的过程。在 Kubernetes 环境中，它会验证 Pod 的 service account、namespace、labels 等，以便向该 workload 签发相应的 SVID（SPIFFE Verifiable Identity Document）。

</details>

### 9. 在 audit mode 中测试网络策略时，Cilium 的行为是什么？

A. 阻止所有流量
B. 记录策略违规，但允许流量
C. 完全禁用策略
D. 仅发送告警

<details>
<summary>显示答案</summary>

**答案：B. 记录策略违规，但允许流量**

**说明：**
在 audit mode（cilium.io/audit-mode: "true" annotation）中，违反策略的流量不会被阻止，只会被记录。这样可以在将新策略应用到生产环境之前评估其影响。

</details>

### 10. 在三层架构中实施 microsegmentation 时，backend 服务的正确策略是什么？

A. 允许所有流量
B. 仅允许来自 frontend 的 ingress，并且仅允许到 database 的 egress
C. 阻止所有 ingress
D. 允许互联网访问

<details>
<summary>显示答案</summary>

**答案：B. 仅允许来自 frontend 的 ingress，并且仅允许到 database 的 egress**

**说明：**
在 microsegmentation 中，backend 服务遵循最小权限原则：仅允许来自 frontend 层的 ingress，并且仅允许到 database 层的 egress。这样可以明确定义和控制各层之间的流量。

</details>

### 11. 以下哪项正确描述了 Cilium 中 IPsec 和 WireGuard 加密的差异？

A. 只有 IPsec 在 kernel 中运行
B. WireGuard 需要手动密钥管理
C. IPsec 是 IETF 标准，WireGuard 是非标准协议
D. 只有 WireGuard 支持 node-to-node 加密

<details>
<summary>显示答案</summary>

**答案：C. IPsec 是 IETF 标准，WireGuard 是非标准协议**

**说明：**
IPsec 是 IETF 标准协议，而 WireGuard 是非标准协议。两者都在 kernel 中运行，WireGuard 提供自动密钥管理。两者都支持 node-to-node 加密。

</details>

### 12. 使用 Hubble 监控策略违规时使用哪个命令？

A. hubble observe --verdict FORWARDED
B. hubble observe --verdict DROPPED
C. hubble policy list
D. hubble status --violations

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

**说明：**
`hubble observe --verdict DROPPED` 命令监控被网络策略拒绝（DROPPED）的流量。这样可以实时检测和分析策略违规。

</details>
