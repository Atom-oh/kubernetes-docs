# VPC Lattice 詳細ガイドの概要

> **対象範囲**: VPC Lattice のサービス/リソース API と AWS Gateway API Controller。選択したリリースとインストール済み CRD を確認してください。
> **最終更新日**: 2026年10月12日

## このセクションの内容

- サイドカープロキシ型のサービスメッシュ (App Mesh、Istio) から**マネージドデータプレーン** (VPC Lattice) に移行すると、実際に何が変わるか
- ドキュメントに記載された Lattice のアドレス指定、SigV4 署名、適用可能な認証ポリシーがリクエスト経路をどう変えるか
- SPIFFE/SPIRE から IAM にワークロード ID を移行するときに直面する構造上の違いと、それがレビュー委員会の議題になる理由

## このセクションを独立させている理由

このセクションでは**概念の理解**を扱います。Lattice リソースの作成方法と AWS Gateway API Controller のインストール方法は、[VPC Lattice](../../networking/02-vpc-lattice.md) で既に説明しています。Istio との機能ごとの比較は、[Istio と VPC Lattice](../istio/comparison/02-istio-vs-lattice.md) にあります。これら 2 つのドキュメントで扱っていない内容が、このセクションの対象です。すなわち、「**なぜこのように設計されたのか」と「その設計から何が生じるのか**」です。

急いで対応すべき背景があります。**AWS App Mesh のサポートは 2026年9月30日に終了**し、App Mesh コンソールと App Mesh リソースにはアクセスできなくなりました。新規顧客のオンボーディングは 2024年9月24日から停止されていました。App Mesh を使用していた組織にとって、この移行はもはや任意ではなく、期限も過ぎています。

しかし、App Mesh と Lattice は**同じものの 2 つの実装ではありません。** データプレーンが置かれる場所 (Pod 内か AWS インフラストラクチャ内か)、ID を証明する粒度 (接続単位かリクエスト単位か)、信頼の起点を所有する主体 (顧客 CA か AWS IAM/STS か) が異なります。リソース名を一つずつ置き換える方法で移行すると、機能上の不足やセキュリティレビューの不合格に移行の終盤で気付くことになります。このセクションの目的は、そうした不足を**先に明らかにすること**です。

## 対象読者と前提条件

- AWS アーキテクトと顧客側のインフラストラクチャエンジニア
- EKS と Kubernetes の知識があることを前提とします
- VPC Lattice とサービスメッシュの内部動作は初めて学ぶことを前提とします
- コードやマニフェストの例は最小限です。ハンズオンラボのガイドではありません

## ドキュメント構成

| # | ドキュメント | 解説する内容 |
|---|----------|---------------------|
| 1 | [App Mesh と VPC Lattice のアーキテクチャ](./01-appmesh-vs-lattice.md) | データプレーンが Pod からインフラストラクチャに移ると、何が残り、何がなくなるのか |
| 2 | [レイテンシへの影響分析](./02-latency.md) | レイテンシを悪化させる要因と改善させる要因の両方があります。自分たちの環境ではどちらが勝るのか |
| 3 | [IAM 認証フローの詳細](./03-auth-flow.md) | リクエストの署名から認可までの 4 段階で何が起きるのか |
| 4 | [基礎: リンクローカルと SNI](./04-networking-basics.md) | サイドカーなしでトラフィックをどのようにインターセプトするのか。TLS を終端しないことで何が失われるのか |
| 5 | [ワークロード ID の移行: SPIFFE から IAM へ](./05-spiffe-to-iam.md) | IAM で SPIRE の機能を実現できるか。置き換えられないものは何か |
| 6 | [制約と意思決定のポイント](./06-constraints.md) | どのような機能、信頼、コスト、復旧の選択肢を確定する必要があるか |
| 7 | [カーネルデータパス](./07-kernel-datapath.md) | Pod のルーティング、プロキシルール、接続追跡が経路にどう影響するか |

1 から順に読むことを推奨します。ドキュメント 4 (リンクローカル、SNI) は 3 と 6 の制約を理解する前提知識です。後の方に配置されていますが、ネットワークの基礎が不明な場合は最初に 4 を読んでください。

## 正確性に関する注意

このセクションの事実に関する記述は、AWS の公式ドキュメント、AWS Gateway API Controller のドキュメント、`aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice` のリファレンス実装、SPIFFE/SPIRE のドキュメントに基づいています。

公式ドキュメントで確認できない内容は事実として記述せず、`Needs verification` ブロックで示します。Lattice には機能が追加され続けており、特に**クォータと料金はリージョンや時期によって異なります。** 設計を確定する前に、Service Quotas コンソールと [VPC Lattice の料金ページ](https://aws.amazon.com/vpc/lattice/pricing/)で最新の値を直接確認してください。

## 関連ドキュメント

- [VPC Lattice](../../networking/02-vpc-lattice.md): Lattice リソースの設定と Gateway API Controller のインストール
- [Gateway API](../../networking/04-gateway-api.md): Kubernetes Gateway API 標準
- [Istio と VPC Lattice](../istio/comparison/02-istio-vs-lattice.md): 機能、コスト、運用の複雑さの比較
- [Istio セキュリティ: mTLS](../istio/security/01-mtls.md): サイドカー型の相互認証の仕組み
- [Pod ネットワークのベンチマーク](../../networking/06-pod-network-benchmark.md): 実測した同一 AZ と AZ 間のレイテンシ基準値
