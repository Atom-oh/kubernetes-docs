# Table of contents

## Introduction

* [Introduction](README.md)

## 基础

* [Linux 基础](basics/01-linux-basics.md)
* [Linux 运维技能](basics/02-linux-advanced.md)
* [容器技术](basics/03-container-technology.md)
* [Kubernetes 简介](basics/04-kubernetes-introduction.md)
* [eBPF 基础与实践应用](basics/05-ebpf-fundamentals.md)

## 实验指南

* [实验指南简介](labs/README.md)
  * [Linux 基础实验](labs/basics/01-linux-basics-lab.md)
  * [Linux 运维技能实验](labs/basics/02-linux-advanced-lab.md)
  * [容器技术实验](labs/basics/03-container-technology-lab.md)

## 测验集合

* [测验合集 - 按主题分类的测验](quizzes/README.md)
  * [Linux 基础测验](quizzes/basics/01-linux-basics-quiz.md)
  * [Linux 运维技能测验](quizzes/basics/02-linux-advanced-quiz.md)
  * [容器技术测验](quizzes/basics/03-container-technology-quiz.md)
  * [Kubernetes 简介测验](quizzes/basics/04-kubernetes-introduction-quiz.md)
  * [eBPF 基础与实践应用测验](quizzes/basics/05-ebpf-fundamentals-quiz.md)

  * [第 1 部分：Kafka 基础知识测验](quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
  * [第 2 部分：Strimzi Operator 测验](quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
  * [第 3 部分：Kafka 运维测验](quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
  * [第 4 部分：Schema Registry 测验](quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
  * [第 5 部分：Kafka Connect 和 MirrorMaker 测验](quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
  * [第 6 部分：MSK 集成测验](quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
  * [第 7 部分：监控测验](quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
  * [第 8 部分：最佳实践测验](quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

  * [自定义调度器测验 - 第 1 部分](quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
  * [自定义调度器测验 - 第 2 部分](quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
  * [自定义调度器测验 - 第 3 部分](quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

  * [先决条件测验](quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
  * [网络配置测验](quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
  * [隔离网络环境设置测验](quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
  * [节点引导测验](quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
  * [GPU 服务器集成测验](quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
  * [工作负载放置策略测验](quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
  * [节点生命周期管理测验](quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
  * [运维测验](quizzes/eks-hybrid-nodes/08-operations-quiz.md)
  * [裸金属操作系统设置测验](quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
  * [混合节点网关测验](quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

## EKS 上的数据

* [EKS 上的数据概述](data-on-eks/README.md)
* [EKS 上的 Kafka 深入解析](data-on-eks/kafka/README.md)
  * [第 1 部分：Kafka 基础知识](data-on-eks/kafka/01-kafka-fundamentals.md)
  * [第 2 部分：Strimzi Operator](data-on-eks/kafka/02-strimzi-operator.md)
  * [第 3 部分：Kafka 运维](data-on-eks/kafka/03-kafka-operations.md)
  * [第 4 部分：Schema Registry](data-on-eks/kafka/04-schema-registry.md)
  * [第 5 部分：Kafka Connect 和 MirrorMaker](data-on-eks/kafka/05-kafka-connect-mirrormaker.md)
  * [第 6 部分：MSK 集成](data-on-eks/kafka/06-msk-integration.md)
  * [第 7 部分：监控](data-on-eks/kafka/07-monitoring.md)
  * [第 8 部分：最佳实践](data-on-eks/kafka/08-best-practices.md)
  * [KEDA 测验](quizzes/autoscaling/05-keda-quiz.md)
  * [Karpenter 测验](quizzes/autoscaling/06-karpenter-quiz.md)
  * [Knative 测验](quizzes/autoscaling/03-knative-quiz.md)

## 自动扩缩容

* [KEDA](autoscaling/01-keda.md)
* [Karpenter](autoscaling/02-karpenter.md)
* [Knative](autoscaling/03-knative.md)

## 调度

* [自定义调度器](scheduling/01-custom-scheduler-part1.md)
  * [第 1 部分：基本概念](scheduling/01-custom-scheduler-part1.md)
  * [第 2 部分：实现](scheduling/02-custom-scheduler-part2.md)
  * [第 3 部分：高级功能](scheduling/03-custom-scheduler-part3.md)

## Amazon EKS

* [EKS 混合节点](eks-hybrid-nodes/README.md)
  * [先决条件](eks-hybrid-nodes/01-prerequisites.md)
  * [网络配置](eks-hybrid-nodes/02-network-configuration.md)
  * [隔离网络环境设置](eks-hybrid-nodes/03-airgap-setup.md)
  * [节点引导](eks-hybrid-nodes/04-node-bootstrap.md)
  * [GPU 服务器集成](eks-hybrid-nodes/05-gpu-integration.md)
  * [工作负载放置策略](eks-hybrid-nodes/06-workload-placement.md)
  * [节点生命周期管理](eks-hybrid-nodes/07-node-lifecycle.md)
  * [运维](eks-hybrid-nodes/08-operations.md)
  * [裸金属操作系统设置](eks-hybrid-nodes/09-bare-metal-os-setup.md)
  * [混合节点网关](eks-hybrid-nodes/10-hybrid-nodes-gateway.md)
