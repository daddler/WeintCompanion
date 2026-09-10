"""
Was WeintTV, die Academy und das Archiv beantworten - in Worten.

**Warum diese Datei existiert.** Gemeldet wurde: "Viele wissen nicht,
inwieweit man alles überhaupt bedienen muss/kann und wo man was
findet." Die drei Bereiche teilen sich unsichtbar eine Datenquelle,
einen Snapshot und eine Archivauswahl; wer das nicht weiss, sieht drei
Seiten, von denen zwei "keine Daten" sagen, ohne Anhaltspunkt, woran
es liegt.

Qt-frei und ohne Netz, aus demselben Grund wie
`gui/widgets/tv/analysis_gap.py`: **was die App über sich selbst sagt,
ist eine Auskunft und keine Darstellung.** Drei Seiten, die dieselbe
Frage verschieden beantworten, sind genau der Zustand, den der
Wegweiser beheben soll - also darf es die Antwort nur einmal geben.

Zwei Regeln für die Texte hier:

- **Jeder Abschnitt beantwortet dieselben drei Fragen** (wofür, was
  tue ich, was braucht es). Einer, der einmal eine Voraussetzung nennt
  und beim nächsten nicht, liest sich wie eine Ausnahme, wo keine ist.
- **Kein Zustand.** Ob gerade Daten fliessen, steht in der
  Quellenzeile auf der Seite - dort, wo man es ändern kann. Hier steht
  nur, wofür ein Bereich da ist.
"""

from __future__ import annotations

from dataclasses import dataclass


GUIDE_INTRO = (
    "Drei Bereiche, eine Datenquelle: WeintTV zeigt den Kampf, die "
    "Academy bewertet deine Rolle darin, das Archiv holt einen "
    "vergangenen Kampf zurück. Was du im Archiv auswählst, sehen "
    "WeintTV und die Academy sofort - du musst nichts zweimal "
    "einstellen."
)


@dataclass(frozen=True)
class GuideSection:
    """Ein Bereich, in drei Zeilen erklärt."""

    eyebrow: str

    title: str

    purpose: str

    actions: str

    needs: str


GUIDE_SECTIONS: tuple[GuideSection, ...] = (

    GuideSection(
        eyebrow="BEREICH 1",
        title="WeintTV - der Kampf",
        purpose=(
            "Was im Kampf passiert ist: Bossleben, Pulldauer, Tode, "
            "Schaden und Heilung je Spieler, Cooldowns, "
            "Verbrauchsgüter."
        ),
        actions=(
            "Nichts einstellen müssen. Oben wählst du zwischen "
            "*Live* (der laufende Kampf), *Analyse* (die "
            "Tiefenauswertung eines abgeschlossenen Pulls) und "
            "*Verlauf* (die Pulls dieses Abends). Ein Klick auf einen "
            "Spieler öffnet ihn in der Academy."
        ),
        needs=(
            "Eine Datenquelle, die gerade etwas liefert - beim Livelog "
            "also einen laufenden Raid. Ohne Kampf steht dort ehrlich "
            "\"keine Daten\" statt geschätzter Zahlen."
        ),
    ),

    GuideSection(
        eyebrow="BEREICH 2",
        title="WeintAcademy - deine Rolle darin",
        purpose=(
            "Wie gut du selbst gespielt hast - sechs Bereiche mit "
            "Sternen, ein Trainingsplan daraus, und eine Kurve über "
            "mehrere Pulls hinweg."
        ),
        actions=(
            "Oben deinen Charakter wählen, oder *Dem Spiel folgen* "
            "eingeschaltet lassen - dann übernimmt sie, wer gerade "
            "eingeloggt ist. Im *Trainingsplan* hakst du ab, was du "
            "geübt hast; im *Katalog* schaltest du Lektionen aus, die "
            "dich nicht betreffen."
        ),
        needs=(
            "Denselben Kampf wie WeintTV - und dass dein Charakter "
            "darin vorkommt. Null Sterne heisst immer \"keine Daten\", "
            "nie \"schlecht\"."
        ),
    ),

    GuideSection(
        eyebrow="BEREICH 3",
        title="Archiv - ein vergangener Kampf",
        purpose=(
            "Jeden Pull, der bei WarcraftLogs liegt: der Wipe von "
            "letzter Woche, der Kill von gestern, der Versuch, über "
            "den in der Gilde gesprochen wurde."
        ),
        actions=(
            "Links den Raidabend wählen, rechts den Pull - fertig. "
            "Suchfeld und *Nur Kills* engen ein. Mit *Wiedergabe* "
            "läuft der Kampf Sekunde für Sekunde erneut ab."
        ),
        needs=(
            "Ein verknüpftes Discord-Konto: die Berichte kommen über "
            "den WeintCodex-Bot, damit nicht 25 Rechner eigene "
            "WarcraftLogs-Zugänge brauchen."
        ),
    ),

    GuideSection(
        eyebrow="DAHINTER",
        title="Die Datenquelle - der eine Schalter",
        purpose=(
            "Woher die Zahlen kommen. Sie gilt für alle drei Bereiche "
            "zugleich; es gibt keine zweite Einstellung daneben."
        ),
        actions=(
            "In der Zeile über dieser Seite umschalten. *WarcraftLogs* "
            "liest den Livelog deines Raids über den Bot; *Simulation* "
            "zeigt einen berechneten Beispiel-Pull, mit dem sich alle "
            "Ansichten auch außerhalb der Raidzeiten ansehen lassen."
        ),
        needs=(
            "Für den Livelog ein verknüpftes Discord-Konto und einen "
            "Raid, der gerade aufzeichnet. Die Simulation braucht "
            "nichts - ihre Zahlen gehören aber auch niemandem."
        ),
    ),

)
