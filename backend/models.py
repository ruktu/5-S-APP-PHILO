import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

from database import Base


class Action(Base):
    """5S audit findings/corrective actions. Column names are kept camelCase
    (quoted in Postgres) to match what index.html expects verbatim, so the
    frontend's legacy lowercase-fallback shim never has to trigger."""

    __tablename__ = "actions"

    actionId = Column(String, primary_key=True)
    auditId = Column(String, index=True)
    location = Column(Text)
    cleanLocation = Column(Text)
    department = Column(Text)
    owner = Column(Text)
    status = Column(Text)
    openDate = Column(String)
    dueDate = Column(String)
    closedDate = Column(String, nullable=True)
    responseScore = Column(Integer, nullable=True)
    isLate = Column(Boolean, nullable=True)
    agingDays = Column(Integer, nullable=True)
    daysToClose = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)


class LayoutCoord(Base):
    __tablename__ = "layout_coords"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    map = Column(Text)
    type = Column(Text)
    name = Column(Text)
    x = Column(Numeric)
    y = Column(Numeric)
    width = Column(Numeric)
    height = Column(Numeric)


class OwnerDirectory(Base):
    __tablename__ = "owners_directory"

    area_id = Column(Text, primary_key=True)
    owner_name = Column(Text)
    department = Column(Text)


class Perfil(Base):
    """Dormant table: only reachable if the app's Supabase-Auth login path
    (currently bypassed in checkSession()) is ever reactivated."""

    __tablename__ = "perfiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=True)
    rol = Column(Text, nullable=True)
    primer_ingreso = Column(Boolean, nullable=True, default=True)
    area = Column(Text, nullable=True)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    audit_date = Column(String)
    area_name = Column(Text)
    status = Column(Text)


class GembaEvent(Base):
    __tablename__ = "gemba_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(String, server_default=text("now()"))
    status = Column(Text, nullable=False, server_default=text("'waiting'"))
    admin_name = Column(Text)
    event_date = Column(Text)
    shift = Column(Text)
    areas = Column(Text)
    pin_code = Column(Text, unique=True, nullable=False)


class GembaParticipant(Base):
    __tablename__ = "gemba_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(String, server_default=text("now()"))
    event_id = Column(UUID(as_uuid=True), ForeignKey("gemba_events.id", ondelete="CASCADE"))
    participant_name = Column(Text, nullable=False)
    assigned_section = Column(Text, nullable=True)


class GembaLiveAction(Base):
    __tablename__ = "gemba_live_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(String, server_default=text("now()"))
    event_id = Column(UUID(as_uuid=True), ForeignKey("gemba_events.id", ondelete="CASCADE"))
    participant_id = Column(UUID(as_uuid=True), ForeignKey("gemba_participants.id", ondelete="CASCADE"))
    section = Column(Text, nullable=False)
    question = Column(Text, nullable=False)
    action_text = Column(Text, nullable=False)
    owner = Column(Text)
    due_date = Column(Text)
    priority = Column(Text)
    photo_base64 = Column(Text, nullable=True)
