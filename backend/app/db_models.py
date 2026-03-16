from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case_progress = relationship("UserCaseProgress", back_populates="user")


class UserCaseProgress(Base):
    __tablename__ = "user_case_progress"
    __table_args__ = (UniqueConstraint("user_id", "case_id", name="uq_user_case"),)

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    case_id = Column(String, index=True, nullable=False)
    started_at = Column(DateTime, nullable=True)
    intro_seen = Column(Boolean, default=False)
    last_session_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="case_progress")

class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    case_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)
    user_email = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # State tracking
    current_stage = Column(Integer, default=1)
    completed_stages = Column(JSON, default=list) # List of ints
    message_count = Column(Integer, default=0)
    
    # Discovery tracking
    discovered_entities = Column(JSON, default=list) # List of IDs
    evidence_collected = Column(JSON, default=list) # List of IDs
    interrogated_characters = Column(JSON, default=list) # List of IDs
    contradictions_found = Column(JSON, default=list) # List of IDs
    satisfied_gates = Column(JSON, default=list) # List of strings
    
    # Large objects
    chat_history = Column(JSON, default=list)
    timeline = Column(JSON, default=list)
    
    # Persistence for frontend specific data
    notes = Column(String, default="")
    graph_state = Column(JSON, default=dict) # {nodes: {id: {x, y}}, edges: [], viewport: {}}

    def __repr__(self):
        return f"<SessionRecord(id={self.session_id}, case={self.case_id}, stage={self.current_stage})>"
