from fastapi import APIRouter

router = APIRouter()


@router.get("/registry/slm")
def get_slm_registry() -> dict:
    return {
        "family": "slm",
        "model_types": [
            {
                "id": "decoder_transformer",
                "label": "Decoder-only Transformer",
            }
        ],
        "attention": [
            {
                "id": "baseline",
                "label": "Baseline full attention",
                "description": "Standard causal self-attention.",
            },
            {
                "id": "gqa",
                "label": "Grouped Query Attention",
                "description": "Grouped-query attention for reduced KV cost.",
            },
            {
                "id": "sliding_window",
                "label": "Sliding Window Attention",
                "description": "Local attention over a fixed window.",
            },
            {
                "id": "xsa",
                "label": "XSA",
                "description": "Experimental attention variant.",
            },
        ],
        "normalization": [
            {"id": "rmsnorm", "label": "RMSNorm"},
            {"id": "layernorm", "label": "LayerNorm"},
        ],
        "mlp": [
            {"id": "gelu", "label": "GELU MLP"},
            {"id": "swiglu", "label": "SwiGLU"},
        ],
        "optimizer": [
            {"id": "adamw", "label": "AdamW"},
        ],
        "scheduler": [
            {"id": "cosine", "label": "Cosine decay"},
            {"id": "constant", "label": "Constant LR"},
        ],
        "dataset": [
            {"id": "fineweb_edu", "label": "FineWeb-Edu"},
            {"id": "local_jsonl", "label": "Local JSONL"},
            {"id": "synthetic", "label": "Synthetic"},
        ],
        "tokenizer": [
            {"id": "bpe", "label": "BPE"},
            {"id": "sentencepiece", "label": "SentencePiece"},
        ],
        "compatibility_rules": [
            {
                "id": "decoder_transformer_only",
                "message": "M7 currently supports SLM decoder-only transformer configs only.",
            },
            {
                "id": "xsa_experimental",
                "message": "XSA is experimental and should only be used with supported SLM configs.",
            },
        ],
    }