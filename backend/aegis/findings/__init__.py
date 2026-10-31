"""Findings: doğrulama, küçültme, gruplama, ATLAS eşleme."""
from aegis.findings.pipeline import FindingPipeline
from aegis.findings.atlas import ATLAS_CATALOG, map_finding_to_atlas

__all__ = ["FindingPipeline", "ATLAS_CATALOG", "map_finding_to_atlas"]
