# 8. 総合演習: Web Service の障害から Container、Cloud へ

> **学習環境の基準**: Ubuntu Server 24.04 LTS。代替として Rocky Linux 9 の手順も示します。
>
> **最終更新**: 2026年9月15日

**前提条件:** [レッスン1～7](README.md#course-map)、両 VM の lab address、検証済み SSH key login、lab client から許可する TCP 8000 rule。最初にレッスン7の web server を停止します。

**学習目標:** 小さな web service の正常状態を記録し、異なる層の障害を1つずつ再現、診断、復旧します。その後、同じ問いを Docker と Kubernetes に適用します。所要時間の目安は約3～4時間です。

## 課題と正常時の基準状態 {#baseline}

課題は「client から server の `/health.txt` を読む」です。Web framework や cloud account は必要ありません。

**Server console A:**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

5分の制限時間が切れたら同じ command で再起動します。意図して server を停止した状態を network 障害と誤認しないよう console を確認してください。この directory には演習用 file だけを置いてください。

**Server console B:**

```bash
ip -br address
ip route get 192.0.2.10
sudo ss -ltnp 'sport = :8000'
```

**Client:**

```bash
ip route get 192.0.2.20
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve lesson.test:8000:192.0.2.20 \
  -i http://lesson.test:8000/health.txt
```

どちらの route も lab NIC を使い、listener は `192.0.2.20:8000`、両方の request は HTTP 200 を返し、body に `healthy` が含まれる必要があります。`--resolve` は、この curl 呼び出しに限った **host／port の address mapping**を指定します。System DNS やほかの application は変更しません。

基準状態が失敗する場合は、先にレッスン4～6の設定と rule を確認してください。正常に動作するまでは、新しい障害を起こさないでください。

## 障害を1つずつ再現する {#faults}

各実験は正常な基準状態から始め、復旧後に正常な request を繰り返します。通常の `curl` request は HTTP 404 でも exit status 0 になる場合があるため、HTTP status line を確認してください。HTTP error を失敗として扱う必要のある automation では、`--fail-with-body` のような対応 option を明示できます。

### A. 名前解決と IP 接続を分ける

Client から `--resolve` なしで request します。

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

この lab で `lesson.test` を別途登録していなければ、通常は名前解決に失敗します。すでに `/etc/hosts` や local DNS に設定している場合は、失敗を期待せず実際の mapping を記録してください。同じ環境で先ほどの IP 直指定と `--resolve` を使った request が成功するかも確認します。

**診断:** IP request が動作し、名前解決だけ失敗する場合は、まず名前解決を調べます。これだけで特定の DNS server の障害や、internet 全体の停止が確定するわけではありません。**復旧:** 正常時の request と同じ `--resolve` mapping を再利用します。この一時的な実験に system resolver の上書きは不要です。

### B. Application の path error

Client から存在しない file を request します。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**診断:** HTTP 404 の受信は、request に対して server が HTTP response を返したことを示します。すべての routing と firewall 設定を初期化する必要はありません。Request path と server log を比較します。**復旧:** 再び `/health.txt` を request します。

### C. 誤った listen address

Server console A で Ctrl+C を押して server を停止します。**同じ terminal**で、bind address だけを変更します。

```bash
timeout 300 python3 -m http.server 8000 \
  --bind 127.0.0.1 --directory "$LAB_WEB"
```

Server console B:

```bash
sudo ss -ltnp 'sport = :8000'
curl --disable --noproxy '*' --max-time 5 \
  -i http://127.0.0.1:8000/health.txt
```

Client の元の `192.0.2.20:8000` request が失敗し、server 自身からの loopback request は成功することを確認します。Firewall の挙動によって拒否と timeout のどちらに見えるかも変わります。`ss` が示す `127.0.0.1` listener が重要な証拠です。

**復旧:** Console A で Ctrl+C を押し、`--bind 192.0.2.20` を指定した正常時の command で再起動します。一方の VM の loopback address は、もう一方の VM の loopback ではありません。

### D. Firewall 仮説を証拠で検証する {#firewall-fault}

レッスン6で選択した manager **だけ**を、server の hypervisor console から使います。この障害では、演習用の TCP 8000 allow だけを削除します。TCP 22 allow、lab deny、既定 policy、zone／profile の割り当て、management NIC は維持します。この試験と競合しないよう、任意の Fail2ban 実験を先に完了してください。

**Server console B、通常 user:** Hypervisor に記録した MAC address を使い、両 NIC を識別し直します。レッスン6の変数が残っているとは仮定しません。

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

Lab NIC に `.20/24` が設定され、NIC 名が異なり、management 側が変更されていないこと、正常な `.20:8000` listener があることを確認します。以下の指示に従い、現在の rule を記録してください。Server timer が切れていた場合は、server console A で既存 directory を使い `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"` **だけ**を再起動します。停止した server の障害を同時に混ぜないでください。

**Client、通常 user:** 記録からレッスン5の既存 key directory と server の通常 account を確認します。新しい key を作成したり、検証済み host record を迂回したりしないでください。

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

Client terminal でこの短い shell function を一度定義します。`check_lab_ssh` を実行すると**新規の** SSH 接続を行い、remote account／connection を表示して client に戻ります。File や service は作成しません。

```bash
check_lab_ssh() {
  ssh -F /dev/null -b 192.0.2.10 \
    -i "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
    -o "UserKnownHostsFile=${SSH_LAB_DIR:?missing key directory}/known_hosts" \
    -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
    -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
    -o BatchMode=no -o ConnectTimeout=5 \
    "${SERVER_USER:?missing account}@192.0.2.20" \
    'whoami; printf "%s\n" "$SSH_CONNECTION"'
}
check_lab_ssh
```

Private key の**passphrase prompt は出ても問題ありません**。Unlocked agent は必須ではありません。Remote account password への fallback は無効です。`-F /dev/null` は無関係な client 設定を避け、multiplexing の無効化は以前に認証した接続の再利用を防ぎます。通常 account から `.10` → `.20` の port 22 に接続したことを確認します。この**障害を起こす前**の確認または正常な HTTP が失敗したら、rule を変更せず中止してください。別途必要な management SSH 経路も維持／再確認します。

#### UFW: 保存済み／適用済み HTTP allow だけを変更する

**Ubuntu server console B、sudo:**

```bash
sudo ufw status numbered
sudo ufw show added
```

UFW が有効で、レッスン6の演習用 rule が次の順序で存在する場合だけ進みます。**1: `.10`→`.20` TCP 22 allow、`LAB_IF` 上。2: 独立した TCP 8000 allow。3: 同じ interface／宛先への TCP `22,8000` deny。** Full specification を記録してください。古い22／8000の一括 allow が残っている、または順序が異なる場合は、まずレッスン6の設定を整理してください。Multiport rule から片方の port を消すことは、その設定の逆操作ではありません。

HTTP だけを削除します。

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

TCP 22 allow が先頭に残り、lab deny が2番目になったことを確認します。これは保存済み／適用済み UFW state の両方を変更します。その2つの rule と既定 policy には手を加えません。次に、以下の**障害中の確認**を実施します。

**同じ Ubuntu console から復旧:** Deny が引き続き2番目であることを確認し、HTTP rule を2番目、つまりその deny より**前に**挿入します。

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

元の SSH allow → HTTP allow → lab deny の順序と、元の送信元／interface／宛先 scope が戻ることを確認してください。Deny より後に allow を追加しても HTTP は許可されません。削除の逆操作には元の配置も含まれます。別の rule 変更で位置がずれていたら、古い番号を使わず、記録した順序を再確立してから続けてください。復旧後の確認へ進みます。

#### firewalld: 保存済み policy を保ち、runtime から HTTP だけを外す

**Rocky server console B、割り当てには通常 user、firewall 照会には sudo:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

Lab NIC だけが `network-beginner` に属し、元の management zone が保たれていて、4つの query がすべて `yes` を返すことを確認します。これは期限切れの試行設定ではなく、レッスン6の永続 rule が残っていることを前提とします。より広い policy が HTTP を別途許可していないかも記録し、調べてください。

Runtime の **HTTP rule だけ**を削除します。

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

結果が `no`、`yes`、`yes`、`yes` になることを確認します。最初の `no` は非ゼロ status で、ここでは期待どおりです。障害中の確認を実行します。`--runtime-to-permanent`、reload、reboot は行わないでください。Reload すると保存済み HTTP rule が復帰し、runtime を permanent にコピーすると障害状態を意図せず永続化します。

**同じ Rocky console から復旧:** 全体の reload や permanent 設定の変更なしで元に戻します。

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

4つの query がすべて再び `yes` になるはずです。Runtime／permanent list を事前に記録した基準と比較します。保存済み rule は変更されておらず、同じ scope の runtime HTTP rule が復元されています。保存済み policy に予想外の変更があれば、一括上書きせず記録と照らして調べてください。

#### 障害中と復旧後の確認

**Client、通常 user、同じ terminal:** この組を HTTP 削除**後**と復旧**後**の両方で実行します。障害前の確認に加えて行ってください。

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

障害中も、新しい key-only SSH 接続は成功する必要があります。Server listener が `.20:8000` で稼働している一方、記録した演習用 policy によって HTTP は失敗する必要があります。SSH が失敗した場合は、server console から削除した HTTP permission だけを戻し、変更していない SSH rule／経路を比較して中止してください。HTTP だけの障害を実証できていません。HTTP が成功する場合は、別の一致する許可、zone／default の挙動、listener、packet の証拠を調べます。単一の rule を削除しただけで block できたと結論づけないでください。

復旧後は、新しい key-only SSH 接続の成功と、`healthy` を含む HTTP 200 の両方が必要です。Server console B では `sudo ss -ltnp 'sport = :8000'`、関係する rule query／一覧、`ip -4 -br address show dev "$MGMT_IF"`、`ip -4 route` を再実行します。障害前の記録と比較し、必要な management access も再確認してください。3段階それぞれの観測を分けて記録します。文書を作成した時点で guest 上の試験を実行したという主張ではありません。

## 報告と完了条件 {#capstone-report}

Password、private key、実際の user traffic ではなく、lab address と結果を記録してください。

| 項目 | 記録内容 |
|---|---|
| Environment | Distribution、kernel、lab NIC、client／server address、firewall manager |
| 正常状態 | Route、listener、HTTP status／body |
| 症状 | どの host からどの request を送り、何を受け取ったか |
| 仮説 | 名前解決、route、listener、firewall、HTTP のどれか |
| 証拠 | 関係する command、時刻、address／port、観測結果 |
| 仮説の反証 | 仮説が誤りなら何を観測するはずか |
| 変更と復旧 | 変更した1点と正確な復旧手順 |
| 再確認 | 正常な HTTP 200、SSH key access、lab／management NIC の状態 |

**合格:** A～Cを区別して復旧し、実際の rule と観測が D の仮説を支持するか説明します。次の5項目を満たしてください。Environment の識別、層に沿った仮説、証拠、範囲を絞った変更／復旧、復旧後の検証。未達があれば該当レッスンに戻ります。速く終えることは評価基準ではありません。

## 学んだ問いを Docker と Kubernetes に適用する {#container-cloud-map}

VM 間の診断を理解してから container を学びます。次の表は後続学習における役割の対応を示します。すべての packet が必ず表の順で各段階を通るという意味ではありません。

| 学んだこと | Docker | Kubernetes | Cloud |
|---|---|---|---|
| Process の address／port | Container の network namespace 内の listener | Pod 内で共有される listener と network | Backend process と load-balancer target port |
| Link と route | veth、Linux bridge、環境に応じた NAT | CNI が設定する Pod 経路、overlay、native routing | VPC subnet、route、接続境界 |
| 名前解決 | User-defined bridge 上の container 名 | Service 名と cluster DNS | Organization／cloud DNS と private name |
| Access rule | Published port と host forwarding rule | NetworkPolicy とその実装による enforcement | Security Group のような層別の制御 |
| 観測位置 | Host と container namespace | Node、Pod、Service 実装 | Client、load balancer、node、AZ の境界 |

Docker の **bridge** は一般に1つの host 内の container を接続し、**overlay** は基盤 network 上に仮想 network を構築します。Docker Swarm の overlay を実習するには、複数 host など追加の準備が必要です。Kubernetes CNI は別の interface／plugin ecosystem です。Docker bridge の構成をコピーしても Kubernetes cluster にはなりません。

同様に、`localhost`、Pod IP、Service IP、外部 entry point は別々の観測対象です。Host firewall rule、container forwarding rule、CNI policy は相互に置き換え可能な単一の rule list ではありません。

## 次の実践ステップ {#next-path}

体系的に学ぶには、[Expert Networking の学習パス](../expert/README.md)に進みます。以下の個別ガイドを、読む順序、実験、評価に沿って接続しています。

1. [Container technology](../../basics/03-container-technology.md)で namespace、bridge、公開 port を学ぶ。
2. [Linux network diagnostics](../07-linux-network-diagnostics.md)で next hop、ICMP、PMTU を測る。最初にそのガイドの Docker 前提、範囲、cleanup を読む。
3. [Kubernetes introduction](../../basics/04-kubernetes-introduction.md)と[Pod／workload](../../core/02-pods-and-workloads.md)を学び、[Service／DNS lab](../../labs/core/03-services-networking-lab.md)を行う。
4. [eBPF の基礎](../../basics/05-ebpf-fundamentals.md)を学び、[Cilium](../cilium/README.md)と[Calico](../calico/README.md)を比較する。
5. AWS が必要になったら、[EKS networking](../../eks/03-eks-networking-part1.md)、[VPC CNI](../01-vpc-cni.md)、[load balancing](../03-aws-lb-controller.md)を学ぶ。Resource 作成の前に、各ガイドの cost、permission、cleanup 条件を個別に確認する。
6. 性能を扱う場合は、[kernel network stack](../../kernel/02-network-stack.md)と[Pod benchmark](../06-pod-network-benchmark.md)の測定条件を読む。この小さな HTTP 演習を cloud throughput の結果に一般化しない。

## Cleanup

Console A で演習用 server を停止してから、同じ terminal で作成した file を削除します。

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

レッスン6の rule を後続演習でも残すか記録します。コース全体を終えるときは、各レッスンの復旧手順に従うか、**自分の VM snapshot**に戻してください。Management NIC と既存 SSH access を確認し、VM を通常の方法で shutdown します。

## 参考資料

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [curl の address mapping](https://curl.se/docs/manpage.html)
- [Ubuntu 24.04 UFW: rule 順序、multiport rule、削除](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld: runtime／permanent 設定と rich-rule 操作](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [OpenSSH client option と connection sharing](https://man.openbsd.org/ssh_config)
- [Docker bridge](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker overlay](https://docs.docker.com/engine/network/drivers/overlay/)
- [Kubernetes networking model](https://kubernetes.io/docs/concepts/services-networking/)

[前へ: Monitoring と性能](07-monitoring-performance.md) · [クイズ](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [コースに戻る](README.md)
