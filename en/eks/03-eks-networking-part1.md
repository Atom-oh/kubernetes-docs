# EKS Networking - Part 1: Basic Concepts and VPC Configuration

## Overview

Amazon EKS networking is a core component that manages communication for Kubernetes clusters. This document covers basic concepts of EKS networking, VPC configuration, subnet design, and security group configuration.

## EKS Networking Architecture

The EKS networking architecture consists of the following components:

![EKS Networking Architecture Overview](../assets/generated-diagrams/eks_networking_architecture_overview.drawio)
    Node1 --- Pod1
    Node1 --- Pod2
    Node2 --- Pod3
    Pod1 <--> Pod2
    Pod2 <--> Pod3
    Pod1 <--> Pod3
    Node1 <--> NLB
    Node2 <--> NLB
    Worker_Nodes <--> EKS_CP
    Worker_Nodes <--> S3_EP
    Worker_Nodes <--> ECR_EP
    Worker_Nodes <--> EKS_EP
    S3_EP <--> S3
    ECR_EP <--> ECR
    EKS_EP <--> EKS_CP

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class IGW,NATGW,ALB,NLB,S3_EP,ECR_EP,EKS_EP,S3,ECR,EKS_CP awsService;
    class Node1,Node2 k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
```

1. **VPC (Virtual Private Cloud)**: Isolated network environment where the EKS cluster runs
2. **Subnets**: Units that divide IP address ranges within the VPC
3. **Route Tables**: Rule sets that determine network traffic paths
4. **Internet Gateway**: Component that enables communication between VPC and the internet
5. **NAT Gateway**: Component that allows resources in private subnets to access the internet
6. **Security Groups**: Instance-level virtual firewalls
7. **Network ACLs**: Subnet-level virtual firewalls
8. **CNI (Container Network Interface)**: Plugin that manages container networking

### EKS Networking Flow

Network traffic flows in an EKS cluster as follows:

![EKS Network Traffic Flow](../assets/generated-diagrams/eks_network_traffic_flow.drawio)
    Pod2 <--> Pod4

    %% Pod to service communication
    Pod1 --> ClusterIP
    Pod2 --> ClusterIP
    Pod3 --> ClusterIP
    Pod4 --> ClusterIP

    %% Internal to external cluster communication
    Internet <--> LoadBalancer
    External_Services <--> LoadBalancer
    LoadBalancer --> NodePort
    NodePort --> ClusterIP

    %% Control plane to node communication
    API <--> Kubelet1
    API <--> Kubelet2
    Controller <--> Kubelet1
    Controller <--> Kubelet2

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class API,Controller,Scheduler,Kubelet1,Kubelet2,ClusterIP,NodePort,LoadBalancer k8sComponent;
    class Pod1,Pod2,Pod3,Pod4 userApp;
    class Internet,External_Services default;
```

1. **Pod-to-Pod Communication**: Communication between pods on the same node or different nodes
2. **Pod-to-Service Communication**: Communication between pods and services within the cluster
3. **Internal to External Cluster Communication**: Communication between internal cluster resources and external resources
4. **Control Plane to Node Communication**: Communication between EKS control plane and worker nodes

### Relationship Between EKS Networking Components

![Relationship Between EKS Networking Components](../assets/generated-diagrams/eks_networking_components_relationship.drawio)

## VPC Requirements

A VPC for an EKS cluster must meet the following requirements:

![EKS VPC Requirements](../assets/generated-diagrams/eks_vpc_requirements.drawio)

1. **Subnets**: Must have subnets in at least 2 availability zones
2. **IP Addresses**: Must provide a sufficient number of IP addresses
3. **DNS Hostnames**: DNS hostnames and DNS resolution must be enabled
4. **Internet Access**: Nodes must be able to access the internet (through NAT gateway or internet gateway)

### VPC CIDR Planning

Considerations when planning VPC CIDR blocks:

![VPC CIDR Planning Considerations](../assets/generated-diagrams/eks_vpc_cidr_planning.drawio)

1. **Cluster Size**: Expected number of nodes and pods
2. **IP Address Requirements**: Number of IP addresses needed for each node and pod
3. **Future Expansion**: Room for future expansion
4. **Integration with Existing Networks**: Avoiding overlap with existing networks

Common VPC CIDR block sizes:
- Small clusters: /24 (256 IP addresses)
- Medium clusters: /20 (4,096 IP addresses)
- Large clusters: /16 (65,536 IP addresses)

### Subnet Design

![EKS Subnet Design](../assets/generated-diagrams/eks_subnet_design.drawio)

Best practices for subnet design for EKS clusters:

1. **Public Subnets**: Subnets directly connected to the internet gateway
   - Use: Public load balancers, NAT gateways, bastion hosts
   - Typical size: /24 (256 IP addresses)

2. **Private Subnets**: Subnets not directly connected to the internet gateway
   - Use: EKS worker nodes, internal load balancers
   - Typical size: /22 (1,024 IP addresses)

3. **Availability Zone Distribution**: Distribute subnets across multiple availability zones
   - Use at least 2 availability zones
   - Place public and private subnets in each availability zone

Example subnet design:

| Subnet Type | Availability Zone | CIDR Block | Use |
|------------|---------|----------|------|
| Public | us-west-2a | 10.0.0.0/24 | Load balancers, NAT gateways |
| Public | us-west-2b | 10.0.1.0/24 | Load balancers, NAT gateways |
| Private | us-west-2a | 10.0.2.0/22 | EKS worker nodes |
| Private | us-west-2b | 10.0.6.0/22 | EKS worker nodes |

### Subnet Tags

![EKS Subnet Tag Configuration](../assets/generated-diagrams/eks_subnet_tags.drawio)

EKS uses specific tags on subnets to automatically discover resources:

1. **Public Subnet Tags**:
   - `kubernetes.io/role/elb`: Set value to `1` for use with internet-facing load balancers
   - `kubernetes.io/cluster/<cluster-name>`: Set value to `shared` or `owned`

2. **Private Subnet Tags**:
   - `kubernetes.io/role/internal-elb`: Set value to `1` for use with internal load balancers
   - `kubernetes.io/cluster/<cluster-name>`: Set value to `shared` or `owned`

Example:
```bash
aws ec2 create-tags \
  --resources subnet-xxxxxxxxxxxxxxxxx \
  --tags Key=kubernetes.io/cluster/my-cluster,Value=shared Key=kubernetes.io/role/elb,Value=1
```

### Security Group Configuration

![EKS Security Group Configuration](../assets/generated-diagrams/eks_security_groups.drawio)

EKS clusters have two main security groups:

1. **Cluster Security Group (Control Plane)**:
   - Inbound rules:
     - 443/TCP: Allow traffic from worker node security group
   - Outbound rules:
     - 1025-65535/TCP: Allow traffic to worker node security group

2. **Node Security Group (Worker Nodes)**:
   - Inbound rules:
     - 443/TCP: Allow traffic from cluster security group
     - 1025-65535/TCP: Allow traffic from cluster security group
     - ALL: Allow traffic within the same security group
   - Outbound rules:
     - ALL: Allow traffic to all destinations

## Conclusion

In this document, we learned about basic concepts of EKS networking and VPC configuration. In the next document, we will cover more advanced networking topics such as services, load balancing, and network policies.

## Quiz

To test what you learned in this chapter, try the [EKS Networking - Part 1 Quiz](../quizzes/eks/03-eks-networking-part1-quiz.md).
