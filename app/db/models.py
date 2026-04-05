from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ExperimentStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"


class MetricType(str, enum.Enum):
    binary = "binary"
    continuous = "continuous"


class Experiment(Base):
    __tablename__ = "experiments"
    experiment_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.draft)
    metric_name = Column(String, nullable=False)
    metric_type = Column(Enum(MetricType), nullable=False)
    allocation = Column(Float, default=1.0)  # fraction of traffic in experiment

    variants = relationship("Variant", back_populates="experiment")
    assignments = relationship("Assignment", back_populates="experiment")
    events = relationship("Event", back_populates="experiment")


class Variant(Base):
    __tablename__ = "variants"
    variant_id = Column(String, primary_key=True)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    name = Column(String, nullable=False)
    allocation_weight = Column(Float, nullable=False)  # e.g. 0.5, 0.5

    experiment = relationship("Experiment", back_populates="variants")


class Assignment(Base):
    __tablename__ = "assignments"
    assignment_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    variant_id = Column(String, ForeignKey("variants.variant_id"))
    assigned_at = Column(DateTime, nullable=False)

    experiment = relationship("Experiment", back_populates="assignments")


class Event(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    event_name = Column(String, nullable=False)  # exposure, conversion, revenue, session_length
    event_value = Column(Float)
    event_time = Column(DateTime, nullable=False)

    experiment = relationship("Experiment", back_populates="events")
