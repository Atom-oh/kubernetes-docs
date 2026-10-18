# Landing Zone、OU、組織制御クイズ

> このクイズでは、[Landing Zone、OU、組織制御](../../governance/01-landing-zone-and-ou.md)の理解度を確認します。

---

1. Control Tower 4.0 で IdentityCenterBaseline を有効にする前に、何が必要ですか？
   - A) ベースラインは不要
   - B) CentralSecurityRolesBaseline と、その前提条件である CentralConfigBaseline
   - C) BackupCentralVaultBaseline
   - D) Identity Center 自体が、すべての環境で Config を必要とする

<details>
<summary>回答を表示</summary>

**回答: B) CentralSecurityRolesBaseline と、その前提条件である CentralConfigBaseline**

**解説:**
これは Control Tower が管理するベースラインの依存関係であり、Identity Center サービスに共通する Config の前提条件ではありません。

</details>

---

2. Control Tower 4.0 の Security OU を正しく説明しているのはどれですか？
   - A) すべての OU が Security OU である
   - B) サービス統合用の Account を含む OU が Security OU として指定される
   - C) Security OU は廃止された
   - D) そこにあるすべての一般 Account に、すべてのベースラインが適用される

<details>
<summary>回答を表示</summary>

**回答: B) サービス統合用の Account を含む OU が Security OU として指定される**

**解説:**
統合用 Account は共通の親 OU を持ち、landing zone を通じて管理されます。AWSControlTowerBaseline/ConfigBaseline はその Security OU には適用されません。一般的な運用 Account を別の場所に配置するかどうかは、設計上の選択です。

</details>

---

3. 階層化された SCP のセットによって、直接アタッチのクォータを節約できるのはなぜですか？
   - A) ドキュメントのサイズ上限がなくなる
   - B) 継承されたポリシーは、子 OU の直接アタッチ数を消費しない
   - C) 子 OU の Allow は、親の Deny を上書きする
   - D) Root のクォータは無制限である

<details>
<summary>回答を表示</summary>

**回答: B) 継承されたポリシーは、子 OU の直接アタッチ数を消費しない**

**解説:**
直接アタッチ数の上限は、エンティティごとに SCP 10 個です。継承はこの枠を消費しませんが、親ポリシーによる実効的な制約は引き続き適用されます。

</details>

---

4. RCP のアタッチと継承について、正しく説明しているのはどれですか？
   - A) RCP は権限を直接付与する
   - B) RCP は継承できない
   - C) RCPFullAWSAccess が5つの枠のうち1つを使うため、残りの直接アタッチ枠と継承を合わせて設計する
   - D) RCP のサイズ上限は SCP と同じである

<details>
<summary>回答を表示</summary>

**回答: C) RCPFullAWSAccess が5つの枠のうち1つを使うため、残りの直接アタッチ枠と継承を合わせて設計する**

**解説:**
直接アタッチ枠は4つ残り、ドキュメントのサイズ上限は5,120文字です。この枠の範囲内であっても、階層化された継承は禁止されません。サポート対象のリソースとプリンシパルの例外を確認してください。

</details>
