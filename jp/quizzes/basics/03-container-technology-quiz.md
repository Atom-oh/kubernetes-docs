# コンテナ技術クイズ

このクイズでは、コンテナ技術の基礎、それがどのように動作するか、そして Kubernetes との関係についての理解を確認します。

## 選択式問題

1. 次のうち、コンテナの主要な特徴ではないものはどれですか？
   - A) 可搬性
   - B) 軽量性
   - C) 完全なハードウェア仮想化
   - D) 分離された実行環境
   
<details>

<summary>答えを表示</summary>

**回答: C) 完全なハードウェア仮想化**

**解説:**
コンテナはホスト OS のカーネルを共有し、ハードウェアを仮想化しません。完全なハードウェア仮想化は仮想マシン（VM）の特徴です。コンテナは可搬性、軽量な動作、分離された実行環境を提供しますが、動作するためにホスト OS のカーネルに依存します。
</details>

2. コンテナと仮想マシンの主な違いは何ですか？
   - A) コンテナはそれぞれ独立した OS を必要とする
   - B) 仮想マシンはコンテナより起動時間が速い
   - C) コンテナはホスト OS のカーネルを共有する
   - D) 仮想マシンはコンテナより少ないリソースを使用する
   
<details>

<summary>答えを表示</summary>

**回答: C) コンテナはホスト OS のカーネルを共有する**

**解説:**
コンテナはホスト OS のカーネルを共有して動作しますが、仮想マシンはそれぞれ完全な OS を含みます。そのため、コンテナは仮想マシンより軽量で、起動が速く、リソース効率に優れています。
</details>

3. 次のうち、OCI（Open Container Initiative）互換の低レベルコンテナランタイムではないものはどれですか？
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>答えを表示</summary>

**回答: C) containerd**

**解説:**
containerd は、イメージ転送、ストレージ、コンテナ実行管理などの機能を提供する高レベルコンテナランタイムです。runc、crun、gVisor はいずれも、実際のコンテナ作成と実行を担当する OCI 互換の低レベルコンテナランタイムです。
</details>

4. コンテナイメージのレイヤーについて正しい記述はどれですか？
   - A) 各レイヤーは独立して変更できる
   - B) レイヤーは常にマージされ、単一ファイルとして保存される
   - C) レイヤーは前のレイヤーに対する変更を表す
   - D) すべてのコンテナは独自のレイヤーセットを持つ
   
<details>

<summary>答えを表示</summary>

**回答: C) レイヤーは前のレイヤーに対する変更を表す**

**解説:**
コンテナイメージは複数のレイヤーで構成され、各レイヤーは前のレイヤーに対する変更を表します。このレイヤー構造により、イメージの共有とキャッシュが効率的になり、ストレージ容量を節約し、イメージのダウンロード速度を向上させます。レイヤーは読み取り専用であり、コンテナが実行されると、その上に書き込み可能なレイヤーが追加されます。
</details>

5. Dockerfile でマルチステージビルドを使用する主な目的は何ですか？
   - A) ビルド速度を向上させる
   - B) 最終イメージサイズを削減する
   - C) セキュリティ脆弱性を減らす
   - D) 複数のオペレーティングシステムをサポートする
   
<details>

<summary>答えを表示</summary>

**回答: B) 最終イメージサイズを削減する**

**解説:**
マルチステージビルドの主な目的は、最終イメージサイズを削減することです。ビルドステージにはソースコードのコンパイルや依存関係のインストールなどに必要なすべてのツールを含め、実行ステージにはビルド成果物だけを持ち込むことで、最小限のランタイム環境を持つ小さなイメージを作成します。これにより、ビルドツールや中間ファイルを最終イメージから除外できます。
</details>

6. Docker のデフォルトネットワークドライバーは何ですか？
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>答えを表示</summary>

**回答: B) bridge**

**解説:**
bridge は Docker のデフォルトネットワークドライバーで、同じホスト上で実行されているコンテナ間の通信を可能にします。このドライバーは、コンテナを接続するためにホスト内に仮想ブリッジを作成します。host ドライバーはホストネットワークを直接使用し、overlay は複数ホスト間の通信に使用され、macvlan はコンテナに MAC アドレスを割り当てて物理ネットワークデバイスのように見せます。
</details>

7. コンテナ内の永続データ保存において、Docker が管理するホストファイルシステム上の領域を使用する方法はどれですか？
   - A) エフェメラルストレージ
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>答えを表示</summary>

**回答: B) Volume**

**解説:**
Volume は Docker が管理するホストファイルシステム上の領域であり、コンテナ内の永続データ保存に最も適した方法です。エフェメラルストレージはコンテナ内部のファイルシステムで、コンテナが削除されるとデータが失われます。Bind mount は特定のホストパスをコンテナにマウントし、tmpfs mount はデータをメモリ内にのみ保存します。
</details>

8. コンテナセキュリティを強化する方法ではないものはどれですか？
   - A) コンテナを非 root ユーザーとして実行する
   - B) 必要な Linux capabilities のみを付与する
   - C) すべてのコンテナに管理者権限を付与する
   - D) 読み取り専用ファイルシステムを使用する
   
<details>

<summary>答えを表示</summary>

**回答: C) すべてのコンテナに管理者権限を付与する**

**解説:**
すべてのコンテナに管理者権限を付与することは、セキュリティを弱める行為です。コンテナセキュリティを強化するには、最小権限の原則に従う必要があります。コンテナを非 root ユーザーとして実行すること、必要な Linux capabilities のみを付与すること、可能な場合にファイルシステムを読み取り専用としてマウントすることは、優れたセキュリティプラクティスです。
</details>

9. サーバーレスのコンテナ実行環境を提供する AWS サービスはどれですか？
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>答えを表示</summary>

**回答: C) Amazon Fargate**

**解説:**
Amazon Fargate は AWS のサーバーレスコンテナ実行環境で、サーバーを管理せずにコンテナを実行できます。Amazon EC2 は仮想サーバーサービス、Amazon ECS はコンテナオーケストレーションサービス、Amazon ECR はコンテナイメージレジストリサービスです。
</details>

10. コンテナオーケストレーションツールの主な機能ではないものはどれですか？
    - A) 自動デプロイとロールバック
    - B) サービスディスカバリとロードバランシング
    - C) コンテナイメージのビルド
    - D) Auto scaling

<details>

<summary>答えを表示</summary>

**回答: C) コンテナイメージのビルド**

**解説:**
コンテナイメージのビルドは通常、CI/CD パイプラインや Docker のようなコンテナビルドツールの役割です。コンテナオーケストレーションツール（Kubernetes、Docker Swarm など）の主な機能は、自動デプロイとロールバック、サービスディスカバリとロードバランシング、Auto scaling、自己修復、構成管理、ストレージオーケストレーションです。
</details>

11. コンテナが実行中でないときに取り得ない状態はどれですか？
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>答えを表示</summary>

**回答: C) Building**

**解説:**
コンテナのライフサイクル状態には、Created（作成済み）、Running（実行中）、Paused（一時停止中）、Restarting（再起動中）、Exited（終了済み）、Dead（デッド）があります。Building はイメージビルドプロセスの状態であり、コンテナの状態ではありません。コンテナはイメージがビルドされた後に作成されます。
</details>

12. Docker デーモンの起動時にコンテナを再起動するが、手動で停止されたコンテナは再起動しないコンテナ再起動ポリシーはどれですか？
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>答えを表示</summary>

**回答: D) unless-stopped**

**解説:**
`unless-stopped` 再起動ポリシーは、明示的に停止されていない限り、常にコンテナを再起動します。Docker デーモンが再起動した場合でもコンテナは自動的に起動しますが、ユーザーが `docker stop` コマンドで手動停止していた場合、デーモン再起動後にコンテナは起動しません。`always` は手動停止の状態に関係なく再起動します。
</details>

13. コンテナと元のイメージの間のファイルシステム変更を確認する Docker コマンドはどれですか？
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>答えを表示</summary>

**回答: B) docker diff**

**解説:**
`docker diff` コマンドは、コンテナのファイルシステムと元のイメージの間の変更を表示します。出力では、A は追加されたファイル、C は変更されたファイル、D は削除されたファイルを表します。このコマンドは、コンテナの実行中にどのファイルが変更されたかをデバッグするのに役立ちます。
</details>

## 短答問題

14. コンテナイメージの内容に基づく一意の識別子で、SHA256 ハッシュとして表現されるものは何ですか？

<details>

<summary>答えを表示</summary>

**回答: Digest**

**解説:**
Digest はコンテナイメージ内容の SHA256 ハッシュであり、イメージの一意の識別子として機能します。タグとは異なり、イメージ内容が変更されると Digest も変わるため、特定のイメージバージョンを正確に参照するために使用されます。例: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. コンテナ起動時に実行するコマンドを指定する Dockerfile ディレクティブは何ですか？

<details>

<summary>答えを表示</summary>

**回答: CMD**

**解説:**
CMD ディレクティブは、コンテナ起動時に実行するデフォルトコマンドを指定します。たとえば、`CMD ["node", "server.js"]` はコンテナ起動時に `node server.js` コマンドを実行します。CMD は docker run コマンドに引数を指定することで上書きできます。
</details>

16. コンテナ間通信のために Docker が作成する仮想ネットワークインターフェイスの名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: docker0**

**解説:**
docker0 は Docker がデフォルトで作成する仮想ブリッジネットワークインターフェイスです。このブリッジにより、同じホスト上で実行されているコンテナ間の通信が可能になり、コンテナと外部ネットワーク間の通信を仲介します。
</details>

17. コンテナ内で実行されているプロセスが使用できるシステムコールを制限する Linux のセキュリティ機能は何ですか？

<details>

<summary>答えを表示</summary>

**回答: seccomp (Secure Computing Mode)**

**解説:**
seccomp は、プロセスが使用できるシステムコールを制限する Linux カーネルのセキュリティ機能です。Docker のようなコンテナランタイムは seccomp プロファイルを使用して、コンテナが実行できるシステムコールを制限し、それによってセキュリティを強化します。
</details>

18. コンテナイメージを保存および管理する AWS サービスの名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: Amazon ECR (Elastic Container Registry)**

**解説:**
Amazon ECR (Elastic Container Registry) は AWS のマネージドコンテナイメージレジストリサービスです。イメージ脆弱性スキャン、IAM 連携、イメージライフサイクル管理などの機能を提供し、他の AWS サービスとシームレスに統合されます。
</details>

19. 実行中のコンテナ内で追加のコマンドを実行できる Docker コマンドは何ですか？

<details>

<summary>答えを表示</summary>

**回答: docker exec**

**解説:**
`docker exec` コマンドを使用すると、実行中のコンテナ内で追加のコマンドを実行できます。たとえば、`docker exec -it <container> bash` はコンテナ内の対話型シェルに接続し、`docker exec <container> ls /app` はコンテナ内のファイルを一覧表示します。このコマンドはコンテナのデバッグに非常に役立ちます。
</details>

20. リアルタイムのコンテナイベント（start、stop、restart など）をストリームとして監視する Docker コマンドは何ですか？

<details>

<summary>答えを表示</summary>

**回答: docker events**

**解説:**
`docker events` コマンドは、Docker デーモンからのリアルタイムイベントをストリームとして表示します。コンテナの start、stop、restart、イメージの pull、ネットワークの connect/disconnect などのイベントを監視できます。`--filter` オプションを使用すると、特定のコンテナやイベントタイプでフィルタリングでき、デバッグや監視に役立ちます。
</details>

## ハンズオン問題

21. 次の要件を満たす Dockerfile を作成してください。
    - Node.js 14 Alpine イメージを使用する
    - 作業ディレクトリを /app に設定する
    - package.json と package-lock.json ファイルを最初にコピーする
    - 依存関係をインストールする
    - 残りのファイルをコピーする
    - ポート 3000 を公開する
    - コンテナ起動時に "node server.js" コマンドを実行する

<details>

<summary>答えを表示</summary>

**回答:**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**解説:**
この Dockerfile は Node.js アプリケーションの基本構成を示しています。依存関係ファイル（package*.json）を最初にコピーし、残りのファイルをコピーする前にインストールすることで、Docker のレイヤーキャッシュを最適化します。この方法では、ソースコードが変更されても、依存関係が変更されていなければ npm install ステップを再利用できます。
</details>

22. 次の Docker コマンドを分析し、その目的を説明してください。
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>答えを表示</summary>

**回答:**
このコマンドは次の目的で使用されます。
    - `-d`: コンテナをバックグラウンドで実行する（detached mode）
    - `--name my-app`: コンテナ名を "my-app" に設定する
    - `-p 8080:80`: ホストポート 8080 をコンテナポート 80 にマッピングする
    - `-v data:/app/data`: "data" という名前の Volume をコンテナ内の /app/data パスにマウントする
    - `--restart always`: コンテナが終了したときに常に自動再起動する
    - `nginx:latest`: nginx イメージの最新バージョンを使用する

このコマンドは nginx Web サーバーをバックグラウンドで実行し、ホストポート 8080 経由でアクセス可能にし、永続データ保存用の Volume を設定し、コンテナ終了時の自動再起動を構成します。
</details>

23. マルチステージビルドを使用して、React アプリケーション用に最適化された Dockerfile を作成してください。

<details>

<summary>答えを表示</summary>

**回答:**
```dockerfile
# Build stage
FROM node:14 AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Run stage
FROM nginx:alpine

# Copy build artifacts to nginx's service directory
COPY --from=build /app/build /usr/share/nginx/html

# Use default nginx configuration

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**解説:**
このマルチステージ Dockerfile は 2 つのステージで構成されています。
1. ビルドステージ: Node.js イメージを使用して React アプリケーションをビルドします。
2. 実行ステージ: 軽量な nginx イメージを使用して、ビルドされた静的ファイルを配信します。

このアプローチの利点は、最終イメージに Node.js ランタイム、npm パッケージ、ソースコードなどが含まれず、イメージサイズを大幅に削減できることです。最終イメージにはビルド済みの静的ファイルと nginx のみが含まれるため、より小さく、より安全になります。
</details>

24. コンテナのヘルスチェックを含む Dockerfile を作成してください。HTTP エンドポイント /health を 30 秒ごとに確認し、3 秒以内に応答がない場合は失敗とみなし、3 回失敗した後に unhealthy とマークするように構成してください。

<details>

<summary>答えを表示</summary>

**回答:**
```dockerfile
FROM nginx:alpine

# Copy application (example)
COPY ./html /usr/share/nginx/html

# Health check configuration
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**解説:**
各 HEALTHCHECK ディレクティブオプションの意味:
- `--interval=30s`: 30 秒ごとにヘルスチェックを実行する
- `--timeout=3s`: ヘルスチェックコマンドは 3 秒以内に完了する必要がある
- `--start-period=10s`: コンテナ起動後 10 秒間はヘルスチェックの失敗を無視する（初期化時間）
- `--retries=3`: 3 回連続で失敗した後にコンテナを unhealthy とマークする
- `CMD`: 実行するヘルスチェックコマンド。wget を使用して /health エンドポイントを確認する

ヘルスチェックは、コンテナオーケストレーションツールが自動復旧やトラフィックルーティングの判断のためにコンテナの状態を判定する際に使用されます。
</details>

25. デバッグ目的で、実行中のコンテナの環境変数、ネットワーク設定、プロセス一覧を確認する Docker コマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
# 1. Check environment variables
docker exec <container-id> env

# Or use inspect
docker inspect <container-id> --format='{{range .Config.Env}}{{println .}}{{end}}'

# 2. Check network settings
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln
# or
docker exec <container-id> ss -tuln

# Check IP address only
docker inspect <container-id> --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 3. Check process list
docker exec <container-id> ps aux
# or
docker top <container-id>

# 4. Additional useful debugging commands
# Container detailed information
docker inspect <container-id>

# Container logs
docker logs <container-id>

# File system changes
docker diff <container-id>

# Real-time resource usage
docker stats <container-id>
```

**解説:**
コンテナをデバッグする際は、これらのコマンドを組み合わせて問題を診断します。
- `docker exec` は実行中のコンテナ内でコマンドを実行する
- `docker inspect` は詳細なコンテナメタデータを確認する
- `docker top` はホスト視点でコンテナのプロセスを表示する
- `docker diff` はイメージと比較して変更されたファイルを確認する
これらのツールを効果的に使用することで、コンテナの内部状態を理解し、問題を解決できます。
</details>

## 応用問題

26. コンテナ技術の中核コンポーネントである namespaces と cgroups の役割を比較し、それぞれがコンテナの分離にどのように貢献するかを説明してください。

<details>

<summary>答えを表示</summary>

**回答:**

**Namespaces**:
    - **役割**: 各グループがシステムリソースを独立して見られるように、プロセスグループを分離します。
    - **分離タイプ**: 可視性の分離を提供します。
    - **主な namespaces**:
    - PID namespace: プロセス ID の分離
    - Network namespace: ネットワークスタックの分離
    - Mount namespace: ファイルシステムのマウントポイントの分離
    - UTS namespace: ホスト名とドメイン名の分離
    - IPC namespace: プロセス間通信リソースの分離
    - User namespace: ユーザー ID とグループ ID の分離

**cgroups (Control Groups)**:
    - **役割**: プロセスグループのリソース使用量を制限し、分離します。
    - **分離タイプ**: リソース制限を提供します。
    - **主な機能**:
    - CPU 時間の制限
    - メモリ使用量の制限
    - ブロック I/O 帯域幅の制限
    - ネットワーク帯域幅の制限
    - デバイスアクセス制御

**コンテナ分離への貢献**:

Namespaces と cgroups は相互補完的な役割を果たします。

    - Namespaces は、コンテナが独自の独立した環境（プロセスツリー、ネットワークインターフェイス、マウントポイントなど）を持てるようにし、論理的な分離を提供します。これにより、各コンテナはシステムに対して独自のビューを持ちます。

    - cgroups は、コンテナが使用できるシステムリソース（CPU、メモリ、ディスク I/O など）を制限し、物理的なリソース分離を提供します。これにより、1 つのコンテナが過剰なリソースを使用して、他のコンテナやホストシステムに影響を与えることを防ぎます。

これら 2 つの技術が連携することで、コンテナはリソース使用量を制限された分離環境で実行できます。この分離は仮想マシンより軽量ですが、セキュリティとリソース管理に十分な分離を提供します。
</details>

27. コンテナイメージのレイヤーシステムがどのように動作するか、また Copy-on-Write（CoW）戦略がコンテナの効率性にどのように貢献するかを説明してください。

<details>

<summary>答えを表示</summary>

**回答:**

**Container Image Layering System**:

コンテナイメージは複数のレイヤーのスタックで構成されます。各レイヤーはファイルシステムの変更を表し、各 Dockerfile コマンド（FROM、RUN、COPY など）が新しいレイヤーを作成します。これらのレイヤーは読み取り専用で、階層的に積み重なって最終イメージを形成します。

レイヤーシステムの主な特徴:
1. **増分ビルド**: イメージビルド中に変更されたレイヤーだけが再生成される
2. **レイヤー共有**: 複数のイメージが同じベースレイヤーを共有する
3. **キャッシュ**: すでにダウンロード済みのレイヤーが再利用される

**Copy-on-Write (CoW) Strategy**:

Copy-on-Write は、データが実際に変更されるまでコピー操作を遅延させる最適化戦略です。コンテナの文脈では次のようになります。

1. **コンテナ起動**: コンテナが起動すると、既存のイメージレイヤーの上に薄い書き込み可能レイヤーが追加されます。
2. **読み取り操作**: ファイルを読み取るとき、システムは上から下へレイヤーを検索し、最初に見つかったファイルのバージョンを使用します。
3. **書き込み操作**: ファイルを変更するとき、まずファイルが書き込み可能レイヤーにコピーされ、その後変更されます（Copy-on-Write）。元のファイルは変更されません。
4. **削除操作**: ファイルを削除するとき、ファイルは実際には削除されません。代わりに、書き込み可能レイヤーに「whiteout」ファイルが作成され、削除されたように見せます。

**効率性への貢献**:

1. **ストレージ効率**: 
    - 同じベースイメージを使用する複数のコンテナがイメージレイヤーを共有し、ディスク容量を節約します。
    - 各コンテナは自身の変更データだけを保存すれば済みます。

2. **起動時間の短縮**:
    - 新しいコンテナを起動するとき、ファイルシステム全体をコピーする必要はなく、書き込み可能レイヤーを作成するだけで済みます。
    - これにより、コンテナの起動時間が大幅に短縮されます。

3. **メモリ効率**:
    - 同じファイルが複数のコンテナで使用される場合、ページキャッシュを共有できます。

4. **ネットワーク効率**:
    - イメージダウンロード時に、すでに存在するレイヤーを再度ダウンロードする必要がありません。

これらの効率性により、コンテナは仮想マシンより軽量かつ高速に起動でき、同じホスト上でより多くのコンテナを実行できます。
</details>

28. コンテナのライフサイクル全体を説明し、各状態（Created、Running、Paused、Restarting、Exited、Dead）におけるコンテナの動作と状態遷移方法を説明してください。

<details>

<summary>答えを表示</summary>

**回答:**

**コンテナライフサイクル状態:**

1. **Created**
   - コンテナは作成済みだが、まだ開始されていない
   - `docker create` コマンドで作成される
   - プロセスは実行されておらず、リソース割り当ては最小限
   - 遷移: `docker start` → Running

2. **Running**
   - コンテナのメインプロセスが実行中
   - `docker run` または `docker start` によって移行する
   - CPU やメモリなどのリソースを積極的に使用している
   - 遷移:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - プロセス終了時 → Exited

3. **Paused**
   - すべてのプロセスが SIGSTOP により一時停止している
   - `docker pause` コマンドによって移行する
   - メモリは保持されるが CPU は使用しない
   - 遷移: `docker unpause` → Running

4. **Restarting**
   - コンテナが再起動中の一時的な状態
   - `docker restart` または再起動ポリシーによって発生する
   - 遷移: 自動的に Running または Exited に遷移する

5. **Exited**
   - メインプロセスが終了している
   - 終了コードが保持される
   - ファイルシステムの変更は保持される
   - 遷移:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - コンテナ削除の試行に失敗した異常状態
   - リソースのクリーンアップが完了していない
   - 一般的に手動での介入が必要
   - `docker rm -f` で強制削除を試みる

**状態確認と管理コマンド:**
```bash
# Check state
docker ps -a                    # List all containers
docker inspect <id> | jq '.[0].State'  # Detailed state

# State transitions
docker create nginx             # → Created
docker start <id>               # → Running
docker pause <id>               # → Paused
docker unpause <id>             # → Running
docker stop <id>                # → Exited
docker restart <id>             # → Running
docker rm <id>                  # Delete
```

**再起動ポリシーとライフサイクル:**
- `no`: 自動再起動しない
- `on-failure[:max]`: 異常終了時に再起動し、最大回数を指定できる
- `always`: 常に再起動する（デーモン再起動を含む）
- `unless-stopped`: 手動停止されるまで常に再起動する

コンテナライフサイクルを理解することで、アプリケーションの可用性を確保し、問題発生時に適切な復旧戦略を確立できます。
</details>

---

[学習資料に戻る](../../basics/03-container-technology.md) | [次のクイズ: Kubernetes 入門](./04-kubernetes-introduction-quiz.md)
