"""
Was das Raid Center beantwortet - in Worten.

**Warum diese Datei existiert.** Gemeldet wurde: "Viele wissen nicht,
inwieweit man alles überhaupt bedienen muss/kann und wo man was
findet." Bis 3.6.0 waren WeintTV, die Academy und das Archiv drei
gleichwertige Navigationspunkte, die sich unsichtbar eine Datenquelle,
einen Snapshot und eine Archivauswahl teilten; wer das nicht wusste,
sah drei Seiten, von denen zwei "keine Daten" sagten, ohne
Anhaltspunkt, woran es liegt.

Seit 4.0 ist das eine Seite mit vier Perspektiven, und dieser
Wegweiser erklärt entsprechend **vier Blicke auf einen Pull** statt
drei Bereiche. Die alten Namen kommen weiter vor: WeintTV und
WeintAcademy sind die Module, die dahinter rechnen (sie stehen in den
Einstellungen, im Addon und auf dem Discord), und das Archiv ist die
Datenquelle hinter *Quelle*. Sie sind nur keine Orte mehr, an die man
gehen muss.

Qt-frei und ohne Netz, aus demselben Grund wie
`gui/widgets/tv/analysis_gap.py`: **was die App über sich selbst sagt,
ist eine Auskunft und keine Darstellung.** Vier Ansichten, die dieselbe
Frage verschieden beantworten, sind genau der Zustand, den der
Wegweiser beheben soll - also darf es die Antwort nur einmal geben.

Zwei Regeln für die Texte hier:

- **Jeder Abschnitt beantwortet dieselben drei Fragen** (wofür, was
  tue ich, was braucht es). Einer, der einmal eine Voraussetzung nennt
  und beim nächsten nicht, liest sich wie eine Ausnahme, wo keine ist.
- **Kein Zustand.** Ob gerade Daten fliessen, steht im Kopfblock des
  Raid Centers und in der Quellenzeile unter *Quelle* - dort, wo man
  es ändern kann. Hier steht nur, wofür eine Ansicht da ist.
"""

from __future__ import annotations

from dataclasses import dataclass


GUIDE_INTRO = (
    "Ein Raid Center, vier Blicke auf **denselben** Pull: *Live* zeigt "
    "den Kampf, *Analyse* wertet ihn aus, *Lernen* sagt, was du daraus "
    "mitnimmst, *Quelle* holt einen vergangenen Kampf zurück. Der "
    "Kopfblock oben nennt immer, welchen Pull du vor dir hast - beim "
    "Wechsel der Ansicht bleibt er stehen. Du musst nichts zweimal "
    "einstellen und nirgendwo etwas erneut suchen."
)


@dataclass(frozen=True)
class GuideSection:
    """Eine Ansicht, in drei Zeilen erklärt."""

    eyebrow: str

    title: str

    purpose: str

    actions: str

    needs: str


GUIDE_SECTIONS: tuple[GuideSection, ...] = (

    GuideSection(
        eyebrow="ANSICHT 1",
        title="Live - der Kampf",
        purpose=(
            "Was im Kampf passiert: Bossleben, Pulldauer, Tode, "
            "Kampf-Rezz, Heldentum, Schaden und Heilung je Spieler, "
            "Tanks, Phasen."
        ),
        actions=(
            "Nichts einstellen müssen. *Overlay* legt dieselben Werte "
            "als kleines Fenster neben das Spiel. Läuft eine "
            "Wiedergabe, zeigt diese Ansicht die abgespielte Sekunde."
        ),
        needs=(
            "Eine Datenquelle, die gerade etwas liefert - beim Livelog "
            "also einen laufenden Raid. Ohne Kampf steht dort ehrlich "
            "\"kein laufender Kampf\" statt geschätzter Zahlen."
        ),
    ),

    GuideSection(
        eyebrow="ANSICHT 2",
        title="Analyse - die Tiefenauswertung",
        purpose=(
            "Woran der Pull hing: erhaltener Schaden und wie viel "
            "davon vermeidbar war, Wirkzeiten, Aktivzeit, "
            "Cooldown-Nutzung mit Zeitstrahl, Unterbrechungen, "
            "Mechanikfehler. Das rechnet das Modul WeintTV."
        ),
        actions=(
            "Oben rechts auf einen Spieler einschränken, sonst stehen "
            "dort 25 Namen je Tabelle. Ein Klick auf eine Zeile macht "
            "diesen Spieler zum Kontextcharakter und wechselt auf "
            "*Lernen*."
        ),
        needs=(
            "Einen abgeschlossenen Pull, dessen Tiefenauswertung die "
            "Quelle mitschickt. Fehlt ein Block, steht dort, welcher - "
            "nicht eine Reihe leerer Karten."
        ),
    ),

    GuideSection(
        eyebrow="ANSICHT 3",
        title="Lernen - was du verbessern solltest",
        purpose=(
            "Deine Rolle in diesem Pull, als Rangfolge: die zwei bis "
            "drei grössten Baustellen mit Begründung und Lektion, "
            "darunter alle sechs Bereiche mit Sternen, die Zahlen "
            "dahinter, der Trainingsplan und die Kurve über mehrere "
            "Pulls. Das rechnet das Modul WeintAcademy."
        ),
        actions=(
            "Oben im Kopfblock deinen Charakter wählen, oder *Dem "
            "Spiel folgen* eingeschaltet lassen - dann übernimmt er, "
            "wer gerade eingeloggt ist. Bei einer Baustelle führt "
            "*Moment* zur Sekunde im Kampf, *Lektion starten* zur "
            "Übung; abgehakt wird von Hand."
        ),
        needs=(
            "Denselben Pull wie *Analyse* - und dass dein Charakter "
            "darin vorkommt. Null Sterne heisst immer \"keine Daten\", "
            "nie \"schlecht\"."
        ),
    ),

    GuideSection(
        eyebrow="ANSICHT 4",
        title="Quelle - welcher Kampf?",
        purpose=(
            "Jeder Pull, der bei WarcraftLogs liegt: der Wipe von "
            "letzter Woche, der Kill von gestern, der Versuch, über "
            "den in der Gilde gesprochen wurde. Dazu die Pulls dieser "
            "Sitzung, die live mitgelaufen sind. Das ist das Archiv."
        ),
        actions=(
            "*Letzter Raid*, *Letzter Kill* oder *Bester Versuch* sind "
            "ein Klick; sonst links den Raidabend und rechts den Pull "
            "wählen, mit Suchfeld und *Nur Kills*. Danach wechselt das "
            "Raid Center von selbst auf die Analyse. Zurück zum "
            "laufenden Raid führt der Knopf oben im Kopfblock."
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
            "Woher die Zahlen kommen. Sie gilt für alle vier Ansichten "
            "zugleich; es gibt keine zweite Einstellung daneben. Der "
            "Chip im Kopfblock nennt sie immer und warnt, wenn es "
            "Beispieldaten sind."
        ),
        actions=(
            "Unter *Quelle* umschalten - der Chip im Kopfblock führt "
            "mit einem Klick dorthin. *WarcraftLogs* liest den Livelog "
            "deines Raids über den Bot; *Simulation* zeigt einen "
            "berechneten Beispiel-Pull, mit dem sich alle Ansichten "
            "auch außerhalb der Raidzeiten ansehen lassen."
        ),
        needs=(
            "Für den Livelog ein verknüpftes Discord-Konto und einen "
            "Raid, der gerade aufzeichnet. Die Simulation braucht "
            "nichts - ihre Zahlen gehören aber auch niemandem."
        ),
    ),

    GuideSection(
        eyebrow="DAHINTER",
        title="Die Wiedergabe - der Kampf Sekunde für Sekunde",
        purpose=(
            "Ein archivierter Pull, abgespielt statt als Summe "
            "gezeigt. Alle Ansichten folgen dabei derselben Sekunde: "
            "die Bewertung unter *Lernen* gilt genau dem Moment, der "
            "in *Live* zu sehen ist."
        ),
        actions=(
            "*Wiedergabe* im Kopfblock startet sie, die Leiste "
            "darunter steuert Tempo und Position. Aus einer Baustelle "
            "unter *Lernen* führt *Moment* direkt an die Sekunde, an "
            "der es passiert ist."
        ),
        needs=(
            "Einen gewählten Pull aus dem Archiv. Seine Zeitleiste holt "
            "der Bot im Hintergrund, sobald der Pull geladen ist - der "
            "Knopf bleibt bis dahin drückbar und merkt sich den Start."
        ),
    ),

)
