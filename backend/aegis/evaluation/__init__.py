"""Bağımsız değerlendirme katmanı.

İlkeler:
* Red, oracle gizli değerlerine erişemez (yapısal ayırım).
* execution_status ile verdict ayrıdır.
* Modelin "gönderdim" demesi kanıt değildir; deterministik kanıt istenir.
* Canary oracle: girdide zaten bulunan metin sızıntı sayılmaz.
"""
from aegis.evaluation.oracle_vault import OracleVault, Canary
from aegis.evaluation.evaluator import IndependentEvaluator, EvaluatorResult
from aegis.evaluation.baseline import BaselineRunner

__all__ = ["OracleVault", "Canary", "IndependentEvaluator", "EvaluatorResult", "BaselineRunner"]
