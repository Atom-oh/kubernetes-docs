# 真实事件中的纵深防御与事件响应

> **审查依据**：AWS、Kubernetes、Palo Alto Networks 和 Fortinet 官方文档、CISA 警报以及 NIST SP 800-61r3。发布日期与研究日期是不同的时间信息。
> **最后更新**：2026 年 10 月 15 日

安全设计必须涵盖入口、横向移动、数据外泄和恢复。本章将边界控制和事件处理与现有的 [EKS 安全](./06-eks-security-best-practices.md)、[NetworkPolicy](./04-network-policies.md) 和[运行时安全](./08-runtime-security.md)指南联系起来。下文的运维标准和实施顺序是本指南的**设计提议**，并非安装某个产品后就能获得的保证。

## 1. 已核实的事件及其设计教训

| 案例及发布 / 退役日期 | 一手来源已确认的范围 | 对设计的影响 |
|---|---|---|
| ingress-nginx CVE-2025-1974，2025-03-24 | 攻击经由 Pod 网络可访问的 validating admission controller；当时的修复版本为 1.11.5 和 1.12.1 | 除外部 WAF 防护外，还要检查 webhook 可达性和 controller 的 Secret 权限 |
| ingress-nginx 退役，2026-03 | Kubernetes Steering / SRC 于 2026-01-29 警告，退役后将停止安全更新 | 迁移到仍受维护的实现；历史 CVE 修复版本并不代表 2026 年的新版本建议 |
| PAN-OS CVE-2025-0108，2025-02-12 | 管理 Web 身份验证绕过，并观察到被串联利用的尝试 | 将管理访问与公共应用路径分开 |
| PAN-OS CVE-2026-0322，2026-10-14 | 经身份验证后，可通过管理界面以 root 身份远程执行代码；观察到有限的利用活动；受影响产品为 PA-Series、VM-Series 和 Panorama | 保护管理员凭证、会话和管理界面的可达性；区分产品系列 |
| FortiCloud SSO CVE-2026-24858，2026-01-27 加入 CISA KEV | 启用 FortiCloud SSO 时可跨账户访问、修改账户 / VPN；即使设备已修补早期 SSO CVE，仍出现新的攻击路径 | 审计管理变更；仅仅采用 SSO 并不足以防护 |
| FortiGate 持久化访问，2025-04-10 | 与 SSL-VPN 相关的符号链接可能在早前漏洞修补后仍保留文件读取权限 | 将漏洞修补和清除入侵痕迹作为两个独立的完成条件进行追踪 |

证据来源：[Kubernetes CVE 警报][S01]、[退役声明][S02]、[PAN-OS 2025 公告][S04]、[2026 公告][S03]、[CISA KEV 数据][S06] 以及 [Fortinet 持久化分析][S07]。Fortinet 于 1 月 28 日更正了其 2026 年 SSO 分析：**第三方 SAML IdP 和 FortiAuthenticator 不受该问题影响**。不要重复最初较宽泛的“所有 SAML 都受影响”的说法。[S05]

CISA 于 2026-10-14 将 CVE-2026-0322 加入 KEV，并于 2026-01-27 将 CVE-2026-24858 加入其中。确定优先级时，应同时检查 KEV 条目和供应商公布的受影响范围。不要把美国联邦政府的修复期限泛化成普遍适用的法律义务。[S06]

漏洞披露本身并不能证明每个安装都已遭到入侵。应检查产品、分支、hotfix、已启用功能、暴露情况和证据。PAN-OS 2026 公告不包括 Cloud NGFW 和 Prisma Access；此排除范围并不适用于所有 CVE。预计补丁日期也不等同于已确认的发行可用日期。[S03]

## 2. 控制职责和剩余覆盖范围

| 控制 | 主要范围 | 配套控制 |
|---|---|---|
| WAF | 发往已关联资源且符合配置规则的 HTTP(S) 请求 | 应用身份验证 / 授权、校验、上传检查和源站限制 |
| NGFW / IPS | 穿越网络的会话及已配置的安全配置文件 | TLS 可视性、管理界面保护、补丁和双向路由 |
| GWLB / GWLBE | 插入兼容 GENEVE 的设备并分配流量 | 设备检查策略、会话处理、容量和恢复 |
| Kubernetes NetworkPolicy | 由受支持 CNI 强制执行的 Pod 连接 | hostNetwork / 节点 / 本地路径检查以及服务身份验证 |
| mTLS / SPIFFE | 对端身份和传输保护 | 服务授权、请求校验和访问记录 |
| 镜像 / 准入策略 | 已部署镜像和工作负载配置 | 运行时检测、补丁和 Secret 管理 |

[WAF 资源列表][S09] 和 [GWLB 文档][S24]明确了各自的范围。NetworkPolicy 需要有实际执行策略的插件；该 API 不提供 TLS，也不强制每个连接都经过共同网关。[S34]

**设备已安装和请求已被检查，需要不同的证据**。建议的验收标准应确认：

1. **路径**：此请求是否确实经过指定 WAF 或防火墙？
2. **策略**：应用了哪个规则、签名、解密策略和例外？
3. **结果**：允许 / 拒绝决策和应用行为是否符合预期？

## 3. 先清点流量

使用以下威胁模型模板，填入实际主体、CIDR 和资源 ID；未观测到的路径应标记为尚未验证。

| 流量 | 要调查的入口 / 出口路径 | 控制和证据 |
|---|---|---|
| 用户 → Web / API | CloudFront、ALB、其他负载均衡器 / 域名 / NodePort | Web ACL 关联、合法请求、无害的拦截 canary，以及直接访问源站的结果 |
| 操作员 → 管理界面 | PAN-OS / FortiGate、Panorama / FortiManager、EKS API、GitOps | 可信管理路径、身份验证、管理员 / 策略变更记录 |
| API Server → webhook | 控制平面和 admission Service | API Server 访问、普通工作负载限制、证书和 RBAC |
| Pod → 外部 | 节点 SNAT、NAT Gateway、TGW、IPv4 / IPv6、代理 | 允许 / 拒绝目标、转换前 / 后地址及防火墙会话 |
| Pod → Pod / 数据库 | 同节点、同 VPC、不同 VPC | CNI 策略、数据库 SG、服务授权和双向测试 |
| Pod → AWS 服务 | PrivateLink、S3 / DynamoDB gateway endpoint、公共端点 | IAM / 资源 / endpoint 策略和观测到的连接路径 |
| CI/CD → 集群 | OIDC 角色、镜像仓库、GitOps controller | 签名 / digest、最小权限和经过审计的变更 |

集中式 TGW 检查覆盖的是**经过 TGW 路由的流量**。不要假设它还包括同节点 Pod 流量、VPC 本地路由、peering 或单独的 endpoint 路径。应结合检查路由和 CNI。[S29] [S30] [S34]

## 4. 架构职责归属

面向公共应用时，使用 [WAF 和源站保护](./14-waf-edge-api-security.md)。出站和 VPC 间检查使用 [NGFW 设计](./15-ngfw-paloalto-fortinet.md)和 [GWLB / GENEVE](./16-gwlb-geneve-inspection.md)。在 VPC 内部，再将这些控制与 NetworkPolicy、安全组和 mTLS 关联起来。

以下是职责划分示例：

| 责任方 | 建议职责 | 变更审查重点 |
|---|---|---|
| 应用团队 | 身份验证、授权、schema 和上传 | WAF 例外之后的应用防护 |
| 平台团队 | EKS、controller、CNI、准入和 GitOps | webhook、Pod 和 AWS 权限边界 |
| 网络团队 | TGW、VPC 路由、GWLBE、NAT 和设备容量 | 请求 / 返回路径、AZ 故障和绕过路径 |
| 安全团队 | 检查策略、签名、调查和例外到期 | 拦截有效性、检测证据和恢复 |
| 事件指挥官 | 遏制、证据和恢复决策 | 业务影响、凭证更换和复测 |

应将更改默认路径的权限与授予检查例外的权限分开。记录紧急绕过范围、理由、到期时间和恢复负责人。这是组织设计建议，并非检查某个 AWS 账户后得出的发现。

## 5. 检测证据

| 行为 | 关联证据 | 单一来源的局限 |
|---|---|---|
| 管理员登录后创建账户 / 策略 | 设备身份验证 / 配置审计、中央管理器和管理路径记录 | 设备遭到入侵时，其本地记录可能不够可信 |
| 移除 WAF / 设置例外或绕过检查 | AWS 变更、Web ACL 关联、路由 / SG 变更和应用访问记录 | 拦截数为零并不能证明策略有效执行 |
| Controller 遭入侵后访问 Secret | Kubernetes 审计、controller RBAC 和运行时行为 | Web 访问日志不覆盖所有 webhook 攻击 |
| 疑似数据外泄 | CNI 观测、防火墙会话、NAT 前地址和应用 / AWS API 审计 | VPC Flow Logs 不包含应用载荷或授权结果 |
| 修补后再次进入系统 | 管理员 / VPN 账户、配置差异和凭证使用情况 | 版本号不能证明持久化访问已经清除 |

Fortinet 记录了管理员创建和配置变更的情况。EKS 文档说明 Flow Logs 中的元数据性质，以及 Pod 地址变化时归因的困难。[S05] [S33]

GuardDuty 威胁检测、Inspector 漏洞管理、Security Hub 暴露 / 关联分析和 CSPM 配置检查用途各不相同。先确认已使用服务的覆盖范围，再按时间和资源身份关联网络、设备和应用记录。各项服务的详情请参阅 [EKS 安全实践](./06-eks-security-best-practices.md)。

## 6. 疑似遭到入侵时的响应

NIST SP 800-61r3 将检测、响应和恢复与更广泛的风险管理联系起来。以下设备 / EKS 响应流程是本指南提出的运维方案。[S08]

1. **分类**：确定受影响的产品、分支、功能、暴露情况和调查范围。区分存在漏洞的资产与有入侵证据的资产。
2. **保全证据**：记录 UTC 时间、配置修订版本、管理员 / VPN 账户、身份验证 / 系统 / 威胁日志和云端变更。如果延迟遏制会扩大损害，则应并行遏制；记录该决策。
3. **遏制**：限制受影响的管理路径和工作负载，同时识别控制平面、DNS、日志以及获批准的恢复依赖项。
4. **清除访问**：按照供应商流程处理未授权账户、设置和文件系统变更。必要时，使用已验证的镜像和确认干净的配置重新构建；不要盲目恢复可疑设置。
5. **更换 Secret**：根据暴露情况检查管理员 / VPN / LDAP / AD / API / 云凭证、证书和会话。仅修改一个防火墙密码并不足够。
6. **证明恢复完成**：重新测试被拒绝的管理访问、合法业务功能、无害的拦截 canary、出站流量、AZ 故障和日志采集。
7. **改进**：分析原因、暴露时长、例外、检测延迟和变更权限，并更新控制和操作手册。

如果确认存在入侵迹象，Fortinet 建议将系统 / 配置视为已遭入侵，恢复或审计配置并轮换关联凭证。其持久化分析还要求审查配置。[S05] [S07]

## 7. 采用顺序和完成标准

以下是可调整的执行计划，并非供应商 SLA 或事件补救期限。

| 阶段 | 工作内容 | 完成证据 |
|---|---|---|
| 首先 | 清点公共管理界面、已退役 ingress、正在被利用的 CVE 和源站绕过路径 | 资产 / 暴露 / 受影响分支 / 负责人记录及整改措施 |
| 阶段 1 | 验证 WAF 日志 / 规则、管理员变更检测以及 webhook / Pod 边界 | 允许 / 拒绝结果和有效策略 ID |
| 阶段 2 | 出站 / VPC 间检查、Palo Alto / Fortinet PoC 和双向 GWLB 路径 | 请求 / 响应捕获、NAT 位置和故障演练 |
| 阶段 3 | 容量、升级、恢复和例外生命周期 | SLO 测量、恢复演练和经过审查的变更流程 |

不要只看拦截百分比。应同时追踪**检查路径覆盖率、源站绕过测试、未授权管理员变更、日志缺失、恢复时间和合法流量错误**。在实际测量之前，不要声称性能或可用性数据。

## 继续学习

- [WAF、边缘和 API 安全](./14-waf-edge-api-security.md)
- [Palo Alto 和 Fortinet NGFW](./15-ngfw-paloalto-fortinet.md)
- [GWLB 和 GENEVE 检查](./16-gwlb-geneve-inspection.md)
- [本章测验](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## 参考资料和研究依据

一手来源访问日期为 2026-10-15。变更前，请针对所选产品 / 分支重新核查安全公告和限制。

- [S01：Kubernetes：CVE-2025-1974][S01]
- [S02：Kubernetes：ingress-nginx 退役声明][S02]
- [S03：Palo Alto：CVE-2026-0322][S03]
- [S04：Palo Alto：CVE-2025-0108][S04]
- [S05：Fortinet：FortiOS 上 SSO 滥用分析][S05]
- [S06：CISA：已知遭利用漏洞目录][S06]
- [S07：Fortinet：威胁行为者活动分析][S07]
- [S08：NIST SP 800-61r3][S08]
- [S09：AWS WAF：关联 Web ACL][S09]
- [S24：AWS：Gateway Load Balancer][S24]
- [S29：AWS：使用 GWLB 和 TGW 实现集中检查][S29]
- [S30：AWS：NAT Gateway 场景][S30]
- [S33：EKS：网络安全][S33]
- [S34：Kubernetes：Network Policies][S34]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/
