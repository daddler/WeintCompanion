"""
Die Lernlogik der WeintAcademy.

Sie liegt bewusst im Analyzer und nicht in der Oberfläche: aus einem
Kampf eine Bewertung und daraus einen Trainingsplan abzuleiten ist
Auswertung, keine Darstellung. So bleibt sie ohne laufende Qt-Anwendung
testbar und kann später genauso vom Discord-Bot genutzt werden.

Die Academy wertet denselben `RaidSnapshot` aus, den auch WeintTV
anzeigt - es gibt keine zweite Datenquelle und keine zweite Rechnung.
"""

from analyzer.academy.evaluator import build_plan, build_profile
from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_LABELS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_ORDER,
    CATEGORY_ROTATION,
    Lesson,
    PlayerProfile,
    SkillRating,
    TrainingPlan,
)

__all__ = [
    "build_plan",
    "build_profile",
    "CATEGORY_COOLDOWNS",
    "CATEGORY_LABELS",
    "CATEGORY_MECHANICS",
    "CATEGORY_MOVEMENT",
    "CATEGORY_ORDER",
    "CATEGORY_ROTATION",
    "Lesson",
    "PlayerProfile",
    "SkillRating",
    "TrainingPlan",
]
