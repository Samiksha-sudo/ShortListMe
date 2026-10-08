from typing import Literal

from pydantic import BaseModel, Field


class JDAnalysisResult(BaseModel):
    role_title: str
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "principal", "unspecified"]
    required_skills: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)
