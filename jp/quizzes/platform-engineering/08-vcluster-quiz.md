# vCluster クイズ

1. vCluster は従来の Namespace ベースのマルチテナンシーと比べて、どのように優れていますか？
   - A) vCluster は追加の物理 cluster を作成する
   - B) host cluster のリソースを共有しながら、各 tenant に完全な Kubernetes API を提供する
   - C) vCluster は network を完全に分離する
   - D) vCluster には dedicated node が必要である

<details>
<summary>答えを表示</summary>

**答え: B) host cluster のリソースを共有しながら、各 tenant に完全な Kubernetes API を提供する**

**説明:**
vCluster は virtual control plane を通じて、各 tenant に独立した Kubernetes API（CRD のインストール、RBAC 管理、Namespace 作成など）を提供します。実際の workload は host cluster 上で実行されるため、追加の物理 cluster のコストなしに強力な分離を実現します。

</details>

---

2. vCluster の Syncer component の中核的な役割は何ですか？
   - A) virtual cluster DNS を管理する
   - B) virtual cluster のリソースを host cluster に同期し、host の状態を反映する
   - C) virtual cluster 間の network を接続する
   - D) virtual cluster の log を収集する

<details>
<summary>答えを表示</summary>

**答え: B) virtual cluster のリソースを host cluster に同期し、host の状態を反映する**

**説明:**
Syncer は vCluster の中核 component であり、virtual cluster 内で作成されたリソース（Pod、Service、ConfigMap など）を host cluster 上の実際のリソースに変換します。また、host の情報（Node、StorageClass など）を virtual cluster に同期し返し、双方向のリソース管理を行います。

</details>

---

3. PR ごとの preview environment に vCluster を使用する利点は何ですか？
   - A) PR merge なしで code を production に deploy する
   - B) integration testing のために、PR ごとに分離された Kubernetes environment をすばやく作成・削除できる
   - C) PR reviewer に cluster admin 権限を付与する
   - D) CI pipeline の実行時間を短縮する

<details>
<summary>答えを表示</summary>

**答え: B) integration testing のために、PR ごとに分離された Kubernetes environment をすばやく作成・削除できる**

**説明:**
vCluster は 30 秒未満で作成できるため、CI/CD pipeline で PR ごとに分離された Kubernetes environment を provision できます。PR が merge または close されると vCluster は削除され、リソースを回収します。これにより、各 PR の変更を独立した environment で integration testing できます。

</details>

---

4. vCluster の Sleep Mode feature の目的は何ですか？
   - A) virtual cluster の security を強化する
   - B) 使用されていない virtual cluster のリソースを解放して cost を削減する
   - C) virtual cluster data を backup する
   - D) virtual cluster の performance を最適化する

<details>
<summary>答えを表示</summary>

**答え: B) 使用されていない virtual cluster のリソースを解放して cost を削減する**

**説明:**
Sleep Mode は、指定された期間 inactive だった vCluster の workload を自動的に停止します。API request が届くと、vCluster は自動的に wake up します。これにより、夜間や週末に使用されない dev/test vCluster の cost を大幅に削減できます。

</details>

---

5. virtual cluster で host cluster の StorageClass を使用するにはどうしますか？
   - A) virtual cluster 内で StorageClass を再作成する
   - B) syncFromHost settings を使用して host の StorageClass を virtual cluster に同期する
   - C) PV を手動で mount する
   - D) virtual cluster に CSI driver を個別に install する

<details>
<summary>答えを表示</summary>

**答え: B) syncFromHost settings を使用して host の StorageClass を virtual cluster に同期する**

**説明:**
vCluster の `syncFromHost` configuration は、StorageClass、IngressClass、Node のような host cluster のリソースを同期し、virtual cluster で見えるようにします。virtual cluster 内の PVC は host cluster の StorageClass を使用して、実際の PV を provision します。

</details>

---

6. Backstage + vCluster integration における developer self-service workflow はどのように機能しますか？
   - A) developer が kubectl で vCluster を直接作成する
   - B) Backstage Template が vCluster request を生成 → GitOps repo に push → ArgoCD が同期して vCluster を provision する
   - C) Backstage が Kubernetes API を直接呼び出して vCluster を作成する
   - D) admin が手動で vCluster を作成し、developer に割り当てる

<details>
<summary>答えを表示</summary>

**答え: B) Backstage Template が vCluster request を生成 → GitOps repo に push → ArgoCD が同期して vCluster を provision する**

**説明:**
developer が Backstage Template に parameter（environment name、resource size など）を入力すると、Template は vCluster Helm Release manifest を生成し、それらを GitOps repository に push します。ArgoCD は変更を検出して cluster に同期し、vCluster を自動的に provision します。

</details>

---

7. vCluster の security isolation における NetworkPolicy の役割は何ですか？
   - A) virtual cluster 間の CPU 使用量を制限する
   - B) network isolation によって、virtual cluster の Pod が他の vCluster の Pod や host cluster のリソースに access するのを防ぐ
   - C) virtual cluster の Ingress traffic を暗号化する
   - D) DNS query を filter する

<details>
<summary>答えを表示</summary>

**答え: B) network isolation によって、virtual cluster の Pod が他の vCluster の Pod や host cluster のリソースに access するのを防ぐ**

**説明:**
vCluster の Pod は host cluster 上で実行されるため、NetworkPolicy がない場合、他の vCluster の Pod に network access できます。各 vCluster の namespace に NetworkPolicy を適用し、namespace 内通信のみを許可して外部 access を block することで、強力な network isolation を実現します。

</details>

---

8. 物理 cluster ではなく vCluster を選択すべきなのはどのような場合ですか？
   - A) 完全な hardware isolation が必要な場合
   - B) 高速な provisioning、cost efficiency、CRD isolation が必要だが、完全な node isolation は不要な場合
   - C) regulatory requirement によって別々の AWS account が必須の場合
   - D) GPU workload を実行する場合

<details>
<summary>答えを表示</summary>

**答え: B) 高速な provisioning、cost efficiency、CRD isolation が必要だが、完全な node isolation は不要な場合**

**説明:**
vCluster は 30 秒未満での作成、host cluster リソース共有による cost efficiency、CRD/RBAC/Namespace isolation を提供します。dev/test environment、CI/CD の ephemeral environment、training environment に最適です。regulatory compliance、完全な hardware isolation、または dedicated network isolation が必要な production workload には、物理 cluster の方が適しています。

</details>
