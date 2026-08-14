import uuid
from decimal import Decimal


def row_to_dict(obj):
    """SQLAlchemy row -> JSON-safe dict, matching the column names verbatim
    (camelCase columns stay camelCase, as the frontend expects)."""
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, Decimal):
            value = float(value)
        result[column.name] = value
    return result


def apply_fields(obj, data: dict, allowed: set):
    for key, value in data.items():
        if key in allowed:
            setattr(obj, key, value)
