# Container Technology Quiz

このクイズでは、コンテナ技術の基本、その仕組み、および Kubernetes との関係についての理解を確認します。

## Multiple Choice Questions

1. 次のうち、コンテナの主要な特徴ではないものはどれですか？
   - A) 移植性
   - B) 軽量性
   - C) 完全なハードウェア仮想化
   - D) 分離された実行環境
   
<details>

<summary>答えを表示</summary>

**答え: C) 完全なハードウェア仮想化**

**解説:**
コンテナはホスト OS kernel を共有し、ハードウェアを仮想化しません。完全なハードウェア仮想化は virtual machine (VM) の特徴です。コンテナは移植性、軽量な動作、分離された実行環境を提供しますが、動作するためにホスト OS kernel に依存します。
</details>

2. コンテナと virtual machine の主な違いは何ですか？
   - A) コンテナはそれぞれ独立した OS を必要とする
   - B) virtual machine はコンテナより起動時間が速い
   - C) コンテナはホスト OS kernel を共有する
   - D) virtual machine はコンテナより少ないリソースを使用する
   
<details>

<summary>答えを表示</summary>

**答え: C) コンテナはホスト OS kernel を共有する**

**解説:**
コンテナはホスト OS kernel を共有して動作しますが、virtual machine はそれぞれ完全な OS を含みます。その結果、コンテナは virtual machine より軽量で、起動が速く、リソース効率に優れています。
</details>

3. 次のうち、OCI (Open Container Initiative) 互換の low-level container runtime ではないものはどれですか？
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>答えを表示</summary>

**答え: C) containerd**

**解説:**
containerd は high-level container runtime であり、image 転送、storage、container 実行管理などの機能を提供します。runc、crun、gVisor はいずれも、実際の container 作成と実行を担う OCI 互換の low-level container runtime です。
</details>

4. container image layer について正しい記述はどれですか？
   - A) 各 layer は独立して変更できる
   - B) layer は常にマージされ、単一のファイルとして保存される
   - C) layer は前の layer に対する変更を表す
   - D) すべてのコンテナは独自の layer セットを持つ
   
<details>

<summary>答えを表示</summary>

**答え: C) layer は前の layer に対する変更を表す**

**解説:**
container image は複数の layer で構成され、各 layer は前の layer に対する変更を表します。この layer 化された仕組みにより、image の共有と caching が効率的になり、storage 領域を節約し、image のダウンロード速度を向上させます。layer は読み取り専用であり、コンテナが実行されると、その上に書き込み可能な layer が追加されます。
</details>

5. Dockerfile で multi-stage build を使用する主な目的は何ですか？
   - A) build 速度の向上
   - B) 最終 image size の削減
   - C) セキュリティ脆弱性の削減
   - D) 複数の operating system のサポート
   
<details>

<summary>答えを表示</summary>

**答え: B) 最終 image size の削減**

**解説:**
multi-stage build の主な目的は、最終 image size を削減することです。build stage には source code の compile、dependency installation などに必要なすべての tool を含め、run stage では build artifact だけを持ち込むことで、最小限の runtime environment を持つ小さな image を作成します。これにより、build tool や中間ファイルを最終 image から除外できます。
</details>

6. Docker の default network driver は何ですか？
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>答えを表示</summary>

**答え: B) bridge**

**解説:**
bridge は Docker の default network driver であり、同じホスト上で実行されているコンテナ間の通信を可能にします。この driver はホスト内に virtual bridge を作成してコンテナを接続します。host driver はホスト network を直接使用し、overlay は multi-host 通信用で、macvlan はコンテナに MAC address を割り当てて物理 network device のように見せます。
</details>

7. コンテナで永続データを保存する場合、Docker によって管理されるホスト file system の領域を使用する方法はどれですか？
   - A) Ephemeral storage
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>答えを表示</summary>

**答え: B) Volume**

**解説:**
Volume は Docker によって管理されるホスト file system の領域であり、コンテナで永続データを保存するために最も適した方法です。Ephemeral storage はコンテナ内部の file system で、コンテナが削除されるとデータも失われます。Bind mount は特定のホスト path をコンテナ内に mount し、tmpfs mount はデータを memory のみに保存します。
</details>

8. コンテナのセキュリティを強化する方法ではないものはどれですか？
   - A) コンテナを non-root user として実行する
   - B) 必要な Linux capabilities のみを付与する
   - C) すべてのコンテナに administrator privileges を付与する
   - D) read-only file system を使用する
   
<details>

<summary>答えを表示</summary>

**答え: C) すべてのコンテナに administrator privileges を付与する**

**解説:**
すべてのコンテナに administrator privileges を付与することは、セキュリティを弱める行為です。コンテナのセキュリティを強化するには、最小権限の原則に従う必要があります。コンテナを non-root user として実行すること、必要な Linux capabilities のみを付与すること、可能な場合は file system を read-only として mount することは、優れたセキュリティ practice です。
</details>

9. serverless container execution environment を提供する AWS service はどれですか？
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>答えを表示</summary>

**答え: C) Amazon Fargate**

**解説:**
Amazon Fargate は AWS の serverless container execution environment であり、server を管理せずにコンテナを実行できます。Amazon EC2 は virtual server service、Amazon ECS は container orchestration service、Amazon ECR は container image registry service です。
</details>

10. container orchestration tool の主な機能ではないものはどれですか？
    - A) 自動 deployment と rollback
    - B) Service discovery と load balancing
    - C) Container image building
    - D) Auto scaling

<details>

<summary>答えを表示</summary>

**答え: C) Container image building**

**解説:**
Container image building は通常、CI/CD pipeline や Docker のような container build tool の役割です。container orchestration tool (Kubernetes、Docker Swarm など) の主な機能は、自動 deployment と rollback、service discovery と load balancing、auto scaling、self-healing、configuration management、storage orchestration です。
</details>

11. コンテナが実行中でないときに取り得ない状態はどれですか？
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>答えを表示</summary>

**答え: C) Building**

**解説:**
Container lifecycle state には Created (created)、Running (running)、Paused (paused)、Restarting (restarting)、Exited (exited)、Dead (dead) が含まれます。Building は image build process の状態であり、container state ではありません。コンテナは image が build された後に作成されます。
</details>

12. Docker daemon が起動したときにコンテナを再起動するが、コンテナが手動で停止されていた場合は再起動しない container restart policy はどれですか？
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>答えを表示</summary>

**答え: D) unless-stopped**

**解説:**
`unless-stopped` restart policy は、明示的に停止されていない限り、常にコンテナを再起動します。Docker daemon が再起動した場合でもコンテナは自動的に起動しますが、user が `docker stop` command で手動停止していた場合、daemon restart 後にコンテナは起動しません。`always` は手動停止状態に関係なく再起動します。
</details>

13. コンテナと元の image の間の file system 変更を確認する Docker command はどれですか？
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>答えを表示</summary>

**答え: B) docker diff**

**解説:**
`docker diff` command は、コンテナの file system と元の image の間の変更を表示します。出力では、A は Added files、C は Changed files、D は Deleted files を表します。この command は、コンテナの実行中にどのファイルが変更されたかを debugging するのに役立ちます。
</details>

## Short Answer Questions

14. container image の内容に基づく一意の識別子で、SHA256 hash として表されるものは何ですか？

<details>

<summary>答えを表示</summary>

**答え: Digest**

**解説:**
Digest は container image の内容の SHA256 hash であり、image の一意の識別子として機能します。tag とは異なり、image の内容が変更されると digest も変わるため、特定の image version を正確に参照するために使用されます。例: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. コンテナの起動時に実行する command を指定する Dockerfile directive は何ですか？

<details>

<summary>答えを表示</summary>

**答え: CMD**

**解説:**
CMD directive は、コンテナの起動時に実行する default command を指定します。たとえば、`CMD ["node", "server.js"]` はコンテナ起動時に `node server.js` command を実行します。CMD は docker run command に引数を指定することで上書きできます。
</details>

16. コンテナ間通信のために Docker が作成する virtual network interface の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: docker0**

**解説:**
docker0 は Docker が default で作成する virtual bridge network interface です。この bridge は、同じホスト上で実行されているコンテナ間の通信を可能にし、コンテナと外部 network 間の通信を仲介します。
</details>

17. コンテナ内で実行される process が使用できる system call を制限する Linux のセキュリティ機能は何ですか？

<details>

<summary>答えを表示</summary>

**答え: seccomp (Secure Computing Mode)**

**解説:**
seccomp は、process が使用できる system call を制限する Linux kernel のセキュリティ機能です。Docker のような container runtime は seccomp profile を使用して、コンテナが実行できる system call を制限し、それによってセキュリティを強化します。
</details>

18. container image を保存および管理する AWS service の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Amazon ECR (Elastic Container Registry)**

**解説:**
Amazon ECR (Elastic Container Registry) は AWS の managed container image registry service です。image vulnerability scanning、IAM integration、image lifecycle management などの機能を提供し、他の AWS services と seamless に統合されます。
</details>

19. 実行中のコンテナ内で追加の command を実行できる Docker command は何ですか？

<details>

<summary>答えを表示</summary>

**答え: docker exec**

**解説:**
`docker exec` command を使用すると、実行中のコンテナ内で追加の command を実行できます。たとえば、`docker exec -it <container> bash` はコンテナ内の interactive shell に接続し、`docker exec <container> ls /app` はコンテナ内のファイルを一覧表示します。この command はコンテナの debugging に非常に役立ちます。
</details>

20. container event (start、stop、restart など) を stream としてリアルタイムに監視する Docker command は何ですか？

<details>

<summary>答えを表示</summary>

**答え: docker events**

**解説:**
`docker events` command は、Docker daemon からのリアルタイム event を stream として表示します。container start、stop、restart、image pull、network connect/disconnect などの event を監視できます。`--filter` option を使用すると、特定のコンテナや event type で filter でき、debugging と monitoring に役立ちます。
</details>

## Hands-on Questions

21. 次の要件を満たす Dockerfile を作成してください:
    - Node.js 14 Alpine image を使用する
    - working directory を /app に設定する
    - package.json と package-lock.json files を先に copy する
    - dependencies を install する
    - remaining files を copy する
    - port 3000 を expose する
    - コンテナ起動時に "node server.js" command を実行する

<details>

<summary>答えを表示</summary>

**答え:**
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
この Dockerfile は Node.js application の基本的な構成を示しています。dependency files (package*.json) を先に copy し、remaining files を copy する前に install することで、Docker の layer caching を最適化します。これにより、source code が変更されても dependencies が変更されていなければ、npm install step を再利用できます。
</details>

22. 次の Docker command を分析し、その目的を説明してください:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>答えを表示</summary>

**答え:**
この command は次の目的で使用されます:
    - `-d`: コンテナを background (detached mode) で実行する
    - `--name my-app`: コンテナ名を "my-app" に設定する
    - `-p 8080:80`: host port 8080 を container port 80 に map する
    - `-v data:/app/data`: "data" という名前の volume をコンテナ内の /app/data path に mount する
    - `--restart always`: コンテナが終了したときに常に自動で再起動する
    - `nginx:latest`: nginx image の latest version を使用する

この command は nginx web server を background で実行し、host port 8080 経由でアクセスできるようにし、永続データ保存用の volume を設定し、コンテナ終了時の自動再起動を構成します。
</details>

23. multi-stage build を使用して React application 用に最適化された Dockerfile を作成してください。

<details>

<summary>答えを表示</summary>

**答え:**
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
この multi-stage Dockerfile は 2 つの stage で構成されています:
1. Build stage: Node.js image を使用して React application を build します。
2. Run stage: 軽量な nginx image を使用して build 済みの static files を提供します。

この approach の利点は、最終 image に Node.js runtime、npm packages、source code などが含まれないため、image size を大幅に削減できることです。最終 image には build 済みの static files と nginx のみが含まれるため、より小さく、より安全になります。
</details>

24. container health check を含む Dockerfile を作成してください。HTTP endpoint /health を 30 秒ごとに確認し、3 秒以内に応答がない場合は失敗として扱い、3 回失敗した後に unhealthy として mark するように構成してください。

<details>

<summary>答えを表示</summary>

**答え:**
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
各 HEALTHCHECK directive option の意味:
- `--interval=30s`: 30 秒ごとに health check を実行する
- `--timeout=3s`: health check command は 3 秒以内に完了する必要がある
- `--start-period=10s`: コンテナ起動後 10 秒間は health check failure を無視する（初期化時間）
- `--retries=3`: 3 回連続で失敗した後、コンテナを unhealthy として mark する
- `CMD`: 実行する health check command。wget を使用して /health endpoint を確認する

Health check は、container orchestration tool が自動回復や traffic routing の判断のために container status を判定する際に使用されます。
</details>

25. debugging 目的で、実行中のコンテナの environment variables、network settings、process list を確認する Docker commands を作成してください。

<details>

<summary>答えを表示</summary>

**答え:**
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
コンテナを debugging する際は、これらの commands を組み合わせて問題を診断します:
- `docker exec` は実行中のコンテナ内で commands を実行する
- `docker inspect` は詳細な container metadata を確認する
- `docker top` はホストの視点から container processes を表示する
- `docker diff` は image と比較して変更された files を確認する
これらの tools を効果的に使用すると、コンテナの内部状態を理解し、問題を解決するのに役立ちます。
</details>

## Advanced Questions

26. コンテナ技術の中核 components である namespaces と cgroups の役割を比較し、それぞれが container isolation にどのように貢献するか説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Namespaces**:
    - **Role**: process group を分離し、各 group が system resources を独立して見えるようにする。
    - **Isolation type**: visibility isolation を提供する。
    - **Main namespaces**:
    - PID namespace: Process ID isolation
    - Network namespace: Network stack isolation
    - Mount namespace: File system mount point isolation
    - UTS namespace: Hostname and domain name isolation
    - IPC namespace: Inter-process communication resource isolation
    - User namespace: User and group ID isolation

**cgroups (Control Groups)**:
    - **Role**: process group の resource usage を制限し分離する。
    - **Isolation type**: resource limitation を提供する。
    - **Main functions**:
    - CPU time limiting
    - Memory usage limiting
    - Block I/O bandwidth limiting
    - Network bandwidth limiting
    - Device access control

**Container isolation への貢献**:

Namespaces と cgroups は補完的な役割を果たします:

    - Namespaces は、コンテナが独自の独立した environment (process trees、network interfaces、mount points など) を持つことを可能にし、logical isolation を提供します。これにより、各コンテナは system に対する独自の view を持ちます。

    - cgroups は、コンテナが使用できる system resources (CPU、memory、disk I/O など) を制限し、physical resource isolation を提供します。これにより、1 つのコンテナが過剰な resources を使用して他のコンテナやホスト system に影響を与えることを防ぎます。

これら 2 つの技術は連携して、コンテナが resource usage を制限された分離環境で実行できるようにします。この isolation は virtual machine より軽量ですが、セキュリティと resource management に十分な分離を提供します。
</details>

27. container image layering system の仕組みと、Copy-on-Write (CoW) strategy が container efficiency にどのように貢献するか説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Container Image Layering System**:

Container image は複数の layer の stack で構成されます。各 layer は file system changes を表し、各 Dockerfile command (FROM、RUN、COPY など) が新しい layer を作成します。これらの layer は read-only で、階層的に stack されて最終 image を形成します。

layering system の主な特徴:
1. **Incremental builds**: image build 中に変更された layer だけが再生成される
2. **Layer sharing**: 複数の image が同じ base layer を共有する
3. **Caching**: すでに download 済みの layer が再利用される

**Copy-on-Write (CoW) Strategy**:

Copy-on-Write は、data が実際に変更されるまで copy operation を遅延させる optimization strategy です。container の文脈では次のようになります:

1. **Container start**: コンテナが起動すると、既存の image layer の上に薄い writable layer が追加されます。
2. **Read operations**: ファイルを読み取るとき、system は layer を上から下へ検索し、最初に見つかった file version を使用します。
3. **Write operations**: ファイルを変更するとき、まずファイルが writable layer に copy され、その後変更されます (Copy-on-Write)。元のファイルは変更されません。
4. **Delete operations**: ファイルを削除するとき、実際には削除されません。代わりに、削除されたように見せるために writable layer に "whiteout" file が作成されます。

**Efficiency への貢献**:

1. **Storage efficiency**: 
    - 同じ base image を使用する複数のコンテナが image layer を共有し、disk space を節約します。
    - 各コンテナは自身の変更 data だけを保存すれば済みます。

2. **Faster startup time**:
    - 新しいコンテナを起動するとき、file system 全体を copy するのではなく、writable layer だけを作成すれば済みます。
    - これにより、container startup time が大幅に短縮されます。

3. **Memory efficiency**:
    - 同じファイルが複数のコンテナで使用される場合、page cache を共有できます。

4. **Network efficiency**:
    - image download 時に、すでに存在する layer を再度 download する必要がありません。

これらの効率性により、コンテナは virtual machine より軽量かつ高速に起動でき、同じホスト上でより多くのコンテナを実行できます。
</details>

28. container lifecycle 全体を説明し、各 state (Created、Running、Paused、Restarting、Exited、Dead) における container behavior と state transition method を説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Container Lifecycle States:**

1. **Created**
   - コンテナは作成済みだが、まだ起動していない
   - `docker create` command で作成される
   - process は実行されておらず、resource allocation は最小限
   - Transition: `docker start` → Running

2. **Running**
   - コンテナの main process が実行中
   - `docker run` または `docker start` 経由で入る
   - CPU、memory などの resources を能動的に使用している
   - Transitions:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - process termination 時 → Exited

3. **Paused**
   - すべての processes が SIGSTOP で一時停止している
   - `docker pause` command 経由で入る
   - memory は維持されるが CPU usage はない
   - Transition: `docker unpause` → Running

4. **Restarting**
   - コンテナが restart している間の一時 state
   - `docker restart` または restart policy により発生する
   - Transition: Running または Exited に自動的に遷移する

5. **Exited**
   - main process が終了している
   - exit code は保持される
   - file system changes は維持される
   - Transitions:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - container removal の試行が失敗した異常 state
   - resource cleanup が完了していない
   - 一般に手動介入が必要
   - `docker rm -f` で force removal を試行する

**State check and management commands:**
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

**Restart policies and lifecycle:**
- `no`: 自動 restart なし
- `on-failure[:max]`: abnormal exit 時に restart し、最大回数を指定できる
- `always`: 常に restart する（daemon restart を含む）
- `unless-stopped`: 手動で停止されるまで常に restart する

container lifecycle を理解することで、application availability を確保し、問題発生時に適切な recovery strategy を確立できます。
</details>

---

[学習資料に戻る](../../basics/03-container-technology.md) | [次のクイズ: Kubernetes Introduction](./04-kubernetes-introduction-quiz.md)
