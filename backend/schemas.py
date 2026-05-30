from typing import List, Optional

from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""


class JobIntention(BaseModel):
    position: str = ""
    expected_salary: str = ""


class Background(BaseModel):
    education: str = ""
    work_years: str = ""
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    experiences: List[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    overall_score: int = 0
    skill_score: int = 0
    experience_score: int = 0
    education_score: int = 0
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    advantages: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    summary: str = ""


class AnalyzeData(BaseModel):
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    job_intention: JobIntention = Field(default_factory=JobIntention)
    background: Background = Field(default_factory=Background)
    match_result: MatchResult = Field(default_factory=MatchResult)
    raw_text_preview: str = ""


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AnalyzeData] = None
    cached: Optional[bool] = None
