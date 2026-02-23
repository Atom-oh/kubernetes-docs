# Glossary and Abbreviations

> **Last Updated**: February 22, 2026

This document provides explanations of key terms and abbreviations related to Cilium. This glossary helps in understanding Cilium, eBPF, Kubernetes, and networking concepts.

## Term Categories

Terms are classified into the following categories:
- Blue **Cilium-related terms**
- Orange **eBPF-related terms**
- Green **Kubernetes-related terms**
- Purple **Networking-related terms**
- White **General terms**

## A

**API (Application Programming Interface)** - General
- A set of interface definitions that enable communication between applications

**AWS ENI (Elastic Network Interface)** - Networking
- Virtual network interface provided by Amazon Web Services
- Used in Cilium's AWS ENI IPAM mode

**ARP (Address Resolution Protocol)** - Networking
- Protocol that converts IP addresses to MAC addresses
- Essential protocol for communication in L2 networks

## B

**BGP (Border Gateway Protocol)** - Networking
- Standard external gateway protocol used to exchange routing information on the Internet
- Can be used as native routing mode in Cilium

**BPF (Berkeley Packet Filter)** - eBPF
- Technology for packet filtering, predecessor to eBPF
- Originally developed for network packet capture

**BPF Maps** - eBPF
- Key-value stores used to store and retrieve data in eBPF programs
- Used for data sharing between user space and kernel space

## C

**CGroup (Control Group)** - Kubernetes
- Linux kernel feature that limits and isolates resource usage of process groups
- Used for container resource limiting

**CIDR (Classless Inter-Domain Routing)** - Networking
- Method for IP address allocation and routing aggregation
- Example: 192.168.1.0/24 represents IP address range from 192.168.1.0 to 192.168.1.255

**CNI (Container Network Interface)** - Kubernetes
- Standard interface between container runtimes and network plugins
- Cilium is one of the CNI implementations

**CoreDNS** - Kubernetes
- DNS server commonly used in Kubernetes clusters
- Plays an important role in service discovery

**CRD (Custom Resource Definition)** - Kubernetes
- Method to define custom resources by extending the Kubernetes API
- Cilium uses CRDs to define network policies, etc.

**Cilium** - Cilium
- Open source networking, security, and observability solution based on eBPF
- Used as a Kubernetes CNI implementation

## D

**DNAT (Destination Network Address Translation)** - Networking
- NAT type that modifies the destination IP address of packets
- Used for load balancing and port forwarding

**DNS (Domain Name System)** - Networking
- System that converts domain names to IP addresses
- Cilium supports DNS-based network policies

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF
- Technology that allows safe execution of programs within the Linux kernel
- Core technology used in Cilium

**Endpoint** - Cilium
- Workload unit to which network policies are applied in Cilium
- Generally corresponds to Kubernetes pods

**Envoy** - Cilium
- L7 proxy and service mesh component
- Used for L7 policy enforcement in Cilium

## H

**Hubble** - Cilium
- Cilium's observability layer
- Tool for real-time monitoring and analysis of network flows

## I

**IPAM (IP Address Management)** - Networking
- System responsible for allocating, tracking, and managing IP addresses
- Cilium supports multiple IPAM modes

**IPsec** - Networking
- Protocol suite that provides secure communication by encrypting IP packets
- Can be used for inter-node traffic encryption in Cilium

## K

**kube-proxy** - Kubernetes
- Network proxy that implements Kubernetes service abstraction
- Cilium can replace kube-proxy

## V

**VXLAN (Virtual Extensible LAN)** - Networking
- Network virtualization technology that overlays Layer 2 networks over Layer 3 networks
- One of Cilium's overlay networking modes

## W

**WireGuard** - Networking
- Modern and fast VPN protocol
- Can be used for inter-node traffic encryption in Cilium

## X

**XDP (eXpress Data Path)** - eBPF
- eBPF feature that processes packets at the network driver level
- Provides very high-performance packet processing

**DaemonSet**
- Kubernetes resource that runs a copy of a pod on all nodes

## E

**eBPF (extended Berkeley Packet Filter)**
- Technology that allows safe execution of programs within the Linux kernel

**Endpoint**
- Network endpoint (generally a pod) to which network policies are applied in Cilium

**Envoy**
- Open source edge and service proxy used as L7 proxy and communication bus

## F

**FQDN (Fully Qualified Domain Name)**
- Complete domain name of a host (e.g., www.example.com)

## G

**GENEVE (Generic Network Virtualization Encapsulation)**
- Encapsulation protocol for network virtualization

**gRPC (gRPC Remote Procedure Call)**
- High-performance RPC (Remote Procedure Call) framework developed by Google

## H

**Hubble**
- Cilium's network visibility and monitoring component

## I

**IPAM (IP Address Management)**
- Planning, tracking, and management of IP addresses

**IPsec (Internet Protocol Security)**
- Protocol suite for IP communication security

**Istio**
- Open source platform that implements service mesh

## K

**Kafka**
- Distributed streaming platform

**kube-proxy**
- Network proxy that implements Kubernetes service abstraction

**Kubernetes**
- Open source platform that automates deployment, scaling, and management of containerized applications

## L

**L2 (Layer 2)**
- Data link layer of OSI model

**L3 (Layer 3)**
- Network layer of OSI model

**L4 (Layer 4)**
- Transport layer of OSI model

**L7 (Layer 7)**
- Application layer of OSI model

**LoadBalancer**
- Device or service that distributes traffic across multiple servers

## M

**MAC (Media Access Control) Address**
- Unique identifier assigned to network interfaces

**MTU (Maximum Transmission Unit)**
- Maximum packet size that can be transmitted over a network

**mTLS (mutual TLS)**
- Extension of TLS where both client and server authenticate each other with certificates

## N

**NAT (Network Address Translation)**
- Process of modifying IP address information in IP packets

**NodePort**
- Kubernetes service type that exposes a static port on each node's IP

## O

**OSI (Open Systems Interconnection) Model**
- Conceptual model that classifies network communication into 7 abstract layers

**Overlay Network**
- Virtual network built on top of an existing network

## P

**Pod**
- Smallest deployable computing unit in Kubernetes

**Proxy**
- Server that acts as intermediary between client and server

## R

**RBAC (Role-Based Access Control)**
- Method for controlling access to system resources based on roles

## S

**Service**
- Abstraction in Kubernetes that provides a stable endpoint for a set of pods

**SNAT (Source Network Address Translation)**
- NAT type that modifies the source IP address of packets

**Socket**
- Endpoint for inter-process communication over a network

## T

**TCP (Transmission Control Protocol)**
- Connection-oriented transport protocol that provides reliable byte streams

**TLS (Transport Layer Security)**
- Cryptographic protocol that protects communication over networks

## U

**UDP (User Datagram Protocol)**
- Connectionless transport protocol

## V

**VETH (Virtual Ethernet)**
- Virtual ethernet device, typically created in pairs

**VNI (VXLAN Network Identifier)**
- 24-bit identifier that identifies VXLAN networks

**VTEP (VXLAN Tunnel Endpoint)**
- Endpoint responsible for encapsulation and decapsulation of VXLAN packets

**VXLAN (Virtual Extensible LAN)**
- Network virtualization technology that overlays Layer 2 networks over Layer 3 networks

## W

**WireGuard**
- Modern, fast, and secure VPN tunnel protocol

## X

**XDP (eXpress Data Path)**
- eBPF-based technology for very fast network packet processing

## Quiz

To test what you learned in this chapter, try the [Topic Quiz](../../quizzes/networking/cilium/glossary-quiz.md).
