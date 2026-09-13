# VPC Lattice

Amazon VPC LatticeはVPCやAWSアカウントをまたいでアプリケーションを接続します。この章ではリソースモデル、EKSとの統合、ルーティング、IAM認可、監視、トラブルシューティングを説明します。

> **最終更新**: September 11, 2026。AWS Gateway API Controller **v2.1.3**とGateway API **v1.5.0**に照らして確認しました。例は設定と検証の手順を示しており、このレビューの一環としてAWSアカウントにデプロイしてはいません。

## 目次

- [概要](#overview)
- [アーキテクチャ](#architecture)
- [EKSとVPC Latticeの統合](#eks-and-vpc-lattice-integration)
- [インストールと設定](#installation-and-configuration)
- [サービス管理](#service-management)
- [ルーティングとトラフィック管理](#routing-and-traffic-management)
- [セキュリティと認証](#security-and-authentication)
- [監視とログ記録](#monitoring-and-logging)
- [ベストプラクティス](#best-practices)
- [トラブルシューティング](#troubleshooting)
- [参考資料](#references)

## 概要 {#overview}

### VPC Latticeとは

VPC Latticeは、各アプリケーションの隣にプロキシを配置せずにアプリケーションネットワーキングを提供します。**サービスネットワーク**はサービスとリソース設定をまとめ、許可された利用者に接続します。サービスはリスナー、ルーティングルール、ターゲットグループ、サービスDNS名を提供します。

現在の製品はリソースゲートウェイを通じて**リソース設定**も接続し、TCPを使用するRDSデータベースなどのリソースを扱います。このリソースアクセスモデルは、ターゲットグループをバックエンドとするHTTPサービスとは異なります。サービスネットワーク/サービスのIAM認証ポリシーは、リソース設定のトラフィックを認可しません。PrivateLinkを利用する**サービスネットワークVPCエンドポイント**は、ピアリング、Transit Gateway、Direct Connect、VPN経由のクライアントにアクセスを提供できます。VPCの直接関連付けだけでは、Transit Gatewayやピアリング接続の背後にあるクライアントへアクセスを拡張できません。

代表的な用途には、アカウント間のアプリケーションAPI、EKSと他のコンピュートサービス間の通信、共有データリソースへのアクセスがあります。関連付け、ルーティング、セキュリティグループ、認証、アプリケーション認可の設定は引き続き必要です。

### 他のサービスとの比較

| サービス | 主な責務 | 重要な違い |
|---|---|---|
| VPC Lattice | プライベートなアプリケーションとリソースの接続 | HTTP/HTTPS/gRPCのサービスルーティングと、別個のTLS/TCPリソース機能。インターネット向けAPIの入口ではない |
| API Gateway | マネージドAPIエンドポイントとAPI管理 | REST、HTTP、WebSocket APIは機能が異なる。GraphQLは独立したAPI GatewayのAPIタイプではない |
| AWS App Mesh | Envoyベースのサービスメッシュ | AWSは**2026-09-30**にサポートを終了する。このレビュー時点では将来の日付。新規インストールではなく移行を計画する |
| Transit Gateway | IPルーティングによるネットワーク接続 | ネットワークを接続する。サービスごとのHTTPルーティングと認可を代替しない |
| Istio / Linkerd / Cilium | それぞれのデータプレーンで実装されるメッシュ機能 | 機能と運用コストは異なる。すべてのメッシュ構成でサイドカーが必須ではない |

VPC Latticeではマネージドデータプレーンを運用する必要がなくなりますが、総コストの低下や同一のメッシュ機能は保証されません。実際のワークロードについて、リクエスト/データ/リソース料金、コントローラー運用、ID要件、再試行、ルーティング機能、可観測性を比較してください。[IstioとLatticeの比較](../service-mesh/istio/comparison/02-istio-vs-lattice.md)を参照してください。

## アーキテクチャ {#architecture}

### コンポーネントとトラフィックフロー

| コンポーネント | 責務 |
|---|---|
| サービスネットワーク | 論理的なグループ化と関連付け。オプションのIAM認可境界 |
| サービス | 独自のDNS名を持つアプリケーションエンドポイント |
| リスナーとルール | **サービス**に属し、アクションとターゲットグループを選択 |
| ターゲットグループ | 登録されたインスタンス、IP、Lambda、ALBターゲット。動作はターゲットタイプによる |
| VPC関連付け | セキュリティ制御に従い、関連付けられたVPC内のクライアントにネットワークへのアクセスを許可 |
| サービスネットワークVPCエンドポイント | サポートされる中継/オンプレミス経路を含むPrivateLinkベースのアクセス |
| リソース設定 / リソースゲートウェイ | TCP/データベースリソースを含む別個のリソースアクセスモデル |

![2つのAWSアカウントにある3つのVPCがサービスネットワークに関連付けられ、そのサービスはEC2、EKS、Lambdaワークロード用のターゲットグループを使用する。](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

図は論理的な関連付けを示しており、単一のルータープロセスを示すものではありません。アクセスはネットワーク到達性と適用ポリシーにも依存します。リクエストは**サービスの**DNS名を解決し、リスナーに到達して該当する認可チェックを通過し、リスナールールに従ってターゲットへルーティングされます。ターゲットグループは宛先を記述するものであり、追加のアプリケーションホップではありません。

実際のドメインは`get-service --query dnsEntry`またはコントローラーのルートアノテーションで確認してください。サービス名とサービスネットワークIDから組み立てないでください。割り当てられた名前にはサービス固有の識別子が含まれ、サービスを再作成すると変わる場合があります。

### セキュリティモデル

ネットワークアクセス、IAM認可、暗号化は別々の制御です。`AWS_IAM`にはサポートされる署名付きリクエストと適切なポリシーが必要です。`NONE`はそのレイヤーのIAM認証を無効にしますが、別レイヤーのIAMポリシー、セキュリティグループ、アプリケーション認可を迂回するものではありません。HTTPSはクライアントからLatticeへの通信を保護します。バックエンドTLSを明示的に設定しない限り、バックエンドHTTPは平文のままです。

## EKSとVPC Latticeの統合 {#eks-and-vpc-lattice-integration}

AWS Gateway API ControllerはKubernetesリソースをVPC Latticeリソースに調整します。

| Kubernetesリソース | Latticeでの解釈 |
|---|---|
| GatewayClass | `application-networking.k8s.aws/gateway-api-controller`を選択 |
| Gateway | 名前空間を除いた**Gateway名**でサービスネットワークを参照 |
| HTTPRoute / GRPCRoute | 独自のドメインとリスナー/ルーティング設定を持つサービスを作成 |
| バックエンドServiceとそのエンドポイント | ターゲットグループと登録するPodエンドポイントを定義 |
| TargetGroupPolicy | ターゲットグループのプロトコルとヘルスチェックを設定 |
| IAMAuthPolicy | GatewayのネットワークまたはRouteのサービスに認証ポリシーを添付 |
| AccessLogPolicy | 対象リソースのアクセスログ送信先を設定 |

同名の2つのGatewayは、Kubernetes名前空間が異なっても同じサービスネットワークを参照できます。Gateway単体ではネットワークも共有の単一Ingress IPも作成**しません**。ネットワークは外部管理、単純な場合にはコントローラーの`defaultServiceNetwork`オプション、またはコントローラーのServiceNetwork CRDで管理できます。クラウドリソースごとに所有者を1つ選択してください。

以下の例は外部管理のネットワークとVPC関連付けを使用します。`defaultServiceNetwork`は未設定のままで、その関連付けにVpcAssociationPolicyを添付しません。CRDベースのモデルを採用する場合、ネットワーク、VPC関連付け、認可を別々のリソースとして管理し、同じリソースをCloudFormationでも管理しないでください。

## インストールと設定 {#installation-and-configuration}

### 前提条件

コントローラーのv2.1アップグレードガイドは**Kubernetes 1.31以降**とGateway API **1.5以降**を要求します。この例はv2.1のビルドに使用された**1.5.0**に固定します。この最小要件はEKSのサポートマトリックスでも、すべての新しいGateway APIリリースとの互換性の証明でもありません。変更前にEKSのバージョンライフサイクルと、Gateway API CRDを共有する全コントローラーを確認してください。特にv2.0コントローラーは、Gateway API 1.5で導入されたTLSRouteのストレージ/API移行後に失敗する可能性があります。

サポート対象のEKSクラスター、対応する`kubectl`、Helm、AWS CLI v2、および意図したリソースの設定権限を持つ運用者ロールを使用してください。サンプルのバックエンドは、VPC Latticeから到達可能なIPを持つLinux Podを前提とします。クラスターのCNI、サブネット容量、エンドポイントの準備状態、DNS、ネットワークポリシー設定を確認します。

```bash
export AWS_REGION=us-west-2
export CLUSTER_NAME=my-cluster
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export VPC_ID="$(aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
export NETWORK_NAME=my-network
export ASSOCIATION_SG_ID=sg-0123456789abcdef0
kubectl config current-context
kubectl version
```

例のセキュリティグループIDを置き換えてください。VPC関連付けのセキュリティグループは、TCP 443で**承認されたクライアント**を許可する必要があります。バックエンドのPod/ノードのセキュリティグループは、実際のバックエンド/ヘルスポート（ここではTCP 8080）で該当するLatticeのマネージドプレフィックスリストを許可する必要があります。全ノードがEKSクラスターのセキュリティグループを使用すると想定せず、実際のPod ENIまたはノードENIに付いたグループを調べてください。EKSコントロールプレーンからコントローラーのWebhookの必要ポートへの到達も許可します。全ポートをインターネット全体に開放しないでください。

### IAMロールの設定

**コントローラーロール**はクラウドリソースを管理します。**呼び出し元ロール**はアプリケーションリクエストに署名し、`vpc-lattice-svcs:Invoke`を必要とします。この2つは別のロールです。

対応ノードではEKS Pod Identity、またはIRSAを使用します。以下のIRSA例はクラスターのIAM OIDCプロバイダーがすでに存在することを前提に、専用サービスアカウントを作成します。Pod Identityでは、現在のEKSアドオンと、この同じ名前空間/サービスアカウントへの関連付け、および適切な信頼ポリシーを使用してください。同じ例でIRSAアノテーションにも依存させないでください。

リリース推奨のコントローラーポリシーには、広範な`vpc-lattice:*`とログ記録/タグ付け権限が含まれます。上流の出発点として扱い、**最小権限ポリシーとは見なさないでください**。リソース範囲と有効な機能を見直し、サービスリンクロールの制約条件を保持し、レビューしたポリシーを保存してから作成します。後の実行でポリシーを重複作成せず、レビュー済みの既存ポリシーARNを再利用してください。

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

既存サービスアカウントには、意図的な所有権/ロール移行が必要です。この例は自動で上書きしません。

### リリース済みコントローラーのインストール

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

既存Helmリリースでは、保存したvaluesを使い、レビュー済みの`helm upgrade`計画に従います。Helmは`crds/`内のCRDを自動アップグレードしません。変更を別途確認してください。アップグレードを通すために、共有Gateway API CRDやアドミッションポリシーを削除しないでください。

マニフェストで配信する場合、同じvaluesとサービスアカウントの選択を使い、`helm template --include-crds`で**同じチャート**をレンダリングし、結果のマニフェストを確認して適用します。これにより、リリースのRBAC、EndpointSlice監視、リーダー選出権限、Webhook設定が保持されます。古い手書きのv1.0デプロイを使用しないでください。証明書を明示的に提供するかcert-managerオプションで管理しない限り、チャートがWebhook証明書を生成します。アップグレード中は片方だけを再生成せず、Webhook SecretとCAバンドルの整合性を保ってください。

### サービスネットワークの作成

同じネットワークには**CLIかCloudFormation**のどちらかを選び、両方を使わないでください。CLI例は`AWS_IAM`ネットワークを作成します。該当するAllowポリシーが設定され伝播するまでは、リクエストは拒否されます。

以下を`api-auth-policy.json`として保存し、アカウントと呼び出し元ロールを置き換えてください。ネットワークポリシーは意図的に、このデモの`/api`エンドポイントとサブパスだけを許可します。本番ネットワークには、意図したサービスと呼び出し元を対象にしたレビュー済みポリシーが必要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

```bash
aws vpc-lattice create-service-network --name "$NETWORK_NAME" \
  --auth-type AWS_IAM > service-network.json
export SERVICE_NETWORK_ID="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["id"])')"
export SERVICE_NETWORK_ARN="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["arn"])')"

aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ID" \
  --vpc-identifier "$VPC_ID" --security-group-ids "$ASSOCIATION_SG_ID"

# Save the reviewed policy below as api-auth-policy.json, then compact it.
python3 -c 'import json; print(json.dumps(json.load(open("api-auth-policy.json")),separators=(",",":")))' \
  > api-auth-policy.compact.json
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_NETWORK_ID" \
  --policy file://api-auth-policy.compact.json
aws vpc-lattice get-service-network --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
```

ルートを公開する前に、関連付けが`ACTIVE`、ネットワークが引き続き`authType: AWS_IAM`であり、`get-auth-policy`が意図したポリシーを返すことを確認します。ポリシー伝播には数分かかる場合があります。

同等の**ネットワークと関連付け**のCloudFormationテンプレートは次のとおりです。

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: VPC Lattice service network and client VPC association
Parameters:
  NetworkName:
    Type: String
    Default: my-network
    MinLength: 3
    MaxLength: 63
    AllowedPattern: '^[a-z0-9]+(-[a-z0-9]+)*$'
    Description: Must match the Kubernetes Gateway name
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC containing the intended clients
  AssociationSecurityGroupIds:
    Type: List<AWS::EC2::SecurityGroup::Id>
    Description: Existing security groups allowing approved clients on listener ports
Resources:
  ServiceNetwork:
    Type: AWS::VpcLattice::ServiceNetwork
    Properties:
      Name: {Ref: NetworkName}
      AuthType: AWS_IAM
  ClientAssociation:
    Type: AWS::VpcLattice::ServiceNetworkVpcAssociation
    Properties:
      ServiceNetworkIdentifier: {Ref: ServiceNetwork}
      VpcIdentifier: {Ref: VpcId}
      SecurityGroupIds: {Ref: AssociationSecurityGroupIds}
Outputs:
  ServiceNetworkArn:
    Description: ARN used for authorization and sharing
    Value: {Fn::GetAtt: [ServiceNetwork, Arn]}
  ServiceNetworkId:
    Description: ID used with VPC Lattice API operations
    Value: {Fn::GetAtt: [ServiceNetwork, Id]}
```

このテンプレートは認証ポリシーを添付しません。同じ所有権モデルで認証ポリシーリソースを追加するか、リクエストをテストする前にレビュー済みネットワークポリシーを明示的に適用してください。ネットワークID/ARNはスタック出力から取得します。デプロイ前にテンプレートを検証して変更セットを確認してください。この例はVPCやそのセキュリティグループを作成しません。

### Gatewayとアプリケーション

次を`gateway.yaml`として保存し、適用してください。Gateway名は上で作成した`my-network`と一致する必要があります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lattice-demo
---
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
```

`certificateRefs: [{name: unused}]`はこのコントローラーの文書化された設定に従っています。Gateway APIのTLS設定を満たしますが、このコントローラーはそこでKubernetes TLS Secretを読みません。カスタムホスト名がなければ、Latticeが生成ドメインの証明書を提供します。これは**コントローラー固有**であり、移植可能な証明書管理の手順ではありません。

以下を`stable.yaml`として保存します。NGINXが実際に8080で待ち受け、`/health`を提供するように設定します。`containerPort`の宣言だけでは、どちらも実現しません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-stable
  namespace: lattice-demo
data:
  nginx.conf: |
    worker_processes 1;
    pid /tmp/nginx.pid;
    error_log stderr notice;
    events { worker_connections 1024; }
    http {
        access_log /dev/stdout;
        default_type application/json;
        client_body_temp_path /tmp/client_temp;
        proxy_temp_path /tmp/proxy_temp;
        fastcgi_temp_path /tmp/fastcgi_temp;
        uwsgi_temp_path /tmp/uwsgi_temp;
        scgi_temp_path /tmp/scgi_temp;
        server {
            listen 8080;
            location = /health { return 200 '{"status":"ok"}\n'; }
            location = /api { return 200 '{"version":"stable"}\n'; }
            location /api/ { return 200 '{"version":"stable"}\n'; }
            location / { return 404 '{"error":"not found"}\n'; }
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  replicas: 2
  selector:
    matchLabels: &id001
      app: lattice-demo
      version: stable
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: nginx:1.30.4-alpine@sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c
        command:
        - nginx
        args:
        - -c
        - /etc/lattice/nginx.conf
        - -g
        - daemon off;
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 250m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /etc/lattice
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: service-stable
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  selector:
    app: lattice-demo
    version: stable
  ports:
  - name: http
    port: 8080
    targetPort: http
```

同じ3オブジェクトから`canary.yaml`を作成し、すべての`service-stable`名を`service-canary`に、セレクター/テンプレート両方の`version: stable`ラベルを`version: canary`に、JSON応答値`"stable"`を`"canary"`に変更します。`app: lattice-demo`、ポート、ヘルスエンドポイントは変更しません。両ファイルを`lattice-demo`に適用します。固定したイメージにはLinux AMD64とARM64のバリアントがあります。リソースリクエストとレプリカ数はデモ設定であり、測定された本番サイズではありません。

以下の`TargetGroupPolicy`を保存して適用し、`service-canary`を対象とする同等の`canary-health`ポリシーも作成します。

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

CRDでは`intervalSeconds`、`timeoutSeconds`、`statusMatch`を使用します。AWS CLIでは、後述の別のフィールド名を使用します。プロトコル/バージョンの変更でターゲットグループが置き換わる場合があります。ポリシーを削除すると、デフォルトのHTTP/HTTP1動作を含めて設定が元に戻ります。

## サービス管理 {#service-management}

### HTTPRouteによるサービスの作成

これを`api-route.yaml`として保存し、下のIAMAuthPolicyも`api-iam.yaml`として保存します。アプリケーションとヘルスポリシーを適用してから、ルートと認証ポリシーを適用します。調整によってルートのサービスが作成され保護される間、ネットワークレベルの`AWS_IAM`ポリシーを有効に保ってください。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: api-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

`spec.policy`はJSONの**文字列**です。このCRDは対象サービスで`AWS_IAM`を有効にします。auth-typeアノテーションや、ポリシーを含むConfigMapでは代替できません。`Gateway`を対象とするポリシーはネットワークのポリシーを管理するため、この例の外部管理のネットワークポリシーと競合させてはいけません。

`Accepted` / `ResolvedRefs`とポリシーステータス、関連するAWSリソース状態、バックエンドの準備状態を確認してください。`kubectl apply`の成功は、クラウドの調整やログ配信の成功の証明ではありません。

```bash
kubectl -n lattice-demo get gateway my-network -o yaml
kubectl -n lattice-demo get httproute api -o yaml
kubectl -n lattice-demo get iamauthpolicy api-caller -o yaml
kubectl -n lattice-demo get endpointslices \
  -l kubernetes.io/service-name=service-stable
kubectl -n lattice-demo rollout status deployment/service-stable --timeout=120s
kubectl -n lattice-demo rollout status deployment/service-canary --timeout=120s

export SERVICE_DNS="$(kubectl -n lattice-demo get httproute api \
  -o jsonpath='{.metadata.annotations.application-networking\.k8s\.aws/lattice-assigned-domain-name}')"
test -n "$SERVICE_DNS"
# A caller inside the associated VPC, with MyAppRole credentials, runs:
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

最後のコマンドを実行する前に、次のセクションの署名付きクライアントを設定します。許可されたネットワーク上の場所から、**呼び出し元ロール**の認証情報で実行してください。ワークステーションにはAWS認証情報に加えて適切なネットワーク経路が必要です。

### 署名付きHTTPSクライアント

これを`lattice_get.py`として保存します。デフォルトのAWS認証情報プロバイダーチェーンを使用し、リクエストごとに認証情報を固定して **`vpc-lattice-svcs`** 用に署名し、VPC Latticeが要求する **`UNSIGNED-PAYLOAD`** を設定します。TLSを検証し、古い署名でリダイレクトを追跡せず、自動再試行もしません。

```python
import argparse
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError
from botocore.session import Session


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_request(url: str, region: str, credentials) -> Request:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.fragment):
        raise ValueError("Use an HTTPS URL without user info or a fragment")
    request = AWSRequest(method="GET", url=url, headers={
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    })
    request.context["payload_signing_enabled"] = False
    SigV4Auth(credentials, "vpc-lattice-svcs", region).add_auth(request)
    return Request(url, method="GET", headers=dict(request.headers.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        provider = Session().get_credentials()
        if provider is None:
            raise ValueError("No AWS credentials available")
        request = signed_request(args.url, args.region, provider.get_frozen_credentials())
        opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(request, timeout=10) as response:
            print(response.status)
            print(response.read(1048576).decode("utf-8", errors="replace"))
        return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code}; check the policy and access logs", file=sys.stderr)
    except (URLError, BotoCoreError, ValueError) as exc:
        print(f"Request failed: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3.12 -m venv lattice-client
lattice-client/bin/python -m pip install 'botocore==1.43.93'
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

GET専用のこの例はPython 3.12とbotocore 1.43.93で確認しました。ワークロードは設定済みのPod IdentityまたはIRSA認証情報を使用してください。静的な認証情報や署名済みヘッダーを、マニフェスト、ログ、サポートチケットにコピーしないでください。VPC LatticeはSigV4Aもサポートしますが、この例はリージョンのSigV4を使用します。

### AWS APIによる直接管理

以下は独立して管理するリソース向けの**代替手段**です。8080でHTTPと`/health`を提供する、到達可能で安定したバックエンドIPを使用します。一時的なPod IPには、置き換えを追跡するコントローラーが必要です。HTTPRouteが所有するサービスを手動変更して、その変更をコントローラーが保持すると期待しないでください。

```bash
# Separate API-managed example; do not use for controller-managed resources.
export TARGET_IP=10.0.1.25
export TARGET_GROUP_ID="$(aws vpc-lattice create-target-group \
  --name api-manual --type IP \
  --config "{\"port\":8080,\"protocol\":\"HTTP\",\"protocolVersion\":\"HTTP1\",\"vpcIdentifier\":\"${VPC_ID}\"}" \
  --query id --output text)"
aws vpc-lattice register-targets --target-group-identifier "$TARGET_GROUP_ID" \
  --targets "id=$TARGET_IP,port=8080"
export SERVICE_ID="$(aws vpc-lattice create-service \
  --name api-manual --auth-type AWS_IAM --query id --output text)"
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_ID" \
  --policy file://api-auth-policy.compact.json
export LISTENER_ID="$(aws vpc-lattice create-listener \
  --service-identifier "$SERVICE_ID" --name https --protocol HTTPS --port 443 \
  --default-action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TARGET_GROUP_ID}\",\"weight\":1}]}}" \
  --query id --output text)"
aws vpc-lattice create-service-network-service-association \
  --service-identifier "$SERVICE_ID" --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID" --query dnsEntry
```

検出したHTTPSドメインを呼び出す前に、ターゲットが正常になり、関連付けが有効になるまで待ちます。この例はカスタムドメインではなく、生成されたドメイン用のAWS管理証明書を使用します。

### サービスの更新と削除

Kubernetes所有のリソースでは、Route、バックエンドワークロード、ポリシーマニフェストを変更し、調整を確認します。API所有のリソースでは、対応する更新APIを使って結果の状態を確認します。アカウント内の最初のサービスを選ぶのではなく、応答からリソースIDを記録してください。

削除前に、すべての利用者、ネットワーク関連付け、リスナー/ルール、ターゲットグループ参照、所有権を特定します。依存関係に従い、依存する側から特定のルート/サービスの関連付けとサービスリソースを削除し、その後に未使用のターゲットグループを削除します。共有Gateway/ネットワークは他の名前空間やアカウントに影響する可能性があります。finalizerとクラウドのクリーンアップが完了するまでコントローラーを保持し、一括削除しないでください。

**IAMAuthPolicyを削除すると、ポリシーを切り離す前に対象のIAM認証が無効化されます（`NONE`）。** アクセス拒否や認可の安全なロールバックの手段ではありません。サービスを削除する間は制限的なポリシーを保持し、残るネットワーク/サービスの制御を確認してください。

## ルーティングとトラフィック管理 {#routing-and-traffic-management}

### パスとヘッダーの一致

上記ルートは`/api`とそのパス配下に一致します。ヘッダーに基づく明示的なカナリアルールを追加するには、**同じ**HTTPRouteを次の内容で置き換えます。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: x-version
        value: canary
    backendRefs:
    - name: service-canary
      port: 8080
      weight: 1
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

コントローラーの文書では、パス一致は大文字小文字を区別せず、ルールごとにメソッド一致1つ、ヘッダー一致は最大5つで、クエリパラメーター一致はありません。すべてのGateway APIフィルターや一致条件が実装されていると想定しないでください。別のHTTPRouteは別のLatticeサービス/ドメインを作成し、最初のサービスにルールを自動追加するわけではありません。

### 重み付きルーティング

`backendRefs.weight: 90`と`10`はGateway APIネイティブの設定で、重み付きルーティングのアノテーションは不要です。相対的な分配を表し、10リクエストでの正確な結果ではありません。カナリアの重みを増やす前に、適切なサンプル数で両バージョンのエンドポイント、健全性、エラー、レイテンシーを確認します。

独立管理のAWSリソースでは次のようにします。

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

CLIのプレフィックス一致は文字列上の前方一致です。境界動作はKubernetesの`PathPrefix`の意味と分けて確認してください。ルーティングの一致条件は認可境界ではありません。パスルーティングのテストを、IAMポリシーが正規化やエンコードされたすべてのパスの変種をカバーする証明として使わないでください。

### ヘルスチェック

Kubernetes例は`TargetGroupPolicy`を使用します。同等のAPI更新は次のとおりです。

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

ヘルスチェックはしきい値に従って準備状態を評価します。可用性や無停止を保証するものではありません。HTTP1ターゲットグループではデフォルトで有効ですが、HTTP2では明示的な検討が必要です。gRPCターゲットはHTTP1/HTTP2ヘルスチェックを使用し、Lambda/ALBターゲットタイプでは動作が異なります。Podの例を全ターゲットに適用せず、現在のターゲットタイプの文書を確認してください。

## セキュリティと認証 {#security-and-authentication}

### 認証ポリシーと呼び出し元権限

`put-auth-policy` / `get-auth-policy`は呼び出しの認可を管理します。`put-resource-policy`は別の管理/共有APIです。呼び出し元には **`vpc-lattice-svcs:Invoke`** アクションを使用します。

ネットワークとサービスの両方が`AWS_IAM`を使用する場合、呼び出し元のIDポリシーと、該当する**両方の**認証ポリシーでアクセスを許可する必要があります。明示的Denyが優先されます。一方のリソースの`NONE`は他方のIAM要件を取り消しません。KubernetesのClusterIP/Pod IPへの直接通信はLattice認証を迂回するため、適切なネットワークとアプリケーションの制御で保護してください。

`StringEquals`は`/api/*`をワイルドカードとして解釈しません。例は`StringLike`を使用し、`/api/*`に加えて`/api`も含みます。IAM条件の一致やアプリケーションのパス正規化は、コントローラーのルーティングと異なる場合があります。管理機能には、管理者ロールに制限した専用サービスを優先し、アプリケーション認可を保持してください。広範な一般Allowを追加して、パスのワイルドカードがすべての別名を保護すると考えないでください。

### クロスアカウントアクセス

RAM共有は共有エンティティとの関連付けを許可しますが、それ自体でアプリケーション呼び出しを許可しません。ネットワーク/サービスの認証ポリシー、呼び出し元権限、関連付けのセキュリティグループ、ネットワーク経路でもリクエストを許可する必要があります。

```bash
# Owner account: choose a verified account ID or the actual Organizations ARN.
export CONSUMER_ACCOUNT_ID=111122223333
aws ram create-resource-share --name lattice-network-share \
  --resource-arns "$SERVICE_NETWORK_ARN" --principals "$CONSUMER_ACCOUNT_ID"

# Consumer account: inspect invitations only when the sharing mode requires one.
aws ram get-resource-share-invitations
# After verifying the owner, resources, and intended permissions:
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "$VERIFIED_INVITATION_ARN"

# Run with consumer credentials and that account's VPC/security group values.
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ARN" \
  --vpc-identifier "$CONSUMER_VPC_ID" \
  --security-group-ids "$CONSUMER_ASSOCIATION_SG_ID"
```

Organizations共有が有効な場合、組織内の利用者は招待なしでアクセスを受け取ります。その他のサポート対象の共有方法では、招待の承認が必要です。組織やOUと共有するには、メンバーアカウントIDから組み立てず、管理アカウント識別子を含む**Organizationsから取得した実際のARN**を使用します。

所有者はサービス、ネットワーク、リソース設定を共有できますが、個々のIAMロールをRAMの利用者にはできません。共有の停止は新規関連付けを防ぎますが、**既存の関連付けを削除しません**。アクセス取り消し時には明示的に見直してください。

### TLSとカスタムドメイン

サンプルGatewayはHTTPSのみを公開します。カスタムホスト名を使うには、そのホスト名でサービスを作成し、一致するACM証明書を取得して、実際に割り当てられたドメインにDNSを設定します。サービスごとにカスタムドメインは1つだけサポートされ、作成後は変更できません。

コントローラーでは、HTTPRouteの`spec.hostnames`とGatewayリスナーの`tls.options["application-networking.k8s.aws/certificate-arn"]`を設定するか、文書化されたACM検出を使用します。秘密鍵をアノテーションに入れないでください。ExternalDNSの自動化には、さらにそのコントローラー、権限、DNSEndpoint CRDが必要です。ホスト名の設定だけではDNSレコードの存在は証明されません。

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

クライアント向けHTTPSとバックエンドTLSは別です。`protocol: HTTPS`を設定したバックエンドの`TargetGroupPolicy`には、実際にTLSで通信するバックエンドと互換性のあるHTTPSヘルスチェックも必要です。VPC Latticeは**バックエンド証明書を検証しません**。接続を暗号化しますが、バックエンドの証明書によるIDを認証しません。意図する設計がそうであれば、別のTLSRoute/TLSパススルーモデルを使用し、機能制限を確認してください。

## 監視とログ記録 {#monitoring-and-logging}

### CloudWatchメトリクス、ダッシュボード、アラーム

サービスメトリクスは **`AWS/VpcLattice`** 名前空間を使用します。

| メトリクス | 意味 / 統計 |
|---|---|
| `TotalRequestCount` | リクエスト数。`Sum` |
| `HTTPCode_4XX_Count` | 4xx応答。`Sum` |
| `HTTPCode_5XX_Count` | 5xx応答。`Sum` |
| `RequestTime` | リクエスト所要時間、単位は**ミリ秒**。平均または適切なパーセンタイル |

サービスメトリクスは`Service`ディメンションと、必要に応じて`AvailabilityZone`を使用します。ターゲットグループメトリクスは`TargetGroup`を使用します。`ServiceName=my-service`のような名前では識別できません。実際のディメンション値/組み合わせを確認します。

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

トラフィックによりメトリクスが生成された後、対象サービスの**サービス全体**のディメンション配列を選び、`service-dimensions.json`として保存します。最初の結果を任意に選んだり、AZメトリクスと集計値を混在させたりしないでください。識別子が観測対象サービスと一致することを確認します。次で`dashboard.json`を作成します。

```python
import json
import os

dimensions = json.load(open("service-dimensions.json"))
if {d["Name"] for d in dimensions} != {"Service"}:
    raise ValueError("Select the service-wide metric, without AvailabilityZone")
pairs = [item for d in dimensions for item in (d["Name"], d["Value"])]
dashboard = {"widgets": [{
    "type": "metric", "width": 12, "height": 6,
    "properties": {
        "title": "VPC Lattice requests and errors",
        "region": os.environ["AWS_REGION"], "period": 60, "stat": "Sum",
        "metrics": [["AWS/VpcLattice", name, *pairs] for name in
                    ("TotalRequestCount", "HTTPCode_4XX_Count", "HTTPCode_5XX_Count")],
    },
}]}
with open("dashboard.json", "w") as output:
    json.dump(dashboard, output)
```

```bash
aws cloudwatch put-dashboard --dashboard-name VPCLattice \
  --dashboard-body file://dashboard.json
aws cloudwatch put-metric-alarm --alarm-name LatticeApi5xx \
  --namespace AWS/VpcLattice --metric-name HTTPCode_5XX_Count \
  --dimensions file://service-dimensions.json \
  --statistic Sum --period 60 --evaluation-periods 3 --datapoints-to-alarm 2 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing
```

このアラームは**3期間のうち2期間で、1分あたり5件を超える5xx応答**を意味し、エラー率5%ではありません。通知が必要なら、レビュー済みのアラームアクションを別途設定します。欠損データの扱いは明示的に選択しています。メトリクスはトラフィック開始後に公開され、NoDataを暗黙に健全性の証拠として扱ってはいけません。ダッシュボードとアラームの設定は例であり、ワークロード固有のSLOではありません。

### アクセスログ記録

CloudWatch Logsでは既存送信先を使うか、保持ポリシー付きの専用ロググループを作成します。

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

設定するプリンシパルには、文書化されたログ配信権限も必要です。必要な権限があれば、AWSはログのリソースポリシーを作成/更新できます。そうでなければ事前設定してください。`delivery.logs.amazonaws.com`の権限と送信元アカウント/送信元ARN条件を確認します。

Kubernetes管理のルートでは、競合するCLI作成のサブスクリプションの**代わりに**次を使用します。

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: AccessLogPolicy
metadata:
  name: api-logs
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  destinationArn: arn:aws:logs:us-west-2:123456789012:log-group:/aws/vendedlogs/vpc-lattice/api:*
```

ARNを置き換え、ポリシーステータスと実際の配信イベントを確認します。ネットワークログにはGateway、サービスログにはRouteを対象にできます。対象ごとに、サポートされる各送信先タイプにつき1つの送信先を設定できます。

S3では、Block Public Access、暗号化、保持/ライフサイクルルール、適切な配信権限を備えた、レビュー済みの送信先バケットを使用します。

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

S3配信には、`delivery.logs.amazonaws.com`に対する文書化された`s3:GetBucketAcl`と`s3:PutObject`権限、配信プレフィックス、`aws:SourceAccount`と`aws:SourceArn`条件が必要です。既存ポリシーは上書きせずマージします。SSE-KMSにはサポートされるカスタマー管理キーと、その配信用キーポリシーが必要です。`--destination-name`はアクセスログサブスクリプションのパラメーターではありません。

### ログ分析とトレース

HTTPサービスのアクセスログには、`sourceIpPort`、`requestMethod`、`requestPath`、`responseCode`、`durationMS`、`callerPrincipal`、`authDeniedReason`などのフィールドが含まれます。リソース/TCPログのスキーマは異なります。

```bash
END_TIME="$(python3 -c 'import time; print(int(time.time()))')"
START_TIME="$((END_TIME - 3600))"
QUERY_ID="$(aws logs start-query --log-group-name "$LOG_GROUP" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --query-string 'fields @timestamp, sourceIpPort, requestMethod, requestPath, responseCode, durationMS, callerPrincipal, authDeniedReason | filter responseCode >= 400 | sort @timestamp desc | limit 100' \
  --query queryId --output text)"
aws logs get-query-results --query-id "$QUERY_ID"
# Repeat get-query-results until Complete; Failed/Cancelled/Timeout are errors.
```

VPC Latticeには、アプリケーションをX-Ray向けに自動計装する`update-service --tracing-config`オプションやコントローラーアノテーションはありません。OpenTelemetry/ADOTまたは適切なトレースSDKでアプリケーションを計装し、トレースコンテキストを伝播して、エクスポート/サンプリングを設定します。アプリケーショントレースをアクセスログやリクエストIDと関連付けてください。クライアント提供のリクエストIDは、認証済みIDではありません。

## ベストプラクティス {#best-practices}

- **設計と所有権:** ネットワーク/サービスの命名と環境境界を明確にします。名前空間をまたぐ同名Gateway、共有ネットワーク利用者、クォータ、各ポリシーと関連付けの所有権を考慮します。
- **デプロイ:** 安定版とカナリアのバックエンドを独立して選択可能に保ちます。重み変更前にエンドポイント、ターゲットの健全性、認可を確認します。ロールバック基準を記録し、最後に確認済みの設定を保持します。
- **性能:** 上限のあるタイムアウトと適切な接続再利用を使います。ヘルスエンドポイントは軽量かつ意味のあるものにします。アプリケーションの意味上許される場合に限ってキャッシュやバッチ処理を使います。キャッシュを有効にするだけで、プライベートなLatticeサービスがCDNオリジンになるわけではありません。
- **セキュリティ:** 管理ロールと呼び出し元ロールを分離し、認証情報をマニフェストに含めません。許可/拒否されるロール、ルートパスとサブパス、バックエンドへの直接アクセス、TLS動作をテストします。通信を拒否するためにIAMポリシーCRDを削除しないでください。
- **可観測性:** リクエスト数、エラー数/率、レイテンシー、ターゲットの健全性、テレメトリーの欠損を別々に監視します。必要な期間アクセスログを保持し、アプリケーショントレースを明示的に計装します。
- **コスト:** 選択したモデルの現在のリージョン別サービス/リソース、リクエスト、データ処理、エンドポイント、ログ記録料金を確認します。タグを使用し、未使用と確認したリソースだけを削除し、バックエンドの自動スケーリングの規模はマネージドLatticeデータプレーンと分けて決めます。

## トラブルシューティング {#troubleshooting}

コントローラーのアノテーション/ステータスとAWS一覧の識別子を使用します。直接APIのサンプルの`$SERVICE_ID`がKubernetesルートのサービスだと想定しないでください。

```bash
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-service-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_ID"
aws vpc-lattice list-listeners --service-identifier "$SERVICE_ID"
aws vpc-lattice list-rules --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID"
aws vpc-lattice get-target-group --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
```

| 症状 | 確認項目 |
|---|---|
| DNS/接続の失敗 | 実際の割り当てDNS、クライアントVPC関連付けまたはエンドポイント経路、関連付け状態、SG、NACL、Pod到達性 |
| 403/認証失敗 | 呼び出し元ロール、認証情報期限と署名リージョン/サービス、`UNSIGNED-PAYLOAD`、両方の認証レイヤー、伝播、ログの拒否理由フィールド |
| ルートまたはバージョンが違う | Route条件、リスナー/ルールの優先順位と一致条件、ターゲットグループのメンバー、重み、Routeごとに異なるドメイン |
| ターゲットが異常 | 実際の待ち受けポート、`/health`、HTTPとHTTPS、準備状態、SG、ターゲットタイプとヘルスチェックしきい値 |
| ログ/メトリクスがない | 送信先権限と配信状態、正しいメトリクスディメンション、初期トラフィック、保持期間、クエリ状態 |
| コントローラーの調整失敗 | `manager`ログ、IAMロール、EndpointSlice、CRDバージョン互換性、Webhookとリーダー選出の状態 |

GNU専用の`date -d`に依存せず、範囲を限定したメトリクス期間を使用します。

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

AWSサービスの障害では、AWS Healthと関連アカウントイベントを確認してください。アカウント固有のAPIアクセスやサポート操作は、該当プランとエンドポイントに依存します。サポートケースには、確認済みのリソースID、時間範囲、障害症状、機密情報を削除したログを含めます。アカウントで現在利用できるサービス/カテゴリ/重大度を選択し、`urgent`を固定したケース作成コマンドを貼り付けないでください。

## 参考資料 {#references}

- [VPC Latticeの概要](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [サービスネットワークの関連付け](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [コントローラーv2.1.3のインストール](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [コントローラーv2.1のアップグレード要件](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [コントローラーAPIリファレンス](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [コントローラーのHTTPSとバックエンドTLS](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [VPC Latticeの認証ポリシー](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [リクエストへの署名](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [エンティティの共有](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [CloudWatchメトリクス](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [アクセスログ](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [CloudWatch Logsの配信権限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [S3の配信権限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## クイズ

[VPC Latticeクイズ](../quizzes/networking/02-vpc-lattice-quiz.md)で理解度を確認してください。
