# **Review of Cluster Workload Orchestration System w/re Prompt Cache Integration**

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                        |
| Section    | research/prompt-cache-integration-workload-orchestration               |
| Version    | 0.1                                                                    |
| Date       | 2025-07-29                                                             |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/) |
| Summarized | Prompt Cache, Cluster Design, Perf References                          |
| Inferenced | Qwen3-235B-Instruct                                                    |
| Reference  | [Cluster Workload Orchestrator Proposal](https://cerebras.atlassian.net/wiki/spaces/AIC/embed/4260724771) |

---

## **1. Structured Analysis**

There are several concurrent projects in-flight which impact scalability and necessitate improvements to the Prompt Cache architecture, particularly off-wafer caching designs. One of these design choices will require the inference software stack to support **on-premises appliance deployments**, enabling customers to run models locally with ease. This initiative addresses limitations in the current cloud-centric architecture by introducing a **modular, scalable, and user-friendly platform** built around three core components:  

- **Workload Orchestrator (WO)**  
- **Workload Manager (WM)**  
- **Inference Brain (IB)**  

In an effort to contextualize and integrate these changes, this structured report will categorically inspect **high-level design**, **decision processes**, **performance implications**, **integration with prompt caching**, and **overall benefits** of the proposed architecture. Additionally, an implementation roadmap (likely moving targets) is detailed, along with a **Glossary of Terms**.

## **1.1. Towards a General Purpose Inference Architecture**
The proposed Cluster Workload Orchestrator enables a cloud-centric monolithic stack into a modular on-premise system, which aims to improve deployment methods and infrastructure requirements by decoupling the system roles involved with: management, job invocation**, and job execution. In doing so it enables several functional benefits:

- **Easy on-prem deployment** with minimal setup.
- **High-performance inference** through intelligent routing and prompt caching.
- **Operational resilience** with zero-downtime updates and HA components.
- **Future extensibility** for training, multi-appliance orchestration, and advanced optimizations.

---

## **2. High-Level Design**

### **2.1 Architectural Overview**

The new architecture decouples **workload management** from **workload invocation**, enabling scalable, secure, and maintainable inference operations.

![Overall Platform Arch](https://via.placeholder.com/600x300?text=Overall+Platform+Arch)  
*(Note: Diagram referenced as "Overall platform arch (6).png")*

#### **Core Components**
| Component | Role |
|--------|------|
| **Workload Orchestrator (WO)** | Central API for managing inference workloads (create/update/delete). Stateless, replicated FastAPI service. |
| **Workload Manager (WM)** | Per-workload controller that compiles and executes the model via `wsjob`. Containerized version of existing API server logic. |
| **Inference Brain (IB)** | Entry point for inference requests. Handles validation, tokenization, routing, and reverse proxying. |
| **Redis (HA)** | Shared state store for backend discovery, load tracking, and affinity metadata. |
| **Cluster Server (gRPC)** | Interface to Cerebras cluster software; now extended to support workload lifecycle management. |

### **2.2 Design Aspects**

#### **A. Workload Management Aspect**
- **Flow**:
  1. User sends `POST /workload` to WO.
  2. WO instructs Cluster Server to deploy a **WM Pod** (via Deployment + Headless Service + ConfigMap).
  3. WM spawns `wsjob` (compile → execute) and maintains appliance client connection.
  4. WM becomes ready once execute job is live.
  5. WO leader polls Kubernetes (via DNS resolution of headless services) and caches ready endpoints in **Redis**.

- **Replica Lifecycle**:
  - **Create**: WO → Cluster Server → WM Deployment → WM → `wsjob`
  - **Update**: Rolling update via ConfigMap + Deployment rollout (zero downtime).
  - **Delete**: WO triggers deletion of WM resources.

#### **B. Workload Invocation Aspect**
- **Flow**:
  1. User sends inference request to **IB Ingress**.
  2. IB validates and tokenizes input.
  3. IB queries **Redis** for available backends.
  4. IB applies routing logic:
     - **Affinity**: Route same prompt types to same replica (for caching).
     - **Load balancing**: Prefer less-loaded replicas.
     - *(Future)* **Request batching**: Group similar-size prompts for throughput gains.
  5. IB forwards request to selected replica via **appliance client**.
  6. IB updates Redis with in-flight request count.

---

## **3. Decision Processes**

### **3.1 Why a New Architecture?**
| Issue with Current Stack | Proposed Solution |
|-------------------------|-------------------|
| Manual on-prem setup | Standardized, scriptable deployment |
| Internal logic in API server | Decouple and expose clean APIs |
| No support for advanced routing | Introduce Inference Brain |
| Steep learning curve | Self-contained, declarative interface |

> **Key Driver**: Customer demand for **easy-to-deploy, enterprise-grade inference appliances**.

---

### **3.2 Component Decisions**

#### **Workload Orchestrator (WO)**
- **Decision**: Use **FastAPI** + **Kubernetes Ingress**.
- **Rationale**:
  - Modern, easy-to-integrate web framework.
  - Stateless → supports horizontal scaling.
  - Exposes clean REST API for integration with customer apps.

#### **Workload Manager (WM)**
- **Decision**: Containerize existing **API server logic**.
- **Rationale**:
  - Reuse battle-tested compilation and execution flow.
  - Avoid reinventing logic; focus on orchestration.
  - Security: WM runs in workload namespace; cluster server not exposed externally.

#### **Inference Brain (IB)**
- **Decision**: Separate **request handling** from **workload control**.
- **Rationale**:
  - Enables **smart routing** and **caching optimization**.
  - Supports multiple tokenizers and models.
  - Enables retry logic and observability.

#### **Redis for State Management**
- **Decision**: Use **Redis (HA)** as shared cache.
- **Rationale**:
  - Low-latency lookup for routing decisions.
  - Decouples IB from Kubernetes API.
  - Enables affinity and load tracking.

> **Ground Truth Model**:
> - WO reads from **Kubernetes (k8s)** → writes to Redis.
> - IB reads from **Redis** → fast, scalable inference routing.

---

### **3.3 Security & Authentication**
| Component | Auth Approach |
|--------|---------------|
| **WO** | Requires valid JWT token (same as cluster server). Reuses existing auth logic. |
| **IB** | Initially **no authentication** (assumes trusted internal network). Future: add auth layer. |
| **Cluster Server** | Internal-only exposure; secured via network policy (no external ingress). |

> **Trade-off**: Simplified auth for first version; extensible for future RBAC.

---

### **3.4 Weight Loading Strategy**
| Phase | Approach |
|------|---------|
| **Initial** | Weights manually copied to NFS; WM mounts volume and sends via CRD ingress. |
| **Future** | **Remote S3-compatible storage**; ACT driver loads weights directly (no client involvement). |

> **Constraint**: Remote weight loading not yet supported in cluster SW → workaround required.

---

### **3.5 Tokenizer Management**
| Phase | Strategy |
|------|----------|
| **Initial** | Pre-load common tokenizers (e.g., Llama, Qwen) into IB container. |
| **Future** | Allow users to upload tokenizers via WO; store in cluster storage. |

---

### **3.6 Monitoring & Observability**
| Option | Status |
|-------|--------|
| **Piggyback on existing Prometheus** | Preferred (simpler) |
| **Dedicated stack (Prometheus + Grafana + Alertmanager)** | For user-facing observability in future |

> **Decision**: Deferral to cluster team for integration.

---

## **4. Performance Statistics & Metrics**

### **4.1 Inference Latency & Throughput**
| Factor | Impact |
|------|--------|
| **Redis caching** | Eliminates Kubernetes API calls during routing → **<1ms lookup** |
| **Affinity routing** | Increases **prompt cache hit rate** → reduces TTFT and gen latency |
| **Load balancing** | Prevents hot replicas → improves **overall throughput** |
| **Request batching (future)** | Potential **2–3x throughput gain** (based on vLLM benchmarks) |

> **Estimate**: With prompt caching and affinity, **cache hit rate can exceed 60%** in chat scenarios.

---

### **4.2 System Scalability**
| Metric | Capability |
|------|------------|
| **Workloads per appliance** | Limited by CS-X capacity and AX memory |
| **Replicas per model** | Only constrained by k8s resource limits |
| **Requests per second (RPS)** | Scales horizontally with IB and WM replicas |
| **Routing latency (IB → replica)** | <5ms (within same cluster) |

---

### **4.3 Redis Performance Requirements**
| Metric | Requirement |
|------|-------------|
| **Reads/sec** | ~10K (for 100+ replicas, 100 RPS each) |
| **Writes/sec** | ~1K (state refresh every 30s + request updates) |
| **Persistence** | Not required — WO rebuilds state from k8s |
| **HA** | Required — Redis Sentinel or Redis Cluster |

---

## **5. Integration with Prompt Caching**

### **5.1 Affinity-Based Routing**
- **Key Benefit**: IB routes requests with **common prefixes** to the **same replica**.
- **Mechanism**:
  - IB tracks **request affinities** (e.g., prompt hash, `isolation_id`) in Redis.
  - For chat continuations, routes to replica that already has the KV cache.

> ✅ Enables **high cache hit rates** without cross-replica coordination.

---

### **5.2 Load Balancing with Caching Awareness**
- **Conflict**: Random load balancing → **cache fragmentation**.
- **Solution**: IB prioritizes **affinity match**, then applies **load balancing** as tiebreaker.

> Example: Two replicas have the same prompt cached → IB picks the **less-loaded** one.

---

### **5.3 TTL and Cache Expiry Alignment**
- **Redis tracks**:
  - `last_used` timestamp per affinity.
  - Can trigger cache cleanup if affinity inactive > TTL.
- Enables **coordinated cache expiry** with prompt caching system.

---

### **5.4 Future: Two-Level Cache Support**
- **L1**: On-replica KVSS (fast, short-term).
- **L2**: SharedKVSS (disk-backed, long-term).
- IB can query L2 if L1 miss, with optional **prefetch** on affinity match.

---

## **6. Overall Benefits**

| Benefit | Description |
|-------|-------------|
| **Ease of Use** | Users launch models via simple API — no manual setup. |
| **Scalability** | Supports multiple models, replicas, and concurrent requests. |
| **Performance** | Smart routing maximizes prompt cache utilization. |
| **Operational Simplicity** | Helm-based install/uninstall; integrates with `csctl`/`csadm`. |
| **Extensibility** | Foundation for training, multi-appliance orchestration, and advanced features. |
| **Security** | Isolated namespaces, internal-only cluster server, JWT auth. |
| **Zero Downtime Updates** | Rolling updates via Kubernetes Deployment. |

---

## **7. Implementation Plan**

| Stage | Goals | Timeline |
|------|------|---------|
| **Stage 1**<br>e2e Mock Backend | - Implement WO/IB APIs<br>- Containerize WM<br>- Mock cluster server interaction | 4–6 weeks |
| **Stage 2**<br>Real Backend | - Run WM with real CS-X<br>- Use NFS workaround for weights<br>- Validate e2e workflow | 2–3 weeks |
| **Stage 3**<br>Installation | - Helm charts for WO/IB<br>- Installation scripts<br>- Integration with `csadm` | 2 weeks |
| **Stage 4**<br>New Features | - Affinity routing<br>- Monitoring<br>- Remote weight loading | Ongoing |
| **Stage 5+** | - Migrate cloud workflows to WO<br>- Cross-appliance orchestration<br>- Training support | Future |


---

## **8. Appendix - Glossary of Terms**

| Term | Definition |
|------|-----------|
| **Workload Orchestrator (WO)** | Central service for managing inference workloads via REST API; deploys and monitors Workload Managers. |
| **Workload Manager (WM)** | Per-model controller that manages model compilation, execution, and weight loading via `wsjob`. |
| **Inference Brain (IB)** | Frontend service that validates, tokenizes, and routes inference requests to appropriate replicas. |
| **Redis** | In-memory data store used for caching backend states, load metrics, and request affinities. |
| **wsjob** | Kubernetes Custom Resource (CRD) representing a Cerebras workload (compile or execute). |
| **Cluster Server** | gRPC service that interfaces with Cerebras cluster software to manage jobs and hardware. |
| **Appliance Client** | Library used by WM and IB to communicate with cluster server and wafer systems. |
| **Prompt Caching** | Reusing previously computed KV states to accelerate inference on common prompt prefixes. |
| **Affinity Routing** | Routing requests with similar prompts to the same replica to maximize cache reuse. |
| **Headless Service** | Kubernetes service without a cluster IP; used for direct Pod discovery. |
| **Ingress** | Kubernetes resource that exposes HTTP routes to external clients. |
| **S3-Compatible Storage** | Object storage interface (e.g., MinIO, AWS S3) for storing model weights. |
| **NFS** | Network File System; used as interim solution for weight sharing. |
| **TTFT** | Time to First Token; latency metric for inference start. |
| **HA (High Availability)** | System design to ensure continuous operation despite failures. |
| **JWT (JSON Web Token)** | Secure token format for authentication and authorization. |
| **RBAC** | Role-Based Access Control; future extension for fine-grained permissions. |

--- 
