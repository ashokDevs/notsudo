from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    
    id = Column(String, primary_key=True) 
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    emailVerified = Column(Boolean, nullable=True)
    image = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    selectedModel = Column(String, nullable=True, default='anthropic/claude-3.5-sonnet')
    customRules = Column(Text, nullable=True)
    dodoCustomerId = Column(String, nullable=True)
    
    repositories = relationship("Repository", back_populates="user")
    jobs = relationship("Job", back_populates="user")
    issues = relationship("Issue", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Session(Base):
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
    __tablename__ = 'verification'
    
    id = Column(String, primary_key=True)
    identifier = Column(String, nullable=False)
    value = Column(String, nullable=False)
    expiresAt = Column(DateTime, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=True)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


class Repository(Base):
    __tablename__ = 'repository'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_private = Column(Boolean, default=False, nullable=False)
    html_url = Column(String, nullable=False)
    default_branch = Column(String, default='main')
    language = Column(String, nullable=True)
    github_created_at = Column(DateTime, nullable=True)
    github_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="repositories")
    jobs = relationship("Job", back_populates="repository")
    issues = relationship("Issue", back_populates="repository")
    memories = relationship("CodebaseMemory", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        Index('repository_user_id_idx', 'user_id'),
        Index('repository_full_name_idx', 'full_name'),
    )


class CodebaseMemory(Base):
    __tablename__ = 'codebase_memory'

    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey('repository.id', ondelete='CASCADE'), nullable=False)
    memory = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    repository = relationship("Repository", back_populates="memories")

    __table_args__ = (
        Index('codebase_memory_repository_id_idx', 'repository_id'),
    )


class GitHubAppInstallation(Base):
    __tablename__ = 'github_app_installation'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    account_login = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    account_id = Column(Integer, nullable=False)
    target_type = Column(String, nullable=True)
    repository_selection = Column(String, default='all')
    suspended_at = Column(DateTime, nullable=True)
    access_tokens_url = Column(String, nullable=True)
    repositories_url = Column(String, nullable=True)
    html_url = Column(String, nullable=True)
    app_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('installation_user_id_idx', 'user_id'),
        Index('installation_account_login_idx', 'account_login'),
    )


class Job(Base):
    __tablename__ = 'job'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    repository_id = Column(String, ForeignKey('repository.id', ondelete='SET NULL'), nullable=True)
    issue_number = Column(Integer, nullable=True)
    issue_title = Column(String, nullable=True)
    status = Column(String, default='processing', nullable=False)
    stage = Column(String, default='analyzing')
    retry_count = Column(Integer, default=0, nullable=False)
    pr_url = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    logs = Column(JSON, default=[])
    validation_logs = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="jobs")
    repository = relationship("Repository", back_populates="jobs")
    logs_relation = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('job_user_id_idx', 'user_id'),
        Index('job_repository_id_idx', 'repository_id'),
        Index('job_status_idx', 'status'),
    )


class JobLog(Base):
    __tablename__ = 'job_log'

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey('job.id', ondelete='CASCADE'), nullable=False)
    role = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="logs_relation")

    __table_args__ = (
        Index('job_log_job_id_idx', 'job_id'),
        Index('job_log_created_at_idx', 'created_at'),
    )


class Issue(Base):
    __tablename__ = 'issue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, nullable=False)
    user_id = Column(String, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    repository_id = Column(String, ForeignKey('repository.id', ondelete='CASCADE'), nullable=True)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    state = Column(String, default='open')
    html_url = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="issues")
    repository = relationship("Repository", back_populates="issues")

    __table_args__ = (
        Index('issue_user_id_idx', 'user_id'),
        Index('issue_repository_id_idx', 'repository_id'),
        Index('issue_github_id_idx', 'github_id'),
    )


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    plan = Column(String, nullable=False)
    status = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    next_billing_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="subscriptions")

    __table_args__ = (
        Index('subscription_user_id_idx', 'user_id'),
        Index('subscription_status_idx', 'status'),
    )
