"""Paylaşılan test fixture'ları."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from aegis.contracts.models import TenantContext
from aegis.targets.synthetic_assistant import build_manifest
from aegis.targets.synthetic_assistant.app import DefenseStack, SyntheticAssistant


@pytest.fixture()
def manifest():
    return build_manifest()


@pytest.fixture()
def assistant(manifest):
    return SyntheticAssistant(manifest.documents, DefenseStack())


@pytest.fixture()
def ctx():
    return TenantContext(tenant_id="tenant-alpha", user_id="red")
