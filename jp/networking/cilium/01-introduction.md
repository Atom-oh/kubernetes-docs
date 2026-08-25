# パート 1: はじめに

> **サポート対象バージョン**: Cilium 1.18 **最終更新**: February 23, 2026

## Lab 環境のセットアップ

このドキュメントの例を実行するには、以下のツールと環境が必要です。

### 必要なツール

* kubectl v1.33 以降
* Helm v3.12 以降
* 動作する Kubernetes cluster（EKS、minikube、kind など）
* Linux kernel 4.19 以降（eBPF 機能のサポート用）

### Cilium のインストール

```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status
```

## Cilium とは？

Cilium は、Linux kernel の強力な eBPF 技術を活用して、コンテナ化されたアプリケーションにネットワーキング、セキュリティ、および可観測性を提供するオープンソースソフトウェアです。Kubernetes、Docker、Mesos などのコンテナオーケストレーションプラットフォーム向けに、ネットワーキング、セキュリティ、および可観測性を提供するよう設計されています。

### 主な機能:

* **eBPF ベース**: kernel 内のプログラム可能な datapath により、高性能なネットワーキングおよびセキュリティ機能を提供
* **API 対応ネットワーキング**: L3-L7 レイヤーで API 対応の network security policy をサポート
* **Kubernetes 統合**: Kubernetes CNI（Container Network Interface）実装を提供
* **分散 Load Balancing**: service-to-service 通信向けの効率的な分散 Load Balancing
* **Network Visibility**: Hubble による network flow の監視とトラブルシューティング
* **Multi-cluster サポート**: cluster 間ネットワーキングおよび security policy のサポート
* **Kubernetes 互換性**: Kubernetes 1.32 以降のバージョンと完全互換
* **強化された BGP サポート**: Cilium 1.18 の改善された BGP control plane による、より柔軟な routing 設定
* **強化された可観測性**: 改善された metrics および tracing 機能による、より深い洞察

### Cilium アーキテクチャ

## コンテナネットワーキングの基本

コンテナネットワーキングは、コンテナ化されたアプリケーション同士、および外部との通信を可能にする仕組みを提供します。

### コンテナネットワーキングモデル:

1. **Host Network**: コンテナが host の network namespace を共有
2. **Bridge Network**: コンテナが host 内の仮想 bridge に接続
3. **Overlay Network**: 複数の host にまたがって仮想 network を作成
4. **Underlay Network**: 物理 network infrastructure を直接利用

### コンテナネットワーキングの課題:

* **Scalability**: 数千のコンテナと Service をサポート
* **Performance**: latency を最小化し、throughput を最大化
* **Security**: microservice 間の通信を保護
* **Observability**: network flow の監視とトラブルシューティング
* **Portability**: さまざまな環境で一貫したネットワーキング体験を提供

## CNI（Container Network Interface）を理解する

> **重要な概念**: CNI（Container Network Interface）は、container runtime と network plugin 間の標準インターフェースを定義する CNCF project です。

### CNI の主要コンポーネント:

* **Plugin Architecture**: さまざまなネットワーキングソリューションの統合を可能にするモジュール設計
* **Network Configuration**: JSON 形式で定義される network 設定
* **IPAM（IP Address Management）**: IP address の割り当てと管理
* **Standard API**: container の追加・削除時に network を設定するための標準 API

### 主な CNI Plugin の比較:

| 機能                      | Cilium                    | Calico         | Flannel        | AWS VPC CNI            |
| ---------------------------- | ------------------------- | -------------- | -------------- | ---------------------- |
| **基本技術**          | eBPF                      | iptables/IPVS  | VXLAN/host-gw  | AWS ENI                |
| **Network Policy**           | L3-L7                     | L3-L4          | 限定的        | AWS Security Groups    |
| **暗号化**               | IPsec/WireGuard           | IPsec          | なし           | なし                   |
| **可観測性**            | Hubble                    | Flow Logs      | 限定的        | VPC Flow Logs          |
| **Service Mesh**             | 組み込み                  | Istio が必要 | Istio が必要 | Istio/AppMesh が必要 |
| **Performance**              | 非常に高い                | 高い           | 中程度         | 高い                   |
| **IPAM**                     | Cluster Pool, CRD         | IPAM Plugin    | Host Subnet    | AWS IPAM               |
| **Kubernetes 互換性** | 1.32+                     | 1.29+          | 1.28+          | 1.29+                  |
| **BGP サポート**              | 強化された control (v1.18+) | 限定的        | なし           | VPC Routing            |

* **Weave Net**: Multi-host コンテナネットワーキング
* **AWS VPC CNI**: AWS VPC との直接統合

## Cilium の差別化機能

Cilium は、他の CNI ソリューションと比較していくつかの独自の利点を提供します。

### 技術的な差別化:

* **eBPF の活用**: kernel 内のプログラム可能な datapath による高性能と柔軟性
* **API 対応ネットワーキング**: L7 レイヤーまでの Network Policy サポート
* **XDP（eXpress Data Path）**: packet processing 性能の最適化
* **Kube-proxy の置き換え**: より効率的な Service Load Balancing
* **Hubble 統合**: 強力な network observability tool
* **最新 Kubernetes 互換性**: Kubernetes 1.32 以降のバージョンと完全互換

### ユースケース別の利点:

* **Microservices Architecture**: きめ細かな Network Policy と可観測性
* **Multi-cluster Deployment**: cluster 間のシームレスなネットワーキング
* **Security 重視の環境**: 強力な Network Security Policy
* **高性能要件**: 最適化された datapath
* **Service Mesh 統合**: Istio などの Service Mesh との統合

## Lab: Cilium のインストールと基本設定

```bash
# Install Cilium CLI on Kubernetes cluster
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

### 基本 Network Policy の適用:

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。
