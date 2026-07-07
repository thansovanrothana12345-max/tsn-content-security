import numpy as np

class SimilarityService:
    @staticmethod
    def hamming_distance(hex_hash1: str, hex_hash2: str) -> int:
        """Computes raw Hamming distance between two hex string hashes."""
        if not hex_hash1 or not hex_hash2:
            return 64
        # Pad or truncate to ensure both are same length (usually 16 chars = 64 bits)
        h1 = hex_hash1.ljust(16, '0')[:16]
        h2 = hex_hash2.ljust(16, '0')[:16]
        
        # Convert hex to integer
        val1 = int(h1, 16)
        val2 = int(h2, 16)
        
        # XOR and count set bits
        xor_val = val1 ^ val2
        return bin(xor_val).count('1')

    @classmethod
    def normalized_hamming_similarity(cls, hex_hash1: str, hex_hash2: str) -> float:
        """Returns similarity score from 0.0 to 1.0 based on Hamming distance."""
        dist = cls.hamming_distance(hex_hash1, hex_hash2)
        # Hamming distance ranges from 0 to 64
        return float(1.0 - (dist / 64.0))

    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Computes cosine similarity between two feature vectors."""
        if embedding1 is None or embedding2 is None:
            return 0.0
            
        # Standard cosine similarity formula: A . B / (||A|| * ||B||)
        dot_product = np.dot(embedding1, embedding2)
        norm_a = np.linalg.norm(embedding1)
        norm_b = np.linalg.norm(embedding2)
        
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
            
        return float(dot_product / (norm_a * norm_b))

    @classmethod
    def calculate_hybrid_score(cls, hash_score: float, embedding_score: float, weight_hash: float = 0.4) -> float:
        """Combines perceptual hash and embedding score with a weighted sum."""
        weight_embed = 1.0 - weight_hash
        return float((hash_score * weight_hash) + (embedding_score * weight_embed))
