# CIパイプラインのクイズ

> **関連ドキュメント**: [CIパイプライン](../../ops/03-ci-pipelines.md)

## 選択問題

### 1. リリースイメージとBuildKit cacheで、別々のECR repositoryを使うのはなぜですか？

- A) Cache imageにはIAM認証が不要だから
- B) 不変のrelease tagと更新可能なcache参照では、異なるpolicyが必要だから
- C) ECRではtagを1つしか使えないから
- D) Cacheを使えばscanが不要になるから

<details>
<summary>解答を表示</summary>

**解答: B) 不変のrelease tagと更新可能なcache参照では、異なるpolicyが必要だから**

**解説:** この例ではアプリケーション用repositoryをIMMUTABLE、build cache用repositoryをMUTABLEにします。commit SHA形式のtagだけでは上書きを防げません。deploymentでは検証済みdigestを使います。

</details>

### 2. GitLab Kubernetes executorでjobごとに別のPodを作ると、何が得られますか？

- A) privileged jobを含めた完全な分離
- B) Nodeへのアクセスに関するすべてのリスクの除去
- C) jobごとのlifecycleとresourceの分離。ただし完全なsecurity boundaryが保証されるわけではない
- D) 信頼できないPRに対する、継承されたAWS publish権限

<details>
<summary>解答を表示</summary>

**解答: C) jobごとのlifecycleとresourceの分離。ただし完全なsecurity boundaryが保証されるわけではない**

**解説:** このガイドのprivileged DinD設定は、信頼されたprotected job向けです。Podの分離、専用CI Node、最小権限roleはそれぞれ別のcontrolであり、どれか一つだけで任意の信頼できないcodeが安全だと証明できるわけではありません。

</details>

### 3. `poll_interval`と`check_interval`はどのように異なりますか？

- A) `poll_interval`はKubernetes Podの状態を確認し、`check_interval`はcoordinatorによるjob pollingに関係する
- B) 同じ設定の別名である
- C) どちらもDocker image cacheを期限切れにする
- D) `poll_interval`はPodを再起動する

<details>
<summary>解答を表示</summary>

**解答: A) `poll_interval`はKubernetes Podの状態を確認し、`check_interval`はcoordinatorによるjob pollingに関係する**

**解説:** Kubernetes executorはjob Podがreadyになるのを待つ間、`poll_interval`を使います。Runner全体の`check_interval`は別のpolling経路を制御するため、一方を変更しても他方の代わりにはなりません。

</details>

### 4. GitLab managerとbuild PodのAWS roleを分けるのはなぜですか？

- A) managerにすべてのAWS権限を付与するため
- B) Pod IdentityがServiceAccountを自動作成するため
- C) build Podが長期鍵を保存する必要があるため
- D) managerのS3 cacheアクセスとbuild PodのECR publishアクセスを別々に制限するため

<details>
<summary>解答を表示</summary>

**解答: D) managerのS3 cacheアクセスとbuild PodのECR publishアクセスを別々に制限するため**

**解説:** `RoleARN`を指定しない場合、この例のS3 cacheはmanagerのcredential chainを使います。build Podには別のECR roleを割り当てます。ServiceAccountは別途作成が必要です。また、AWS Pod Identityのtokenは通常のKubernetes API tokenとは別です。

</details>

### 5. 現行のARCの例では、jobをどのように受け付けて振り分けますか？

- A) RunnerDeploymentとHorizontalRunnerAutoscalerだけをinstallする
- B) 公式のscale-set chart/listenerを使い、`runs-on`を実際のscale-set名に一致させる
- C) organizationのrunner-group名は常にjob labelになる
- D) `minRunners=0`にすればクラスターのcostがすべてなくなる

<details>
<summary>解答を表示</summary>

**解答: B) 公式のscale-set chart/listenerを使い、`runs-on`を実際のscale-set名に一致させる**

**解説:** 旧CRDモデルと現行のscale-set chartを混在させないでください。ARC 0.15.0は`scaleSetLabels`もサポートします。`minRunners`が制御するのはidle runnerであり、controller/listenerのcostがなくなるわけでも、起動待ちがなくなる保証でもありません。

</details>

### 6. どのGitHub jobが、この例のAWS OIDC credentialを取得しますか？

- A) すべての外部PR test
- B) 任意のPR codeを実行する`pull_request_target` job
- C) testに合格した後の、信頼されたpush publish job
- D) 起動したすべてのself-hosted runner

<details>
<summary>解答を表示</summary>

**解答: C) testに合格した後の、信頼されたpush publish job**

**解説:** PR testはpublish credentialを要求せず、GitHub-hosted runnerで実行します。role trustでは正確なrepositoryとmain/protected tagを制限し、ARC PodにはAWS publish roleを継承させません。

</details>

### 7. scanからpublishまでの契約を守る順序はどれですか？

- A) build → 同じimageのscan成功 → publish → 承認済みdigestからindexを作成
- B) publish → scan失敗を無視 → latestをdeploy
- C) sourceをscan → 別のimageをbuild → 常にpublish
- D) JSON fileが1つでもあればscan成功とみなす

<details>
<summary>解答を表示</summary>

**解答: A) build → 同じimageのscan成功 → publish → 承認済みdigestからindexを作成**

**解説:** GitLabはarchitectureごとの1対1 dependencyを通じてimage archiveを渡します。GitHubはローカルでbuildしたimageをpush前にscanします。Trivy errorや脆弱性gateの失敗時はpublishしません。また、標準のTrivy JSONをGitLab report schemaだと誤表示しません。

</details>

### 8. native runnerとQEMUを正しく比較している説明はどれですか？

- A) platform flagを指定するだけで、異なるCPU向けの命令を必ず実行できる
- B) QEMU自体がアプリケーションのcross compilerである
- C) AMD64 imageはtagを変えるだけでARM64になる
- D) native runnerは対象CPU上でbuildし、QEMUは別のCPUの命令をemulateする

<details>
<summary>解答を表示</summary>

**解答: D) native runnerは対象CPU上でbuildし、QEMUは別のCPUの命令をemulateする**

**解説:** manager/jobのNode selector、runner tag、helperのarchitectureを一致させてください。最終indexは個別に確認したplatform digestを参照する必要があります。cross-compilationには意図して設定したtoolchainとDockerfileが必要です。

</details>

### 9. Next.jsのstandalone例で必要なものは何ですか？

- A) どのbuildでも`npm ci --omit=dev`だけで十分
- B) standalone output、build dependency、copyしたstatic asset、正しいserver path
- C) `public`と`.next/static`は常にstandaloneへ自動copyされる
- D) どのmonorepoもrootの`server.js`から起動する

<details>
<summary>解答を表示</summary>

**解答: B) standalone output、build dependency、copyしたstatic asset、正しいserver path**

**解説:** この例は単一のapp rootとnpm lockfileを前提とします。runtime layoutへ`public`と`.next/static`をcopyし、`0.0.0.0`にbindします。monorepoでは独自のtracing rootと、出力先の階層を確認する必要があります。

</details>

### 10. Kanikoとrootless BuildKitについて正しい説明はどれですか？

- A) daemonlessなら、すべてのbuildがrootなしで完全に分離される
- B) privileged DinD imageの名前を変えればrootless設定が完了する
- C) 保守状況とNodeのuser namespace、mount、security policyの対応を確認する
- D) `no-process-sandbox`はprocess分離を強化する

<details>
<summary>解答を表示</summary>

**解答: C) 保守状況とNodeのuser namespace、mount、security policyの対応を確認する**

**解説:** GoogleのKaniko repositoryはarchiveされています。任意で使うrootless BuildKitの設定には、別途検証したrunnerが必要です。`no-process-sandbox`はdaemon containerのprocess分離とcleanupを弱めます。また、registry cacheだけではすべてのcache mountが自動的に永続化されるわけではありません。

</details>
