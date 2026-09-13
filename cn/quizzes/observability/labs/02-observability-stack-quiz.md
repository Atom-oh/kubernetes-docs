# 可观测性实验 02 测验

<span id="observability-lab-part-2-observability-stack-quiz"></span>

> **最后更新**: September 13, 2026

1. 跨集群采集应使用什么端点？
   - A) 仅使用另一个集群的 Service DNS。
   - B) 具备实际路由、DNS 和 TLS 的私有端点。
   - C) 始终禁用 TLS 验证。
   - D) 将 kubeconfig 文件用作 URL。

<details>
<summary>显示答案</summary>

**答案：B) 具备实际路由、DNS 和 TLS 的私有端点。**

NLB 转发 TCP，服务器验证客户端证书。

</details>

---

2. CRI 日志解析顺序是什么？
   - A) 仅使用 Docker JSON 解析器。
   - B) 先使用 Container/CRI 解析器，再解析 JSON。
   - C) 将整个前缀视为 JSON 字段。
   - D) 将每个 trace ID 设为流标签。

<details>
<summary>显示答案</summary>

**答案：B) 先使用 Container/CRI 解析器，再解析 JSON。**

验证是否保留了应用正文中的 service/level/trace_id。

</details>

---

3. 应如何探测 mTLS Prometheus？
   - A) 不带证书的默认 HTTPS 探测始终成功。
   - B) 使用配置了客户端证书的 promtool exec 探测。
   - C) 删除所有探测。
   - D) 始终返回 readiness true。

<details>
<summary>显示答案</summary>

**答案：B) 使用配置了客户端证书的 promtool exec 探测。**

已测试实际的 Operator 合并以及 Prometheus TLS ready/healthy 行为。

</details>

---

4. 哪项 Tempo3 配置更改很重要？
   - A) 仅复制旧的 Tempo2 ingester 值。
   - B) 使用 live-store/backend scheduler/worker 和当前 chart 值。
   - C) 复制 Loki 配置。
   - D) chart 和应用版本始终相同。

<details>
<summary>显示答案</summary>

**答案：B) 使用 live-store/backend scheduler/worker 和当前 chart 值。**

将 chart 渲染与实际二进制配置/启动分开检查。

</details>

---

5. 单实例 Loki/Tempo 基线意味着什么？
   - A) 生产环境 HA 会自动实现。
   - B) 一个持久的实验实例，而非 HA/容量保证。
   - C) 没有存储成本。
   - D) 自动保证备份。

<details>
<summary>显示答案</summary>

**答案：B) 一个持久的实验实例，而非 HA/容量保证。**

验证保留期、PVC、清理以及故障影响。

</details>

---

6. AIOps CloudWatch 路径需要什么 JSON？
   - A) 仅需要查询字符串。
   - B) 保留 service/level/trace_id 的结构化日志。
   - C) 所有明文密码。
   - D) Trace 会自动创建日志。

<details>
<summary>显示答案</summary>

**答案：B) 保留 service/level/trace_id 的结构化日志。**

已在本地检查 raw_log 行为和实际 exporter PutLogEvents 消息。

</details>

---

7. Grafana 关联需要什么？
   - A) 仅启用一个 UI 选项。
   - B) 匹配的 UID、字段名称、实际数据和保留期。
   - C) 仅匹配显示名称。
   - D) 始终将 trace_id 大写。

<details>
<summary>显示答案</summary>

**答案：B) 匹配的 UID、字段名称、实际数据和保留期。**

对齐 prometheus/loki/tempo UID 和转义后的 derived-field 表达式。

</details>

---

8. Service Prometheus remote-write 如何处理 exemplar？
   - A) 始终自动保留。
   - B) 验证 sendExemplars、接收/存储以及 datasource 链接。
   - C) 一个标签会自动创建 trace。
   - D) 每个请求都必然会被存储。

<details>
<summary>显示答案</summary>

**答案：B) 验证 sendExemplars、接收/存储以及 datasource 链接。**

验证代表性的 trace 确实存在，而不仅仅是传输选项。

</details>

---

9. 应如何对待节点日志 DaemonSet 权限？
   - A) 始终启用 hostPID 和所有 capability。
   - B) 仅允许受限的只读 host 挂载、读取 RBAC 以及明确的 root 例外。
   - C) 完整 cluster-admin。
   - D) host 日志路径不涉及任何权限影响。

<details>
<summary>显示答案</summary>

**答案：B) 仅允许受限的只读 host 挂载、读取 RBAC 以及明确的 root 例外。**

一并验证 namespace 准入和实际文件权限。

</details>

---

10. 应如何描述可选后端和持久队列？
   - A) 所有后端均已部署。
   - B) 它们需要单独验证；基线不保证持久的 offset/queue。
   - C) 重启时不可能发生丢失/重复。
   - D) 24 小时保留期证明 30 天 SLO。

<details>
<summary>显示答案</summary>

**答案：B) 它们需要单独验证；基线不保证持久的 offset/queue。**

仅将实际配置和验证记录为成功。

</details>

---

[返回指南](../../../labs/observability/02-observability-stack-lab.md)
