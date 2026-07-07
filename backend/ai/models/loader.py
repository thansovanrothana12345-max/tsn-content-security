import logging

logger = logging.getLogger("backend.ai.models.loader")

class ModelLoader:
    HAS_TORCH = False
    HAS_SENTENCE_TRANSFORMERS = False
    HAS_FAISS = False
    
    try:
        import torch
        HAS_TORCH = True
    except ImportError:
        logger.warning("PyTorch is not installed in the environment. Embeddings will use mock fallbacks.")
        
    try:
        import sentence_transformers
        HAS_SENTENCE_TRANSFORMERS = True
    except ImportError:
        logger.warning("SentenceTransformers is not installed. Text/OCR embeddings will use mock fallbacks.")
        
    try:
        import faiss
        HAS_FAISS = True
    except ImportError:
        logger.warning("FAISS is not installed. Similarity check will use NumPy-based cosine searches.")

    @classmethod
    def get_clip_model(cls):
        if not cls.HAS_TORCH:
            return None
        return "CLIP_MODEL_LOADED"

    @classmethod
    def get_sentence_transformer(cls):
        if not cls.HAS_SENTENCE_TRANSFORMERS:
            return None
        return "SENTENCE_TRANSFORMERS_LOADED"
