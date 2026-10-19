# 6. ネットワーク自動化と最終評価

> **最終更新日**: 2026年9月15日

**前提条件:** 第1、2、4章で共通の観測スキルを学びます。EVPN／ファブリックの総合演習には第3章を、クラウドの総合演習には第5章を追加します。Linux ホストの総合演習には、第4章の範囲を限定した実験を使います。バリデーターの演習には Python 3.9 以降と、自分が所有する新しいディレクトリだけが必要です。

**目標:** 意図と観測結果を区別し、正常、禁止、失敗、復旧の状態を再現可能な形で提出します。自動化によって、根拠がない状態を成功として扱ってはいけません。

## 1. 変更前に意図を確認する {#intent}

| 領域 | 変更前に定義する内容 | 変更後に検証する内容 |
|---|---|---|
| 到達性 | どの利用者が、どのサービスにアクセスするか | 実際の応答と観測地点 |
| 分離 | 禁止するフロー | プローブと合わせたポリシーの根拠 |
| ルーティングポリシー | どのプレフィックスを、どのピア／VRF に広告するか | 同じスコープでの経路広告、選択、転送の状態 |
| 耐障害性 | 単一障害で維持すべきもの | サービスの継続性と収束／復旧にかかる時間 |
| 運用上の境界 | 管理アクセス、変更範囲、停止条件 | 範囲外の変更がないことと、状態の復元 |

新しい出力に合わせるためだけに期待値を変更すると、リグレッションを隠す可能性があります。最初に意図を確認し、その改訂番号／ハッシュを記録してください。観測アダプターは実際の出力を正規化する際、単位、スコープ、時刻を保持します。

例えば、FRR ピアが広告する経路、Linux ホストの FIB 全体、TGW ルートテーブルは、それぞれ異なるデータセットです。以下のプレフィックス契約で比較するのは、**指定したピアに広告された経路の集合**です。優先順位、ECMP 数、FIB への登録、実際の転送には別の根拠が必要です。

## 2. 小さなバリデーター演習 {#record-validator}

以下のデータは**合成データ**です。ネットワークの設定やパケット送信は行いません。バリデーターが確認するのは、与えられた意図と記録の整合性です。PCAP やカウンターの真正性を証明するものではありません。

ラボ VM または手元の学習用端末に、新しいディレクトリを作成します。

```bash
EVIDENCE_DIR=$(mktemp -d /tmp/network-evidence.XXXXXX)
printf '%s\n' "$EVIDENCE_DIR"
```

この JSON を `intent.json` として、そのディレクトリに保存します。実際の自動化では、これを別途レビューする入力データとして保持します。

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "maximum_window_seconds": 60,
  "exported_prefixes": ["203.0.113.0/24"],
  "flows": {"a-to-web": "allow", "b-to-a": "deny"}
}
```

以下の内容を `observations.json` として保存します。アドレス、時刻、アーティファクト名は例示です。

```json
{
  "schema": 1,
  "scenario": "tenant-isolation",
  "phase": "steady",
  "route_scope": "r2:export-to-r1",
  "evidence_kind": "synthetic",
  "window": {"start": "2026-09-15T00:00:00Z", "end": "2026-09-15T00:00:10Z"},
  "exported_prefixes": ["203.0.113.0/24"],
  "route_artifact": "synthetic:advertised-routes",
  "flows": {
    "a-to-web": {
      "verdict": "allow",
      "artifacts": {"probe": "synthetic:http-response"}
    },
    "b-to-a": {
      "verdict": "deny",
      "artifacts": {"probe": "synthetic:blocked-probe", "policy": "synthetic:policy-decision"}
    }
  }
}
```

以下の Python コードを同じディレクトリの `check_record.py` として保存します。

```python
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def prefixes(values):
    require(isinstance(values, list), "prefixes must be a list")
    return {str(ipaddress.ip_network(value, strict=True)) for value in values}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp needs a timezone")
    return parsed


require(len(sys.argv) == 3, "usage: check_record.py intent.json observations.json")
intent, seen = load(sys.argv[1]), load(sys.argv[2])
for record in (intent, seen):
    require(type(record.get("schema")) is int and record["schema"] == 1, "schema")
for key in ("scenario", "phase", "route_scope"):
    require(intent[key] == seen[key], "scope mismatch: " + key)
require(seen["evidence_kind"] in {"synthetic", "supplied", "measured"}, "evidence kind")
duration = (timestamp(seen["window"]["end"]) - timestamp(seen["window"]["start"])).total_seconds()
require(0 < duration <= intent["maximum_window_seconds"], "invalid observation window")
require(prefixes(intent["exported_prefixes"]), "empty intended prefix scope")
require(prefixes(seen["exported_prefixes"]) == prefixes(intent["exported_prefixes"]), "prefix mismatch")
require(isinstance(seen.get("route_artifact"), str) and seen["route_artifact"].strip(), "route evidence missing")
require(intent["flows"] and set(intent["flows"]) == set(seen["flows"]), "flow coverage mismatch")
for name, wanted in intent["flows"].items():
    require(wanted in {"allow", "deny"}, "unsupported intent")
    actual = seen["flows"][name]
    require(actual["verdict"] == wanted, "flow mismatch: " + name)
    needed = {"probe"} if wanted == "allow" else {"probe", "policy"}
    artifacts = actual["artifacts"]
    require(all(isinstance(artifacts.get(k), str) and artifacts[k].strip() for k in needed),
            "evidence missing: " + name)
print("CONSISTENT_RECORD kind=" + seen["evidence_kind"] + "; live behavior not attested")
```

実行します。

```bash
python3 "${EVIDENCE_DIR:?}/check_record.py" \
  "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json"
```

期待される出力は `CONSISTENT_RECORD kind=synthetic; live behavior not attested` です。これは、この記録の必須条件が合格したことを意味します。ネットワーク通信の成功や、本番運用への変更が承認されたことを意味するものではありません。Python の最適化によって `assert` 文が除去されてもチェックが有効であるよう、明示的な例外処理を使います。

### 失敗するはずの入力

元ファイルは保持したまま、`observations-bad.json` のコピーを作成し、**一度に1項目ずつ**変更します。そのコピーを最後の引数として同じコマンドを実行します。

| 変更 | 期待される結果 |
|---|---|
| `b-to-a` の観測を削除する | `flow coverage mismatch` |
| `b-to-a.verdict` を `unknown` または `allow` にする | `flow mismatch` |
| 禁止フローの `policy` アーティファクトを削除する | `evidence missing` |
| 広告するプレフィックスに `0.0.0.0/0` を追加するか、リストを空にする | `prefix mismatch` |
| 終了時刻を開始時刻より前にする | `invalid observation window` |
| `phase` を変更する | `scope mismatch` |

空の出力やタイムアウトを `deny` に正規化しないでください。禁止された結果とするには、プローブに紐付くポリシー／強制適用の根拠が必要です。アーティファクトに名前を付けただけでは、ファイルが存在することや、正しい観測地点で収集されたことの証明になりません。

この演習を実際のコレクターに拡張する場合は、元の根拠と照合してファイルの存在、ハッシュ、時間範囲、コレクター、デバイス／アカウントの ID を確認してください。さらに、パス属性やエンドポイントごとの準備状況など、集合に正規化すると失われる属性を別途検証します。

## 3. 変更のパイプラインを設計する {#pipeline}

各段階の入力、出力、失敗時の責任者を定義します。

| 段階 | 確認内容 | 次へ渡す結果 |
|---|---|---|
| 意図のレビュー | 許可／禁止するフロー、ルート、管理アクセス、障害の境界 | レビュー済みの意図の改訂版 |
| 静的検証 | 構文、サポート対象の機能、アドレスの重複、ポリシーの範囲 | 正確なツール／プロバイダーのバージョンに対する結果 |
| 変更プレビュー | 対象、影響、想定差分、復旧可能性 | 人がレビューできる変更計画 |
| ラボへの適用 | 1つの変更、限定した時間／リソース、維持された管理アクセス | 変更前／変更後の状態と実行記録 |
| 動作チェック | 許可、禁止、失敗、復旧、根拠の欠落 | 元データと関連付けた構造化結果 |
| 運用上の判断 | 検証範囲、不明点、ロールアウト／ロールバック条件 | 別途定められた運用手順による承認または拒否 |

このコースでは、本番環境への変更を自動承認するパイプラインは提供しません。復旧コマンドを事前に読み、管理接続に影響する可能性がある場合は、コンソールなど独立した復旧アクセスを確保してください。

## 4. 総合演習を選ぶ {#capstones}

### A. ルーティング／ファブリック

[第2章](02-routing-policy-convergence.md)または[第3章](03-datacenter-evpn.md)で、準備済みのラボを1つ選びます。

1. 特定のピア／VRF に許可するプレフィックスと、禁止するルート／フローを定義します。
2. 正常時の経路広告、選択、FIB、サービスプローブを記録します。
3. その章から、復旧可能なポリシー／経路障害を1つ選びます。
4. コントロールプレーンの変更時間と、実際のサービス復旧時間を分けます。
5. 元の設定を復元し、到達性と分離の両方を再確認します。

セッションが Established になるまでの時間を、サービス収束時間の代わりに使ってはいけません。異なるデバイスの時計を比較する場合は、時刻同期／不確かさを記録するか、1つの観測者による時刻軸を使います。

### B. Linux／クラウド／SRE

[第4章](04-linux-performance.md)の範囲を限定したホスト実験、または承認済みの[第5章](05-cloud-cni-design.md)のクラウド根拠を選びます。

1. 順方向／戻り方向の経路と、少なくとも2つの観測地点を示します。
2. 遅延、損失、キュー、ポリシーに関する仮説を1つ選び、仮説を否定する条件を定義します。
3. 観測結果を、発生元／名前空間、時刻、単位に関連付けます。
4. 実験を行った場合は完全に元へ戻し、同じチェックを再実行します。
5. 設計または提供済みの根拠だけを分析した場合は、それに応じて結論の範囲を限定します。

機器やアカウントがない場合は、設計または提供済み根拠を分析して提出します。自分で範囲を限定した実験から元データと復旧の根拠を提示できる場合に限り、**実践的な実行を完了**とします。

## 5. 評価 {#assessment}

各項目を `met / unmet / unobserved` で評価します。必須の根拠が欠けている状態を、集計スコアに隠してはいけません。

| 項目 | 合格基準 |
|---|---|
| 範囲／再現性 | トポロジー、環境、権限、バージョン／改訂版、入力、時刻を再現できる |
| プロトコルの推論 | パケット、ルート、アプリケーションの関係を説明し、少なくとも1つの仮説を否定している |
| 肯定／否定チェック | 許可されるトラフィックと分離を別々に評価し、不在を成功として数えていない |
| 失敗／復旧 | 単一変更の影響と復旧後の状態を、同じ基準で確認している |
| 自動化の品質 | 範囲違い、欠落、不明点、意図との不一致を拒否し、元データを追跡できる |
| 誠実な結論 | 測定済み、提供済み、合成、設計、未観測の根拠を区別している |

必須項目が未達の場合は、該当する章に戻ります。未観測の項目について、実環境の検証が完了したと宣言しないでください。レビュー担当者が同じ根拠から結論を再現できる必要があります。

## クリーンアップと学習の続行

バリデーター演習で作成したファイルを削除する前に、内容を確認してください。

```bash
ls -la -- "${EVIDENCE_DIR:?}"
rm -- "${EVIDENCE_DIR:?}/intent.json" "${EVIDENCE_DIR:?}/observations.json" \
  "${EVIDENCE_DIR:?}/check_record.py"
```

コピーを作った場合は、**コピーだと確認できたファイルだけ**を削除してから、`rmdir -- "${EVIDENCE_DIR:?}"` を実行します。実験で作成した元データには別途承認済みの保持ポリシーが適用されます。この一時的な合成データの例とは別のものです。

ポートフォリオで最も弱い領域の実験を追加します: [プロトコル](01-protocol-projects.md)、[ルーティング](02-routing-policy-convergence.md)、[EVPN](03-datacenter-evpn.md)、[Linux パフォーマンス](04-linux-performance.md)、または[クラウド設計](05-cloud-cni-design.md)。

参考資料: [Python JSON](https://docs.python.org/3/library/json.html)、[ipaddress](https://docs.python.org/3/library/ipaddress.html)、[datetime](https://docs.python.org/3/library/datetime.html)。

[前へ: クラウド／CNI](05-cloud-cni-design.md) · [クイズ](../../quizzes/networking/expert/06-automation-capstone-quiz.md) · [コース](README.md)
