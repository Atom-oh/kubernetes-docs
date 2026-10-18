# シークレット管理クイズ

> **最終更新**: 2026年9月13日

このクイズでは、Kubernetes Secret、AWS Secrets Manager、External Secrets Operator、暗号化について確認します。

## クイズ問題

### 1. Kubernetes Secretのデフォルトのencoding方式は何ですか？

A. AES-256暗号化
B. Base64 encoding
C. SHA-256 hash
D. RSA暗号化

<details>
<summary>解答を表示</summary>

**正解: B. Base64 encoding**

**解説:**
シリアライズされたSecretの`data` fieldはBase64で表現されます。encodingは暗号化ではありません。APIへのアクセス制御、保存データの保護、Secretを使うapplicationの保護が必要であり、外部storeを使ってもこれらの要件はなくなりません。

</details>

### 2. EKSのetcd暗号化には、どのAWS serviceが使われますか？

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>解答を表示</summary>

**正解: B. AWS KMS (Key Management Service)**

**解説:**
EKS 1.28以降では、AWS所有のkeyを使ったKMS envelope encryptionにより、Kubernetes APIのすべてのdataがデフォルトで暗号化されます。customer-managed keyも選択できます。これはself-managed API serverの設定とは異なります。EKSではdataが暗号化されないと決めつけたり、customer-managed keyが常に必要だと考えたりしないでください。

</details>

### 3. External Secrets OperatorでAWS Secrets Managerのsecretを参照するresourceはどれですか？

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. AとB、またはCとB

<details>
<summary>解答を表示</summary>

**正解: D. AとB、またはCとB**

**解説:**
SecretStore/ClusterSecretStoreはproviderへのaccessとidentityを設定し、ExternalSecretは外部の値を選択して、作成するtarget Secretを定義します。namespace内のSecretStoreが参照するServiceAccountも同じnamespaceに置きます。ClusterSecretStoreでは参照先namespaceを明示し、利用範囲の制限も設定してください。

</details>

### 4. PodでSecretを使う方法ではないものはどれですか？

A. environment variableとして注入する
B. volumeとしてmountする
C. image pull secretとして使う
D. ConfigMapに変換する

<details>
<summary>解答を表示</summary>

**正解: D. ConfigMapに変換する**

**解説:**
Podはkey参照、volume、imagePullSecretsを通じてSecretを利用できます。ConfigMapは別のresourceであり、Secretを保護する仕組みではありません。実行中containerのenvironment variableは更新されず、volumeの更新とapplicationによる再読み込みも別に扱う必要があります。

</details>

<span id="_5-which-aws-service-is-used-to-configure-automatic-rotation-in-aws-secrets-manager"></span>

### 5. AWS Secrets Managerで、custom Lambda-based rotation functionを実行するserviceはどれですか？

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>解答を表示</summary>

**正解: B. AWS Lambda**

**解説:**
custom Lambda-based rotation workflowでは、更新処理、権限、network accessを備えたLambda functionを使います。Secrets Managerにはmanaged rotationの統合機能もあり、すべてのrotationで利用者がLambdaを管理するわけではありません。ESOは値を同期しますが、database credential自体はrotationしません。

</details>

### 6. Sealed Secretsの主な特徴は何ですか？

A. etcd内で暗号化される
B. Gitに保存できる
C. AWS専用である
D. 自動rotationに対応する

<details>
<summary>解答を表示</summary>

**正解: B. Gitに保存できる**

**解説:**
Sealed Secretsは信頼されたcertificateを使って値を暗号化するため、Gitに保存できます。適切なprivate keyを持つ人は、復旧担当者として認可された人も含め、復号できます。metadataは見えるままです。keyを更新してもapplication credentialはrotationされず、Gitに残る過去の暗号文も消えません。

</details>

### 7. ExternalSecretのrefreshInterval fieldは何を設定しますか？

A. secretの有効期限
B. 外部secretとの同期間隔
C. cacheの保持期間
D. retry間隔

<details>
<summary>解答を表示</summary>

**正解: B. 外部secretとの同期間隔**

**解説:**
refreshPolicyがPeriodicで、refreshIntervalが正の値の場合、ESOは外部の値を定期的にreconcileします。これは同期完了までの時間を保証するものではなく、OnChangeやCreatedOnceとも動作が異なります。provider errorやbackoffへの対応と、application側での再読み込みも必要です。

</details>

### 8. Kubernetes Secretのimmutable fieldをtrueにすると、どうなりますか？

A. Secretを削除できなくなる
B. Secretのdataを変更できなくなる
C. Secretを読み取れなくなる
D. Secretを複製できなくなる

<details>
<summary>解答を表示</summary>

**正解: B. Secretのdataを変更できなくなる**

**解説:**
immutableにするとSecretのdataを変更できず、mutableな状態へ戻すこともできません。metadataは引き続き変更でき、Secretも削除できます。稼働中の依存先を置き換える場合は、新しい名前のSecretを作成し、管理された手順でrolloutしてください。

</details>

### 9. CSI Secrets Store Driverの主な機能は何ですか？

A. etcd内でsecretを暗号化する
B. 外部secretをvolumeとしてmountする
C. secretを自動生成する
D. secretをbackupする

<details>
<summary>解答を表示</summary>

**正解: B. 外部secretをvolumeとしてmountする**

**解説:**
Secrets Store CSI Driverと対応providerは、外部の値をfileとしてmountします。Kubernetes Secretへの同期は任意ですが、sync機能を有効にし、同期先Secretを使うmountも必要です。rotation、fileへの反映、applicationによる再読み込みはそれぞれ別の処理であり、platformによって対応状況も異なります。

</details>

### 10. IRSA (IAM Roles for Service Accounts) とExternal Secretsを使う利点は何ですか？

A. secretに速くaccessできる
B. PodにIAM credentialをhardcodeしなくてよい
C. secretが自動rotationされる
D. 無料で使える

<details>
<summary>解答を表示</summary>

**正解: B. PodにIAM credentialをhardcodeしなくてよい**

**解説:**
IRSAはprojected identity tokenを、厳密に指定したrole trust bindingを通じてtemporary AWS credentialと交換します。長期間有効なaccess keyのhardcodeを避けられますが、credentialそのものが不要になるわけではありません。ESOのPod Identityではcontrollerのidentityを使うため、serviceAccountRefによるimpersonationの代用にはなりません。

</details>

### 11. stringDataでSecret dataを定義する場合の特徴は何ですか？

A. 暗号化される
B. Base64 encodingが不要
C. より安全になる
D. 圧縮される

<details>
<summary>解答を表示</summary>

**正解: B. Base64 encodingが不要**

**解説:**
stringDataは、手動でBase64変換せずにplaintextを入力でき、その値はdataに統合されます。暗号化でも追加のaccess保護でもありません。APIから読み取ると、認可された利用者にはdataの表現が見えます。追跡対象のYAMLに実際の値を書かないようにし、server-side applyの制約にも注意してください。

</details>

### 12. 次のうち、secret管理のbest practiceではないものはどれですか？

A. etcd encryptionを有効にする
B. RBACでSecret accessを制限する
C. plaintext credentialをsource codeにcommitする
D. 外部secret管理systemを使う

<details>
<summary>解答を表示</summary>

**正解: C. plaintext credentialをsource codeにcommitする**

**解説:**
plaintext credentialや復号用private keyをcommitしてはいけません。暗号化済みのSOPS/SealedSecret artifactや、値を含まないESO referenceは、recipientをレビューし、keyを保護し、復旧テストとaccess controlを行ったうえでGitに保存できます。どのtoolも、それだけでsecurityやcomplianceを保証するものではありません。

</details>

---

[シークレット管理ガイド](../../security/05-secrets-management.md)
