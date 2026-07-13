> [한국어](../ko/) | [English](../en/) | [日本語](../jp/) | [Español](../es/)

# Kubernetes 与 Amazon EKS 培训内容

本站正在从 [English 版本](../en/) 逐步进行机器翻译，按章节陆续上线。当前尚未翻译的章节，请暂时参考 [English](../en/) 或 [한국어](../ko/) 版本。

## Table of Contents

（章节将在翻译完成后依次添加）

### 基本概念
1. [Linux 基础](./basics/01-linux-basics.md) | [Quiz](./quizzes/basics/01-linux-basics-quiz.md) | [Lab](./labs/basics/01-linux-basics-lab.md)
2. [Linux 运维技能](./basics/02-linux-advanced.md) | [Quiz](./quizzes/basics/02-linux-advanced-quiz.md) | [Lab](./labs/basics/02-linux-advanced-lab.md)
3. [容器技术](./basics/03-container-technology.md) | [Quiz](./quizzes/basics/03-container-technology-quiz.md) | [Lab](./labs/basics/03-container-technology-lab.md)
4. [Kubernetes 简介](./basics/04-kubernetes-introduction.md) | [Quiz](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [eBPF 基础与实践应用](./basics/05-ebpf-fundamentals.md) | [Quiz](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### EKS 上的数据
1. [EKS 上的数据概述](./data-on-eks/README.md)
2. **Kafka on EKS Deep Dive**
   - [EKS 上的 Kafka 简介](./data-on-eks/kafka/README.md)
   - [第 1 部分：Kafka 基础知识](./data-on-eks/kafka/01-kafka-fundamentals.md) | [Quiz](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [第 2 部分：Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [Quiz](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [第 3 部分：Kafka 运维](./data-on-eks/kafka/03-kafka-operations.md) | [Quiz](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [第 4 部分：Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [Quiz](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [第 5 部分：Kafka Connect 和 MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Quiz](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [第 6 部分：MSK 集成](./data-on-eks/kafka/06-msk-integration.md) | [Quiz](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [第 7 部分：监控](./data-on-eks/kafka/07-monitoring.md) | [Quiz](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [第 8 部分：最佳实践](./data-on-eks/kafka/08-best-practices.md) | [Quiz](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
### 自动扩缩容
1. [KEDA](./autoscaling/01-keda.md) | [Quiz](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [Quiz](./quizzes/autoscaling/06-karpenter-quiz.md)
3. [Knative](./autoscaling/03-knative.md) | [Quiz](./quizzes/autoscaling/03-knative-quiz.md)

### 调度
1. Custom Scheduler
   - [第 1 部分：自定义调度器基础](./scheduling/01-custom-scheduler-part1.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [第 2 部分：调度器扩展与框架](./scheduling/02-custom-scheduler-part2.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [第 3 部分：自定义调度器实现示例与监控](./scheduling/03-custom-scheduler-part3.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### 人工智能/机器学习
1. [AI/ML 工作负载](./ai-ml/01-ai-ml-workloads.md) | [Quiz](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI 基础设施](./ai-ml/06-ai-infrastructure.md) | [Quiz](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [在 EKS 上进行模型训练](./ai-ml/05-model-training.md) | [Quiz](./quizzes/ai-ml/05-model-training-quiz.md)
4. [推理框架](./ai-ml/04-inference-frameworks.md) | [Quiz](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM 部署与优化](./ai-ml/02-vllm-deployment.md) | [Quiz](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上的智能体 AI 平台](./ai-ml/03-agentic-ai-platform.md) | [Quiz](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML 最佳实践](./ai-ml/07-ai-ml-best-practices.md) | [Quiz](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)

