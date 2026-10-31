"""Kimlik yardımcıları."""
from aegis.contracts.models import new_id


def id_for(kind: str) -> str:
    return new_id(kind)
