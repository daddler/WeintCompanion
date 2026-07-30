"""
Allgemeine Lektionen - gültig für jede Klasse und jede Rolle.

Sie sind die Rückfallebene des Katalogs: solange für eine
Spezialisierung nichts hinterlegt ist, bekommt der Spieler trotzdem
einen sinnvollen Plan. Deshalb decken sie alle sechs Bereiche ab.

Wo es messbar ist, trägt eine Lektion `checks` - dann erkennt der
Trainingsplan selbst, ob sie im gewählten Kampf eingehalten wurde.
Lektionen ohne `checks` sind bewusst nicht messbar ("lege feste
Einsatzzeitpunkte fest") und bleiben das, was sie immer waren: Text
zum Lesen und selbst Abhaken. Einen grünen Haken dafür zu erfinden
wäre schlimmer als keiner.
"""

from __future__ import annotations

from analyzer.academy.models import (
    CATEGORY_COOLDOWNS,
    CATEGORY_MECHANICS,
    CATEGORY_MOVEMENT,
    CATEGORY_OUTPUT,
    CATEGORY_ROTATION,
    CATEGORY_SURVIVAL,
    CHECK_AT_LEAST,
    CHECK_AT_MOST,
    Lesson,
    LessonCheck,
)
from analyzer.models import (
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    ROLE_DPS,
    ROLE_HEALER,
    ROLE_TANK,
)


GENERIC_LESSONS: tuple[Lesson, ...] = (

    #
    # --------------------------------------------------
    # Rotation
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.rotation.uptime",
        title="Uptime am Ziel halten",
        category=CATEGORY_ROTATION,
        summary=(
            "Jede Sekunde ohne Angriff kostet Schaden. Ziel ist eine "
            "Aktivitätszeit von über 95 Prozent im Kampf."
        ),
        steps=(
            "Im Log die Lücken zwischen zwei Fähigkeiten suchen.",
            "Die drei längsten Lücken einer Ursache zuordnen: "
            "Bewegung, Ressourcenmangel oder Reaktionszeit.",
            "Für jede Ursache eine Gegenmaßnahme festlegen.",
        ),
        checks=(
            LessonCheck(
                metric="active_percent",
                comparison=CHECK_AT_LEAST,
                target=95.0,
                unit="%",
                label="Aktivzeit",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.rotation.resources",
        title="Ressourcen nicht überlaufen lassen",
        category=CATEGORY_ROTATION,
        summary=(
            "Volle Energie, volles Runenmal oder volle Combopunkte "
            "sind verschenkter Schaden."
        ),
        steps=(
            "Den Ressourcenverlauf über einen ganzen Pull ansehen.",
            "Zeitpunkte markieren, an denen das Maximum erreicht wurde.",
            "Den Ausgeber vorziehen, bevor das Maximum erreicht wird.",
        ),
    ),

    Lesson(
        lesson_id="generic.rotation.dots",
        title="Effekte über den ganzen Kampf halten",
        category=CATEGORY_ROTATION,
        summary=(
            "Ein abgelaufener Effekt kostet doppelt: den fehlenden "
            "Schaden und die Zeit zum Neuauftragen."
        ),
        steps=(
            "Die eigenen Dauereffekte und ihre Laufzeit notieren.",
            "Im Log die Uptime jedes einzelnen prüfen.",
            "Den schwächsten davon einen Kampf lang bewusst "
            "beobachten.",
        ),
        roles=(ROLE_DPS,),
        checks=(
            LessonCheck(
                metric="dot_uptime",
                comparison=CHECK_AT_LEAST,
                target=90.0,
                unit="%",
                label="Mittlere DoT-Uptime",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.rotation.tempo",
        title="Aktionen pro Minute steigern",
        category=CATEGORY_ROTATION,
        summary=(
            "Wer selten drückt, verliert Schaden, auch wenn nie etwas "
            "falsch gedrückt wird. Tempo ist trainierbar."
        ),
        steps=(
            "Die eigenen Aktionen pro Minute im Log ablesen.",
            "Mit einem Raidmitglied derselben Rolle vergleichen.",
            "Tastenbelegung entrümpeln: alles Wichtige in Reichweite "
            "der Ruhehand.",
        ),
    ),

    #
    # --------------------------------------------------
    # Movement
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.movement.instants",
        title="Bewegung mit Instants überbrücken",
        category=CATEGORY_MOVEMENT,
        summary=(
            "Bewegung muss keinen Schadensverlust bedeuten - sie muss "
            "nur geplant sein."
        ),
        steps=(
            "Die eigenen Fähigkeiten ohne Zauberzeit auflisten.",
            "Sie bewusst für angekündigte Bewegungsphasen aufsparen.",
            "Lange Zauber vor einer Bewegungsphase nicht mehr anfangen.",
        ),
    ),

    Lesson(
        lesson_id="generic.movement.preposition",
        title="Vorpositionieren statt nachlaufen",
        category=CATEGORY_MOVEMENT,
        summary=(
            "Wer sich vor der Mechanik bewegt, verliert keine Zeit - "
            "wer danach reagiert, verliert immer."
        ),
        steps=(
            "Die wiederkehrenden Mechaniken des Bosses notieren.",
            "Für jede einen festen Zielpunkt im Raum bestimmen.",
            "Den Weg dorthin schon vor der Ankündigung antreten.",
        ),
        checks=(
            LessonCheck(
                metric="mechanic_count",
                comparison=CHECK_AT_MOST,
                target=0.0,
                subject=MECHANIC_MOVEMENT,
                unit="×",
                label="Vermeidbare Treffer durch Bewegung",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.movement.economy",
        title="Nur so weit laufen wie nötig",
        category=CATEGORY_MOVEMENT,
        summary=(
            "Jeder Meter über das Notwendige hinaus ist Zeit ohne "
            "Schaden. Kurze, gezielte Wege schlagen große Bögen."
        ),
        steps=(
            "Den eigenen Laufweg mit dem Rollenschnitt vergleichen.",
            "Die Stellen suchen, an denen ohne Mechanik gelaufen wurde.",
            "Nach jeder Mechanik sofort zurück auf die Ausgangsposition.",
        ),
        checks=(
            LessonCheck(
                metric="movement_ratio",
                comparison=CHECK_AT_MOST,
                target=125.0,
                unit="%",
                label="Laufweg gegenüber dem Raidschnitt",
            ),
        ),
    ),

    #
    # --------------------------------------------------
    # Cooldowns
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.cooldowns.early",
        title="Cooldowns früh und oft einsetzen",
        category=CATEGORY_COOLDOWNS,
        summary=(
            "Ein Cooldown, der am Ende des Kampfes noch bereit ist, "
            "hat gar nichts gebracht."
        ),
        steps=(
            "Alle eigenen Cooldowns mit ihrer Abklingzeit auflisten.",
            "Ausrechnen, wie oft jeder in einen Pull passt.",
            "Den ersten Einsatz fest an den Kampfbeginn koppeln.",
        ),
        checks=(
            LessonCheck(
                metric="cooldown_usage",
                comparison=CHECK_AT_LEAST,
                target=80.0,
                unit="%",
                label="Genutzte von möglichen Einsätzen",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.cooldowns.potion",
        title="Kampftrank nicht vergessen",
        category=CATEGORY_COOLDOWNS,
        summary=(
            "Flask, Nahrung und Kampftrank sind der billigste "
            "Schadenszuwachs überhaupt."
        ),
        steps=(
            "Vor dem Pull Flask und Nahrung prüfen.",
            "Den Kampftrank fest an einen Zeitpunkt koppeln.",
            "Genug Vorrat für den ganzen Abend mitnehmen.",
        ),
        checks=(
            LessonCheck(
                metric="consumables_missing",
                comparison=CHECK_AT_MOST,
                target=0.0,
                unit="×",
                label="Fehlende Verbrauchsgüter",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.cooldowns.burst",
        title="Cooldowns auf das Heldentum legen",
        category=CATEGORY_COOLDOWNS,
        summary=(
            "Im Heldentum wirkt jeder Cooldown stärker. Wer daneben "
            "zündet, verschenkt einen Teil seiner Wirkung."
        ),
        steps=(
            "Mit der Raidleitung klären, wann Heldentum kommt.",
            "Die eigenen Cooldowns bis dahin aufsparen, sofern die "
            "Abklingzeit das erlaubt.",
            "Im Log prüfen, wie viele Einsätze im Fenster lagen.",
        ),
        checks=(
            LessonCheck(
                metric="cooldown_alignment",
                comparison=CHECK_AT_LEAST,
                target=30.0,
                unit="%",
                label="Einsätze im Heldentum",
            ),
        ),
    ),

    #
    # --------------------------------------------------
    # Mechaniken
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.mechanics.interrupts",
        title="Unterbrechungen zuverlässig setzen",
        category=CATEGORY_MECHANICS,
        summary=(
            "Eine verpasste Unterbrechung kostet den Raid mehr als "
            "jeder Schadensverlust."
        ),
        steps=(
            "Die zu unterbrechenden Zauber des Bosses auswendig lernen.",
            "Eine feste Unterbrechungsreihenfolge im Raid abstimmen.",
            "Die eigene Unterbrechung auf eine gut erreichbare Taste "
            "legen.",
        ),
        checks=(
            LessonCheck(
                metric="mechanic_count",
                comparison=CHECK_AT_MOST,
                target=0.0,
                subject=MECHANIC_INTERRUPT,
                unit="×",
                label="Verpasste Unterbrechungen",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.mechanics.defensives",
        title="Defensivfähigkeiten planen",
        category=CATEGORY_MECHANICS,
        summary=(
            "Persönliche Schadensreduktion gehört zur Rotation - nicht "
            "in die Panik."
        ),
        steps=(
            "Die eigenen Defensivfähigkeiten auflisten.",
            "Jeder eine feste Bossmechanik zuordnen.",
            "Nach dem Pull prüfen, ob die Zuordnung eingehalten wurde.",
        ),
    ),

    Lesson(
        lesson_id="generic.mechanics.callouts",
        title="Ansagen hören und umsetzen",
        category=CATEGORY_MECHANICS,
        summary=(
            "Die meisten Wipes entstehen nicht aus Unwissen, sondern "
            "aus verpassten Ansagen."
        ),
        steps=(
            "Vor dem Pull die drei kritischen Momente benennen.",
            "Während der Ansage nicht sprechen.",
            "Nach dem Wipe zuerst fragen, was angesagt wurde.",
        ),
    ),

    #
    # --------------------------------------------------
    # Überleben
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.survival.avoidable",
        title="Vermeidbaren Schaden auf null bringen",
        category=CATEGORY_SURVIVAL,
        summary=(
            "Jeder vermeidbare Treffer bindet Heilung, die woanders "
            "fehlt - auch wenn man ihn überlebt."
        ),
        steps=(
            "In der Analyse den eigenen vermeidbaren Schaden ansehen.",
            "Die teuerste Fähigkeit darin herausschreiben.",
            "Einen Pull lang nur auf diese eine Mechanik achten.",
        ),
        checks=(
            LessonCheck(
                metric="avoidable_share",
                comparison=CHECK_AT_MOST,
                target=10.0,
                unit="%",
                label="Anteil vermeidbaren Schadens",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.survival.stay_alive",
        title="Den Pull überleben",
        category=CATEGORY_SURVIVAL,
        summary=(
            "Ein toter Spieler macht keinen Schaden, keine Heilung und "
            "keine Mechanik mehr. Überleben schlägt alles."
        ),
        steps=(
            "Nach jedem Tod im Log die letzten fünf Sekunden ansehen.",
            "Prüfen, welche Defensive noch bereit gewesen wäre.",
            "Die Ursache benennen: Schaden, Position oder Heilung.",
        ),
        checks=(
            LessonCheck(
                metric="deaths",
                comparison=CHECK_AT_MOST,
                target=0.0,
                unit="×",
                label="Tode im Kampf",
            ),
        ),
    ),

    Lesson(
        lesson_id="generic.survival.healthstone",
        title="Selbstheilung tatsächlich benutzen",
        category=CATEGORY_SURVIVAL,
        summary=(
            "Gesundheitsstein, Heiltrank und klassenspezifische "
            "Selbstheilung sind ein Leben wert - ungenutzt sind sie "
            "nichts wert."
        ),
        steps=(
            "Vor dem Pull prüfen, ob Stein und Trank im Beutel sind.",
            "Eine feste Schwelle festlegen, ab der sie genutzt werden.",
            "Beide auf eine Taste legen, nicht ins Menü.",
        ),
    ),

    #
    # --------------------------------------------------
    # Leistung
    # --------------------------------------------------
    #

    Lesson(
        lesson_id="generic.output.compare",
        title="Mit der eigenen Rolle vergleichen",
        category=CATEGORY_OUTPUT,
        summary=(
            "Der Vergleich mit dem gesamten Raid führt in die Irre. "
            "Aussagekräftig ist nur die eigene Rolle."
        ),
        steps=(
            "Den eigenen Rang innerhalb der Rolle ablesen.",
            "Den Abstand zur Spitze in Prozent notieren.",
            "Erst danach nach der Ursache suchen - Rotation, "
            "Cooldowns oder Bewegung.",
        ),
    ),

    Lesson(
        lesson_id="generic.output.target",
        title="Am richtigen Ziel Schaden machen",
        category=CATEGORY_OUTPUT,
        summary=(
            "Schaden am falschen Ziel steht zwar in der Liste, hilft "
            "dem Raid aber nicht."
        ),
        steps=(
            "Vor dem Pull die Zielpriorität des Kampfes klären.",
            "Zielmarkierungen tatsächlich benutzen.",
            "Nach dem Pull den Schaden je Ziel prüfen.",
        ),
        roles=(ROLE_DPS,),
    ),

    Lesson(
        lesson_id="generic.output.healing_focus",
        title="Heilung dorthin lenken, wo sie zählt",
        category=CATEGORY_OUTPUT,
        summary=(
            "Viel geheilt zu haben sagt wenig - entscheidend ist, ob "
            "die Heilung angekommen ist statt zu überheilen."
        ),
        steps=(
            "Die eigene Überheilung im Log ansehen.",
            "Die Zauber mit dem höchsten Anteil herausschreiben.",
            "Bei diesen bewusst später oder gezielter wirken.",
        ),
        roles=(ROLE_HEALER,),
    ),

    Lesson(
        lesson_id="generic.output.threat",
        title="Bedrohung sicher halten",
        category=CATEGORY_OUTPUT,
        summary=(
            "Ein Boss, der sich dreht, kostet den Raid mehr als jeder "
            "verlorene Schadenspunkt."
        ),
        steps=(
            "Beim Pull einen festen Auftakt spielen.",
            "Beim Tankwechsel den Angriff nicht unterbrechen.",
            "Nach Phasenwechseln die Bedrohung neu aufbauen.",
        ),
        roles=(ROLE_TANK,),
    ),

)
