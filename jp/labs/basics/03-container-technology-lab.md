# コンテナ技術ラボガイド

> **難易度**: 初級
> **所要時間**: 45 分
> **最終更新日**: 2026年10月16日

## 学習目標
- Dockerfile を作成してイメージをビルドする
- マルチステージビルドでイメージを最適化する
- コンテナの実行、デバッグ、ログ確認を行う

## 前提条件
- [ ] Docker CLI、サポート対象のローカル Docker Engine、Bash、curl
- [ ] [Container Technology](../../basics/03-container-technology.md) の学習を完了していること

Bash のターミナルを1つ使い、使い捨ての**ローカル Linux コンテナ用 Docker Engine**で実施してください。続行前に選択中の context を確認してください。以下の helper はすべてのコマンドをその context に固定します。クライアントのバージョンだけでなく、サーバーが利用可能でバージョン要件を満たすことも確認してください。記載した loopback ポート公開の挙動には、保守対象で 28.0.0 以降の Engine を使います。それより古いリリースでは、同一 L2 ネットワークから到達できる場合があるという注意点があります。Docker リソースやポートが作成されるのはラボを実行した場合だけであり、この監査では作成していません。

---

## 演習 1: Dockerfile の作成とイメージのビルド

### 目標
シンプルな Web アプリケーションをコンテナ化します。

### 手順

**ステップ 1.1: プロジェクトディレクトリを作成する**
```bash
CONTAINER_LAB_START_DIR=$PWD
unset CONTAINER_LAB_WEB_PORT CONTAINER_LAB_GO_PORT CONTAINER_LAB_WEB_CID CONTAINER_LAB_GO_CID
CONTAINER_LAB_DIR=$(mktemp -d /tmp/k8s-docs-container.XXXXXX)
: "${CONTAINER_LAB_DIR:?mktemp failed}"
CONTAINER_LAB_ID=$(basename "$CONTAINER_LAB_DIR")
CONTAINER_LAB_CONTEXT=$(docker context show)
lab_docker() { docker --context "${CONTAINER_LAB_CONTEXT:?}" "$@"; }
lab_docker context inspect "$CONTAINER_LAB_CONTEXT" --format '{{json .Endpoints.docker.Host}}'
lab_docker version

CONTAINER_LAB_WEB_IMAGE="k8s-docs-lab/web:$CONTAINER_LAB_ID"
CONTAINER_LAB_GO_IMAGE="k8s-docs-lab/go:$CONTAINER_LAB_ID"
CONTAINER_LAB_BUILD_IMAGE="k8s-docs-lab/go-build:$CONTAINER_LAB_ID"
cd "$CONTAINER_LAB_DIR"

cat > index.html << 'EOF'
<!DOCTYPE html>
<html><body>
<h1>Hello from Container!</h1>
<p>Hostname: <!--# echo var="hostname" --></p>
</body></html>
EOF

cat > nginx.conf << 'EOF'
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        ssi on;
    }
}
EOF
```

SSI が読み取るのは、ドキュメントに記載された NGINX の `hostname` 変数です。任意の環境変数展開ではありません。

**ステップ 1.2: Dockerfile を作成する**
```bash
cat > Dockerfile << 'EOF'
FROM nginx:1.30.6-alpine
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
```

**ステップ 1.3: イメージをビルドする**
```bash
lab_docker build --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" \
  -t "${CONTAINER_LAB_WEB_IMAGE:?}" .
lab_docker image ls "$CONTAINER_LAB_WEB_IMAGE"
```

実際のイメージ ID と報告されたサイズを確認してください。以前の「約40MB」という記載は未検証の例であり、ベンチマークでも必須の結果でもありません。サイズはベースイメージ、アーキテクチャ、イメージストアによって変わります。この監査ではイメージサイズを測定していません。

<details>
<summary>ヒントが必要ですか？</summary>

- `docker build -t name:tag .` の `.` はビルドコンテキストのディレクトリです。
- ベースイメージのサイズは、トレードオフの一つに過ぎません。libc／ランタイムの互換性や必要なツールも考慮してください。
- `docker build --no-cache` を使うと、キャッシュを使わずにビルドできます。
</details>

### 検証
```bash
lab_docker image ls "${CONTAINER_LAB_WEB_IMAGE:?}" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
```

---

## 演習 2: コンテナの実行とデバッグ

### 目標
コンテナを実行し、その内部をデバッグします。

### 手順

**ステップ 2.1: コンテナを実行する**
```bash
if lab_docker run -d --pull=never \
  --name "web-${CONTAINER_LAB_ID:?}" --hostname container-lab-web \
  --label "io.kubernetes-docs.lab=$CONTAINER_LAB_ID" \
  --cidfile "${CONTAINER_LAB_DIR:?}/web.cid" \
  -p 127.0.0.1::80 "${CONTAINER_LAB_WEB_IMAGE:?}"; then
  CONTAINER_LAB_WEB_CID=$(cat "$CONTAINER_LAB_DIR/web.cid")
  CONTAINER_LAB_WEB_MAPPING=$(lab_docker port "$CONTAINER_LAB_WEB_CID" 80/tcp)
  CONTAINER_LAB_WEB_PORT=${CONTAINER_LAB_WEB_MAPPING##*:}
  : "${CONTAINER_LAB_WEB_PORT:?No port mapping found}"
  lab_docker ps --filter "id=$CONTAINER_LAB_WEB_CID"
else
  printf 'Container startup failed; inspect the created lab resource before continuing\n' >&2
fi
```

**ステップ 2.2: コンテナにアクセスできることを確認する**
```bash
curl --disable --noproxy '*' --fail --show-error --silent \
  --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?Run Step 2.1}/"
```

**ステップ 2.3: コンテナ内部に接続する**
```bash
# This shell command applies to the NGINX image, which includes sh.
lab_docker exec -it "${CONTAINER_LAB_WEB_CID:?}" sh

# Run these inside that container, then return to the original Bash shell.
ls /usr/share/nginx/html/
cat /etc/nginx/conf.d/default.conf
exit
```

**ステップ 2.4: ログを確認する**
```bash
lab_docker logs "${CONTAINER_LAB_WEB_CID:?}"
lab_docker logs --tail 5 "$CONTAINER_LAB_WEB_CID"
```

<details>
<summary>ヒントが必要ですか？</summary>

- `docker exec -it` の `-it` は interactive と TTY のオプションを表します。
- `docker inspect container-name` で詳細情報を確認できます。
- Kubernetes では `kubectl exec -it pod-name -c container-name -- sh` が相当します。RBAC 権限と、対象イメージ内のシェルが必要です。
</details>

### 検証
```bash
if HTTP_CODE=$(curl --disable --noproxy '*' --silent --show-error \
  --output /dev/null --write-out '%{http_code}' --max-time 5 \
  "http://127.0.0.1:${CONTAINER_LAB_WEB_PORT:?}/"); then
  [ "$HTTP_CODE" = "200" ] && printf 'HTTP 200 confirmed\n' || printf 'Unexpected HTTP %s\n' "$HTTP_CODE"
else
  printf 'HTTP transfer failed; a printed status alone is not success\n' >&2
fi
```

---

## 演習 3: マルチステージビルド

### 目標
マルチステージビルドを使用してイメージサイズを最適化します。

### 手順

**ステップ 3.1: Go アプリケーションを作成する**
```bash
cat > main.go << 'EOF'
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

func newHandler(hostname string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		fmt.Fprintf(w, "Hello from %s!\n", hostname)
	})
	return mux
}

func main() {
	hostname, err := os.Hostname()
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{
		Addr:              ":8080",
		Handler:           newHandler(hostname),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Fatal(server.ListenAndServe())
}
EOF
```

**ステップ 3.2: マルチステージ Dockerfile**
この Go 標準ライブラリのプログラムは `CGO_ENABLED=0` でビルドされるため、`scratch` ランタイムにビルダーの libc は不要です。`scratch` にはシェル、パッケージマネージャー、CA バンドルがありません。これらの資材を必要とするアプリケーションには、適切なランタイムを選ぶか、必要なファイルを明示的に追加してください。2つのタグ付きステージは同じ Go 成果物を含むため、無関係な NGINX と Go アプリケーションを比較するより、ビルド環境を取り除く効果を切り分けられます。BuildKit では、タグを付けた中間イメージを明示しないと残らない場合があります。

```bash
cat > Dockerfile.multi << 'EOF'
FROM golang:1.27.2 AS build
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
WORKDIR /src
COPY main.go .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/server main.go
CMD ["/out/server"]

FROM scratch AS runtime
ARG LAB_ID
LABEL io.kubernetes-docs.lab=$LAB_ID
COPY --from=build /out/server /server
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/server"]
EOF

lab_docker build -f Dockerfile.multi --target build \
  --build-arg "LAB_ID=${CONTAINER_LAB_ID:?}" -t "${CONTAINER_LAB_BUILD_IMAGE:?}" .
lab_docker build -f Dockerfile.multi \
  --build-arg "LAB_ID=$CONTAINER_LAB_ID" -t "${CONTAINER_LAB_GO_IMAGE:?}" .
```

同じプラットフォームとイメージストアで比較してください。レイヤーを共有できるため、報告されるイメージサイズは圧縮後のダウンロードサイズやディスクの実使用量と必ずしも一致しません。

**ステップ 3.3: イメージサイズを比較する**
```bash
# Same Go program/artifact; the build-stage image retains the compiler and base OS.
for image in "${CONTAINER_LAB_BUILD_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}"; do
  lab_docker image ls "$image" --format '{{.Repository}}:{{.Tag}} - {{.Size}}'
done
```

<details>
<summary>ヒントが必要ですか？</summary>

- マルチステージビルドでは `FROM ... AS build` を使い、ビルドステージに名前を付けます。
- `COPY --from=build` を使うと、前のステージから成果物だけをコピーできます。
- 最終イメージにはビルドツールが含まれないため、サイズを大幅に削減できます。
</details>

### 検証
```bash
if lab_docker run -d --pull=never --read-only \
  --name "go-${CONTAINER_LAB_ID:?}" --hostname container-lab-go \
  --label "io.kubernetes-docs.lab=$CONTAINER_LAB_ID" \
  --cidfile "${CONTAINER_LAB_DIR:?}/go.cid" \
  -p 127.0.0.1::8080 "${CONTAINER_LAB_GO_IMAGE:?}"; then
  CONTAINER_LAB_GO_CID=$(cat "$CONTAINER_LAB_DIR/go.cid")
  CONTAINER_LAB_GO_MAPPING=$(lab_docker port "$CONTAINER_LAB_GO_CID" 8080/tcp)
  CONTAINER_LAB_GO_PORT=${CONTAINER_LAB_GO_MAPPING##*:}
  : "${CONTAINER_LAB_GO_PORT:?No port mapping found}"
  curl --disable --noproxy '*' --fail --show-error --silent \
    --retry 5 --retry-delay 1 --retry-connrefused --max-time 5 \
    "http://127.0.0.1:$CONTAINER_LAB_GO_PORT/"
  lab_docker logs "$CONTAINER_LAB_GO_CID"
fi
```

---

## クリーンアップ
```bash
# Resource IDs and labels must match this lab, even after a partial startup failure.
: "${CONTAINER_LAB_DIR:?}"
: "${CONTAINER_LAB_ID:?}"
for cid_file in "$CONTAINER_LAB_DIR/web.cid" "$CONTAINER_LAB_DIR/go.cid"; do
  [ -s "$cid_file" ] || continue
  cid=$(cat "$cid_file")
  owner=$(lab_docker container inspect --format '{{index .Config.Labels "io.kubernetes-docs.lab"}}' "$cid" 2>/dev/null) || continue
  if [ "$owner" = "$CONTAINER_LAB_ID" ]; then
    lab_docker container stop "$cid"
    lab_docker container rm "$cid"
  fi
done
for image in "${CONTAINER_LAB_WEB_IMAGE:?}" "${CONTAINER_LAB_GO_IMAGE:?}" "${CONTAINER_LAB_BUILD_IMAGE:?}"; do
  owner=$(lab_docker image inspect --format '{{index .Config.Labels "io.kubernetes-docs.lab"}}' "$image" 2>/dev/null) || continue
  if [ "$owner" = "$CONTAINER_LAB_ID" ]; then
    lab_docker image rm "$image"
  fi
done
cd "${CONTAINER_LAB_START_DIR:?}"
rm -f -- "$CONTAINER_LAB_DIR/index.html" "$CONTAINER_LAB_DIR/nginx.conf" \
  "$CONTAINER_LAB_DIR/Dockerfile" "$CONTAINER_LAB_DIR/main.go" \
  "$CONTAINER_LAB_DIR/Dockerfile.multi" "$CONTAINER_LAB_DIR/web.cid" "$CONTAINER_LAB_DIR/go.cid"
if rmdir -- "$CONTAINER_LAB_DIR"; then
  unset CONTAINER_LAB_DIR
fi
unset -f lab_docker
```

## 参考資料と検証範囲

- [Docker のマルチステージビルド](https://docs.docker.com/build/building/multi-stage/)
- [Docker のポート公開](https://docs.docker.com/engine/network/port-publishing/)
- [Docker run](https://docs.docker.com/reference/cli/docker/container/run/)
- [NGINX SSI](https://nginx.org/en/docs/http/ngx_http_ssi_module.html)
- [NGINX 公式イメージのタグ](https://github.com/docker-library/official-images/blob/master/library/nginx)
- [Go 公式イメージのタグ](https://github.com/docker-library/official-images/blob/master/library/golang)

Go の handler／静的ファイルのビルドとコマンド構文はローカルで確認できます。この監査では Docker daemon への接続、イメージのビルド／実行、ポートの公開、イメージサイズ削減の測定は行っていません。ラボ手順を実行記録として扱わないでください。

## 次のステップ
- [コンテナ技術クイズ](../../quizzes/basics/03-container-technology-quiz.md)
- [Pod とワークロードのラボ](../core/02-pods-and-workloads-lab.md)
