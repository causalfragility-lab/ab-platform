from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"


class MetricType(str, Enum):
    binary = "binary"
    continuous = "continuous"


# --- Variant ---
class VariantCreate(BaseModel):
    name: str
    allocation_weight: float = Field(gt=0, le=1)


class VariantOut(BaseModel):
    variant_id: str
    name: str
    allocation_weight: float

    class Config:
        from_attributes = True


# --- Experiment ---
class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_name: str
    metric_type: MetricType
    allocation: float = Field(default=1.0, gt=0, le=1)
    variants: List[VariantCreate]


class ExperimentOut(BaseModel):
    experiment_id: str
    name: str
    description: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: ExperimentStatus
    metric_name: str
    metric_type: MetricType
    allocation: float
    variants: List[VariantOut]

    class Config:
        from_attributes = True


# --- Assignment ---
class AssignmentOut(BaseModel):
    user_id: str
    experiment_id: str
    variant_id: str
    variant_name: str
    assigned_at: datetime


# --- Event ---
class EventCreate(BaseModel):
    user_id: str
    experiment_id: str
    event_name: str
    event_value: Optional[float] = None


class EventOut(BaseModel):
    event_id: str
    user_id: str
    experiment_id: str
    event_name: str
    event_value: Optional[float]
    event_time: datetime

    class Config:
        from_attributes = True


# --- Results ---
class ArmResult(BaseModel):
    variant_id: str
    variant_name: str
    n: int
    mean: float
    std: float


class InferenceResult(BaseModel):
    experiment_id: str
    experiment_name: str
    metric_name: str
    metric_type: str
    control: ArmResult
    treatment: ArmResult
    lift_absolute: float
    lift_relative: float
    p_value: float
    ci_lower: float
    ci_upper: float
    statistically_significant: bool
    practically_significant: Optional[bool]
    interpretation: str
    sample_ratio_mismatch: bool
    srm_p_value: Optional[float]
    daily_trends: Optional[dict]
