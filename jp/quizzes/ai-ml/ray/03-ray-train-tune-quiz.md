# Ray Train と Ray Tune クイズ

このクイズでは、Ray Train（Trainer、ScalingConfig、checkpointing）、Ray Tune、および両者を組み合わせた分散 hyperparameter tuning についての理解を確認します。

## 多肢選択問題

1. Ray Train は、分散トレーニングスクリプトにおけるどの問題を主に解決しますか？
   - A) PyTorch などのトレーニングフレームワークを新しいトレーニング API に置き換える
   - B) worker process の起動、communication group の設定、checkpoint の調整に関する定型処理を担う
   - C) 実行開始前にトレーニングデータへ自動的にラベル付けする
   - D) トレーニングを完全に CPU 上で実行することで GPU を不要にする

<details>

<summary>回答を表示</summary>

**回答: B) worker process の起動、communication group の設定、checkpoint の調整に関する定型処理を担う**

**解説:**
Ray Train は Ray の task および actor primitives 上に構築され、分散トレーニングの定型処理、つまり割り当てられた resource ごとに 1 つの worker を起動し、worker 間 communication group（たとえば PyTorch DDP process group）を設定し、checkpointing を調整する処理を引き受けます。これにより、一般的な framework API 向けに書かれたトレーニングスクリプトは、作成者がその調整を手作業で実装しなくてもスケールできます。
</details>

2. 次のうち、Ray Train V2 を最も適切に説明しているものはどれですか？
   - A) 以前の Ray Train リリースとは無関係の、完全に別の製品
   - B) 既存の `ray.train.torch.TorchTrainer` import path の背後にある書き直された実装であり、以前の世代の trainer class が内部で動作していた方法を統合・簡素化したもの
   - C) CPU ベースのトレーニングのみをサポートする Ray Train のバージョン
   - D) Ray がドキュメントを提供しなくなった deprecated API

<details>

<summary>回答を表示</summary>

**回答: B) 既存の `ray.train.torch.TorchTrainer` import path の背後にある書き直された実装であり、以前の世代の trainer class が内部で動作していた方法を統合・簡素化したもの**

**解説:**
Ray Train の API surface は時代とともに進化してきましたが、ユーザー向けの import path（PyTorch の場合は `ray.train.torch.TorchTrainer`）は変更されていません。変更されたのはその背後の実装です。この書き直しがいつ default になったかという正確な version history は、推測せずに現在の Ray documentation で確認するのが最善です。
</details>

3. Ray Train における `ScalingConfig` の役割は何ですか？
   - A) 起動する worker 数と、それぞれが必要とする resources（GPU など）を指定する
   - B) トレーニング時に使用する neural network architecture を定義する
   - C) optimizer の learning rate schedule を設定する
   - D) Ray cluster が実行される cloud region を構成する

<details>

<summary>回答を表示</summary>

**回答: A) 起動する worker 数と、それぞれが必要とする resources（GPU など）を指定する**

**解説:**
`ScalingConfig` は、起動する worker 数と、それぞれに GPU が必要かどうかを Trainer に伝えます。Trainer はこれを使用して、他の Ray task や actor と同様に、基盤となる Ray cluster に対応する resources を要求します。
</details>

4. worker failure 後の recovery を可能にする以外に、Ray Train の checkpointing にはどのような目的がありますか？
   - A) storage を節約するためにトレーニング dataset を圧縮する
   - B) hyperparameter-tuning の判断や model registration など、workflow の後続 step にトレーニング済み model を引き渡す
   - C) model を production serving endpoint に自動的に deploy する
   - D) ScalingConfig を不要にする

<details>

<summary>回答を表示</summary>

**回答: B) hyperparameter-tuning の判断や model registration など、workflow の後続 step にトレーニング済み model を引き渡す**

**解説:**
report された checkpoint は、トレーニングを再開するのに十分な state（通常は model weights と optimizer state）を取得しますが、次に続く処理への handoff point としても機能します。たとえば tuning の判断や、結果を model version として登録する処理です。これは、この documentation site の他の箇所で扱う model registry pattern と概念的に似ています。
</details>

5. Ray Tune は何をしますか？
   - A) cluster 全体で多数の training trial を並列実行し、pluggable search algorithm を用いて次に試す hyperparameter combination を決定する
   - B) 一度に 1 つの hyperparameter だけを順次 tuning する
   - C) あらゆる分散トレーニング workload で Ray Train を完全に置き換える
   - D) Ray の core primitives とは無関係な Kubernetes CRD ベースの controller である

<details>

<summary>回答を表示</summary>

**回答: A) cluster 全体で多数の training trial を並列実行し、pluggable search algorithm を用いて次に試す hyperparameter combination を決定する**

**解説:**
Ray Tune は Ray 上に構築された hyperparameter tuning library です。各 trial は 1 つの hyperparameter combination でトレーニングし、結果を report します。Tune の search algorithm はその結果を利用して、次に試す内容を決定します。これは Kubeflow ecosystem で Katib が提供するものと概念的には並行していますが、別個の Kubernetes CRD ベース system ではなく Ray native です。
</details>

6. 分散トレーニングを必要とする model に対して、Ray Tune は一般に Ray Train とどのように組み合わせられますか？
   - A) Tune と Train は一緒に使用できないため、team はどちらか一方を選択する必要がある
   - B) Tune は探索対象の trainable として Ray Train の `Trainer` を wrap するため、各 trial はそれぞれ独自の分散 Ray Train run になる
   - C) Ray Train が最初に完了まで実行され、その後で初めて Ray Tune が別の cluster 上で開始される
   - D) Tune が Trainer の ScalingConfig を独自の resource model で置き換える

<details>

<summary>回答を表示</summary>

**回答: B) Tune は探索対象の trainable として Ray Train の `Trainer` を wrap するため、各 trial はそれぞれ独自の分散 Ray Train run になる**

**解説:**
一般的な pattern では、Tune に trainable として Ray Train の `Trainer` を渡します。その場合、各 hyperparameter trial はそれ自体が分散 Ray Train run となり、複数の GPU または node にまたがる可能性があります。これは、1 つの trial が妥当な時間内に完了するために分散トレーニングを必要とする場合に有用です。
</details>

7. EKS 上の KubeRay-managed autoscaler が、Ray Train または Ray Tune job の実際の resource demand に反応するのはなぜですか？
   - A) Ray Train と Ray Tune は、他の Ray workload と同様に、Ray の通常の task/actor resource-request mechanism を通じて CPU と GPU を要求するため
   - B) Ray Train と Ray Tune は Ray の scheduler を迂回して Kubernetes API server と直接通信するため
   - C) job を実行する前に、cluster を常に固定サイズで provision する必要があるため
   - D) Karpenter がトレーニング process 自体の内部で GPU utilization を監視するため

<details>

<summary>回答を表示</summary>

**回答: A) Ray Train と Ray Tune は、他の Ray workload と同様に、Ray の通常の task/actor resource-request mechanism を通じて CPU と GPU を要求するため**

**解説:**
どちらの library も、トレーニングや tuning に固有の別経路を使わず、Ray の通常の task/actor resource-request mechanism を通じて resources を要求します。これにより、Part 2 で扱った autoscaler は実際の demand に反応できます。つまり、Tune sweep がより多くの concurrent trial を起動すると追加の worker node を要求し、trial が終了すると scale back down します。固定サイズの cluster を事前に用意する必要はありません。
</details>

8. EKS 上で Ray Train run の分散 worker に必要な co-scheduling により、どのような実用上の問題が生じる可能性がありますか？
   - A) ない。Ray Train worker が同時に開始する必要はない
   - B) autoscaler が妥当な時間内に要求されたすべての worker を provision できない場合、最後の数個の GPU worker が起動するのを待って training run が停止する可能性がある
   - C) Co-scheduling が問題になるのは Ray Tune のみであり、Ray Train では決して問題にならない
   - D) checkpointing が co-scheduling の遅延を自動的に解決する

<details>

<summary>回答を表示</summary>

**回答: B) autoscaler が妥当な時間内に要求されたすべての worker を provision できない場合、最後の数個の GPU worker が起動するのを待って training run が停止する可能性がある**

**解説:**
1 つの Ray Train run に含まれる worker は通常、co-schedule される必要があります。つまり、communication group を確立する前に、すべてが起動し、割り当てられた GPU を保持している必要があります。これは、この documentation site の他の箇所で説明する gang-scheduling の必要性と似ています。GPU node pool の provisioning lead time は、CPU node より長く予測しにくいことが多いため、training job の実際の開始時刻は、要求されたすべての worker をどれだけ速く co-schedule できるかに依存します。
</details>

## 短答問題

9. Ray Train の `Trainer` と `ScalingConfig` がそれぞれ何を行うか、および両者がどのように連携して分散トレーニング job を実行するかを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Trainer（`TorchTrainer` など）は、model の構築、batch の反復処理、loss の計算、optimizer の step 実行といった通常の model-training logic を含む、ユーザー提供の training function を wrap します。Trainer は、基盤となる framework の data-parallel training が期待する分散 process group（たとえば PyTorch DDP process group）内で、その function を worker ごとに 1 回起動する役割を担います。そのため、training function 自体がこの調整を手作業で設定する必要はありません。

`ScalingConfig` は、起動する worker 数と、GPU が必要かどうかなど各 worker が必要とする resources を Trainer に伝えます。Trainer は `ScalingConfig` を使用して、Ray の通常の task/actor resource-request mechanism を通じ、基盤となる Ray cluster に対応する resources を要求します。Trainer は training logic と調整を提供し、`ScalingConfig` は Trainer がその logic をスケールさせる resource shape を提供します。
</details>

10. Ray Tune と Ray Train を組み合わせることが有用な理由、およびその組み合わせによる resource request が EKS 上の cluster autoscaling とどのように連携するかを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
一部の model はトレーニングの cost が高く、1 つの hyperparameter trial 自体が、妥当な時間内に完了するために分散（multi-GPU または multi-node）トレーニングを必要とします。2 つの library を組み合わせなければ、team は分散トレーニング job に対して hyperparameter を serial に tuning するか、search phase 中は分散トレーニングを諦める必要があります。Ray Tune は Ray Train の `Trainer` を trainable として wrap できるため、各 trial は独自の分散 Ray Train run になり、Tune は次に試す hyperparameter combination を決定しながら、そのような run を複数同時に実行できます。

すべての trial のすべての worker は、依然として Ray の通常の task/actor resource-request mechanism を通じて CPU と GPU を要求するため、EKS 上の KubeRay-managed autoscaler は、単一の事前宣言された shape ではなく、アクティブなすべての trial を合わせた real-time resource demand を認識します。Tune sweep がより多くの concurrent trial を起動すると追加の worker node を provision でき、trial の終了に応じて scale back down できます。そのため、最大規模の sweep に合わせて cluster を事前にサイズ設定する必要はありません。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/03-ray-train-tune.md) | [次のクイズ: Ray Serve](./04-ray-serve-quiz.md)
