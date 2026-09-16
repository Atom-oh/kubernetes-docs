> [韓国語版](https://www.atomai.click/kubernetes-docs/ko/)

# Kubernetes および Amazon EKS トレーニングコンテンツ
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

このリポジトリは、Linux とコンテナの基礎、Kubernetes と Amazon EKS、ネットワーキング、Service Mesh（サービスメッシュ）、ストレージ、データベース、データパイプライン、AI/ML、セキュリティと運用を網羅した総合的なクラウドガイドブックです。学習教材に加えて、実際の AWS 環境で計測したベンチマークデータ、トピックごとのクイズ、厳選されたハンズオンラボも提供します。

## 学習教材とクイズ

このトレーニングコンテンツでは、学習教材とあわせてトピックごとのクイズを提供しています。クイズを通じて学んだ内容を確認し、定着させることができます。各クイズは解答が隠されたトグル形式で構成されており、まず自分で問題に取り組んでから解答を確認できます。

- [学習教材の目次](#table-of-contents) - トピック別の学習教材
- [クイズ集](./quizzes/README.md) - トピック別のクイズ
- [ガイドブックロードマップ](./roadmap.md) - 学習マップ全体と推奨学習パス | [クイズ](./quizzes/roadmap-quiz.md)
- [LLM で読む](./llm-guide.md) - llms.txt、マニフェスト、MCP を通じて原典を探して読む方法 | [クイズ](./quizzes/llm-guide-quiz.md)

## 目次

### ニュース
- [週刊ニュース](./news/README.md) - Kubernetes/EKS エコシステムの最新ニュースダイジェスト

### Linux とコンテナ
1. [Linux の基礎](./basics/01-linux-basics.md) | [クイズ](./quizzes/basics/01-linux-basics-quiz.md) | [ラボ](./labs/basics/01-linux-basics-lab.md)
2. [Linux 運用スキル](./basics/02-linux-advanced.md) | [クイズ](./quizzes/basics/02-linux-advanced-quiz.md) | [ラボ](./labs/basics/02-linux-advanced-lab.md)
3. [コンテナ技術](./basics/03-container-technology.md) | [クイズ](./quizzes/basics/03-container-technology-quiz.md) | [ラボ](./labs/basics/03-container-technology-lab.md)
4. [eBPF の基礎と実践的な活用](./basics/05-ebpf-fundamentals.md) | [クイズ](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Linux カーネル
1. [Linux カーネル概要](./kernel/README.md)
2. [コンテナを支えるカーネル機能](./kernel/01-container-primitives.md) | [クイズ](./quizzes/kernel/01-container-primitives-quiz.md)
3. [カーネルネットワークスタック](./kernel/02-network-stack.md) | [クイズ](./quizzes/kernel/02-network-stack-quiz.md)
4. [EKS ノードのカーネルチューニング](./kernel/03-eks-node-tuning.md) | [クイズ](./quizzes/kernel/03-eks-node-tuning-quiz.md)

### Kubernetes のコア概念
1. [Kubernetes 入門](./basics/04-kubernetes-introduction.md) | [クイズ](./quizzes/basics/04-kubernetes-introduction-quiz.md)
2. [クラスターアーキテクチャ](./core/01-cluster-architecture.md) | [クイズ](./quizzes/core/01-cluster-architecture-quiz.md)
3. [Pod とワークロード](./core/02-pods-and-workloads.md) | [クイズ](./quizzes/core/02-pods-and-workloads-quiz.md)
4. [Service とネットワーキング](./core/03-services-networking.md) | [クイズ](./quizzes/core/03-services-networking-quiz.md)
5. [ストレージ](./core/04-storage.md) | [クイズ](./quizzes/core/04-storage-quiz.md)
6. [構成管理](./core/05-configuration-secrets.md) | [クイズ](./quizzes/core/05-configuration-secrets-quiz.md)
7. [セキュリティ](./core/06-security.md) | [クイズ](./quizzes/core/06-security-quiz.md)
8. [ポリシー](./core/07-policies.md) | [クイズ](./quizzes/core/07-policies-quiz.md)
9. [スケジューリング、プリエンプション、退避](./core/08-scheduling-preemption-eviction.md) | [クイズ](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
10. [クラスター管理](./core/09-cluster-administration.md) | [クイズ](./quizzes/core/09-cluster-administration-quiz.md)
11. [Kubernetes における Windows](./core/10-windows-in-kubernetes.md) | [クイズ](./quizzes/core/10-windows-in-kubernetes-quiz.md)
12. [Kubernetes の拡張](./core/11-extending-kubernetes.md) | [クイズ](./quizzes/core/11-extending-kubernetes-quiz.md)
13. カスタムスケジューラー
   - [Part 1: カスタムスケジューラーの基礎](./scheduling/01-custom-scheduler-part1.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Part 2: スケジューラーの拡張とフレームワーク](./scheduling/02-custom-scheduler-part2.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Part 3: カスタムスケジューラーの実装例とモニタリング](./scheduling/03-custom-scheduler-part3.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)
14. オートスケーリング
   - [KEDA](./autoscaling/01-keda.md) | [クイズ](./quizzes/autoscaling/05-keda-quiz.md)
   - [Karpenter](./autoscaling/02-karpenter.md) | [クイズ](./quizzes/autoscaling/06-karpenter-quiz.md)
   - [Knative](./autoscaling/03-knative.md) | [クイズ](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [EKS 入門](./eks/01-eks-introduction.md) | [クイズ](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS クラスターの作成
   - [Part 1: 前提条件](./eks/02-eks-cluster-creation-part1.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Part 2: eksctl によるクラスター作成](./eks/02-eks-cluster-creation-part2.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Part 3: AWS マネジメントコンソールと CLI によるクラスター作成](./eks/02-eks-cluster-creation-part3.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Part 4: Terraform と CDK によるクラスター作成](./eks/02-eks-cluster-creation-part4.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Part 5: クラスターへのアクセス、検証、アップグレード、削除](./eks/02-eks-cluster-creation-part5.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS ネットワーキング
   - [Part 1: 基本概念と VPC 構成](./eks/03-eks-networking-part1.md) | [クイズ](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Part 2: Service とロードバランシング、Network Policy](./eks/03-eks-networking-part2.md) | [クイズ](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Part 3: パフォーマンス最適化、トラブルシューティング、高度なユースケース](./eks/03-eks-networking-part3.md) | [クイズ](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS ストレージ
   - [Part 1: 基本概念、EBS、EFS](./eks/04-eks-storage-part1.md) | [クイズ](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Part 2: FSx for Lustre、S3、スナップショット、ボリューム拡張、パフォーマンス最適化](./eks/04-eks-storage-part2.md) | [クイズ](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Part 3: モニタリング、トラブルシューティング、コスト最適化、セキュリティ](./eks/04-eks-storage-part3.md) | [クイズ](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS セキュリティ](./eks/05-eks-security.md) | [クイズ](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS のモニタリングとロギング](./eks/06-eks-monitoring-logging.md) | [クイズ](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS のコスト最適化](./eks/07-eks-cost-optimization.md) | [クイズ](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS のアップグレード](./eks/08-eks-upgrades.md) | [クイズ](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS のトラブルシューティング](./eks/09-eks-troubleshooting.md) | [クイズ](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS のレジリエンシーと高可用性](./eks/10-eks-resiliency.md) | [クイズ](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS の高度なデバッグ](./eks/11-eks-advanced-debugging.md) | [クイズ](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Kubernetes バージョンの機能とロードマップ](./eks/12-kubernetes-version-roadmap.md) | [クイズ](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes 入門](./eks-hybrid-nodes/README.md)
2. [前提条件](./eks-hybrid-nodes/01-prerequisites.md) | [クイズ](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [ネットワーク構成](./eks-hybrid-nodes/02-network-configuration.md) | [クイズ](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [インターネット制限環境のセットアップ](./eks-hybrid-nodes/03-airgap-setup.md) | [クイズ](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [ノードのブートストラップ](./eks-hybrid-nodes/04-node-bootstrap.md) | [クイズ](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU サーバーの統合](./eks-hybrid-nodes/05-gpu-integration.md) | [クイズ](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [ワークロード配置戦略](./eks-hybrid-nodes/06-workload-placement.md) | [クイズ](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [ノードのライフサイクル管理](./eks-hybrid-nodes/07-node-lifecycle.md) | [クイズ](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [運用と保守](./eks-hybrid-nodes/08-operations.md) | [クイズ](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [ベアメタル OS のセットアップ](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [クイズ](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [クイズ](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
12. [ネットワーク分離のセキュリティレビュー](./eks-hybrid-nodes/11-network-separation-security.md) | [クイズ](./quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode 入門](./eks-auto-mode/README.md)
2. [はじめに](./eks-auto-mode/01-getting-started.md) | [クイズ](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool の構成](./eks-auto-mode/02-nodepool-configuration.md) | [クイズ](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [スケーリングの挙動](./eks-auto-mode/03-scaling-behavior.md) | [クイズ](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [スポットインスタンス戦略](./eks-auto-mode/04-spot-strategies.md) | [クイズ](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [運用と管理](./eks-auto-mode/05-operations.md) | [クイズ](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [コスト管理](./eks-auto-mode/06-cost-management.md) | [クイズ](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [ノードのライフサイクル](./eks-auto-mode/07-node-lifecycle.md) | [クイズ](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [ワークロードの最適化](./eks-auto-mode/08-workload-optimization.md) | [クイズ](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [移行ガイド](./eks-auto-mode/09-migration-guide.md) | [クイズ](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### ネットワーキング

1. [ゼロから学ぶ Linux ネットワーキング](./networking/beginner/README.md)
   - [1. Linux と CLI](./networking/beginner/01-linux-cli.md) | [クイズ](./quizzes/networking/beginner/01-linux-cli-quiz.md)
   - [2. アドレスとインターフェース](./networking/beginner/02-addressing-interfaces.md) | [クイズ](./quizzes/networking/beginner/02-addressing-interfaces-quiz.md)
   - [3. ネットワーク設定の永続化](./networking/beginner/03-persistent-configuration.md) | [クイズ](./quizzes/networking/beginner/03-persistent-configuration-quiz.md)
   - [4. DNS と接続性](./networking/beginner/04-dns-connectivity.md) | [クイズ](./quizzes/networking/beginner/04-dns-connectivity-quiz.md)
   - [5. SSH によるリモートアクセス](./networking/beginner/05-ssh-access.md) | [クイズ](./quizzes/networking/beginner/05-ssh-access-quiz.md)
   - [6. ファイアウォールとホストセキュリティ](./networking/beginner/06-firewalls-host-security.md) | [クイズ](./quizzes/networking/beginner/06-firewalls-host-security-quiz.md)
   - [7. モニタリングとパフォーマンス](./networking/beginner/07-monitoring-performance.md) | [クイズ](./quizzes/networking/beginner/07-monitoring-performance-quiz.md)
   - [8. キャップストーンとクラウド接続](./networking/beginner/08-container-cloud-capstone.md) | [クイズ](./quizzes/networking/beginner/08-container-cloud-capstone-quiz.md)
2. [エキスパート向けネットワーキングパス](./networking/expert/README.md)
   - [1. プロトコルプロジェクト](./networking/expert/01-protocol-projects.md) | [クイズ](./quizzes/networking/expert/01-protocol-projects-quiz.md)
   - [2. ルーティングポリシーと収束](./networking/expert/02-routing-policy-convergence.md) | [クイズ](./quizzes/networking/expert/02-routing-policy-convergence-quiz.md)
   - [3. データセンターの EVPN/VXLAN](./networking/expert/03-datacenter-evpn.md) | [クイズ](./quizzes/networking/expert/03-datacenter-evpn-quiz.md)
   - [4. Linux のパケットパスとパフォーマンス](./networking/expert/04-linux-performance.md) | [クイズ](./quizzes/networking/expert/04-linux-performance-quiz.md)
   - [5. クラウドと CNI の設計](./networking/expert/05-cloud-cni-design.md) | [クイズ](./quizzes/networking/expert/05-cloud-cni-design-quiz.md)
   - [6. 自動化と総合評価](./networking/expert/06-automation-capstone.md) | [クイズ](./quizzes/networking/expert/06-automation-capstone-quiz.md)
3. [Kubernetes ネットワーキング概要](./networking/README.md) | [クイズ](./quizzes/networking/00-networking-overview-quiz.md)
4. [ネットワークの基礎 — 25 のプロトコル](./basics/06-network-fundamentals-part1.md)
   - [Part 1: 階層モデル、リンク層とルーティング層](./basics/06-network-fundamentals-part1.md) | [クイズ](./quizzes/basics/06-network-fundamentals-part1-quiz.md)
   - [Part 2: トランスポート層と TLS](./basics/06-network-fundamentals-part2.md) | [クイズ](./quizzes/basics/06-network-fundamentals-part2-quiz.md)
   - [Part 3: アプリケーションプロトコル](./basics/06-network-fundamentals-part3.md) | [クイズ](./quizzes/basics/06-network-fundamentals-part3-quiz.md)
   - [Part 4: リクエストの旅路とクラウド](./basics/06-network-fundamentals-part4.md) | [クイズ](./quizzes/basics/06-network-fundamentals-part4-quiz.md)
5. [Linux ネットワーク診断の実践](./networking/07-linux-network-diagnostics.md) | [クイズ](./quizzes/networking/07-linux-network-diagnostics-quiz.md)
6. [VPC CNI](./networking/01-vpc-cni.md) | [クイズ](./quizzes/networking/01-vpc-cni-quiz.md)
7. **Cilium ディープダイブ**
   - [Cilium 入門](./networking/cilium/README.md)
   - [Part 1: 導入](./networking/cilium/01-introduction.md) | [クイズ](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [Part 2: eBPF](./networking/cilium/02-ebpf.md) | [クイズ](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [Part 3: ネットワーキング](./networking/cilium/03-networking.md) | [クイズ](./quizzes/networking/cilium/03-networking-quiz.md)
   - [Part 4: IPAM とポリシー](./networking/cilium/04-ipam-policy.md) | [クイズ](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [Part 5: L2-L7 ネットワーキング](./networking/cilium/05-l2-l7-networking.md) | [クイズ](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [Part 6: セキュリティと可視化](./networking/cilium/06-security-visibility.md) | [クイズ](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [Part 7: 高度なトピック](./networking/cilium/07-advanced-topics.md) | [クイズ](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [ネットワーキングの概念](./networking/cilium/networking-concepts.md) | [クイズ](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [用語集](./networking/cilium/glossary.md) | [クイズ](./quizzes/networking/cilium/glossary-quiz.md)
8. **Calico ディープダイブ**
   - [Calico 入門](./networking/calico/README.md)
   - [Part 1: 導入](./networking/calico/01-introduction.md) | [クイズ](./quizzes/networking/calico/01-introduction-quiz.md)
   - [Part 2: アーキテクチャ](./networking/calico/02-architecture.md) | [クイズ](./quizzes/networking/calico/02-architecture-quiz.md)
   - [Part 3: ネットワーキングモード](./networking/calico/03-networking-modes.md) | [クイズ](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [Part 4: BGP ディープダイブ](./networking/calico/04-bgp-deep-dive.md) | [クイズ](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [Part 5: Network Policy](./networking/calico/05-network-policy.md) | [クイズ](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [Part 6: eBPF データプレーン](./networking/calico/06-ebpf-dataplane.md) | [クイズ](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [Part 7: 高度なトピック](./networking/calico/07-advanced-topics.md) | [クイズ](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [Part 8: EKS との統合](./networking/calico/08-eks-integration.md) | [クイズ](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [Part 9: 運用](./networking/calico/09-operations.md) | [クイズ](./quizzes/networking/calico/09-operations-quiz.md)
   - [用語集](./networking/calico/glossary.md) | [クイズ](./quizzes/networking/calico/glossary-quiz.md)
9. [VPC Lattice](./networking/02-vpc-lattice.md) | [クイズ](./quizzes/networking/02-vpc-lattice-quiz.md)
10. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [クイズ](./quizzes/networking/03-aws-lb-controller-quiz.md)
11. [Gateway API](./networking/04-gateway-api.md) | [クイズ](./quizzes/networking/04-gateway-api-quiz.md)
12. [組織間の VPC 接続](./networking/05-cross-org-vpc-connectivity.md) | [クイズ](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
13. [Pod ネットワークベンチマーク](./networking/06-pod-network-benchmark.md) | [クイズ](./quizzes/networking/06-pod-network-benchmark-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [クイズ](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Linkerd 入門](./service-mesh/linkerd/README.md)
   - [インストール](./service-mesh/linkerd/01-installation.md) | [クイズ](./quizzes/service-mesh/linkerd/installation.md)
   - [アーキテクチャ](./service-mesh/linkerd/02-architecture.md) | [クイズ](./quizzes/service-mesh/linkerd/architecture.md)
   - [トラフィック管理](./service-mesh/linkerd/03-traffic-management.md) | [クイズ](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [セキュリティ](./service-mesh/linkerd/04-security.md) | [クイズ](./quizzes/service-mesh/linkerd/security.md)
   - [オブザーバビリティ](./service-mesh/linkerd/05-observability.md) | [クイズ](./quizzes/service-mesh/linkerd/observability.md)
   - [マルチクラスター](./service-mesh/linkerd/06-multi-cluster.md) | [クイズ](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [ベストプラクティス](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Cilium Service Mesh 入門](./service-mesh/cilium-service-mesh/README.md)
   - [アーキテクチャ](./service-mesh/cilium-service-mesh/01-architecture.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [トラフィック管理](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [セキュリティ](./service-mesh/cilium-service-mesh/03-security.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [オブザーバビリティ](./service-mesh/cilium-service-mesh/04-observability.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [ベストプラクティス](./service-mesh/cilium-service-mesh/06-best-practices.md)

4. **VPC Lattice ディープダイブ**
   - [VPC Lattice ディープダイブ概要](./service-mesh/vpc-lattice/README.md)
   - [App Mesh と VPC Lattice のアーキテクチャ比較](./service-mesh/vpc-lattice/01-appmesh-vs-lattice.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/01-appmesh-vs-lattice-quiz.md)
   - [レイテンシーへの影響分析](./service-mesh/vpc-lattice/02-latency.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/02-latency-quiz.md)
   - [IAM 認証フロー](./service-mesh/vpc-lattice/03-auth-flow.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/03-auth-flow-quiz.md)
   - [基礎 — リンクローカルと SNI](./service-mesh/vpc-lattice/04-networking-basics.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/04-networking-basics-quiz.md)
   - [ワークロードアイデンティティの移行](./service-mesh/vpc-lattice/05-spiffe-to-iam.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/05-spiffe-to-iam-quiz.md)
   - [制約と意思決定のポイント](./service-mesh/vpc-lattice/06-constraints.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/06-constraints-quiz.md)
   - [カーネルデータパス](./service-mesh/vpc-lattice/07-kernel-datapath.md) | [クイズ](./quizzes/service-mesh/vpc-lattice/07-kernel-datapath-quiz.md)

### ストレージ
1. [ストレージ概要](./storage/README.md)
2. [EBS gp2 と gp3 の実測ベンチマーク](./storage/01-ebs-gp2-gp3-benchmark.md) | [クイズ](./quizzes/storage/01-ebs-gp2-gp3-benchmark-quiz.md)

### データベース
1. [Kubernetes 上のデータベース概要](./database/README.md)
2. [ClickHouse on EKS の実測ベンチマーク](./database/01-clickhouse-on-eks.md) | [クイズ](./quizzes/database/01-clickhouse-on-eks-quiz.md)

### ブロックチェーン
1. [ブロックチェーン概要](./blockchain/README.md)
2. [ブロックチェーンの基礎](./blockchain/01-fundamentals.md) | [クイズ](./quizzes/blockchain/01-fundamentals-quiz.md)
3. [EKS 上でのブロックチェーンノードの運用](./blockchain/02-nodes-on-eks.md) | [クイズ](./quizzes/blockchain/02-nodes-on-eks-quiz.md)
4. [Amazon Managed Blockchain](./blockchain/03-managed-blockchain.md) | [クイズ](./quizzes/blockchain/03-managed-blockchain-quiz.md)
5. [金融サービスの観点](./blockchain/04-financial-services.md) | [クイズ](./quizzes/blockchain/04-financial-services-quiz.md)

### データパイプライン
1. [Data on EKS 概要](./data-on-eks/README.md)
   - [モダンデータパイプラインの解剖](./data-on-eks/01-data-pipeline-anatomy.md) | [クイズ](./quizzes/data-on-eks/01-data-pipeline-anatomy-quiz.md)
   - [SageMaker Unified Studio のガバナンス](./data-on-eks/sagemaker-unified-studio/README.md)
   - [Part 4: ドメイン、プロジェクト、メンバーシップのガバナンス](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [クイズ](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
2. **Kafka on EKS ディープダイブ**
   - [Kafka on EKS 入門](./data-on-eks/kafka/README.md)
   - [Part 1: Kafka の基礎](./data-on-eks/kafka/01-kafka-fundamentals.md) | [クイズ](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [Part 2: Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [クイズ](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [Part 3: Kafka の運用](./data-on-eks/kafka/03-kafka-operations.md) | [クイズ](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [Part 4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [クイズ](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [Part 5: Kafka Connect と MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [クイズ](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [Part 6: MSK との統合](./data-on-eks/kafka/06-msk-integration.md) | [クイズ](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [Part 7: モニタリング](./data-on-eks/kafka/07-monitoring.md) | [クイズ](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [Part 8: ベストプラクティス](./data-on-eks/kafka/08-best-practices.md) | [クイズ](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
   - [Part 9: Kafka の実測ベンチマーク](./data-on-eks/kafka/09-kafka-benchmark.md) | [クイズ](./quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)
3. **Spark on EKS ディープダイブ**
   - [Spark on EKS 入門](./data-on-eks/spark/README.md)
   - [Part 1: Spark on Kubernetes の基礎](./data-on-eks/spark/01-spark-fundamentals.md) | [クイズ](./quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
   - [Part 2: Spark Operator](./data-on-eks/spark/02-spark-operator.md) | [クイズ](./quizzes/data-on-eks/spark/02-spark-operator-quiz.md)
   - [Part 3: Amazon EMR on EKS](./data-on-eks/spark/03-emr-on-eks.md) | [クイズ](./quizzes/data-on-eks/spark/03-emr-on-eks-quiz.md)
   - [Part 4: パフォーマンスとコストのチューニング](./data-on-eks/spark/04-performance-tuning.md) | [クイズ](./quizzes/data-on-eks/spark/04-performance-tuning-quiz.md)
   - [Part 5: ベストプラクティスとセキュリティ](./data-on-eks/spark/05-best-practices.md) | [クイズ](./quizzes/data-on-eks/spark/05-best-practices-quiz.md)
4. **Airflow on EKS ディープダイブ**
   - [Airflow on EKS 入門](./data-on-eks/airflow/README.md)
   - [Part 1: Kubernetes 上の Airflow アーキテクチャ](./data-on-eks/airflow/01-architecture.md) | [クイズ](./quizzes/data-on-eks/airflow/01-architecture-quiz.md)
   - [Part 2: Helm によるデプロイと Executor の選択](./data-on-eks/airflow/02-helm-deployment.md) | [クイズ](./quizzes/data-on-eks/airflow/02-helm-deployment-quiz.md)
   - [Part 3: DAG のパターンと KubernetesPodOperator](./data-on-eks/airflow/03-dag-patterns.md) | [クイズ](./quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)
   - [Part 4: Amazon MWAA との統合](./data-on-eks/airflow/04-mwaa-integration.md) | [クイズ](./quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
   - [Part 5: 運用とセキュリティ](./data-on-eks/airflow/05-operations.md) | [クイズ](./quizzes/data-on-eks/airflow/05-operations-quiz.md)
5. **Flink on EKS ディープダイブ**
   - [Flink on EKS 入門](./data-on-eks/flink/README.md)
   - [Part 1: Kubernetes 上の Flink アーキテクチャ](./data-on-eks/flink/01-architecture.md) | [クイズ](./quizzes/data-on-eks/flink/01-architecture-quiz.md)
   - [Part 2: Flink Kubernetes Operator](./data-on-eks/flink/02-flink-kubernetes-operator.md) | [クイズ](./quizzes/data-on-eks/flink/02-flink-kubernetes-operator-quiz.md)
   - [Part 3: 状態、チェックポイント、ストリーミングパターン](./data-on-eks/flink/03-state-checkpointing-streaming.md) | [クイズ](./quizzes/data-on-eks/flink/03-state-checkpointing-streaming-quiz.md)
   - [Part 4: 運用、高可用性、Managed Flink](./data-on-eks/flink/04-operations-ha.md) | [クイズ](./quizzes/data-on-eks/flink/04-operations-ha-quiz.md)

### AI/ML
1. [AI/ML ワークロード](./ai-ml/01-ai-ml-workloads.md) | [クイズ](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI インフラストラクチャ](./ai-ml/06-ai-infrastructure.md) | [クイズ](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [EKS 上でのモデル学習](./ai-ml/05-model-training.md) | [クイズ](./quizzes/ai-ml/05-model-training-quiz.md)
4. [推論フレームワーク](./ai-ml/04-inference-frameworks.md) | [クイズ](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM のデプロイと最適化](./ai-ml/02-vllm-deployment.md) | [クイズ](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上の Agentic AI プラットフォーム](./ai-ml/03-agentic-ai-platform.md) | [クイズ](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML のベストプラクティス](./ai-ml/07-ai-ml-best-practices.md) | [クイズ](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **Ray on EKS ディープダイブ**
   - [Ray on EKS 入門](./ai-ml/ray/README.md)
   - [Part 1: Ray のアーキテクチャ](./ai-ml/ray/01-architecture.md) | [クイズ](./quizzes/ai-ml/ray/01-architecture-quiz.md)
   - [Part 2: KubeRay Operator](./ai-ml/ray/02-kuberay-operator.md) | [クイズ](./quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
   - [Part 3: Ray Train と Ray Tune](./ai-ml/ray/03-ray-train-tune.md) | [クイズ](./quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
   - [Part 4: Ray Serve](./ai-ml/ray/04-ray-serve.md) | [クイズ](./quizzes/ai-ml/ray/04-ray-serve-quiz.md)
9. **Kubeflow on EKS ディープダイブ**
   - [Kubeflow on EKS 入門](./ai-ml/kubeflow/README.md)
   - [Part 1: Kubeflow のアーキテクチャと EKS へのインストール](./ai-ml/kubeflow/01-architecture-installation.md) | [クイズ](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [Part 2: Kubeflow Pipelines](./ai-ml/kubeflow/02-pipelines.md) | [クイズ](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [Part 3: Kubeflow Notebooks](./ai-ml/kubeflow/03-notebooks.md) | [クイズ](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [Part 4: Katib — ハイパーパラメータチューニングと AutoML](./ai-ml/kubeflow/04-katib.md) | [クイズ](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [Part 5: Kubeflow Trainer と分散学習](./ai-ml/kubeflow/05-training-operator.md) | [クイズ](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [Part 6: KServe — Kubernetes 上でのモデルサービング](./ai-ml/kubeflow/06-kserve.md) | [クイズ](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
10. **MLflow on EKS ディープダイブ**
   - [MLflow on EKS 入門](./ai-ml/mlflow/README.md)
   - [Part 1: MLflow Tracking](./ai-ml/mlflow/01-tracking.md) | [クイズ](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
   - [Part 2: MLflow Model Registry](./ai-ml/mlflow/02-model-registry.md) | [クイズ](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
   - [Part 3: EKS への MLflow のデプロイ](./ai-ml/mlflow/03-eks-deployment.md) | [クイズ](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
11. **SageMaker AI Qwen PII ガイドブック**
   - [ガイドブック入門](./ai-ml/sagemaker-ai/README.md)
   - [Part 1: プラットフォームアーキテクチャ](./ai-ml/sagemaker-ai/01-platform-architecture.md) | [クイズ](./quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)
   - [Part 2: 合成 PII データとトークン化](./ai-ml/sagemaker-ai/02-pii-data-tokenization.md) | [クイズ](./quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)
   - [Part 3: SageMaker AI と MLflow の実行](./ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md) | [クイズ](./quizzes/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution-quiz.md)
   - [Part 4: Unified Studio のガバナンス](./data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | [クイズ](./quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
   - [Part 5: 事実検証の結果](./ai-ml/sagemaker-ai/04-validation-results.md) | [クイズ](./quizzes/ai-ml/sagemaker-ai/04-validation-results-quiz.md)
12. [LLM Gateway（Inference Gateway）ディープダイブ](./ai-ml/08-llm-gateway.md) | [クイズ](./quizzes/ai-ml/08-llm-gateway-quiz.md)

### セキュリティとポリシー
1. [Kyverno によるポリシー管理](./security/01-kyverno-policy-management.md) | [クイズ](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes の認証と認可](./security/02-kubernetes-auth-authz.md) | [クイズ](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod Security Standards](./security/03-pod-security-standards.md) | [クイズ](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Network Policy](./security/04-network-policies.md) | [クイズ](./quizzes/security/04-network-policies-quiz.md)
5. [Secret の管理](./security/05-secrets-management.md) | [クイズ](./quizzes/security/05-secrets-management-quiz.md)
6. [EKS セキュリティのベストプラクティス](./security/06-eks-security-best-practices.md) | [クイズ](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [イメージセキュリティ](./security/07-image-security.md) | [クイズ](./quizzes/security/07-image-security-quiz.md)
8. [ランタイムセキュリティ](./security/08-runtime-security.md) | [クイズ](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [クイズ](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [クイズ](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [クイズ](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [クイズ](./quizzes/security/12-spiffe-spire-quiz.md)

### GitOps
1. [GitOps 概要](./gitops/README.md)
2. **ArgoCD**
   - [ArgoCD 入門](./gitops/argocd/README.md) | [クイズ](./quizzes/gitops/01-argocd-quiz.md)
   - [インストール](./gitops/argocd/01-installation.md) | [クイズ](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Application](./gitops/argocd/02-applications.md) | [クイズ](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [同期戦略](./gitops/argocd/03-sync-strategies.md) | [クイズ](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [クイズ](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [トラフィック管理](./gitops/argocd/05-traffic-management.md) | [クイズ](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Project と RBAC](./gitops/argocd/06-projects-rbac.md) | [クイズ](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [セキュリティ](./gitops/argocd/07-security.md) | [クイズ](./quizzes/gitops/argocd/07-security-quiz.md)
   - [通知](./gitops/argocd/08-notifications.md) | [クイズ](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [ベストプラクティス](./gitops/argocd/09-best-practices.md) | [クイズ](./quizzes/gitops/argocd/09-best-practices-quiz.md)
   - [Rollouts の Experiment ディープダイブ](./gitops/argocd/10-rollouts-experiment.md) | [クイズ](./quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [クイズ](./quizzes/gitops/02-fluxcd-quiz.md)
4. [GitOps ツールの比較](./gitops/03-gitops-comparison.md) | [クイズ](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Flagger によるプログレッシブデリバリー](./gitops/04-flagger.md) | [クイズ](./quizzes/gitops/04-flagger-quiz.md)
6. [フィーチャーフラグと OpenFeature](./gitops/05-feature-flags.md) | [クイズ](./quizzes/gitops/05-feature-flags-quiz.md)

### エンタープライズクラウドガバナンス
1. [ガバナンス概要](./governance/00-governance-overview.md) | [クイズ](./quizzes/governance/00-governance-overview-quiz.md)
2. [Landing Zone、OU、組織統制](./governance/01-landing-zone-and-ou.md) | [クイズ](./quizzes/governance/01-landing-zone-and-ou-quiz.md)
3. [アカウント構成と IAM の境界](./governance/02-account-and-iam.md) | [クイズ](./quizzes/governance/02-account-and-iam-quiz.md)
4. [マルチアカウント・マルチクラスターの EKS アーキテクチャ](./governance/03-eks-multi-account-multi-cluster.md) | [クイズ](./quizzes/governance/03-eks-multi-account-multi-cluster-quiz.md)
5. [共有 VPC と接続性](./governance/04-shared-vpc-and-connectivity.md) | [クイズ](./quizzes/governance/04-shared-vpc-and-connectivity-quiz.md)
6. [データとセキュリティの境界](./governance/05-data-security-boundaries.md) | [クイズ](./quizzes/governance/05-data-security-boundaries-quiz.md)
7. [意思決定フレームワークと PoC の設計](./governance/06-decision-framework-and-poc.md) | [クイズ](./quizzes/governance/06-decision-framework-and-poc-quiz.md)

### プラットフォームエンジニアリング
0. [プラットフォームエンジニアリング概要](./platform-engineering/00-platform-engineering-overview.md) | [クイズ](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [クイズ](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [クイズ](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [クイズ](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Kubernetes の拡張メカニズム](./platform-engineering/04-kubernetes-extensions.md) | [クイズ](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: ACK と KRO の統合例](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [クイズ](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [クイズ](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [クイズ](./quizzes/platform-engineering/08-vcluster-quiz.md)

### コンテナレジストリ
1. [コンテナレジストリ概要](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [クイズ](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [クイズ](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [クイズ](./quizzes/container-registry/03-harbor-quiz.md)
5. [コンテナレジストリのベストプラクティス](./container-registry/04-best-practices.md) | [クイズ](./quizzes/container-registry/04-best-practices-quiz.md)

### オブザーバビリティ
1. [オブザーバビリティ概要](./observability/README.md)
2. **メトリクス**
   - [メトリクス概要](./observability/metrics/README.md) | [クイズ](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [クイズ](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [クイズ](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [クイズ](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch メトリクス](./observability/metrics/04-cloudwatch-metrics.md) | [クイズ](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [クイズ](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **ロギング**
   - [ロギング概要](./observability/logging/README.md) | [クイズ](./quizzes/observability/logging/README-quiz.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [クイズ](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [クイズ](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [クイズ](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [クイズ](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [ログコレクター](./observability/logging/05-collectors.md) | [クイズ](./quizzes/observability/logging/05-collectors-quiz.md)
4. **トレーシング**
   - [トレーシング概要](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [クイズ](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [クイズ](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [クイズ](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [クイズ](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **アラート**
   - [アラート概要](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [クイズ](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [クイズ](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [クイズ](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [クイズ](./quizzes/observability/grafana/grafana-quiz.md)
7. [オブザーバビリティ最適化ガイド](./observability/09-observability-optimization.md) | [クイズ](./quizzes/observability/09-observability-optimization-quiz.md)

### 運用ガイド
1. [インフラストラクチャの構築](./ops/01-infrastructure-setup.md) | [クイズ](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [インフラストラクチャの応用](./ops/02-infrastructure-advanced.md) | [クイズ](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI パイプライン](./ops/03-ci-pipelines.md) | [クイズ](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps マルチクラスター](./ops/04-gitops-multi-cluster.md) | [クイズ](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps の自動化](./ops/05-gitops-automation.md) | [クイズ](./quizzes/ops/05-gitops-automation-quiz.md)
6. [スケーリング戦略](./ops/06-scaling-strategies.md) | [クイズ](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [オブザーバビリティのアラート](./ops/07-observability-alerts.md) | [クイズ](./quizzes/ops/07-observability-alerts-quiz.md)
8. [オブザーバビリティの分析](./ops/08-observability-analysis.md) | [クイズ](./quizzes/ops/08-observability-analysis-quiz.md)
9. [オブザーバビリティスタック](./ops/09-observability-stack.md) | [クイズ](./quizzes/ops/09-observability-stack-quiz.md)
10. [リソースの最適化](./ops/10-resource-optimization.md) | [クイズ](./quizzes/ops/10-resource-optimization-quiz.md)
11. [アップグレード運用](./ops/11-upgrade-operations.md) | [クイズ](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [イベント時のキャパシティプランニング Playbook](./ops/12-event-capacity-planning.md) | [クイズ](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [FinOps コスト可視化プラットフォーム](./ops/13-finops-cost-platform.md) | [クイズ](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [クイズ](./quizzes/ops/14-tekton-pipelines-quiz.md)
15. [ゾーナルクラスターの運用](./ops/15-zonal-operations-guide.md) | [クイズ](./quizzes/ops/15-zonal-operations-guide-quiz.md)
16. [トラブルシューティング Playbook](./ops/16-troubleshooting-playbook.md) | [クイズ](./quizzes/ops/16-troubleshooting-playbook-quiz.md)
17. [EKS Spot の本番環境実験と結果評価](./ops/17-spot-production-experiments.md) | [クイズ](./quizzes/ops/17-spot-production-experiments-quiz.md)

## ラボガイド

理論を学んだ後に実環境で練習できるハンズオンラボガイドを提供しています。

- [ラボガイド一覧](./labs/README.md)
- Basics: Linux の基礎、Linux 運用、コンテナのラボ
- Core: Pod、Service、ストレージ、ConfigMap のラボ
- EKS: クラスター作成のラボ

### オブザーバビリティのエンドツーエンドラボ
1. [ラボシリーズ入門](./labs/observability/README.md)
2. [Part 1: インフラストラクチャの構築](./labs/observability/01-infrastructure-setup-lab.md) | [クイズ](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [Part 2: オブザーバビリティスタック](./labs/observability/02-observability-stack-lab.md) | [クイズ](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [Part 3: MSA のデプロイとカナリア](./labs/observability/03-msa-deployment-lab.md) | [クイズ](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [Part 4: 負荷テストとオートスケーリング](./labs/observability/04-load-testing-scaling-lab.md) | [クイズ](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [Part 5: アラートと AIOps](./labs/observability/05-alerting-aiops-lab.md) | [クイズ](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [Part 6: 分散トレーシングの分析](./labs/observability/06-distributed-tracing-lab.md) | [クイズ](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## 学習ガイド

### 初心者向けの学習パス
1. 次の順序で学習してください: **Linux とコンテナ** -> **Kubernetes のコア概念** -> **Amazon EKS**
2. 各章を読み終えたら、対応するクイズを解いて理解度を確認する
3. 練習環境でコマンドやサンプルコードを実際に実行してみる

### 上級者向けの学習パス
1. 次の順序で学習してください: **Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **セキュリティとポリシー**
2. **Cilium** セクションでネットワーキングを深く掘り下げる
3. 特定のツールや技術に絞って集中的に学習する

### クイズの活用方法
- 各ドキュメントの末尾にあるクイズリンクをクリックして学習内容を確認する
- トグル形式の解答は、開く前にまず自分で考える
- 間違えた問題については、対応するドキュメントを復習する

## コントリビューション

このプロジェクトに貢献したい場合:
1. 誤字や内容の誤りを見つけたら Issue を登録してください
2. 新しいトピックや改善点を提案してください
3. クイズ問題の追加や改善を提案してください

## ライセンス

このトレーニング教材は学習目的で自由に利用できます。
