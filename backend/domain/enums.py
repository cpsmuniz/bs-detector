from __future__ import annotations

from enum import Enum


class RetrievalStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    DISABLED = "disabled"


class SupportLabel(str, Enum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    DOES_NOT_SUPPORT = "does_not_support"
    COULD_NOT_VERIFY = "could_not_verify"


class QuoteLabel(str, Enum):
    EXACT = "exact"
    MINOR_DIFFERENCE = "minor_difference"
    MATERIAL_DIFFERENCE = "material_difference"
    COULD_NOT_VERIFY = "could_not_verify"


class CrossDocLabel(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    PARTIALLY_SUPPORTED = "partially_supported"
    COULD_NOT_VERIFY = "could_not_verify"


class FindingKind(str, Enum):
    CITATION_SUPPORT = "citation_support"
    QUOTE_ACCURACY = "quote_accuracy"
    CROSS_DOCUMENT_CONSISTENCY = "cross_document_consistency"
