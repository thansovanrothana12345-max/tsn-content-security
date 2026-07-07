from pydantic import BaseModel
from typing import Optional, List, Dict

class ModalityScores(BaseModel):
    visual: float
    acoustic: float
    ocr: float
    logo: float
    metadata: float

class ConfidenceVerdict(BaseModel):
    overall_confidence: float
    confidence_level: str
    explanation: str

class DetectionResult(BaseModel):
    job_id: Optional[int] = None
    evidence_id: int
    case_id: int
    overall_similarity: float
    confidence_score: float
    confidence_level: str
    explanation: str
    modality_scores: ModalityScores
    agreements: List[str]
