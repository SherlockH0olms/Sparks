"""Verification Lab: bağımsız final değerlendirmesi.

Dört süit:
1. Replay — bilinen ihlal örnekleri
2. Unseen variations — düzeltme geliştirmede kullanılmamış varyasyonlar
3. Adaptive defense-aware — savunmanın izinli bilgi profili altında yeni arama
4. Utility regression — normal görevler ve yanlış engelleme

Holdout sızıntısı: geliştirme rolleri gizli final setinin ayrıntılarını
deney kapanmadan görmez.
"""
from aegis.verification.runner import VerificationRunner

__all__ = ["VerificationRunner"]
