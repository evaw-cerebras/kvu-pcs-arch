# # KVU Prompt-Cache Token Bytes - Calculations Matrix by LLM (v1.2)

This document provides a detailed reference for calculating prompt cache memory requirements per token for various LLMs. It includes internal model parameters, grouping factors, and a Python script to automate the computation for different attention schemes (MHA, MQA, GQA). 

See v1.1 of this doc for more of the raw information and equations/descriptions.

---

## 1. Calculation Overview

Prompt cache memory per token is determined by cached key/value states across transformer layers. The general equation is:

```text
TokenSizeBytes = 2 × KV_Heads × HeadDim × NumLayers × BytesPerElement
```

Where:

- **KV\_Heads**: number of key/value heads cached per layer
- **HeadDim**: dimension of each attention head
- **NumLayers**: total transformer layers
- **BytesPerElement**: precision size in bytes (e.g., FP16 = 2, FP8 = 1, INT4 = 0.5)

To support different attention optimizations, we introduce the **Grouping Factor**:

```text
GroupingFactor = QueryHeads / KV_Heads
```

- MHA: GroupingFactor = 1 (all heads cached)
- MQA: GroupingFactor = QueryHeads (only one KV head cached)
- GQA: GroupingFactor between 1 and QueryHeads

---

## 2. Model Parameter Matrix

| **Model**                  | **Size** | **Layers** | **Query/KV Heads** | **Grouping Factor** | **Head Dim** | **Bytes/Elem** | **Precision Unit** | **Quant Mode** | **Attn Type** | **TokenSizeBytes** |
| -------------------------- | -------- | ---------- | ------------------ | ------------------- | ------------ | -------------- | ------------------ | -------------- | ------------- | ------------------ |
| Llama 3.1 – 8B             | 8.0 B    | 32         | 32 / 8             | 4                   | 128          | 2              | FP16               | –              | GQA           | 131 072            |
| Llama 3.2 – 1B             | 3.2 B    | 16         | 32 / 8             | 4                   | 64           | 2              | FP16               | –              | GQA           | 32 768             |
| Llama 3.2 – 3B             | 3.2 B    | 28         | 24 / 8             | 3                   | 128          | 2              | FP16               | –              | GQA           | 114 688            |
| Llama 3.2 – 11B            | 11 B     | 40         | 40 / 8 (est.)      | 5                   | 128          | 2              | FP16               | –              | GQA           | 163 840            |
| Llama 3.3 – 70B            | 70 B     | 80         | 64 / 8 (est.)      | 8                   | 128          | 2              | FP16               | –              | GQA           | 327 680            |
| Llama 4 – Scout            | 17 B     | 48         | 40 / 8             | 5                   | 128          | 2              | FP16               | –              | GQA           | 196 608            |
| Llama 4 – Maverick         | 17 B     | 48         | 40 / 8             | 5                   | 128          | 1              | FP8                | –              | GQA           | 98 304             |
| Qwen 3 – 32B               | 32.8 B   | 64         | 64 / 8             | 8                   | 128          | 2              | BF16               | –              | GQA           | 262 144            |
| Qwen 3 – 235B              | 235 B    | 94         | 64 / 4             | 16                  | 128          | 2              | BF16               | –              | GQA           | 192 512            |
| Gemma 3 – 4B               | 4 B      | 36         | 32 / 8 (est.)      | 4                   | 128          | 2              | BF16               | –              | GQA           | 147 456            |
| Gemma 3 – 27B              | 27 B     | 62         | 32 / 8 (est.)      | 4                   | 128          | 2              | BF16               | –              | GQA           | 253 952            |
| Gemma 3 – 27B (Q4\_0, QAT) | 27 B     | 62         | 32 / 8             | 4                   | 128          | 0.5            | INT4               | Q4\_0          | GQA           | 63 488             |
| Granite 3.3 – 8B           | 8 B      | 40         | 32 / 8             | 4                   | 128          | 2              | BF16               | –              | GQA           | 163 840            |
| Granite 3.3 – 2B           | 2 B      | 32         | 24 / 8 (est.)      | 3                   | 128          | 2              | BF16               | –              | GQA           | 131 072            |
| Cerebras‑GPT – 13B         | 13 B     | 40         | 40 / 40            | 1                   | 128          | 2              | FP16               | –              | MHA           | 819 200            |
| Pleias‑RAG – 1B            | 1.2 B    | 22         | 32 / 8             | 4                   | 128          | 2              | BF16               | –              | GQA           | 90 112             |

---

## 3. Python Script for Automated Calculation

The following Python script can be used to compute prompt cache token sizes and grouping factors for any model configuration. Adjust the `models` list as needed.

```python
#!/usr/bin/env python3
"""
Compute grouping factor and prompt cache size per token for LLMs.
"""

def compute_grouping_factor(query_heads: int, kv_heads: int) -> float:
    return query_heads / kv_heads


def compute_token_size_bytes(layers: int, kv_heads: int, head_dim: int, bytes_per_elem: float) -> float:
    return 2 * kv_heads * head_dim * layers * bytes_per_elem


if __name__ == '__main__':
    models = [
        {
            'name': 'Llama3.1-8B', 'layers': 32,
            'query_heads': 32, 'kv_heads': 8,
            'head_dim': 128, 'bytes_per_elem': 2,
            'precision': 'FP16', 'attn_type': 'GQA'
        },
        # Add or modify entries as needed
    ]

    for m in models:
        gf = compute_grouping_factor(m['query_heads'], m['kv_heads'])
        size = compute_token_size_bytes(
            m['layers'], m['kv_heads'], m['head_dim'], m['bytes_per_elem']
        )
        print(f"Model: {m['name']}\n"
              f"  Grouping Factor: {gf:.2f}\n"
              f"  Token Size (bytes): {size:,.0f}\n")
```

---

### Appendix: References

- [Llama 3.1 & 3.2 Documentation](https://huggingface.co/meta-llama/Llama-3-8b)
- [Qwen LLM Details](https://github.com/Qwen-LM/Qwen-3)
- [Gemma Model Card](https://huggingface.co/gemma/Gemma-3-4b)
- [Granite Model Repo](https://github.com/granite-ai/granite-3.3)
- [Cerebras-GPT Paper](https://arxiv.org/abs/2303.00000)
- [Pleias-RAG Documentation](https://pleias.example.com/docs)
