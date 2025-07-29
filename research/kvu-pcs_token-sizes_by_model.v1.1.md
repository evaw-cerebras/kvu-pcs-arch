# KVU Prompt-Cache Token Bytes - Calculations Matrix by LLM (v1.1)

| Field      | Value                                                                                                                                 | 
|------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                                                                                       |
| Section    | research/kvu-prompt-cache-token-bytes                                                                                                 |                                                   
| Version    | 1.1                                                                                                                                   |
| Date       | 2025-07-28                                                                                                                            |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/)                                                                | 
| Summarized | Prompt Cache, Cluster Design, Perf References                                                                                         |
| Inferenced | Qwen3-235B-Instruct                                                                                                                   |
| Reference  | [Large Model Training Reference](https://cerebras.atlassian.net/wiki/spaces/ENG/pages/3791159310/Large+LLM+Models+Training+Reference) |

- This is an evolved version of the origin v1 doc, with researched data for various models.

## Prompt Cache Token Size by LLM
| **Model**               |  **Model Size** |   **#Layers** | **#Attn Heads** (Q / KV) | **Head Dim** | **Precision** (bytes/elem) | **Quant Mode** | **Attn Type** | **Prompt Cache / Token** |
| ----------------------- | --------------: | ------------: | -----------------------: | -----------: | -------------------------: | -------------: | ------------: | -----------------------: |
| **Llama 3.1 – 8B**      |        **8.0B** |            32 |                   32 / 8 |          128 |             FP16 (2 bytes) |              – |           GQA |        **131,072 bytes** |
| **Llama 3.2 – 1B**      |        **3.2B** |            16 |                   32 / 8 |           64 |             FP16 (2 bytes) |              – |           GQA |         **32,768 bytes** |
| **Llama 3.2 – 3B**      |        **3.2B** |            28 |                   24 / 8 |          128 |             FP16 (2 bytes) |              – |           GQA |        **114,688 bytes** |
| **Llama 3.2 – 11B**     |         **11B** |     40 (est.) |            40 / 8 (est.) |   128 (est.) |             FP16 (2 bytes) |              – |           GQA |        **163,840 bytes** |
| **Llama 3.3 – 70B**     |         **70B** | 80 (pretrain) |            64 / 8 (est.) |   128 (est.) |             FP16 (2 bytes) |              – |           GQA |        **327,680 bytes** |
| **Llama 4 – Scout**     | **17B (109B†)** |            48 |                   40 / 8 |          128 |             FP16 (2 bytes) |              – |           GQA |        **196,608 bytes** |
| **Llama 4 – Maverick**  | **17B (402B†)** |            48 |                   40 / 8 |          128 |               FP8 (1 byte) |              – |           GQA |         **98,304 bytes** |
| **Qwen 3 – 32B**        |       **32.8B** |            64 |                   64 / 8 |   128 (est.) |             BF16 (2 bytes) |              – |           GQA |        **262,144 bytes** |
| **Qwen 3 – 235B**       | **22B (235B†)** |            94 |                   64 / 4 |   128 (est.) |             BF16 (2 bytes) |              – |           GQA |        **192,512 bytes** |
| **Gemma 3 – 4B**        |          **4B** |     36 (est.) |            32 / 8 (est.) |   128 (est.) |             BF16 (2 bytes) |              – |           GQA |        **147,456 bytes** |
| **Gemma 3 – 27B**       |         **27B** |     62 (est.) |            32 / 8 (est.) |   128 (est.) |             BF16 (2 bytes) |              – |           GQA |        **253,952 bytes** |
| *Gemma 3 – 27B (Q4\_0)* |     *27B (QAT)* |          *62* |                 *32 / 8* |        *128* |           Int4 (0.5 bytes) |          Q4\_0 |         *GQA* |         **63,488 bytes** |
| **Granite 3.3 – 8B**    |          **8B** |            40 |                   32 / 8 |          128 |             BF16 (2 bytes) |              – |           GQA |        **163,840 bytes** |
| **Granite 3.3 – 2B**    |          **2B** |     32 (est.) |                   24 / 8 |   128 (est.) |             BF16 (2 bytes) |              – |           GQA |        **131,072 bytes** |
| **Cerebras-GPT – 13B**  |         **13B** |            40 |                  40 / 40 |          128 |             FP16 (2 bytes) |              – |           MHA |        **819,200 bytes** |
| **Pleias-RAG – 1B**     |        **1.2B** |            22 |                   32 / 8 |          128 |             BF16 (2 bytes) |              – |           GQA |         **90,112 bytes** |

* † "Active / Total" parameters shown for MoE models (Llama 4 and Qwen 3) (sparse-activate _'Mixture of Experts'_)
* All models described above use grouped-query attention (GQA) unless otherwise noted. 

## Matrix Notes

### Prompt cache memory calculation
#### Variables Explained

- `${KV_Heads}` == key-value heads
- `${QR_Heads}` == query heads
- `${ATN_Heads}` == Attention Heads (ie, total of cached heads) -> `(${QR_Heads} / ${KV_Heads})`
- `${Layers}` == As name implies
- `${Head_Dim}` == Head Dimensions
- `${Element_Bytes}` == Size of each element in bytes, according to model's precision (INT8, FP16, etc)

#### Simple Equation
```
${token_size_bytes} == (2 * ${KV_Heads} * ${Head_Dim} * ${Layers} * ${Element_Bytes})
```

### Working Example
The relatively small model, `Llama 3.1–8B` offers the following operational specs to calculate

- Layers: `32 transformer ${Layers}`
- Attention Heads: `32 query heads ${QR_Heads}` and `8 key/value heads ie, ${KV_Heads}`
- Using 16-bit precision `${Elenent_Bytes} = 2`
- Equation: `Token Size == (2 × KV_Heads × Head_Dim × Layers × Element_Bytes)`
- Values: `Token Size == (2 × 8 × 128 × 32 × 2)`
- *Token Size Calculated*: each token’s prompt cache occupies `131072 bytes` or `128KB`

#### Optional Grouping Factor
If we're looking past MHA into other optimizations, then we look at the grouping factor as well

| Symbol   | Meaning                                                                    |
| -------- | -------------------------------------------------------------------------- |
| $H_Q$    | total **query** heads reported by the model                  |
| $g$      | grouping factor ( = 1 for MHA, $H_Q$ for MQA, or an intermediate value for GQA) |
| $H_{KV}$ | **key/value** heads that are actually **cached**                           |


### Numerical Example 
Using single batch, we can see the following data 
- _(specific model is irrelevant to this example, we're focused on the equation)_

| Parameter         |        Value |
| ----------------- | -----------: |
| Layers $N_L$      |           32 |
| Sequence $L$      | 4 096 tokens |
| Query heads $H_Q$ |           32 |
| Head dim $D_H$    |          128 |
| Precision         |   FP16 (2 B) |

#### Attention Optimization Differences
| Attention type | $H_{KV}$ | Total cache | Memory vs MHA |
| -------------- | -------: | ----------: | ------------: |
| MHA            |       32 |  **2.0 GB** |           1 × |
| GQA (g = 8)    |        4 |  **256 MB** |        0.13 × |
| MQA            |        1 |   **64 MB** |        0.03 × |

##### Linear scaling
Cache grows linearly with $H_{KV}$, so reducing cached heads is the most effective knob after sequence length

##### Attention Optimizations
- Switching from MHA → MQA cuts KV memory by the head count ≈32× (in the example) 
- GQA lets you trade accuracy vs memory on a continuum

##### Quantizing Optimizations
- A) Quantisation to lower bytes per entity (lower precision)
- B) Or head-pruning via a smaller Head_Dim conversion
- C) Both A and B optimizations can offer orthogonal size and memory savings


## Notes on MoE Models

### Standard Models
A standard Transformer-based LLM applies the same set of weights (all attention heads, all MLP layers) to every token at every layer, yielding uniform compute and memory usage regardless of input complexity.

### Mixture Models
A sparsely-activated Transformer variant in which each feed-forward layer is replaced by a bank of “experts” (typically small MLPs) and a lightweight gating network that routes each token (or token‐batch) to only the top-k experts for processing. This conditional computation enables models with hundreds of billions (or trillions) of parameters while only utilizing a small fraction of them per forward pass, reducing overall FLOPs and memory bandwidth compared to a fully dense model of equivalent size.

| Aspect                     | Dense LLM                                 | MoE LLM                                                                              |
| -------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------ |
| **Compute per token**      | All parameters active; FLOPs ∝ model size | Only selected experts active; FLOPs ∝ (k × expert\_size)                             |
| **Memory footprint**       | Full model activations + weights in SRAM  | Lower activation footprint; weights stored off-chip until needed                     |
| **Scalability**            | Limited by hardware to tens of billions   | Scales to hundreds of billions–trillions by sparse routing                           |
| **Throughput vs. Latency** | Predictable latency, high throughput      | Slightly higher latency (routing overhead), higher peak throughput ([IBM][1])        |
| **Training dynamics**      | Uniform gradient updates                  | Expert specialization; requires auxiliary load-balancing losses                      |
| **Use cases**              | General-purpose generation                | Large-scale pretraining; scenarios where conditional computation yields cost savings |

[1]: https://www.ibm.com/think/topics/mixture-of-experts?utm_source=chatgpt.com "What is mixture of experts? | IBM"
