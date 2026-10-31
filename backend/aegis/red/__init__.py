"""Red Lab: strateji kütüphanesi, hafıza.

Not: coverage katmanı aegis.red.library'yi kullanır; burada coverage
modülleri içe aktarılmaz (döngüsel import önlenir).
"""
from aegis.red.library import STRATEGY_LIBRARY, StrategyLibrary
from aegis.red.memory import RedMemory

__all__ = [
    "STRATEGY_LIBRARY",
    "StrategyLibrary",
    "RedMemory",
]
