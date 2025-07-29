# **Summary of Off-Wafer Prompt Caching Design**

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                        |
| Section    | research/prompt-cache-off-wafer                                        |
| Version    | 0.1                                                                    |
| Date       | 2025-07-29                                                             |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/) |
| Summarized | Prompt Cache, Cluster Design, Perf References                          |
| Inferenced | Qwen3-235B-Instruct                                                    |
| Reference  | [Inference Off-Wafer Prompt Caching](https://cerebras.atlassian.net/wiki/spaces/ENG/pages/4075028527/Inference+Off-Wafer+Prompt+Caching) | 

---

## **Overview**
This document outlines Cerebras’ **off-wafer prompt caching** system to accelerate inference by reusing Key-Value (KV) states from prior computations. When sequences share prefixes (e.g., `ABCDE` and `ABCDHIJ`), previously computed KV values for the common prefix (`ABCD`) can be **evicted and replayed** instead of recomputed — saving significant compute time.

- **Use Cases**:
  - Fixed system prompts.
  - Chat sessions with incremental user input.
- **Why Off-Wafer?**  
  On-wafer memory is too limited for long-term or large-scale caching due to the volume and duration of reusable prefixes.

### **Core Concepts**
- **Prompt caching** saves compute by reusing KV states for common prefixes.
- **SwDriver** manages cache state and protocol; **KVSS** stores data off-wafer.
- **Rail-optimized networking** and **memory fairness** are critical for performance.
- **Security**: Isolation by Org ID, configurable cache scope, TTL policies.
- **Scalability**: Designed for multi-model, multi-cache, and future features like Spec Decode and SWA.
- **Deployment Strategy**: Prefer **load-balancer affinity** over shared cache for robustness and simplicity.

> 🛠️ **Next Steps**: Implement protocol, optimize refill scheduling, support gen-token caching and multimodal inputs.

---

## **Core Components**
1. **KV Storage Servers (KVSS)**:
   - Store evicted KV cache off-wafer.
   - One or more shards per CS box (per transformer core).
   - Communicate with wafer for **eviction (egress)** and **replay (ingress)**.

2. **SwDriver**:
   - Central controller for prompt caching.
   - Manages cache logic: **lookup, refill, eviction, scheduling**.
   - Issues commands to KVSS via a defined protocol.

3. **Communication Protocol**:
   - Defines message types between SwDriver and KVSS.
   - Ensures consistency, concurrency control, and performance.

> 🔍 **Focus**: This doc covers **SwDriver logic** and **SwDriver-KVSS protocol**, deferring full KVSS design to @Summer Zeng.

---

## **Input to SwDriver (from Framework)**
For each prompt, the Framework provides in `GenerationConfig`:
- `isolation_id`: Typically **Org ID**, to prevent cross-organization cache leakage (security).
- `cache_length_allowed`: Max number of **leftmost tokens** eligible for caching.
  - Can include prompt + max gen (future).
  - Used for **security**, **privacy**, and **tiered pricing** (e.g., free users get no caching).
- **Multimodal tokens**: Currently, if present in cacheable range, `cache_length_allowed` is trimmed to text-only. Multimodal support is future work.

> ⏳ **Future Enhancements**:
> - Hints for high-reuse tokens.
> - Per-org cache policies (e.g., TTL).
> - API for dynamic policy updates.

---

## **Basic SwDriver Algorithm**
Caching operates in **cache columns** (e.g., 64 tokens per column). Replays occur in full column units.

- **On New Sequence**:
  - Hash input tokens column-by-column to find longest cached prefix (**cache hit**).
  - If hit: send `kvss_refill` to reload cached columns.
    - Set `start_recv` metadata to start refill.
    - Wait estimated refill time before picking sequence again.
  - Always: send `kvss_reserve_space` to pre-allocate memory (hint to reduce fragmentation).

- **On Sending Cache-Allowed Token**:
  - If limit exceeded: send `kvss_delete` to evict old columns (per **eviction policy**).
  - Set `do_eviction` flag and send `kvss_evict` to store new KV.
  - After completing a column: update internal **PrefixMap** with new hash entry.

- **On Sequence Termination**:
  - If final tokens don’t form full column: delete partial column via `kvss_delete`.

> 🚀 **Future Optimization**:
> - Pre-allocate and refill cache **before** picking sequence (overlap with scheduling).

---

## **Multiple Models, Buffers, and Caches**
- **Multiple Models (e.g., Draft/Target)**:
  - Separate KV caches and KVSS servers.
  - Independent refill/evict per model.
  - Broadcast messages only within a model.

- **Multiple Buffers per Cache**:
  - KV cache may be split into non-contiguous PE buffers (e.g., K/V, d=0/d=1).
  - SwDriver abstracts this; single refill → multiple wafer transfers.
  - SwDriver needs `numBuffers` (from TensorMapping API) to set `start_recv`/`wait_recv` correctly.

- **Multiple Independent Caches**:
  - Some models (e.g., Cohere Command-X) use **regular + SWA (sliding window)** caches.
  - Each cache has own rules → KVSS supports **logical cache per `cache_id`**.
  - Protocol messages include `cache_id`.

---

## **Representing the Off-Wafer Cache (SwDriver Side)**
- **Goal**: Centralized cache management → avoid back-and-forth with KVSS.
- **Structure**:
  - Per-`isolation_id` (Org) → `PrefixMap`
  - `PrefixMap`: hash → `PrefixInfo` (promptId, cachedLength, evictCount, timestamps, parent_hash)

> Example:  
> - Prompt `ABCDE` → hash(`ABCD`) stored with length=4  
> - Prompt `ABCDEFGHIJKLMN` → hash(`ABCD EFGH`) stored with length=8

- **Cache Lookup**:
  - Round down `(min(prompt_length - 1, cache_length_allowed))` to nearest column.
  - Look up hash of first column; if hit, check next combined hash, etc., until miss.
  - Refill all hit columns.

> ⚠️ **Note**: Must send at least one prompt token (can’t fully cache first token) — future work to remove this.

- **Cache Insertion**:
  - On last token of a column: compute hash of all tokens so far → add to `PrefixMap`.

---

## **SwDriver ↔ KVSS Protocol**
All messages are batched (vector) for efficiency across caches.

| Command | Purpose | Key Fields |
|--------|--------|----------|
| `kvss_reserve_space` | Hint to pre-allocate memory | `cache_id`, `prompt_id`, `start_token_idx`, `num_tokens` (estimate), optional `continue_id` |
| `kvss_refill` | Replay cached KV columns | `cache_id`, `sequenceId`, `cacheIdx`, `evictCount`, list of `RefillChunk` (prompt_id, start, num) |
| `kvss_delete` | Remove KV data | `cache_id`, `prompt_id`, `evictCount`, `startTokenIdx`, `endTokenIdx` (right-only, no holes) |
| `kvss_evict` | Ingest new KV from wafer | List of `EvictTokenEntry` (promptId, tokenIdx, sequenceId) per cache |

> ✅ **Constraints**:
> - Tokens per prompt: grow/shrink only on right.
> - No holes, no left modifications (except overwrite for Spec Decode).
> - Prompt ID 0 = discard.

---

## **Concurrency Model**
Two queues in KVSS:
- **Evict Queue**: `reserve_space`, `evict` → processed by **evict thread**
- **Refill Queue**: `refill`, `delete` → processed by **refill thread**

**Synchronization**:
- **Evict → Refill**: `evictCount` ensures refill/delete wait for correct version.
- **Refill → Evict**: `kvss_evict` blocks if no space; SwDriver ensures no deadlock.
- `kvss_reserve_space` never blocks (hint only).

---

## **Sliding Window Attention (SWA)**
- Handled entirely by SwDriver.
- Eviction proceeds normally; PrefixMap entries account for **sink tokens** and **looping**.
- Refill reconstructs logical sequence by gluing:
  - Sink tokens
  - Loop-around tokens
  - Pre-loop tokens

> ⚠️ **Limitation**: Prompt caching disabled beyond window size if window not multiple of column size.
> 🔄 Future: Support mid-window replay.

---

## **Speculative Decoding (Spec Decode)**
- Handled by SwDriver.
- Generated tokens may be speculative → only **verified tokens** are cached.
- `PrefixMap` updated post-verification with correct `evictCount`.
- Initial versions may disable gen-token caching during Spec Decode.

---

## **Cache Expiry Policy**
To address security concerns:
- Track `first_used` and `last_used` timestamps per prefix.
- Support two expiry policies:
  1. **Last-use TTL** (e.g., 1 hour)
  2. **First-use TTL** (e.g., 12 hours)

**Cleanup**:
- Background thread marks expired entries.
- Deletion done by **InferenceCore thread** (safe, non-critical path).
- For first-use expiry: recursively delete children (via `parent_hash`).

---

## **Memory Allocation on KVSS**
- Initial: Simple (INI-controlled, equal per cache).
- SwDriver **must know** exact capacity per cache.
- Future: Smarter allocation (e.g., based on usage, model needs).

---

## **Cross-Replica Considerations**
To maximize cache hits:
1. **Load Balancer Affinity** (Preferred):
   - Route requests by `isolation_id`, then prompt hash.
   - Benefits:
     - No shared state.
     - Fault isolation.
     - Easy restarts.
     - Full SwDriver cache visibility.

2. **Shared KV Cache** (Future possibility):
   - Large, disk-backed, long-lived repository.
   - SwDriver queries shared cache on local miss.
   - Challenges: latency, consistency, emergency reset.

> 💡 **Hybrid Idea**: Two-level cache:
> - L1: On-replica KVSS (fast, short-term)
> - L2: Shared "SharedKVSS" (evict only verified, full columns)

---
