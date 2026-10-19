# コンテナ技術

> **対応バージョン**: 保守対象のLinux Docker／CRIリリース、Kubernetes CRI v1、Node.js 24のビルド例。**最終更新**: 2026年10月16日

アプリケーションと依存関係をまとめてパッケージ化し、さまざまな環境で同じように実行できるようにするのがコンテナ技術です。このドキュメントでは、コンテナの基本概念や動作、Kubernetesとの関係を説明します。

## 目次

* [コンテナとは](03-container-technology.md#what-is-a-container)
* [コンテナと仮想マシンの違い](03-container-technology.md#container-vs-virtual-machine)
* [コンテナの技術的基盤](03-container-technology.md#technical-foundation-of-containers)
* [コンテナランタイム](03-container-technology.md#container-runtime)
* [コンテナイメージ](03-container-technology.md#container-images)
* [Dockerfile](03-container-technology.md#dockerfile)
* [コンテナネットワーク](03-container-technology.md#container-networking)
* [コンテナストレージ](03-container-technology.md#container-storage)
* [コンテナセキュリティ](03-container-technology.md#container-security)
* [コンテナのライフサイクル管理](03-container-technology.md#container-lifecycle-management)
* [コンテナオーケストレーション](03-container-technology.md#container-orchestration)
* [AWS上のコンテナ](03-container-technology.md#containers-on-aws)

> 以下のLinuxコマンドは、Linux上のDockerホストを前提としています。Docker Desktopではデーモンが仮想マシン上で動作するため、デスクトップOSからホストのPIDやファイルシステムのパスを直接確認できません。イメージとCPUアーキテクチャ、OS、カーネル機能との互換性も必要です。KataやFargateなど仮想マシンを使う環境は、ここで説明する基本的なプロセス分離モデルとは異なります。

## コンテナとは {#what-is-a-container}

コンテナは、アプリケーションの実行に必要なもの（コード、ランタイム、システムツール、システムライブラリ、設定）を含む標準化されたソフトウェア単位です。ホストOSのカーネルを共有しながら、分離された環境で動作します。

### コンテナの主な特徴

1. **可搬性**: 開発、テスト、本番環境で一貫した実行環境を提供する
2. **軽量性**: 仮想マシンより少ないリソースで動作する
3. **分離性**: 他のコンテナやホストシステムから隔離された実行環境を提供する
4. **起動と停止の速さ**: 多くの場合、起動は速い。イメージの取得とアプリケーションの初期化にかかる時間が準備完了までの時間を左右する
5. **スケーラビリティ**: 複製しやすく、水平スケーリングに適している
6. **バージョン管理**: イメージのバージョンを使ってアプリケーションのライフサイクルを管理する

### コンテナ技術の歴史

* **2000年代初頭**: Linux VServerやOpenVZなどの初期のコンテナ技術が登場
* **2008年**: Linux 2.6.24でcgroupsの初期実装がリリース
* **2008年**: LXC（Linux Containers）プロジェクトが開始
* **2013年**: Dockerのリリースによってコンテナ技術が広く普及
* **2015年**: Open Container Initiative（OCI）が設立され、コンテナを標準化
* **2017年**: containerdがCNCFプロジェクトに寄贈

## コンテナと仮想マシンの違い {#container-vs-virtual-machine}

### 仮想マシンとコンテナのアーキテクチャ

### 主な違い

これはアーキテクチャの比較であり、性能や起動時間を測定したベンチマークではありません。結果はイメージの大きさ、初期化処理、仮想マシンの復元方式によって変わります。

| 特性 | コンテナ | 仮想マシン |
| --- | --- | --- |
| サイズ | アプリケーションとユーザー空間のレイヤー。環境によって異なる | ゲストOSとアプリケーション。環境によって異なる |
| 起動時間 | イメージがローカルにあれば、多くの場合速い | 起動または復元方式による |
| 分離レベル | プロセス単位の分離 | ハードウェア単位の分離 |
| OS | ホストOSのカーネルを共有する | 各VMに完全なOSが必要 |
| 性能 | ほぼネイティブ | 何らかのオーバーヘッドがある |
| セキュリティ | カーネルを共有するため、強化策が必要 | ハイパーバイザーによる境界があるが、強化策は引き続き必要 |
| リソース効率 | 高い | 中程度 |
| 用途 | マイクロサービス、CI/CD、開発／テスト | レガシーアプリ、多様なOS要件、高いセキュリティ要件 |

## コンテナの技術的基盤 {#technical-foundation-of-containers}

コンテナは複数のLinuxカーネル機能を使って実装されています。これらの技術は`01-linux-basics.md`で詳しく説明しています。ここではコンテナとの関係に注目します。

### Namespacesによる分離

コンテナはLinux Namespacesを使ってプロセスを分離します。Namespaceの共有方法は設定できます。たとえば、同じKubernetes Pod内のコンテナはネットワークNamespaceを共有します。

```bash
# Check container namespaces
docker inspect <container-id> | grep -A 10 "Pid"
ls -la /proc/<pid>/ns/

# Check processes inside container (isolated PID namespace)
docker exec <container-id> ps aux

# Check same process from host (actual PID)
ps aux | grep <process-name>
```

**コンテナで使われるNamespace**:

* **PID**: コンテナごとのプロセスツリー（PID 1から開始）
* **Network**: 独立したネットワークスタック（IPアドレス、ルーティングテーブル、ポート）
* **Mount**: 独立したファイルシステムのビュー
* **UTS**: 独立したホスト名
* **IPC**: 独立したプロセス間通信領域
* **User**: 独立したユーザーIDマッピング（任意）

### cgroupsによるリソース制限

コンテナはcgroupsを使って、リソース使用量を制限・監視します。

```bash
# Run container with CPU limit
docker run --cpus=0.5 --memory=512m nginx

# Check container resource usage
docker stats <container-id>

# Check container cgroup settings
docker inspect <container-id> | grep -A 20 "Cgroup"

# On a Linux cgroup v2 host, inspect a running container's actual path.
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' <container-id>)
if [ "$CONTAINER_PID" -gt 0 ]; then
  CGROUP_PATH=$(awk -F: '$1 == "0" {print $3}' "/proc/$CONTAINER_PID/cgroup")
  cat "/sys/fs/cgroup$CGROUP_PATH/cpu.max"
  cat "/sys/fs/cgroup$CGROUP_PATH/memory.max"
fi
```

**コンテナで使われるcgroupのリソース制御**:

* **CPU**: CPU時間の制限、CPUコアの割り当て
* **Memory**: メモリ使用量の制限、OOM動作の制御
* **Block I/O**: ディスクI/O帯域幅の制限
* **Network**: tc／eBPFと連携したトラフィック分類
* **PIDs**: コンテナ内のプロセス数の上限

### OverlayFSによるレイヤー管理

新規にインストールしたDocker Engine 29.0以降は、containerdのイメージストアとスナップショッターを既定で使います。アップグレード環境では従来のoverlay2が残っている場合があるため、`docker info`で確認してください。`GraphDriver.Data`のパスは、すべてのインストール環境で取得できるわけではありません。

OCIイメージでは、ストレージ実装と切り離してファイルシステムのレイヤーを記述します。OverlayFSはLinuxでよく使われるバックエンドですが、ランタイムによっては別のストレージドライバーやスナップショッターを使います。

```bash
# Check image layers
docker history <image-name>

# Check container file system layers
docker info --format '{{.Driver}} {{json .DriverStatus}}'
docker image inspect <image-name> --format '{{json .RootFS.Layers}}'

# Check OverlayFS mount information
mount | grep overlay
```

**OverlayFSの構造**:

* **LowerDir**: 読み取り専用のイメージレイヤー（下位レイヤーから上位レイヤー）
* **UpperDir**: 読み書き可能なコンテナレイヤー
* **WorkDir**: OverlayFSの作業ディレクトリ
* **MergedDir**: 統合ビュー（コンテナから見えるファイルシステム）

### ラボ: コンテナの技術的基盤を理解する

```bash
# 1. Run a simple container
docker run -d --name test-container nginx

# 2. Get container PID
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' test-container)
echo "Container PID: $CONTAINER_PID"

# 3. Check container namespaces
ls -la /proc/$CONTAINER_PID/ns/

# 4. Check container cgroup
cat /proc/$CONTAINER_PID/cgroup

# 5. Check container file system layers
docker inspect test-container | jq '.[0].GraphDriver'

# 6. Cleanup
docker stop test-container
docker rm test-container
```

## コンテナランタイム {#container-runtime}

コンテナランタイムは、コンテナのライフサイクルを管理するソフトウェアです。コンテナイメージを実行し、コンテナのリソース使用量を制限し、ネットワークとストレージを構成します。

### コンテナランタイムの階層

1. **低レベルランタイム（OCI互換）**
   * **runc**: Dockerの既定ランタイムで、OCI標準を実装する
   * **crun**: Cで書かれた軽量なOCIランタイム
   * **kata-containers**: ハードウェア仮想化を使うセキュリティ強化ランタイム
   * **gVisor**: ユーザー空間でカーネル機能をエミュレートするセキュリティランタイム
2. **高レベルランタイム**
   * **containerd**: Dockerから分離された業界標準のコンテナランタイム
   * **CRI-O**: Kubernetes向けに設計された軽量ランタイム
   * **Docker Engine**: 広く使われているコンテナプラットフォーム

### Kubernetes Container Runtime Interface（CRI）

KubernetesはCRI（Container Runtime Interface）を通じて、さまざまなコンテナランタイムと連携します。CRIはKubernetesとコンテナランタイムの間に標準インターフェイスを提供します。

Kubernetes 1.26以降ではCRI v1が必要です。サポート対象のcontainerdまたはCRI-Oを使い、cgroupドライバーをkubeletに合わせてください。Docker Engine自体はCRIを実装しておらず、組み込みのdockershimは1.24で削除されました。Docker Engineを使う場合はcri-dockerdなどのCRIアダプターが別途必要です。DockerでビルドしたOCIイメージは引き続き使用できます。CRIはkubeletとランタイム間のAPI契約であり、必ずしも個別にデプロイする中間サービスではありません。

## コンテナイメージ {#container-images}

コンテナイメージは、アプリケーションと依存関係を含む不変のテンプレートです。複数のレイヤーから構成され、それぞれがファイルシステムの変更を表します。

### イメージレイヤー

コンテナイメージは複数のレイヤーを積み重ねて構成します。それぞれのレイヤーは前のレイヤーからの変更を表します。この仕組みにより、イメージを効率よく共有・キャッシュできます。

![OSレイヤーの上にランタイム、依存関係、アプリケーションのレイヤーが積み重なるコンテナイメージの図。各レイヤーはその下のレイヤーからの変更を記録するため、イメージを効率よく共有・キャッシュできる。](../.gitbook/assets/en-basics-03-container-technology-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-03-container-technology-0.html)

### イメージレジストリ

コンテナイメージはレジストリに保存し、共有します。主なレジストリは次のとおりです。

* **Docker Hub**: 最大規模の公開レジストリ
* **Amazon ECR**: AWSのコンテナレジストリサービス
* **Google Artifact Registry**: 現行のGoogle Cloudレジストリ。Container Registryは2025年に終了しましたが、Artifact Registryをバックエンドとする`gcr.io`リポジトリは引き続きサポートされます
* **Azure Container Registry**: Microsoft Azureのレジストリ
* **GitHub Container Registry**: GitHubのコンテナレジストリ
* **Harbor**: エンタープライズ向けのオープンソースレジストリ

### イメージのタグとダイジェスト

* **タグ**: 人が読める可変の参照名。レジストリで不変性を強制しない限り、別のイメージに付け替えられます（例: `nginx:1.30.6`）
* **ダイジェスト**: イメージマニフェストまたはマルチプラットフォームインデックスのコンテンツダイジェスト（通常はSHA256）。設定やレイヤーのダイジェストを参照します（例: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`）

## Dockerfile

Dockerfileは、コンテナイメージをビルドする命令を記述したテキストファイルです。ファイルシステムを変更する命令はレイヤーを作成できますが、ENVやCMDなどメタデータだけを変更する命令はファイルシステム差分を追加しません。

### 主なDockerfile命令

```dockerfile
FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
# Requires a committed package-lock.json matching package.json.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --chown=node:node . .
RUN mkdir -p /app/data && chown node:node /app/data
USER node
EXPOSE 3000
VOLUME /app/data
CMD ["node", "server.js"]
```

Node.js 14はサポートが終了しています。以下の例ではサポート対象のNode.js 24系を使います。ネイティブモジュールとAlpineのmuslとの互換性を確認してください。ホストの`node_modules`や認証情報をイメージにコピーしないよう、`.dockerignore`を用意します。EXPOSEはメタデータであり、ポートを公開しません。ポート公開には`docker run -p`またはオーケストレーターの設定が必要です。

```text
# .dockerignore
node_modules
.git
.env
.env.*
npm-debug.log
```

### マルチステージビルド

マルチステージビルドでは複数のビルドステージを使い、最終イメージを小さくします。

```dockerfile
FROM node:24 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.30.6-alpine
# This example assumes a static build written to dist/.
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### イメージの最適化

1. **適切なベースイメージを選ぶ**: Alpineなどの軽量イメージを使用する
2. **マルチステージビルドを使う**: ビルドツールや中間ファイルを最終イメージから除外する
3. **レイヤーの内容とキャッシュを最適化する**: パッケージのインストールと後片付けを1つのRUNにまとめる。レイヤー数を減らすだけでイメージが小さくなるとは限らない
4. **不要なファイルを除外する**: `.dockerignore`を使う
5. **キャッシュを活用する**: 変更頻度の高いレイヤーを後ろに置く

## コンテナネットワーク {#container-networking}

コンテナネットワークを使うと、コンテナ同士、およびコンテナと外部との通信ができます。

### ネットワークドライバー

Dockerには複数のネットワークドライバーがあります。

1. **bridge**: 既定のネットワーク。同一ホスト上のコンテナ間通信に使う
2. **host**: ホストのネットワークNamespaceを共有する。他のコンテナ分離機能は引き続き適用される
3. **overlay**: 複数ホストにまたがるコンテナ間通信に使う
4. **macvlan**: コンテナにMACアドレスを割り当て、物理ネットワークデバイスのように見せる
5. **none**: ループバックだけを残す

### ポートマッピング

外部からアクセスできるように、コンテナ内のポートをホストのポートに割り当てます。

```bash
# Map host port 8080 to container port 80
docker run -p 8080:80 nginx
```

ポート公開では、既定でホスト上のすべてのアドレスにバインドします。ローカルだけで使うラボでは`-p 127.0.0.1:8080:80`を指定してください。

### コンテナ間通信

1. **同じネットワーク**: ユーザー定義bridge上のコンテナは互いの名前を解決できる。既定のbridgeには自動名前解決用DNSがない
2. **links**: コンテナ間を直接つなぐ旧式の方式
3. **外部ネットワーク**: ホストポートを通じて通信する

## コンテナストレージ {#container-storage}

Dockerコンテナの書き込み可能レイヤーは、停止・再起動後も残りますが、コンテナ自体を削除すると失われます。永続化するデータはvolumeなどの外部ストレージに保存してください。

### ストレージの種類

1. **一時ストレージ**: コンテナ内部のファイルシステム。コンテナを削除するとデータも失われる
2. **volume**: Dockerが管理するホストファイルシステム領域
3. **bind mount**: ホスト上の指定パスをコンテナにマウントする
4. **tmpfs mount**: メモリベースの一時ストレージ。ページがディスクにスワップされる場合がある

### volumeの使用例

```bash
# Create volume
docker volume create my-vol

# Run container using volume
docker run -v my-vol:/app/data nginx

# Use bind mount
docker run -v /host/path:/container/path nginx

# Read-only mount
docker run -v /host/path:/container/path:ro nginx
```

### データ共有パターン

1. **volume共有**: 複数のコンテナが同じvolumeを使う
2. **データ用コンテナ**: データだけを含むコンテナを作成し、共有する
3. **外部ストレージとの統合**: AWS EBSやNFSなどの外部ストレージシステムを使う

## コンテナセキュリティ {#container-security}

コンテナのセキュリティは、イメージ、コンテナランタイム、ホストシステムなど複数の層で検討します。

### イメージのセキュリティ

1. **脆弱性スキャン**: TrivyやClairなどでイメージの脆弱性を調べる
2. **信頼できるベースイメージ**: 公式または検証済みのイメージを使う
3. **最小権限の原則**: 必要なパッケージと権限だけを含める
4. **イメージ署名**: Cosignなど、保守されているイメージ署名の仕組みを使う。Docker Content Trustは廃止予定で、DockerのNotary v1サービスは2026年12月8日に終了予定

### ランタイムのセキュリティ

1. **権限の制限**: root以外のユーザーでコンテナを実行する
2. **Capabilitiesの制限**: 必要なLinux capabilityだけを付与する
3. **seccompプロファイル**: システムコールを制限する
4. **AppArmor／SELinux**: 強制アクセス制御を適用する
5. **読み取り専用ファイルシステム**: 可能な場合はファイルシステムを読み取り専用でマウントする

### セキュリティのベストプラクティス

1. **定期更新**: コンテナイメージとホストシステムを定期的に更新する
2. **ネットワーク分離**: 適切なネットワークポリシーでコンテナ間通信を制限する
3. **シークレット管理**: プラットフォームのシークレット機能か外部シークレットマネージャーを使う。Docker Swarmのシークレットはサービス向けで、単独の`docker run`コンテナには適用されない。Composeファイルのシークレットは保証範囲が異なる
4. **リソース上限**: CPU、メモリなどの使用量を制限する
5. **監視とログ**: コンテナの動作を監視し、ログを一元管理する

## コンテナのライフサイクル管理 {#container-lifecycle-management}

コンテナのライフサイクル全体を理解することは、効果的な運用に欠かせません。

### コンテナの状態

コンテナには次のような状態があります。

* **Created**: 作成済みだが、まだ開始していない
* **Running**: 実行中
* **Paused**: freezer cgroupによってLinuxプロセスが凍結されている
* **Restarting**: 再起動中
* **Exited**: 終了済み
* **Removing**: 削除処理中
* **Dead**: 一部削除されたままの状態。再起動できず、後片付けが必要

```bash
# Check container status
docker ps -a

# Detailed status of specific container
docker inspect <container-id> | jq '.[0].State'

# Container state transitions
docker create nginx  # Created state
docker start <container-id>  # Transition to Running state
docker pause <container-id>  # Transition to Paused state
docker unpause <container-id>  # Return to Running state
docker stop <container-id>  # Transition to Exited state
docker rm <container-id>  # Remove container
```

### コンテナの作成と実行

```bash
# Create container only (don't start)
docker create --name my-nginx nginx

# Start container
docker start my-nginx

# Create and start container (all at once)
docker run --name my-nginx2 -d nginx

# Run in interactive mode
docker run -it ubuntu bash

# Run in background
docker run -d nginx

# Auto-remove when container exits
docker run --rm nginx

# Run with environment variables
docker run -e "DB_HOST=localhost" -e "DB_PORT=5432" myapp

# Run with port mapping
docker run -p 8080:80 nginx

# Run with volume mount
docker run -v /host/path:/container/path nginx
```

### コンテナの制御

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop with configured signal (default SIGTERM), then SIGKILL after timeout
docker stop <container-id>

# Force kill container (SIGKILL)
docker kill <container-id>

# Restart container
docker restart <container-id>

# Pause container
docker pause <container-id>

# Resume container
docker unpause <container-id>

# Execute command in running container
docker exec -it <container-id> bash
docker exec <container-id> ls -la /app

# Copy files from/to container
docker cp <container-id>:/path/to/file /local/path
docker cp /local/path <container-id>:/path/to/file
```

### コンテナのログと監視

```bash
# View container logs
docker logs <container-id>

# Stream real-time logs
docker logs -f <container-id>

# Last N log lines
docker logs --tail 100 <container-id>

# Output logs with timestamps
docker logs -t <container-id>

# Logs since specific time
docker logs --since "2025-11-24T10:00:00" <container-id>

# Check container resource usage
docker stats <container-id>

# All container resource usage
docker stats

# Check container processes
docker top <container-id>

# Container detailed information
docker inspect <container-id>
```

### コンテナのクリーンアップ

```bash
# Remove all stopped containers
docker container prune

# Remove stopped containers, unused networks, dangling images and build cache; no volumes
docker system prune

# Additionally prune unused anonymous volumes; running resources are not removed
docker system prune --volumes

# Check disk usage
docker system df

# Remove image
docker rmi <image-id>

# Remove dangling images; -a includes all unused images
docker image prune

# Remove volume
docker volume rm <volume-name>

# Remove unused anonymous volumes; --all includes unused named volumes
docker volume prune

# Remove network
docker network rm <network-name>

# Remove unused networks
docker network prune
```

### ヘルスチェック

HEALTHCHECKはDockerのヘルス状態を記録します。単独Dockerの再起動ポリシーが反応するのはプロセスの終了であり、ヘルス状態だけでは再起動しません。KubernetesはDockerfileのHEALTHCHECKを無視し、liveness／readiness／startup probeを使います。

```dockerfile
FROM nginx:1.30.6-alpine

# Define health check in Dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
```

```bash
# Define health check at runtime
docker run -d \
  --health-cmd="wget -q -O /dev/null http://127.0.0.1/ || exit 1" \
  --health-interval=30s \
  --health-timeout=3s \
  --health-retries=3 \
  nginx:1.30.6-alpine

# Check health check status
docker inspect <container-id> | jq '.[0].State.Health'
```

### 再起動ポリシー

コンテナの終了時に自動で再起動するよう構成します。

```bash
# Restart policy options
# - no: Don't restart (default)
# - on-failure: Restart only on failure
# - always: Restart after exit; manual stop suppresses it until daemon restart or explicit start
# - unless-stopped: Always restart unless explicitly stopped

# Restart on failure (max 3 times)
docker run -d --restart=on-failure:3 nginx

# Always restart
docker run -d --restart=always nginx

# Restart unless explicitly stopped
docker run -d --restart=unless-stopped nginx

# Change restart policy of existing container
docker update --restart=always <container-id>
```

### コンテナのデバッグ

`bash`、`ip`、`netstat`、`ps`はイメージ内にインストールされている必要があります。最小構成のイメージでは、ホスト側の`docker inspect`／`docker top`か、承認済みのデバッグ用イメージを使ってください。`env`や`inspect`の出力にはシークレットが含まれる場合があります。共有ログへ貼り付けないでください。

```bash
# Explore container internal file system
docker exec -it <container-id> bash

# Check container environment variables
docker exec <container-id> env

# Check container network information
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln

# Check container processes
docker exec <container-id> ps aux

# Monitor container events
docker events

# Filter specific container events
docker events --filter container=<container-id>

# Check container changes (compared to image)
docker diff <container-id>
```

## コンテナオーケストレーション {#container-orchestration}

コンテナオーケストレーションとは、複数のコンテナを管理・調整することです。主な機能には、デプロイ管理、スケーリング、ネットワーク、サービスディスカバリーがあります。

### 主なオーケストレーションツール

1. **Kubernetes**: 広く使われているコンテナオーケストレーションプラットフォーム
2. **Docker Swarm**: Docker組み込みのオーケストレーション機能で、設定が簡単
3. **Amazon ECS**: AWSのコンテナオーケストレーションサービス
4. **HashiCorp Nomad**: コンテナと非コンテナのワークロードをどちらもサポート

### オーケストレーションの主な機能

1. **デプロイとロールバックの自動化**: 宣言的な設定によるアプリケーションのデプロイ管理
2. **サービスディスカバリーとロードバランシング**: コンテナ間通信と負荷分散
3. **オートスケーリング**: 負荷に応じてコンテナ数を調整する
4. **自己修復**: 失敗したコンテナを自動で再起動する
5. **設定管理**: アプリケーション設定とシークレットを管理する
6. **ストレージオーケストレーション**: 永続ストレージを管理する
7. **バッチ実行**: 単発ジョブとcronジョブを実行する

## AWS上のコンテナ {#containers-on-aws}

AWSはコンテナワークロード向けに複数のサービスを提供しています。

### Amazon ECS（Elastic Container Service）

EC2インスタンスまたはAWS Fargateでコンテナを実行できる、AWS独自のオーケストレーションサービスです。

**主な機能**:

* AWSサービスとの緊密な統合
* サーバーレスのコンテナ実行（Fargate）
* シンプルな設定と管理
* オートスケーリングとロードバランシング

### Amazon EKS（Elastic Kubernetes Service）

標準のKubernetes APIを使ってAWS基盤上でKubernetesを実行する、AWS管理のKubernetesサービスです。

**主な機能**:

* 管理されたKubernetesコントロールプレーン
* 複数のアベイラビリティゾーンでの高可用性
* AWSサービスとの統合
* EC2とFargateへの対応

### AWS Fargate

サーバーを管理せずにコンテナを実行できるサーバーレス環境です。

**主な機能**:

* サーバー管理が不要
* 料金は要求したタスクリソース（ECS）またはPodリソース（EKS）に基づく。アプリケーション内のコンテナごとに別料金がかかるわけではない
* ECSおよびEKSとの統合
* セキュリティ分離

### Amazon ECR（Elastic Container Registry）

AWSが提供するマネージドコンテナイメージレジストリです。

**主な機能**:

* イメージの脆弱性スキャン
* IAMとの統合
* イメージのライフサイクル管理
* 高可用性とスケーラビリティ

## 用語集

| 用語 | 説明 |
| --- | --- |
| **Container** | アプリケーションと依存関係をパッケージ化し、どこでも一貫して実行できる標準化されたソフトウェア単位 |
| **Image** | コンテナ作成に使う読み取り専用テンプレート。アプリケーションコード、ライブラリ、依存関係、ツール、その他のファイルを含む |
| **Dockerfile** | コンテナイメージのビルド命令を記述したテキストファイル |
| **Registry** | コンテナイメージを保存・配布するリポジトリ（例: Docker Hub、Amazon ECR） |
| **Container Runtime** | コンテナを実行するソフトウェア（例: Docker、containerd、CRI-O） |
| **Namespace** | プロセスを分離し、システムの他の部分を見えなくするLinuxカーネル機能 |
| **cgroups** | プロセスグループのCPUやメモリなど、リソース使用量を制限・監視するLinuxカーネル機能 |
| **Layer** | コンテナイメージを構成するファイルシステム差分。メタデータだけを変更する命令はファイルシステムのレイヤーを必要としない |
| **Volume** | コンテナのデータを永続的に保存する仕組み |
| **Orchestration** | 複数コンテナのデプロイ、管理、スケーリング、ネットワークを自動化すること |
| **ECS** | Amazon Elastic Container Service。AWSのコンテナオーケストレーションサービス |
| **ECR** | Amazon Elastic Container Registry。AWSのコンテナイメージレジストリサービス |
| **Fargate** | インフラストラクチャを管理せずにコンテナを実行するAWSのサーバーレス環境 |

## まとめ

コンテナ技術は、アプリケーションの開発とデプロイの方法を大きく変えました。可搬性、一貫性、効率性によって開発者の生産性を高め、運用の複雑さを減らします。Kubernetesなどのオーケストレーションツールと組み合わせると、大規模な分散アプリケーションを効果的に管理できます。

コンテナの基本概念と動作を理解することは、現代のクラウドネイティブアプリケーションを開発・運用するうえで欠かせません。この知識はKubernetesを効果的に活用する基礎となります。

## クイズ

この章の内容を確認するには、[コンテナ技術クイズ](../quizzes/basics/03-container-technology-quiz.md)に取り組んでください。

## 参考資料

* [Docker公式ドキュメント](https://docs.docker.com/)
* [OCI（Open Container Initiative）](https://opencontainers.org/)
* [containerdプロジェクト](https://containerd.io/)
* [Kubernetesコンテナランタイム概要](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
* [AWSコンテナサービス](https://aws.amazon.com/containers/)

## 検証資料

- https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- https://docs.docker.com/reference/cli/docker/container/pause/
- https://docs.docker.com/reference/cli/docker/container/ls/
- https://docs.docker.com/engine/containers/start-containers-automatically/
- https://docs.docker.com/reference/cli/docker/system/prune/
- https://docs.docker.com/reference/cli/docker/volume/prune/
- https://docs.docker.com/reference/dockerfile/
- https://docs.docker.com/engine/network/drivers/bridge/
- https://docs.docker.com/engine/storage/containerd/
- https://docs.docker.com/engine/storage/tmpfs/
- https://docs.docker.com/engine/security/trust/
- https://docs.docker.com/engine/swarm/secrets/
- https://github.com/opencontainers/image-spec/blob/main/config.md
- https://github.com/opencontainers/image-spec/blob/main/manifest.md
- https://github.com/nodejs/Release/blob/main/schedule.json
- https://github.com/docker-library/official-images/blob/master/library/node
- https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md
- https://github.com/npm/cli/blob/latest/docs/lib/content/commands/npm-ci.md
- https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr
- https://man7.org/linux/man-pages/man7/cgroups.7.html
- https://github.com/torvalds/linux/releases/tag/v2.6.24
- https://docs.aws.amazon.com/eks/latest/userguide/fargate.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- https://aws.amazon.com/fargate/pricing/
