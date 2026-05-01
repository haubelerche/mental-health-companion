from enum import Enum


class ReportCategory(str, Enum):
    """Categories for letter reports"""
    SPAM = "spam"
    ABUSE = "abuse"
    INAPPROPRIATE = "inappropriate"
    SELF_HARM = "self_harm"
    OTHER = "other"


class ReportStatus(str, Enum):
    """Status tracking for report moderation workflow"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"
