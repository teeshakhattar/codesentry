"""
The contract every provider's output must satisfy before it's trusted
by the scoring engine. Gemini can be constrained to this shape at the
API level (response_schema); Groq/DeepSeek can't, so this model is what
actually enforces the contract for them — and, on the same code path,
double-checks Gemini's output too rather than trusting it blindly.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"


class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Finding(BaseModel):
    issue: str
    category: Category
    severity: Severity
    line: Optional[int] = None   # best-effort; LLM line numbers aren't
                                   # ground truth, treat as a hint for the
                                   # UI to jump near, not an exact anchor


class ReviewOutput(BaseModel):
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    clean_code: list[str] = Field(default_factory=list)
    best_practices: list[str] = Field(default_factory=list)
    score: int = Field(ge=0, le=10)