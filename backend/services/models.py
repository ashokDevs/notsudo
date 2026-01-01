"""
SQLAlchemy Models for CloudAgent.

Defines all database tables matching the schema in Supabase.
Tables were initially created by Drizzle, now managed with SQLAlchemy.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON, 
    create_engine, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import uuid
import os

Base = declarative_base()


# ======================
# Better Auth Tables
# ======================

class User(Base):
    """User table - managed by Better Auth."""
    __tablename__ = 'user'
    
    id = Column(String, primary_key=True) 
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    emailVerified = Column(Boolean, nullable=True)
    image = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    repositories = relationship("Repository", back_populates="user")
    jobs = relationship("Job", back_populates="user")
    issues = relationship("Issue", back_populates="user")


class Session(Base):
    """Session table - managed by Better Auth."""
    __tablename__ = 'session'
    
    id = Column(String, primary_key=True)
    userId = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    token = Column(String, nullable=False, unique=True)
    expiresAt = Column(DateTime, nullable=False)
    ipAddress = Column(String, nullable=True)
    userAgent = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Account(Base):
    """Account table - stores OAuth provider data."""
    __tablename__ = 'account'
    
    id = Column(String, primary_key=True)
    userId = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    accountId = Column(String, nullable=False)
    providerId = Column(String, nullable=False)
    accessToken = Column(Text, nullable=True)
    refreshToken = Column(Text, nullable=True)
    accessTokenExpiresAt = Column(DateTime, nullable=True)
    refreshTokenExpiresAt = Column(DateTime, nullable=True)
    scope = Column(String, nullable=True)
    idToken = Column(Text, nullable=True)
    password = Column(String, nullable=True) 
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Verification(Base):
    """Verification table - managed by Better Auth."""
    __tablename__ = 'verification'
    
    id = Column(String, primary_key=True)
    identifier = Column(String, nullable=False)
    value = Column(String, nullable=False)
    expiresAt = Column(DateTime, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=True)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


# ======================
# Custom Tables
# ======================

class Repository(Base):
    """Repository table - synced from GitHub."""
    __tablename__ = 'repository'
    
    id = Column(String, primary_key=True)  # GitHub repo ID
    user_id = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)  # owner/repo
    description = Column(Text, nullable=True)
    is_private = Column(Boolean, default=False, nullable=False)
    html_url = Column(String, nullable=False)
    default_branch = Column(String, default='main')
    language = Column(String, nullable=True)
    github_created_at = Column(DateTime, nullable=True)
    github_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="repositories")
    jobs = relationship("Job", back_populates="repository")
    issues = relationship("Issue", back_populates="repository")
    
    __table_args__ = (
        Index('repository_user_id_idx', 'user_id'),
        Index('repository_full_name_idx', 'full_name'),
    )


class Job(Base):
    """Job table - tracks PR generation jobs."""
    __tablename__ = 'job'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    repository_id = Column(String, ForeignKey('repository.id', ondelete='SET NULL'), nullable=True)
    issue_number = Column(Integer, nullable=False)
    issue_title = Column(String, nullable=True)
    status = Column(String, default='processing', nullable=False)  # processing, completed, failed
    stage = Column(String, default='analyzing')  # analyzing, generating, validating, completed, error
    retry_count = Column(Integer, default=0, nullable=False)
    pr_url = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    logs = Column(JSON, default=[])
    validation_logs = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    repository = relationship("Repository", back_populates="jobs")
    
    __table_args__ = (
        Index('job_user_id_idx', 'user_id'),
        Index('job_repository_id_idx', 'repository_id'),
        Index('job_status_idx', 'status'),
    )


class Issue(Base):
    """Issue table - GitHub issues that have been processed."""
    __tablename__ = 'issue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, nullable=False)
    user_id = Column(String, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    repository_id = Column(String, ForeignKey('repository.id', ondelete='CASCADE'), nullable=True)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    state = Column(String, default='open')  # open, closed
    html_url = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="issues")
    repository = relationship("Repository", back_populates="issues")
    
    __table_args__ = (
        Index('issue_user_id_idx', 'user_id'),
        Index('issue_repository_id_idx', 'repository_id'),
        Index('issue_github_id_idx', 'github_id'),
    )
