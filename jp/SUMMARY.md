# Table of contents

## Introduction

* [Introduction](README.md)

## 基本

* [Linux の基礎](basics/01-linux-basics.md)
* [Linux 運用スキル](basics/02-linux-advanced.md)
* [コンテナ技術](basics/03-container-technology.md)
* [Kubernetes 入門](basics/04-kubernetes-introduction.md)
* [eBPF の基礎と実践的応用](basics/05-ebpf-fundamentals.md)

## ラボガイド

* [ラボガイド入門](labs/README.md)
  * [Linux の基礎ラボ](labs/basics/01-linux-basics-lab.md)
  * [Linux 運用スキルラボ](labs/basics/02-linux-advanced-lab.md)
  * [コンテナ技術ラボ](labs/basics/03-container-technology-lab.md)

  * [Pod とワークロード ラボ](labs/core/02-pods-and-workloads-lab.md)
  * [サービスとネットワーキング ラボ](labs/core/03-services-networking-lab.md)
  * [ストレージ ラボ](labs/core/04-storage-lab.md)
  * [ConfigMap と Secret ラボ](labs/core/05-configuration-secrets-lab.md)

## クイズ集

* [クイズ集 - トピック別クイズ](quizzes/README.md)
  * [Linux の基礎クイズ](quizzes/basics/01-linux-basics-quiz.md)
  * [Linux 運用スキルクイズ](quizzes/basics/02-linux-advanced-quiz.md)
  * [コンテナ技術クイズ](quizzes/basics/03-container-technology-quiz.md)
  * [Kubernetes 入門クイズ](quizzes/basics/04-kubernetes-introduction-quiz.md)
  * [eBPF の基礎と実践的応用クイズ](quizzes/basics/05-ebpf-fundamentals-quiz.md)

  * [KEDAクイズ](quizzes/autoscaling/05-keda-quiz.md)
  * [Karpenterクイズ](quizzes/autoscaling/06-karpenter-quiz.md)
  * [Knativeクイズ](quizzes/autoscaling/03-knative-quiz.md)

  * [カスタムスケジューラー小テスト - パート1](quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
  * [カスタムスケジューラー小テスト - パート2](quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
  * [カスタムスケジューラー小テスト - パート3](quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

  * [前提条件クイズ](quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
  * [ネットワーク設定クイズ](quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
  * [エアギャップ環境のセットアップクイズ](quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
  * [Nodeの初期化クイズ](quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
  * [GPUサーバーの統合クイズ](quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
  * [ワークロード配置戦略クイズ](quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
  * [Nodeライフサイクル管理クイズ](quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
  * [運用と保守クイズ](quizzes/eks-hybrid-nodes/08-operations-quiz.md)
  * [ベアメタルOSのセットアップクイズ](quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
  * [Hybrid Nodesゲートウェイクイズ](quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
  * [クラスターアーキテクチャクイズ](quizzes/core/01-cluster-architecture-quiz.md)
  * [Pod とワークロードクイズ](quizzes/core/02-pods-and-workloads-quiz.md)
  * [サービスとネットワーキングクイズ](quizzes/core/03-services-networking-quiz.md)
  * [ストレージクイズ](quizzes/core/04-storage-quiz.md)
  * [構成クイズ](quizzes/core/05-configuration-secrets-quiz.md)
  * [セキュリティクイズ](quizzes/core/06-security-quiz.md)
  * [ポリシークイズ](quizzes/core/07-policies-quiz.md)
  * [スケジューリング、プリエンプション、退避クイズ](quizzes/core/08-scheduling-preemption-eviction-quiz.md)
  * [クラスター管理クイズ](quizzes/core/09-cluster-administration-quiz.md)
  * [Kubernetes における Windows クイズ](quizzes/core/10-windows-in-kubernetes-quiz.md)
  * [Kubernetes の拡張クイズ](quizzes/core/11-extending-kubernetes-quiz.md)

  * [パート1: Kafkaの基礎クイズ](quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
  * [パート2: Strimzi Operatorクイズ](quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
  * [パート3: Kafkaの運用クイズ](quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
  * [パート4: Schema Registryクイズ](quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
  * [パート5: Kafka ConnectとMirrorMakerクイズ](quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
  * [パート6: MSK統合クイズ](quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
  * [パート7: 監視クイズ](quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
  * [パート8: ベストプラクティスクイズ](quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

## オートスケーリング

* [KEDA](autoscaling/01-keda.md)
* [Karpenter](autoscaling/02-karpenter.md)
* [Knative](autoscaling/03-knative.md)

## スケジューリング

* [カスタムスケジューラー](scheduling/01-custom-scheduler-part1.md)
  * [パート1: 基本概念](scheduling/01-custom-scheduler-part1.md)
  * [パート2: 実装](scheduling/02-custom-scheduler-part2.md)
  * [パート3: 高度な機能](scheduling/03-custom-scheduler-part3.md)

## Amazon EKS

* [EKS Hybrid Nodes](eks-hybrid-nodes/README.md)
  * [前提条件](eks-hybrid-nodes/01-prerequisites.md)
  * [ネットワーク設定](eks-hybrid-nodes/02-network-configuration.md)
  * [エアギャップ環境のセットアップ](eks-hybrid-nodes/03-airgap-setup.md)
  * [Nodeの初期化](eks-hybrid-nodes/04-node-bootstrap.md)
  * [GPUサーバーの統合](eks-hybrid-nodes/05-gpu-integration.md)
  * [ワークロード配置戦略](eks-hybrid-nodes/06-workload-placement.md)
  * [Nodeライフサイクル管理](eks-hybrid-nodes/07-node-lifecycle.md)
  * [運用と保守](eks-hybrid-nodes/08-operations.md)
  * [ベアメタルOSのセットアップ](eks-hybrid-nodes/09-bare-metal-os-setup.md)
  * [Hybrid Nodesゲートウェイ](eks-hybrid-nodes/10-hybrid-nodes-gateway.md)
## Kubernetes の中核概念

* [クラスターアーキテクチャ](core/01-cluster-architecture.md)
* [Pod とワークロード](core/02-pods-and-workloads.md)
* [サービスとネットワーキング](core/03-services-networking.md)
* [ストレージ](core/04-storage.md)
* [構成](core/05-configuration-secrets.md)
* [セキュリティ](core/06-security.md)
* [ポリシー](core/07-policies.md)
* [スケジューリング、プリエンプション、退避](core/08-scheduling-preemption-eviction.md)
* [クラスター管理](core/09-cluster-administration.md)
* [Kubernetes における Windows](core/10-windows-in-kubernetes.md)
* [Kubernetes の拡張](core/11-extending-kubernetes.md)

## EKS 上のデータ

* [EKS上のデータ概要](data-on-eks/README.md)
* [EKS上のKafkaの詳細解説](data-on-eks/kafka/README.md)
  * [パート1: Kafkaの基礎](data-on-eks/kafka/01-kafka-fundamentals.md)
  * [パート2: Strimzi Operator](data-on-eks/kafka/02-strimzi-operator.md)
  * [パート3: Kafkaの運用](data-on-eks/kafka/03-kafka-operations.md)
  * [パート4: Schema Registry](data-on-eks/kafka/04-schema-registry.md)
  * [パート5: Kafka ConnectとMirrorMaker](data-on-eks/kafka/05-kafka-connect-mirrormaker.md)
  * [パート6: MSK統合](data-on-eks/kafka/06-msk-integration.md)
  * [パート7: 監視](data-on-eks/kafka/07-monitoring.md)
  * [パート8: ベストプラクティス](data-on-eks/kafka/08-best-practices.md)
