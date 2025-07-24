
# Deriving **Per-Token Memory Size**
Understanding the Per-Token memory size in the Key Value (KV) cache depends on the **model architecture**
1. number of layers
2. attention heads, and head dimensions
3. data type: FP16, INT8, 4-bit quantized 



## Preemptive Informational Awareness
Prior to digging into this, the following aspects should be kept in mind.

1. **Per-Token KV Cache Size is Fixed**:  
   Token Size depends only on the model architecture and data type, not the sequence length.
   
2. **Quantization is Critical for Performance on Long Contexts**:  
   4-bit models reduce per-token memory by ~4x, enabling longer sequences on the same hardware, but at the potential cost of accuracy and diversity. When looking at Quantizing options, there are sub-optimizations which can offset loss, or focus on the benefits for specific compute hardware (eg system with BF16 or INT8 acceleration at hardware level).

3. **Llama3 8B vs 70B, Requires More Memory**:  
   Larger models require more memory, basic stuff there. Example, for 70B with ~2.62 MB per token (FP16), a 16k sequence would need **~41.9GB** of KV cache memory.

---

### **1. Formula for Per-Token KV Cache Size**
The KV cache stores **keys (K)** and **values (V)** for each attention head across all layers. For a single token, the memory footprint is:

$$
\text{Per-Token Size (bytes)} = 2 \times \text{num\_layers} \times \text{num\_attn\_heads} \times \text{head\_dim} \times \text{bytes\_per\_element}
$$

Where:
- `2`: Multiplied for both Key and Value matrices.
- `num_layers`: Number of transformer layers (e.g., 32 for Llama3-8B, 80 for Llama3-70B).
- `num_attn_heads`: Number of attention heads (e.g., 16 for Llama3-8B, 32 for Llama3-70B).
- `head_dim`: Dimension of each attention head (e.g., 256 for Llama3-8B, 256 for Llama3-70B).
- `bytes_per_element`: Memory per value (e.g., 2 bytes for FP16, 1 byte for INT8, 0.5 bytes for 4-bit quantization).

### **2. Notes regarding MHA vs GQA on Select Models**
Models in discussion in various Slack conversations are GQA based, which optimizes KV cache space requirements.

#### GQA (Grouped Query Attention) == Optimized

##### Benefit
GQA reduces memory bandwidth and KV‑cache overhead
        
##### Optimization Type
A variant of the Transformer’s attention mechanism that sits between standard Multi‑Head Attention (MHA) and Multi‑Query Attention (MQA). 
      
##### Technical
In GQA, the total set of query heads is partitioned into `G` groups, and each group shares its own key‐value head. By doing so, GQA reduces memory bandwidth and KV‑cache overhead—approaching the inference speed of MQA—while retaining accuracy close to full MHA.

#### MHA (Multi‑Head Attention) == Expensive

##### Benefit
Accuracy and diversity of contextual relationships

##### Optimization Type
This is the standard mechanism upon which GQA and MQA leverage their optimizations.

##### Technical
MHA is a standard self‑attention mechanism where the model projects each token’s embedding into `H` parallel sets of query, key, and value vectors (ie, `heads`), computes scaled‑dot‑product attention independently in each head, then concatenates and linearly projects the results. 

This enables the model to capture diverse contextual relationships, at the cost of significant computational and memory overhead that grows quadratically with sequence length. 

---

### **3. Calculations for Llama3 Models**
#### **Llama3-8B**
- **Parameters**:
  - `num_layers` = 32
  - `num_attn_heads` = 16
  - `head_dim` = 256
  - `bytes_per_element` = 2 (FP16)
- **Per-Token Size**:
  $$
  2 \times 32 \times 16 \times 256 \times 2 = 524,\!288\ \text{bytes} \ (\approx 0.524\ \text{MB})
  $$

#### **Llama3-70B**
- **Parameters**:
  - `num_layers` = 80
  - `num_attn_heads` = 32
  - `head_dim` = 256
  - `bytes_per_element` = 2 (FP16)
- **Per-Token Size**:
  $$
  2 \times 80 \times 32 \times 256 \times 2 = 2,\!621,\!440\ \text{bytes} \ (\approx 2.62\ \text{MB})
  $$

---

### **4. Impact of Quantization**
Quantization reduces memory usage by storing values in lower precision. Impact on accuracy or usability of the model is out of scope here, but should taken into account for usability.

- **FP16 (2 bytes)**: Default for most models.
- **INT8 (1 byte)**: Half the size of FP16.
- **4-bit Quantization (0.5 bytes)**: often seen in GGUFs

#### Example: Llama3-8B with 4-bit Quantization
$$
2 \times 32 \times 16 \times 256 \times 0.5 = 131,\!072\ \text{bytes} \ (\approx 0.131\ \text{MB per token})
$$

---

### **5. Practical Use Cases**
#### **A. Total Tokens in a given memory space**
This will vary on the method used for memory space allocation on the system, but for simple terms a synthetic equation concept follows:



Llama3-8B (FP16) on system which allocates 24GB mem per block of distributed Prompt-Cache processing resources.

$$
\text{Max Tokens} = \frac{\text{Available Memory}}{\text{Per-Token Size}} = \frac{24 \times 1024^3}{524,\!288} \approx 47,\!185\ \text{tokens}
$$
(Note: does not include overhead for activations, weights, and other buffers)

#### **B. How does this affect inference operations?**
- Longer context lengths (eg, 8k tokens) require **4.3GB** for Llama3-8B (FP16):  
  $$
  8192\ \text{tokens} \times 0.524\ \text{MB} \approx 4.3\ \text{GB}
  $$
- Quantization to 4-bit reduces this to **~1.07GB** for the same sequence

---

### **6. Calculating via Function**
```python
def calculate_per_token_kv_size(num_layers, num_heads, head_dim, bytes_per_element):
    return (2 * num_layers * num_heads * head_dim * bytes_per_element)

# Llama3-8B (FP16)
size = calculate_per_token_kv_size(32, 16, 256, 2)
print(f"Per-Token Size: {size / 1024**2:.3f} MB")  # Output: 0.524 MB
```

---
