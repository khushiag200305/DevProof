"""
SQLAlchemy ORM models for DevProof's core schema (Section 4 of the
proposal): Candidate, Skill, CandidateSkill, Repository, Evidence,
Project, InterviewQuestion.

Iteration 1 only writes to Candidate, Skill, CandidateSkill and Project
(from resume parsing). Repository, Evidence and InterviewQuestion exist
now so later iterations (GitHub evidence, scoring, question generation)
have a stable schema to build against instead of migrating mid-project.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    github_username = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    skills = relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )
    repositories = relationship(
        "Repository", back_populates="candidate", cascade="all, delete-orphan"
    )
    evidence = relationship(
        "Evidence", back_populates="candidate", cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project", back_populates="candidate", cascade="all, delete-orphan"
    )
    questions = relationship(
        "InterviewQuestion", back_populates="candidate", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(Integer, primary_key=True, index=True)
    skill_name = Column(String, unique=True, nullable=False, index=True)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.skill_id"), primary_key=True)
    # STRONG / GOOD / NEEDS_VERIFICATION, assigned once GitHub evidence
    # scoring runs (Iteration 3). Left null right after resume parsing.
    status = Column(String, nullable=True)
    score = Column(Integer, nullable=True)

    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill")


class Repository(Base):
    __tablename__ = "repositories"

    repo_id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    repo_name = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    is_fork = Column(Boolean, default=False, nullable=False)
    commit_count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=True)

    candidate = relationship("Candidate", back_populates="repositories")
    evidence = relationship("Evidence", back_populates="repository")


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.skill_id"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.repo_id"), nullable=True)
    evidence_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    weight = Column(Integer, nullable=False)

    candidate = relationship("Candidate", back_populates="evidence")
    repository = relationship("Repository", back_populates="evidence")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    project_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    candidate = relationship("Candidate", back_populates="projects")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    question_id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.skill_id"), nullable=False)
    question = Column(Text, nullable=False)

    candidate = relationship("Candidate", back_populates="questions")
