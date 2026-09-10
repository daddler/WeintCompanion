"""
Simmen: ein Sim-Lauf, ein Ergebnis, ein Weg ins Spiel.

WAS DER NUTZER DENKT, UND WAS DAS SYSTEM VERLANGTE.

Er denkt: *„Ich simme meinen Charakter und will danach die Empfehlungen
im WeintCodex haben."* Das System verlangte bis 3.2.0, die interne
Trennung mitzudenken. Aus einem Sim-Lauf kommen technisch **zwei**
Auskünfte — die Wertegewichtung (*Stat Weights*) und der Zielzustand
(*Export → Link/JSON*) —, und die Seite hat sie auch als zwei geführt:
zwei Befundkarten, zwei Übernehmen-Knöpfe, zwei Entfernen-Knöpfe, zwei
Runden durch dasselbe Eingabefeld. Wer die zweite Runde vergaß, bekam im
Spiel eine Empfehlung, der man nicht ansieht, dass ihr die Hälfte fehlt.

**Die Trennung bleibt, sie hört nur auf, die Sorge des Nutzers zu
sein.** Intern gibt es weiter zwei Speicher, zwei Kanäle und zwei
Übertragungsstrings — die Gründe dafür stehen in
`../../docs/stat-weights-bridge.md` und
`../../docs/target-gear-bridge.md` und haben sich nicht geändert. Was
sich geändert hat, ist die Klammer darum: `core/sim_run.py` führt beide
als **einen Lauf**, und diese Seite zeigt genau diesen Lauf.

VIER SCHRITTE, UND JEDER HAT GENAU EINE HAUPTHANDLUNG.

1. **Charakter vorbereiten** — wer wird gesimmt, welche Spezialisierung,
   und sieht die Companion die angelegte Ausrüstung? Der Schritt hat
   keinen Knopf: er ist die Antwort auf „ist mein Charakter richtig
   erkannt".
2. **Sim öffnen und rechnen lassen** — ein Hauptknopf, daneben nur die
   beiden Auswege (*Nur die Seite*, *Export kopieren*). Der Satz, der in
   den Sim schickt, steht hier und nicht in einer eigenen Karte: eine
   Karte ohne Bedienelement wäre eine Überschrift mit Text, und gelesen
   wird er ohnehin genau in dem Moment, in dem der Knopf gedrückt wird.
3. **Sim-Ergebnis einfügen** — **ein** Feld, **ein** Befund, **ein**
   Knopf. Was eingefügt wird, erkennt die Seite an seiner Gestalt; was
   noch fehlt, sagt sie. Beide Sorten sammeln sich im selben Lauf, statt
   sich gegenseitig zu ersetzen. Seit 3.4.0 entfällt das Einfügen
   selbst: was im Sim kopiert wurde, holt sich die Seite (siehe unten).
4. **Ins Spiel übertragen** — ein Vorgang, zwei Wege dorthin, und die
   Seite entscheidet, welcher gerade gilt.

WAS AN SCHRITT 3 NOCH BEDIENUNG WAR, UND JETZT KEINE MEHR IST.

Der Weg durch den Sim endet zweimal an Strg+C — einmal unter *Stat
Weights*, einmal unter *Export*. Danach verlangte diese Seite je drei
Handgriffe, die keine Entscheidung tragen: Fenster wechseln, ins Feld
klicken, Strg+V. Sechs Handgriffe für null Entscheidungen, und sie
waren nach 3.3.0 der ganze Rest an Bedienaufwand.

`_take_from_clipboard()` nimmt jetzt, was dort liegt — aber nur, wenn
`sim_run.recognize()` es als Sim-Ausgabe ausweist. Ein Dateipfad, ein
Zitat, ein halber Befehl landen im Lauf eines Abends in derselben
Zwischenablage, und ein Feld, das sich mit Fremdem füllt, wäre
schlimmer als eins, das man selbst befüllt. Gesagt wird es trotzdem
jedes Mal (`clip_state`), und abstellen lässt es sich dort, wo es wirkt.

WAS DIE SEITE BEANTWORTEN MUSS, UND ZWAR IMMER:

* Was habe ich gerade zu tun?         → der Seitentitel, `_draw_progress()`
* Ist mein Charakter richtig erkannt? → Schritt 1
* Ist mein Sim-Ergebnis vollständig?  → `parts_line()`
* Wurde wirklich etwas optimiert?     → `change_line()`
* Was wird ins Spiel übertragen?      → Schritt 4
* Muss ich noch etwas tun?            → `next_step()`

Die sechs Sätze stehen in `core/sim_run.py` und nicht hier: sie sind die
Antwort auf eine Rechnung, und der Testlauf muss sie ohne Qt prüfen
können — dieselbe Aufteilung wie bei `gap_text()`/`age_text()`.

**Die Companion simmt nicht selbst, und das ist eine Entscheidung.**
Ein brauchbarer Sim wäre eine eigene Spielsimulation; einer, der nur so
aussieht, wäre schlimmer als keiner, weil seine Zahlen aussehen wie
echte. Dieselbe Linie wie im Addon (dort gibt es aus demselben Grund
keinen Sim) und wie beim Rotationshelfer, der den Tankspecs lieber keine
Prioritätenliste gibt als eine erfundene. Diese Seite übernimmt den
**Weg**, nicht die Rechnung.

**Was ankommt, ist ein Vorschlag und keine Einstellung.** Im Spiel füllt
die Gewichtung die Felder auf *Priorisierung* und wird erst auf Klick
wirksam. Eine Gewichtung, die sich nach einem Login von selbst geändert
hat, wäre von einem Fehler nicht zu unterscheiden.

Und dieselbe Zurückhaltung an zwei weiteren Stellen:

* **Die Grenzen aus dem Sim werden genannt, nicht übernommen.** 7,5 %
  Treffer und 15 % Waffenkunde gelten für jeden gleich; sie sind eine
  Aussage über das Spiel und stehen im Spec-Profil des Addons.
* **Eine Ausgabe für eine andere Klasse wird gemeldet, nicht
  abgewiesen.** Vielleicht simmt jemand für seinen Zweitcharakter —
  aber wissen soll er es, und der Knopf sagt dann *Trotzdem
  übernehmen*.

`refresh()` zeichnet ausschliesslich und fasst das Eingabefeld **nie**
an: die Seite wird bei jeder `state_changed` neu gezeichnet, und ein
halb eingefügter Text unter den Fingern des Nutzers wegzuräumen ist
dieselbe Falle wie beim Adressfeld in Einstellungen → Discord.
"""


from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from addon.wse_reader import NO_WOW, WseReader
from core.browser import open_url
from core.stat_weights import (
    SPECS,
    STAT_LABELS,
    STAT_ORDER,
    WeightSet,
    build_transfer,
    class_label,
    normalize,
    ordered,
    parse,
    sim_url,
    spec as spec_of,
    spec_label,
)
from core.wowsims_export import (
    age_text,
    fits_spec,
    gap_text,
    parse_export,
)
from core.wowsims_link import build_link
from core.target_gear import (
    TargetSet,
    build_transfer as build_target_transfer,
    parse_target,
)
from core import qelive
from core import sim_run
from gui.pages._page import Page
from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.restyle import restyle
from gui.widgets.card import Card
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton
from gui.widgets.select import Select
from gui.widgets.toggle_switch import ToggleSwitch
from gui.widgets.wrapped_label import enable_wrap


BASE_PAGE = "https://www.wowsims.com/mop/"


#
# DER WEG IM SIM, IN EINEM SATZ - UND NUR EINMAL IM QUELLTEXT.
#
# Er stand bis 3.1.1 zweimal wörtlich da (beim Aufbau der Karte und beim
# Zurückschalten aus dem Heiler-Zweig). Zwei Fassungen desselben Satzes
# laufen ab der ersten Änderung auseinander, und die falsche steht dann
# genau bei dem, der zwischen zwei Spezialisierungen gewechselt hat.
#
# INHALTLICH IST DER ZWEITE SATZ DER WICHTIGE. *Suggest Reforges*
# optimiert ohne Zutun nur die Umschmiedungen: die Sockelsteine bleiben,
# wie sie stecken. Wer das nicht weiß, exportiert ein Ergebnis, das
# vollständig aussieht und in dem an den Steinen nichts gerechnet wurde -
# und im Spiel folgt WeintCodex dann genau diesen unveränderten Steinen.
# Der Haken sitzt hinter dem Zahnrad neben dem Knopf, also an der einen
# Stelle, an der man ihn nicht sucht.
#
#
# AB DIESER ADDON-FASSUNG DUERFEN BEIDE ZEILEN ZUSAMMEN IN EIN FELD.
#
# WeintCodex vor 3.1.2.0 liest aus einem eingefügten Text nur den ERSTEN
# Umschlag - und zwar ohne zu meckern: sein SW-Parser zerlegt an ":" und
# nimmt Feld 6, alles dahinter fällt weg. Beide Zeilen zusammen ergäben
# dort eine Erfolgsmeldung, in der die Zielausrüstung schlicht fehlt.
#
# Genau diese Sorte Fehler ist die schlimmste: nichts bricht, nichts
# meldet sich, und im Spiel folgt WeintCodex weiter seiner eigenen
# Rechnung, obwohl auf dem Desktop längst entschieden wurde. Deshalb wird
# hier gegen die INSTALLIERTE Fassung geprüft und im Zweifel nur eine
# Zeile ausgegeben - dieselbe Vorsicht wie beim Tag-Vergleich des
# Updaters.
#
COMBINED_SINCE = (3, 1, 2, 0)


def _version_tuple(text: str) -> tuple[int, ...]:
    """
    Eine Fassung als Zahlenfolge - und `()` für alles, was keine ist.

    `()` ist dabei ausdrücklich **nicht** „ganz alt", sondern „nicht
    feststellbar" (kein Addon gefunden, `-` als Platzhalter). Der
    Aufrufer behandelt beides gleich vorsichtig, aber der Unterschied
    gehört in seinen Satz und nicht in diese Zahl.
    """

    parts = []

    for piece in str(text or "").strip().lstrip("vV").split("."):

        if not piece.isdigit():
            return ()

        parts.append(int(piece))

    return tuple(parts)


SIM_STEPS = (
    "Der Sim öffnet sich mit deiner Ausrüstung, wenn der WowSimsExporter "
    "sie im Spiel gemeldet hat. Dort dann zweierlei: erst auf das Zahnrad "
    "neben Suggest Reforges und Include gems anhaken — ohne diesen Haken "
    "rechnet der Sim nur die Umschmiedungen und lässt deine Sockelsteine, "
    "wie sie sind. Danach Suggest Reforges."
)


#
# Was in Schritt 3 zurückzuholen ist, in der Sprache des Nutzers. Der
# Satz nennt beide Knöpfe des Sims, weil sie dort verschieden heissen
# und nebeneinander liegen - und er sagt ausdrücklich, dass beides in
# dasselbe Feld gehört. Genau diese Frage („in welches Feld gehört
# was") hat die Seite bis 3.2.0 dadurch beantwortet, dass sie zwei
# Felder anbot, deren Unterschied nirgends stand.
#

PASTE_HINT = (
    "Im Sim einfach kopieren — hier musst du nichts einfügen: die "
    "Ausgabe unter Stat Weights und das Ergebnis unter Export → Link "
    "oder JSON holt sich die Companion selbst aus der Zwischenablage, "
    "sobald du zurückwechselst. Welche Sorte es ist, erkennt sie an "
    "der Gestalt; von Hand einfügen geht weiterhin."
)


#
# DIE ZWISCHENABLAGE ALS EINGANG (seit 3.4.0).
#
# WARUM ES DEN SCHRITT GAR NICHT MEHR GEBEN SOLLTE. Der Weg durch den
# Sim endet zweimal an derselben Stelle: einmal unter Stat Weights,
# einmal unter Export. Beide Male drückt der Nutzer Strg+C - und beide
# Male verlangte diese Seite danach noch drei Handgriffe, die keine
# Entscheidung tragen: Fenster wechseln, ins Feld klicken, Strg+V.
# Sechs Handgriffe für null Entscheidungen.
#
# Was die Companion dafür wissen muss, weiss sie längst: `recognize()`
# beantwortet ohne Nebenwirkung, ob ein Text aus dem Sim stammt. Was
# nicht aus dem Sim kommt, fasst das Feld nicht an - ein Dateipfad, ein
# Zitat, ein halber Befehl landen im Lauf eines Abends in derselben
# Zwischenablage.
#
# DREI DINGE SIND DABEI NICHT GESCHMACK:
#
# 1. ES WIRD GESAGT, NICHT GEZAUBERT. Ein Feld, das sich von selbst
#    füllt, ist ohne Satz daneben von einem Fehler nicht zu
#    unterscheiden. `clip_state` sagt jedes Mal, was hereinkam.
#
# 2. ES LAESST SICH ABSTELLEN. In die Zwischenablage zu sehen ist eine
#    Zumutung, die man ablehnen können muss - auch wenn hier nichts
#    davon den Rechner verlässt und nichts gespeichert wird, was nicht
#    erkannt wurde. Der Schalter steht an der Stelle, an der er wirkt,
#    nicht in den Einstellungen.
#
# 3. GELESEN WIRD NICHT LEISE. `_read(quiet=True)` gibt es für den, der
#    gerade tippt und noch nichts falsch gemacht hat. Wer Strg+C
#    gedrückt hat, ist damit fertig - ein Export ohne einen einzigen
#    gerechneten Sockelstein muss hier denselben roten Satz bekommen
#    wie beim Einlesen von Hand, sonst sieht das Auffangen aus wie
#    Erfolg.
#

CLIP_ON = (
    "Kopiertes aus dem Sim wird hier automatisch aufgefangen."
)

CLIP_OFF = (
    "Automatik aus — die Ausgabe des Sims von Hand hier einfügen."
)


def _all_gems(entry):
    """
    Alle Steine eines abgelegten Zielzustands, der Reihe nach.

    Die Nullen bleiben drin und werden vom Aufrufer gezählt: eine 0 ist
    ein Sockel ohne Angabe, kein Stein.
    """

    return [gem for item in entry.items for gem in item.gems]


def _spec_items():
    """
    Alle Spezialisierungen, nach Klasse und Name - dieselbe Ordnung,
    in der man sie sucht.
    """

    return [
        (f"{class_label(entry.class_token)} · {entry.label}", entry.key)
        for entry in sorted(
            SPECS,
            key=lambda item: (class_label(item.class_token), item.label),
        )
    ]


class SimPage(Page):

    def __init__(self, manager, parent=None):

        super().__init__(
            manager,
            eyebrow="CHARAKTER",
            title="Sim-Ergebnis übernehmen.",
            parent=parent,
        )

        self.store = getattr(manager, "stat_weights", None)

        self.sync = getattr(manager, "stat_weights_sync", None)

        self.target_store = getattr(manager, "target_gear", None)

        self.target_sync = getattr(manager, "target_gear_sync", None)

        #
        # DER OFFENE SIM-LAUF (seit 3.3.0).
        #
        # Bis 3.2.0 standen hier zwei voneinander unabhängige Merker
        # (`_parsed`/`_weights` und `_target`), und das war genau die
        # Trennung, die der Nutzer mitdenken musste: das zweite Einfügen
        # hat den ersten Befund nicht ergänzt, sondern daneben gestellt.
        #
        # Jetzt sammelt sich beides in **einem** Lauf. Er entsteht aus
        # der gemeldeten Ausrüstung (siehe `_ensure_run()`), trägt seine
        # Kennung mit ins Spiel und beantwortet dort die Frage, die
        # vorher niemand stellen konnte: gehören diese Gewichtung und
        # dieser Zielzustand zusammen?
        #

        self._run = None

        #
        # Der letzte Lesevorgang, nur für die Sätze über die Gewichtung
        # (Grenzen, Nullgewichte, unbekannte Werte). Er gehört nicht in
        # den Lauf: das sind Auskünfte über den *Text*, nicht über den
        # Vorgang.
        #

        self._parsed = None

        #
        # Was der WowSimsExporter zuletzt in seine SavedVariables
        # geschrieben hat. Gelesen wird in `on_enter()`, nicht in
        # `refresh()`: eine Datei anzufassen ist keine Zeichenarbeit,
        # und `refresh()` laeuft bei jeder `state_changed`.
        #

        self._lookup = None

        self._export = None

        self._follow_export = False

        #
        # Die Nummern der vier Schrittkarten - sie werden zu Häkchen,
        # sobald der Schritt beantwortet ist (`_draw_progress()`).
        # Angelegt vor dem ersten `_step()`, das hineinschreibt.
        #

        self._step_marks: dict[str, QLabel] = {}

        #
        # DIE ZWISCHENABLAGE: was schon angesehen wurde, und ob
        # überhaupt hingesehen werden darf.
        #
        # `_clip_seen` ist kein Zwischenspeicher, sondern eine
        # Abgrenzung: dieselbe Zwischenablage feuert je nach System
        # mehrfach für einen einzigen Strg+C, und ohne diese Zeile
        # schriebe jedes Feuern denselben Text noch einmal ins Feld -
        # mitten in das hinein, was der Nutzer gerade tut.
        #
        # Er trägt auch, was diese App SELBST kopiert hat (siehe
        # `_copy_transfer()`): der WCIMPORT-String ist der Weg *ins
        # Spiel*, und ihn zurückzulesen hiesse, das eigene Ergebnis für
        # ein neues zu halten.
        #

        self._clip_seen = ""

        self._clip_active = bool(
            getattr(manager, "config", None) is None
            or manager.config.data.get("sim_clipboard", True)
        )

        self._build_character_card()

        self._build_open_card()

        self._build_paste_card()

        self._build_delivery_card()

        self.body.addStretch(1)

        self._connect_clipboard()

        self.refresh()

    # --------------------------------------------------
    # Aufbau
    # --------------------------------------------------

    def _step(self, card: Card, number: str, text: str):
        """
        Die Kopfzeile einer Schrittkarte - Nummer, Titel, und Platz für
        ein Häkchen.

        DIE NUMMER WIRD ZUM HAEKCHEN, WENN DER SCHRITT BEANTWORTET IST.
        Vier gleich aussehende Karten untereinander sind eine
        Leseaufgabe: „wo bin ich" steht dann nur in den Sätzen, und die
        muss man alle vier lesen, um es zu wissen. Ein Häkchen
        beantwortet dieselbe Frage im Hinsehen.

        Es ersetzt keine Auskunft - jede Zeile, die vorher dastand,
        steht weiter da. Es ordnet sie nur.
        """

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        step = QLabel(number)

        step.setFont(font("mono"))

        restyle(
            step,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        row.addWidget(step, 0, Qt.AlignTop)

        self._step_marks[number] = step

        title = QLabel(text)

        title.setFont(font("card"))

        restyle(title, f"color:{tokens.WHITE};background:transparent;")

        row.addWidget(title, 1)

        card.root.addLayout(row)

    def _hint(self, card: Card, text: str, color: str = "") -> QLabel:

        label = QLabel(text)

        label.setFont(font("small"))

        enable_wrap(label)

        restyle(
            label,
            f"color:{color or tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(label)

        return label

    # --------------------------------------------------

    def _build_character_card(self):
        """
        Schritt 1: wer wird gesimmt, und sieht die Companion ihn?

        DIESE KARTE HAT KEINEN KNOPF, UND DAS IST DER PUNKT. Sie
        beantwortet zwei Fragen, bevor irgendetwas passiert - „ist mein
        Charakter richtig erkannt" und „ist das noch mein aktueller
        Stand". Beide Antworten kamen bis 3.2.0 zwischen den Knöpfen
        von Schritt 2 heraus, und dort liest sie niemand: wer einen
        Knopf sieht, drückt ihn.
        """

        card = Card()

        self._step(card, "1", "Charakter vorbereiten")

        row = QHBoxLayout()

        row.setContentsMargins(0, 0, 0, 0)

        row.setSpacing(tokens.SPACE[2])

        character_column = QVBoxLayout()

        character_column.setContentsMargins(0, 0, 0, 0)

        character_column.setSpacing(4)

        character_column.addWidget(eyebrow_label("CHARAKTER"))

        self.character_select = Select()

        self.character_select.currentIndexChanged.connect(
            self._on_character_changed,
        )

        character_column.addWidget(self.character_select)

        row.addLayout(character_column, 1)

        spec_column = QVBoxLayout()

        spec_column.setContentsMargins(0, 0, 0, 0)

        spec_column.setSpacing(4)

        spec_column.addWidget(eyebrow_label("SPEZIALISIERUNG"))

        self.spec_select = Select()

        self.spec_select.set_items(_spec_items())

        self.spec_select.currentIndexChanged.connect(
            self._on_spec_changed,
        )

        spec_column.addWidget(self.spec_select)

        row.addLayout(spec_column, 1)

        card.root.addLayout(row)

        #
        # Warum die Spezialisierung neben dem Charakter steht und nicht
        # nur aus ihm folgt: eine zweite Spec ist der Normalfall, und
        # wer sie simmt, will sie hier auch wählen können.
        #

        self.spec_hint = self._hint(
            card,
            "Zweitspezialisierung? Hier umstellen — die Gewichtung "
            "gehört im Spiel zu genau einer.",
            tokens.TEXT["faint"],
        )

        #
        # Was der Sim bekommt, und wenn nichts, warum nicht. Welcher
        # Satz das ist, entscheidet `gap_text()`.
        #

        self.gear_state = self._hint(card, "")

        self.gear_note = self._hint(card, "", tokens.TEXT["faint"])

        self.addWidget(card)

    def _build_open_card(self):
        """
        Schritt 2: den Sim öffnen und dort rechnen lassen.

        WARUM „IM SIM RECHNEN LASSEN" KEINE EIGENE KARTE IST. Eine Karte
        ohne Bedienelement wäre eine Überschrift mit einem Absatz
        darunter - und gelesen wird dieser Absatz ohnehin genau in dem
        Moment, in dem der Knopf gedrückt wird. Er steht deshalb direkt
        darüber. Inhaltlich ist er der wichtigste Satz der ganzen Seite:
        ohne *Include gems* hinter dem Zahnrad kommt ein Ergebnis
        zurück, das vollständig aussieht und an den Steinen nichts
        gerechnet hat.
        """

        card = Card()

        self._step(card, "2", "Sim öffnen und rechnen lassen")

        #
        # Der Satz wechselt mit der Spezialisierung: für Heiler geht
        # der Weg über QE Live, und dort gibt es weder eine Adresse,
        # die die Ausrüstung mitbringt, noch etwas, das zurückkommt.
        # Siehe `_draw_source()`.
        #

        self.source_hint = self._hint(card, SIM_STEPS)

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.open_button = HeroButton("Sim mit meiner Ausrüstung öffnen")

        self.open_button.clicked.connect(self._open_sim)

        buttons.addWidget(self.open_button)

        self.plain_button = HeroButton("Nur die Seite", primary=False)

        self.plain_button.clicked.connect(self._open_plain)

        buttons.addWidget(self.plain_button)

        self.copy_export_button = HeroButton(
            "Export kopieren",
            primary=False,
        )

        self.copy_export_button.clicked.connect(self._copy_export)

        buttons.addWidget(self.copy_export_button)

        buttons.addStretch(1)

        card.root.addLayout(buttons)

        #
        # Die Rückmeldung des Kopierens hat eine eigene Zeile, weil
        # `_draw_gear()` bei jeder `state_changed` über die Zeile in
        # Schritt 1 schreibt - das "Kopiert." wäre nach Sekunden weg,
        # und wer kurz wegsieht, hält den Knopf für kaputt.
        #

        self.gear_copy_state = self._hint(card, "", tokens.TEXT["faint"])

        self.url_label = QLabel("")

        self.url_label.setFont(font("small"))

        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        restyle(
            self.url_label,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        card.root.addWidget(self.url_label)

        self.addWidget(card)

    def _build_paste_card(self):
        """
        Schritt 3: das Ergebnis zurückbringen - **ein** Feld, **ein**
        Befund, **ein** Knopf.

        WARUM ES NICHT MEHR ZWEI KARTEN SIND. Gewichtung und
        Zielzustand sind zwei Auskünfte, und die Trennung stimmt
        technisch weiter - zwei Speicher, zwei Kanäle, zwei Strings.
        Nur beantwortet sie eine Frage, die der Nutzer nicht hat. Er
        hat einmal gesimmt; was dabei herauskam, ist für ihn *das
        Ergebnis*. Zwei Karten mit je einem Übernehmen-Knopf haben aus
        einem Vorgang zwei gemacht, und der zweite blieb regelmäßig
        liegen — was einer Empfehlung im Spiel nicht anzusehen ist.

        Beide Sorten **sammeln** sich jetzt im selben Lauf: das zweite
        Einfügen ergänzt den ersten Befund, statt ihn zu ersetzen. Was
        noch fehlt, sagt `parts_line()`; was als Nächstes zu tun ist,
        `next_step()`.
        """

        card = Card()

        self._step(card, "3", "Sim-Ergebnis einfügen")

        self._hint(card, PASTE_HINT)

        #
        # Für Heiler bleibt diese Karte stehen und bekommt einen Satz:
        # QE Live liefert nichts, was hier hineingehört. Eine Karte,
        # die nichts sagt, ist von einer kaputten nicht zu
        # unterscheiden - und wer sie leer lässt, sucht die Ausgabe,
        # die es dort nicht gibt. Ausgeblendet wird sie nicht: eine
        # von Hand getippte Gewichtung geht hier weiterhin (lock,
        # don't hide).
        #

        self.paste_gap = self._hint(card, "", tokens.STATE_TEXT["warn"])

        #
        # DER SCHALTER STEHT DA, WO ER WIRKT.
        #
        # In die Zwischenablage zu sehen ist eine Zumutung, und wer sie
        # ablehnen will, soll das nicht in den Einstellungen suchen
        # müssen - er hat die Frage genau hier, beim Blick auf das
        # Feld, das sich von selbst füllt.
        #

        automatik = QHBoxLayout()

        automatik.setContentsMargins(0, 0, 0, 0)

        automatik.setSpacing(tokens.SPACE[2])

        self.clip_toggle = ToggleSwitch(self._clip_active)

        self.clip_toggle.toggled.connect(self._set_clipboard_pickup)

        automatik.addWidget(self.clip_toggle, 0, Qt.AlignVCenter)

        self.clip_label = QLabel(CLIP_ON if self._clip_active else CLIP_OFF)

        self.clip_label.setFont(font("small"))

        enable_wrap(self.clip_label)

        restyle(
            self.clip_label,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        automatik.addWidget(self.clip_label, 1)

        card.root.addLayout(automatik)

        self.input = QPlainTextEdit()

        self.input.setMinimumHeight(120)

        self.input.setFont(font("mono"))

        self.input.setPlaceholderText(
            "Füllt sich, sobald du im Sim etwas kopierst — Stat Weights "
            "oder Export → Link/JSON. Von Hand einfügen geht genauso, "
            "ein Wertname und eine Zahl je Zeile auch."
        )

        #
        # GELESEN WIRD BEIM EINFÜGEN, NICHT ERST AUF KLICK (seit 3.1.1).
        #
        # *Einlesen* war ein Klick ohne eigene Entscheidung: es gibt
        # keinen Grund, einen eingefügten Text NICHT zu lesen. Der Knopf
        # bleibt trotzdem stehen, und zwar für den einen Fall, in dem er
        # etwas kann, was das Lesen nebenher nicht darf: einen **Fehler
        # sagen**. Wer mitten im Tippen ist, hat noch keine falsche
        # Eingabe gemacht - eine rote Zeile nach jedem Zeichen erzieht
        # nur dazu, rote Zeilen zu übersehen. Deshalb ist das Lesen
        # nebenher still: es zeigt einen Befund, wenn es einen gibt, und
        # sonst nichts.
        #
        self._suppress_read = False

        self._read_timer = QTimer(self)

        self._read_timer.setSingleShot(True)

        self._read_timer.setInterval(250)

        self._read_timer.timeout.connect(self._read_quiet)

        self.input.textChanged.connect(self._on_input_changed)

        card.root.addWidget(self.input)

        #
        # WAS HEREINKAM, BEKOMMT EINEN SATZ. Ein Feld, das sich von
        # selbst füllt, ist ohne diese Zeile von einem Fehler nicht zu
        # unterscheiden - und wer gerade auf den Sim gesehen hat, hat
        # das Füllen nicht gesehen. Sie steht getrennt vom Befund, weil
        # sie etwas anderes beantwortet: nicht „was ist das", sondern
        # „woher kommt es".
        #

        self.clip_state = self._hint(card, "", tokens.TEXT["faint"])

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.read_button = HeroButton("Einlesen", primary=False)

        self.read_button.clicked.connect(self._read)

        buttons.addWidget(self.read_button)

        self.clear_button = HeroButton("Feld leeren", primary=False)

        self.clear_button.clicked.connect(self._clear_input)

        buttons.addWidget(self.clear_button)

        buttons.addStretch(1)

        card.root.addLayout(buttons)

        #
        # DER BEFUND, IN VIER ZEILEN MIT VIER AUFGABEN.
        #
        #   result   was ist das hier (ein Satz, die Überschrift)
        #   parts    was liegt vor, was fehlt (die Häkchenzeile)
        #   notes    wurde wirklich optimiert (Zahlen, nachzählbar)
        #   hint     was jetzt zu tun ist (und nichts, wenn nichts)
        #   problem  was schiefging (nur auf Klick, siehe `quiet`)
        #
        # Getrennt, weil sie zu Verschiedenem raten. Ein Hinweis, der
        # wie ein Fehler aussieht, wird entweder fälschlich ernst
        # genommen oder lehrt, Fehler zu übersehen.
        #

        self.result = QLabel("")

        self.result.setFont(font("body"))

        enable_wrap(self.result)

        restyle(
            self.result,
            f"color:{tokens.WHITE};background:transparent;",
        )

        card.root.addWidget(self.result)

        self.parts = QLabel("")

        self.parts.setFont(font("mono"))

        enable_wrap(self.parts)

        restyle(
            self.parts,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.parts)

        self.notes = QLabel("")

        self.notes.setFont(font("small"))

        enable_wrap(self.notes)

        restyle(
            self.notes,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.notes)

        self.hint = QLabel("")

        self.hint.setFont(font("small"))

        enable_wrap(self.hint)

        restyle(
            self.hint,
            f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
        )

        card.root.addWidget(self.hint)

        #
        # Die Feinheiten über die Gewichtung (Nullgewichte, Grenzen,
        # unbekannte Werte) stehen weiterhin vollständig da - jede von
        # ihnen ist ein stilles Verschwinden, wenn sie fehlt. Sie
        # stehen nur leiser: der Ablauf liest sich sonst nicht mehr.
        #

        self.details = QLabel("")

        self.details.setFont(font("small"))

        enable_wrap(self.details)

        restyle(
            self.details,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        card.root.addWidget(self.details)

        self.problem = QLabel("")

        self.problem.setFont(font("small"))

        enable_wrap(self.problem)

        restyle(
            self.problem,
            f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
        )

        card.root.addWidget(self.problem)

        self.apply_button = HeroButton("Sim-Ergebnis übernehmen")

        self.apply_button.clicked.connect(self._apply)

        self.apply_button.setEnabled(False)

        card.root.addWidget(self.apply_button, 0, Qt.AlignLeft)

        self.addWidget(card)

    def _build_delivery_card(self):
        """
        Schritt 4: **ein** Vorgang namens „ins Spiel übertragen".

        Intern sind es zwei Wege, und beide werden gebraucht: die
        Addon-Brücke (zugestellt, wirkt beim nächsten `/reload`) und der
        String für das Importfeld (wirkt sofort, auch mitten in einer
        Gruppe). Der Nutzer muss zwischen ihnen nicht wählen - die
        Companion tut beides und sagt, was daraus folgt.
        """

        card = Card()

        self._step(card, "4", "Ins Spiel übertragen")

        self.stored = QLabel("")

        self.stored.setFont(font("body"))

        enable_wrap(self.stored)

        restyle(
            self.stored,
            f"color:{tokens.WHITE};background:transparent;",
        )

        card.root.addWidget(self.stored)

        self.stored_weights = QLabel("")

        self.stored_weights.setFont(font("mono"))

        enable_wrap(self.stored_weights)

        restyle(
            self.stored_weights,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        card.root.addWidget(self.stored_weights)

        #
        # Aus welchem Lauf das Abgelegte stammt. Es muss niemandem
        # auffallen; es muss dastehen, wenn jemand fragt, warum eine
        # Empfehlung im Spiel so aussieht, wie sie aussieht.
        #

        self.run_line = QLabel("")

        self.run_line.setFont(font("small"))

        enable_wrap(self.run_line)

        restyle(
            self.run_line,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        card.root.addWidget(self.run_line)

        self.delivery_hint = self._hint(card, "")

        #
        # DIE WARNUNG, DIE EIN STILLES VERSCHLUCKEN VERHINDERT.
        #
        # WeintCodex vor 3.1.2.0 liest aus einem eingefügten Text nur
        # den ERSTEN Umschlag - und zwar ohne zu meckern: sein
        # SW-Parser zerlegt an ":" und liest Feld 6, alles dahinter
        # fällt weg. Beide Zeilen zusammen ergäben dort eine
        # Erfolgsmeldung, in der die Zielausrüstung fehlt. Deshalb
        # kommt bei einem zu alten Addon gar nicht erst beides ins
        # Feld (siehe `_delivery_lines()`), und hier steht, warum.
        #
        # Dieselbe Warnzeile trägt seit 3.3.0 den zweiten Fall, den man
        # einer Empfehlung im Spiel nicht ansieht: eine Gewichtung und
        # ein Zielzustand aus **zwei verschiedenen Läufen**.
        #

        self.delivery_warn = QLabel("")

        self.delivery_warn.setFont(font("small"))

        enable_wrap(self.delivery_warn)

        restyle(
            self.delivery_warn,
            f"color:{tokens.STATE_TEXT['warn']};background:transparent;",
        )

        card.root.addWidget(self.delivery_warn)

        #
        # Mehrzeilig, weil zwei Umschläge hineingehören - je einer pro
        # Zeile. Eine einzeilige Zeile hätte den zweiten unsichtbar
        # angehängt.
        #

        self.transfer = QPlainTextEdit()

        self.transfer.setReadOnly(True)

        self.transfer.setFont(font("mono"))

        self.transfer.setFixedHeight(74)

        card.root.addWidget(self.transfer)

        buttons = QHBoxLayout()

        buttons.setContentsMargins(0, 0, 0, 0)

        buttons.setSpacing(tokens.SPACE[2])

        self.copy_button = HeroButton("Ins Spiel übertragen")

        self.copy_button.clicked.connect(self._copy_transfer)

        buttons.addWidget(self.copy_button)

        #
        # EIN VERWERFEN STATT ZWEIER (seit 3.3.0). „Gewichtung
        # entfernen" und „Zielausrüstung entfernen" waren zwei Knöpfe
        # für eine Absicht - wer das Ergebnis loswerden will, will es
        # ganz loswerden, und die halbe Löschung hinterlässt genau die
        # Mischung aus zwei Läufen, vor der die Warnzeile darüber warnt.
        #

        self.remove_button = HeroButton(
            "Sim-Ergebnis verwerfen",
            primary=False,
        )

        self.remove_button.clicked.connect(self._remove)

        buttons.addWidget(self.remove_button)

        buttons.addStretch(1)

        card.root.addLayout(buttons)

        self.copy_state = QLabel("")

        self.copy_state.setFont(font("small"))

        enable_wrap(self.copy_state)

        restyle(
            self.copy_state,
            f"color:{tokens.TEXT['faint']};background:transparent;",
        )

        card.root.addWidget(self.copy_state)

        self.addWidget(card)

    # --------------------------------------------------
    # Die Zwischenablage als Eingang
    # --------------------------------------------------

    def _connect_clipboard(self):
        """
        Zwei Anlässe, hinzusehen - und beide sind derselbe Moment.

        `dataChanged` feuert, wenn kopiert wird, solange diese App die
        Zwischenablage sehen darf. Unter Wayland darf sie das nur, wenn
        sie den Fokus hat - dort feuert also nichts, während der Nutzer
        im Browser ist. **Genau dafür der zweite Anlass:** wer
        zurückwechselt, macht die Companion aktiv, und dann wird
        nachgesehen. Auf den Nutzer wirkt beides gleich; ohne den
        zweiten Anlass wäre die Automatik auf der halben Linux-Welt
        eine, die nie anspringt.

        Gebundene Methoden, keine Lambdas: `QGuiApplication` lebt so
        lange wie das Programm, und eine Lambda darin hielte diese
        Seite für immer fest (dieselbe Regel wie beim ThemeManager,
        `docs/architecture/theming.md`).
        """

        clipboard = QGuiApplication.clipboard()

        if clipboard is not None:
            clipboard.dataChanged.connect(self._clipboard_changed)

        app = QGuiApplication.instance()

        if app is not None and hasattr(app, "applicationStateChanged"):
            app.applicationStateChanged.connect(self._app_state_changed)

    def _clipboard_changed(self):

        self._take_from_clipboard()

    def _app_state_changed(self, state):
        """
        Die Companion wird wieder aktiv - also kommt jemand zurück.

        Zurück kommt man aus genau zwei Richtungen, und beide bringen
        etwas mit: aus dem Sim ein Ergebnis in der Zwischenablage, aus
        dem Spiel eine frisch bereitgestellte Ausrüstung in den
        SavedVariables. Bis 3.3.0 hat die Seite beides erst beim
        **Betreten** bemerkt - wer sie offen liegen liess und im Spiel
        bereitstellte, musste einmal weg- und wieder hinnavigieren,
        damit Schritt 1 aufhörte, den alten Stand zu behaupten.

        Eine Datei anzufassen ist Aufwand, aber `on_enter()` tut
        dasselbe und aus demselben Grund; was hier ausdrücklich **nicht**
        passiert, ist ein Netzabruf - und in `refresh()` steht davon
        nichts (`docs/architecture/navigation.md`).
        """

        if state != Qt.ApplicationActive:
            return

        if not self.isVisible():
            return

        self.read_export()

        self.refresh()

        self._take_from_clipboard()

    def _set_clipboard_pickup(self, on: bool):

        self._clip_active = bool(on)

        self.clip_label.setText(CLIP_ON if on else CLIP_OFF)

        config = getattr(self.manager, "config", None)

        if config is not None:

            config.data["sim_clipboard"] = self._clip_active

            config.save()

        if not on:

            self.clip_state.setText("")

            return

        #
        # Beim Einschalten gleich nachsehen: wer den Schalter umlegt,
        # hat in aller Regel eben etwas kopiert, das nicht ankam.
        #

        self._take_from_clipboard(force=True)

    def _take_from_clipboard(self, force: bool = False):
        """
        Was in der Zwischenablage liegt, ins Feld - **wenn** es aus dem
        Sim stammt.

        Die Entscheidung darüber fällt in `sim_run.recognize()` und
        nirgends sonst: sie ist dieselbe, nach der auch `_read()` die
        beiden Sorten auseinanderhält. Alles andere wird nicht
        angefasst, nicht gemeldet und nicht gemerkt.

        **Gelesen wird laut** (`quiet=False`). Das leise Lesen gibt es
        für den, der gerade tippt und noch nichts falsch gemacht hat;
        wer Strg+C gedrückt hat, ist fertig. Ein Sim-Export, in dem
        kein einziger Sockelstein gerechnet wurde, muss hier denselben
        roten Satz bekommen wie beim Einlesen von Hand - sonst sähe das
        Auffangen aus wie Erfolg, und im Spiel folgte WeintCodex
        anschliessend unveränderten Steinen.
        """

        if not self._clip_active:
            return

        #
        # SICHTBARKEIT IST DIE GRENZE - AUSSER, WENN GERADE GEFRAGT
        # WURDE. Beim Betreten der Seite und beim Umlegen des Schalters
        # ist die Absicht des Nutzers der Anlass, nicht ein Ereignis von
        # aussen; ob Qt das Widget in diesem Augenblick schon als
        # sichtbar führt, ist dann eine Frage über die Animation und
        # nicht über ihn.
        #

        if not force and not self.isVisible():
            return

        clipboard = QGuiApplication.clipboard()

        if clipboard is None:
            return

        try:
            text = (clipboard.text() or "").strip()

        except Exception:

            #
            # Fremde Zwischenablage, fremdes Format, kein X-Server -
            # eine Seite, die daran hängenbleibt, wäre der teurere
            # Ausgang als eine Automatik, die diesmal nichts tut.
            #

            return

        if not text or text == self._clip_seen:
            return

        #
        # GEMERKT WIRD VOR DEM PRUEFEN. Sonst sieht dasselbe Feuern
        # denselben nicht erkannten Text bei jedem Fensterwechsel neu
        # an - und `recognize()` ist zwar billig, aber nicht umsonst.
        #

        self._clip_seen = text

        kind = sim_run.recognize(text)

        if kind == sim_run.NOTHING:
            return

        if text == self.input.toPlainText().strip():
            return

        #
        # Ins Feld schreiben wie von Hand - ersetzend, nicht anhängend.
        # `_read()` liest den GANZEN Feldinhalt und ordnet ihn EINER
        # Sorte zu; zwei Sorten übereinander hiessen, dass die zweite
        # die erste verdeckt. Gesammelt wird im Lauf, nicht im Feld
        # (siehe `../../docs/sim-run.md`).
        #

        self._suppress_read = True

        self._read_timer.stop()

        self.input.setPlainText(text)

        self._suppress_read = False

        self._read(quiet=False)

        self.clip_state.setText(
            "Aus der Zwischenablage übernommen: "
            + (
                "optimierte Ausrüstung."
                if kind == sim_run.TARGET
                else "Gewichtung."
            )
        )

    # --------------------------------------------------
    # Zustand
    # --------------------------------------------------

    def on_enter(self):

        self.read_export()

        self.refresh()

        #
        # Wer im Sim kopiert und dann erst hierher navigiert, hat
        # dasselbe getan wie der, der zurückwechselt.
        #

        self._take_from_clipboard(force=True)

    # --------------------------------------------------
    # Die Ausrüstung aus dem Spiel
    # --------------------------------------------------

    def read_export(self):
        """
        Liest die SavedVariables des WowSimsExporter.

        Ausdrücklich nicht in `refresh()`: die Seite wird bei jeder
        `state_changed` neu gezeichnet, und eine Datei je Zeichnung
        anzufassen wäre dieselbe Sorte Aufwand wie ein Netzabruf im
        Zeichnen (siehe `ConnectionsPage.refresh()`).
        """

        reader = WseReader(getattr(self.manager.state, "wow_path", None))

        try:
            self._lookup = reader.read()

        except Exception:

            #
            # Eine fremde Datei, an der wir nichts ändern können - sie
            # darf die Seite nicht mitnehmen.
            #

            self._lookup = None

            self._export = None

            self._follow_export = False

            self._rebuild_run()

            return

        newest = self._lookup.newest

        self._export = parse_export(newest.data) if newest else None

        self.gear_copy_state.setText("")

        #
        # Beim Betreten folgt die Auswahl dem, was das Spiel gemeldet
        # hat. Ohne das stünde die Liste auf ihrem ersten Eintrag, und
        # der Knopf wäre ausgerechnet in dem Fall tot, für den es ihn
        # gibt. Nur beim Betreten: wer danach umstellt, hat sich etwas
        # dabei gedacht, und `refresh()` läuft bei jeder
        # `state_changed`.
        #

        self._follow_export = True

        self._rebuild_run()

    def _export_stamp(self) -> int:
        """
        Der Zeitstempel der gemeldeten Ausrüstung - **aus der Uhr des
        Spiels**, nicht aus der dieses Rechners.

        Daran hängt der Handshake: das Addon merkt sich beim
        *Bereitstellen* dieselbe Zahl (`time()` im Spiel), und die
        Kennung des Laufs entsteht daraus. Ohne diesen Bezug wäre ein
        „genau dieser Lauf" im Spiel eine Behauptung.
        """

        newest = self._lookup.newest if self._lookup else None

        return int(getattr(newest, "stamp", 0) or 0) if newest else 0

    def _ensure_run(self):
        """
        Den offenen Lauf herstellen, falls es keinen gibt.

        Er entsteht **aus der gemeldeten Ausrüstung** - das ist sein
        Anker und der Grund, warum seine Kennung nach einem Neustart
        der App dieselbe ist. Ohne gemeldete Ausrüstung entsteht er
        trotzdem, nur ohne Anker: dann hat er keine Kennung, und die
        Seite behauptet nichts über Zusammengehörigkeit.
        """

        if self._run is None:
            self._rebuild_run()

        return self._run

    def _rebuild_run(self, keep: bool = True):
        """
        Den Lauf neu aufsetzen - und mitnehmen, was schon eingelesen
        wurde.

        `keep` ist der Normalfall und kein Komfort: wer einfügt und
        danach die Spezialisierung korrigiert, hat den Text nicht
        zurückgenommen. Ihn wegzuwerfen hiesse, eine Korrektur mit
        einem Verlust zu bestrafen.
        """

        alt = self._run

        sheet = self.selected_character() if hasattr(self, "character_select") else {}

        run = sim_run.start_run(
            self.selected_spec() if hasattr(self, "spec_select") else "",
            export=self._export,
            reported_at=self._export_stamp(),
            character=str(sheet.get("name", "")),
            realm=str(sheet.get("realm", "")),
        )

        if keep and alt is not None:

            if alt.weights:

                run = sim_run.with_weights(
                    run,
                    alt.weights,
                    alt.weights_source,
                    alt.weights_class,
                    now=alt.weights_at,
                )

            if alt.target is not None:
                run = sim_run.with_target(run, alt.target, now=alt.target_at)

        self._run = run

    def selected_spec(self) -> str:

        return self.spec_select.value() or ""

    def selected_character(self) -> dict:

        key = self.character_select.value()

        for sheet in self._sheets():

            if _sheet_key(sheet) == key:
                return sheet

        return {}

    def _sheets(self) -> list[dict]:

        characters = getattr(self.manager, "characters", None)

        if characters is None:
            return []

        try:
            return characters.characters()

        except Exception:
            return []

    # --------------------------------------------------

    def refresh(self):
        """
        Zeichnet - und fasst das Eingabefeld nicht an.
        """

        self._fill_characters()

        self._follow_reported_spec()

        self._draw_source()

        self._draw_gear()

        self._draw_result()

        self._draw_delivery()

        self._draw_progress()

    def _draw_progress(self):
        """
        Wo stehe ich - im Hinsehen statt im Lesen.

        Die Seite beantwortet das bisher nur in Sätzen, und die stehen
        alle gleichzeitig da: vier Karten, jede mit ihrem Hinweis, und
        „was habe ich jetzt zu tun" ergibt sich erst aus dem Lesen
        aller vier. Zwei Dinge ändern das, ohne eine einzige Auskunft
        wegzunehmen.

        **Der Seitentitel ist der nächste Schritt.** Ein Titel, der
        immer „Sim-Ergebnis übernehmen." heisst, sagt nichts über
        diesen Besuch - dieselbe Regel wie bei der Übersicht, deren
        Titel den Termin nennt statt das Wort „Übersicht".

        **Und Schritt 2 bekommt kein Häkchen.** Er passiert im Browser,
        und was dort geschehen ist, weiss diese App nicht. Ein Häkchen
        dafür wäre eine Behauptung - dieselbe Zurückhaltung wie bei
        `at == -1` und `stars == 0`. Abgehakt wird nur, was die
        Companion tatsächlich sieht: die gemeldete Ausrüstung (1), der
        eingelesene Lauf (3), das Abgelegte (4).
        """

        healer = self._healer()

        vorbereitet = (
            healer is not None
            or fits_spec(self._export, self.selected_spec())
        )

        pasted = sim_run.validate(
            self._run,
            expected_spec=self.selected_spec(),
            target_expected=healer is None,
        )

        abgelegt = bool(
            self.weights_store_entry() or self.target_gear_store_entry()
        )

        self._mark_step("1", vorbereitet)

        self._mark_step("3", pasted.usable)

        self._mark_step("4", abgelegt)

        #
        # DER TITEL IST DER NAECHSTE SCHRITT, in der Reihenfolge des
        # Wegs: was jetzt ansteht, steht vor dem, was schon erledigt
        # ist. Der Satz nach dem Übernehmen ist bewusst keine
        # Aufforderung an diese App, sondern der eine Handgriff, der
        # noch im Spiel zu tun ist.
        #

        if not self.selected_spec():
            titel = "Spezialisierung wählen."

        elif pasted.usable:

            titel = (
                "Trotzdem übernehmen?"
                if pasted.state == sim_run.MISMATCH
                else "Sim-Ergebnis übernehmen."
            )

        elif abgelegt:
            titel = "Fertig — im Spiel /wc import, dann einfügen."

        elif vorbereitet:
            titel = "Simmen, dann im Sim kopieren."

        else:
            titel = "Ausrüstung im Spiel bereitstellen."

        self.header.setTitle(titel)

    def _mark_step(self, number: str, done: bool):

        label = self._step_marks.get(number)

        if label is None:
            return

        text = "✓" if done else number

        if label.text() != text:
            label.setText(text)

        restyle(
            label,
            "color:"
            + (tokens.STATE_TEXT["ok"] if done else tokens.TEXT["faint"])
            + ";background:transparent;",
        )

    def _follow_reported_spec(self):
        """
        Stellt die Auswahl auf die Spezialisierung, deren Ausrüstung
        gemeldet wurde - einmal je Besuch.

        Sie schlägt die Spec aus dem Ausrüstungsbogen, wenn beide sich
        widersprechen: hier geht es um die Ausrüstung, und die gehört
        zu genau dem Charakter, den der Exporter gemeldet hat.
        """

        if not self._follow_export:
            return

        self._follow_export = False

        if self._export is None:
            return

        key = self._export.spec_key

        if key and spec_of(key):
            self.spec_select.select_value(key)

    def _fill_characters(self):

        sheets = self._sheets()

        items = [
            (
                f"{sheet.get('name', '?')} · "
                f"{sheet.get('spec') or spec_label(sheet.get('spec_key', ''))}",
                _sheet_key(sheet),
            )
            for sheet in sheets
        ]

        if not items:

            #
            # Kein gemeldeter Charakter heisst nicht "diese Seite geht
            # nicht": die Spezialisierung lässt sich von Hand wählen,
            # und der Sim braucht ohnehin keinen Namen. Gesagt wird es
            # trotzdem, sonst sieht die leere Liste nach Fehler aus.
            #

            items = [("Noch kein Charakter gemeldet", "")]

        filled = self.character_select.set_items(items)

        self.character_select.setEnabled(bool(sheets))

        if filled and sheets:
            self._on_character_changed()

    def _healer(self):
        """
        Die QE-Live-Spezialisierung zur Auswahl, oder `None`.

        Gefragt wird nicht "ist das ein Heiler", sondern "führt QE Live
        diese Spezialisierung" - dieselbe Zurückhaltung wie bei
        `sim_url()`, und dieselbe Frage, die das Addon in
        `modules/qelive.lua` stellt.
        """

        return qelive.spec(self.selected_spec())

    def _draw_healer_source(self, entry):
        """
        Der Heiler-Zweig derselben Karte.

        Zwei Dinge fallen hier weg, und beide, weil QE Live sie nicht
        kann: eine Adresse, die die Ausrüstung mitbringt, und ein
        Export für *Import → Addon*. Ein zweiter Knopf, der dasselbe
        tut wie der erste, ist keine Auswahl - er ist die Frage, worin
        sich die beiden unterscheiden.
        """

        self.source_hint.setText(qelive.guidance(entry))

        self.open_button.setText("QE Live öffnen")

        self.open_button.setEnabled(True)

        self.plain_button.setVisible(False)

        self.copy_export_button.setVisible(False)

        self.gear_copy_state.setText("")

        self.url_label.setText(qelive.URL)

        #
        # Die Ausrüstungszeile sagt hier nichts über eine Meldung des
        # WowSimsExporters - der spielt in diesem Weg keine Rolle. Sie
        # sagt, woher der Text kommt.
        #

        self.gear_state.setText(
            f"{entry.label} · die Ausrüstung kommt als Text aus dem Spiel"
        )

        restyle(
            self.gear_state,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

        self.gear_note.setText(qelive.weights_note(entry))

        self.paste_gap.setText(
            "QE Live gibt keine Wertegewichte heraus — für diese "
            "Spezialisierung bleibt dieses Feld leer. Wer trotzdem eine "
            "Gewichtung von Hand einsetzen will, kann sie hier "
            "einfügen; ihre Vorgabewerte liegen im Spiel unter "
            "Priorisierung bereit."
        )

    def _draw_source(self):

        entry = self._healer()

        if entry is not None:

            self._draw_healer_source(entry)

            return

        #
        # Zurück auf den wowsims-Zweig: die Knöpfe bleiben zwischen zwei
        # Spezialisierungen dieselben Widgets, und was der Heiler-Zweig
        # ausgeblendet hat, muss hier wieder dastehen.
        #

        self.source_hint.setText(SIM_STEPS)

        self.open_button.setText("Sim mit meiner Ausrüstung öffnen")

        self.paste_gap.setText("")

        self.plain_button.setVisible(True)

        self.copy_export_button.setVisible(True)

        key = self.selected_spec()

        url = sim_url(key)

        if url:

            self.url_label.setText(url)

            self.plain_button.setEnabled(True)

        else:

            #
            # Ein unbekannter Profilschlüssel wird nicht geraten - die
            # Seite einer fremden Spezialisierung sähe genauso aus wie
            # die richtige.
            #

            self.url_label.setText(
                f"{BASE_PAGE} — für diese Spezialisierung ist hier keine "
                f"eigene Seite hinterlegt."
            )

            self.plain_button.setEnabled(True)

    # --------------------------------------------------
    # Handlungen
    # --------------------------------------------------

    def _on_character_changed(self):

        sheet = self.selected_character()

        key = (sheet.get("spec_key") or "").strip().upper()

        if key and spec_of(key):
            self.spec_select.select_value(key)

        self._rebuild_run()

        self._draw_source()

        self._draw_gear()

        self._draw_result()

        self._draw_delivery()

        self._draw_progress()

    def _on_spec_changed(self):

        #
        # Der Lauf gehört zu genau einer Spezialisierung; wer umstellt,
        # meint denselben eingefügten Text für eine andere. Deshalb neu
        # aufgesetzt und der Befund mitgenommen (siehe `_rebuild_run`).
        #

        self._rebuild_run()

        self._draw_source()

        #
        # Der Ausrüstungs-Zustand hängt an der gewählten Spec (die
        # Klasse muss passen) - ohne diese Zeile bliebe der Knopf auf
        # dem Stand von vorhin, und beim Wechsel auf die Zweitspec
        # wäre er tot, obwohl die Ausrüstung dieselbe ist.
        #

        self._draw_gear()

        self._draw_result()

        self._draw_delivery()

        self._draw_progress()

    # --------------------------------------------------
    # Schritt 1/2: was der Sim bekommt
    # --------------------------------------------------

    def _export_class(self) -> str:

        return (self._export.char_class if self._export else "").upper()

    def _gear_link(self) -> str:

        #
        # QE Live nimmt die Ausrüstung nur als eingefügten Text an; eine
        # Adresse, die sie mitbringt, gibt es dort nicht. Ein gebauter
        # Link führte auf eine Seite, die ihn ignoriert - und das sähe
        # aus wie eine Ausrüstung, die unterwegs verloren ging.
        #

        if self._healer() is not None:
            return ""

        if not fits_spec(self._export, self.selected_spec()):
            return ""

        url = sim_url(self.selected_spec())

        if not url:
            return ""

        return build_link(url, self._export.items)

    def _draw_gear(self):
        """
        Zeichnet, was der Sim bekommt - und wenn nichts, warum
        nicht. Welcher Satz das ist, entscheidet `gap_text()`; hier
        steht er nur.
        """

        #
        # Für Heiler hat `_draw_healer_source()` die beiden Zeilen
        # schon gesetzt. Sie hier ein zweites Mal zu beschreiben hiesse,
        # den WowSimsExporter zum Thema zu machen, der in diesem Weg
        # keine Rolle spielt.
        #

        if self._healer() is not None:

            return

        reason = self._lookup.reason if self._lookup else NO_WOW

        note = (
            "Die Adresse bringt die Ausrüstung mit. Talente und Glyphen "
            "bleiben, wie du sie im Sim eingestellt hast — für die geht "
            "Export kopieren und im Sim Import → Addon."
        )

        if fits_spec(self._export, self.selected_spec()):

            export = self._export

            #
            # Das Alter kommt aus der Meldung, und wenn keine dasteht,
            # steht hier nichts über die Zeit. Ein "gemeldet vor 0
            # Minuten" wäre eine Behauptung über einen Zeitpunkt, den
            # niemand kennt - dieselbe Regel wie `at == -1`.
            #

            stamp = self._export_stamp()

            self.gear_state.setText(
                f"{export.full_name} · {export.item_count} Teile"
                + (f" · gemeldet {age_text(stamp)}" if stamp else "")
            )

            restyle(
                self.gear_state,
                f"color:{tokens.WHITE};background:transparent;",
            )

            if export.problems:
                note = " ".join(export.problems) + " " + note

            self.gear_note.setText(note)

            self.open_button.setEnabled(True)

            self.copy_export_button.setEnabled(True)

            return

        self.open_button.setEnabled(False)

        self.copy_export_button.setEnabled(bool(self._export))

        if self._export and self._export.usable:

            #
            # Gefunden, passt aber nicht zur gewählten Klasse. Das ist
            # keine Störung, sondern eine Auskunft: gemeldet wird
            # immer der zuletzt gespielte Charakter.
            #

            self.gear_state.setText(
                f"Zuletzt gemeldet wurde {self._export.full_name} "
                f"({class_label(self._export_class())}) — das passt nicht "
                f"zur gewählten Spezialisierung."
            )

            self.gear_note.setText(
                "Im Spiel auf diesen Charakter wechseln und dort unter "
                "Charakter → Simmen bereitstellen. Solange öffnet Nur "
                "die Seite den Sim ohne Ausrüstung."
            )

        else:

            self.gear_state.setText(gap_text(reason, self._export))

            self.gear_note.setText(
                "Ohne gemeldete Ausrüstung stellst du sie im Sim selbst "
                "ein — der Weg zurück in Schritt 3 ändert sich dadurch "
                "nicht, nur die Frage nach dem Optimierungslauf bleibt "
                "dann offen."
            )

        restyle(
            self.gear_state,
            f"color:{tokens.TEXT['muted']};background:transparent;",
        )

    # --------------------------------------------------

    def _open_sim(self):

        link = self._gear_link()

        if not link:

            #
            # Der Knopf ist dann gesperrt; hierher kommt man nur, wenn
            # sich der Zustand zwischen Zeichnen und Klick geändert
            # hat. Die Seite ohne Ausrüstung ist die richtige Antwort
            # darauf - ein Klick, der nichts tut, wäre es nicht.
            #

            self._open_plain()

            return

        open_url(link, getattr(self.manager, "logger", None))

    def _open_plain(self):

        if self._healer() is not None:

            open_url(qelive.URL, getattr(self.manager, "logger", None))

            return

        url = sim_url(self.selected_spec()) or BASE_PAGE

        open_url(url, getattr(self.manager, "logger", None))

    def _copy_export(self):
        """
        Der Export-Text für *Import → Addon* im Sim.

        Er bringt mit, was die Adresse nicht mitbringen kann: Talente,
        Glyphen, Volk und Berufe. Den Weg gibt es also nicht als
        Rückfall, sondern weil er mehr kann.
        """

        if not self._export:
            return

        clipboard = QGuiApplication.clipboard()

        if clipboard is None:

            self.gear_copy_state.setText(
                "Kopieren geht auf diesem System nicht — im Spiel führt "
                "/wse export zum selben Text."
            )

            return

        clipboard.setText(self._export.raw)

        #
        # Derselbe Grund wie in `_copy_transfer()`: das ist der Weg *in
        # den Sim*, und die Automatik in Schritt 3 wartet auf das, was
        # von dort zurückkommt.
        #

        self._clip_seen = self._export.raw.strip()

        self.gear_copy_state.setText(
            "Kopiert. Im Sim oben unter Import → Addon einfügen — so "
            "kommen auch Talente, Glyphen und Berufe mit."
        )

    # --------------------------------------------------
    # Schritt 3: das Ergebnis lesen
    # --------------------------------------------------

    def _on_input_changed(self):

        #
        # Nicht auf den eigenen Schreibzugriff reagieren: `_clear_input()`
        # leert das Feld nach dem Übernehmen, und das ist keine Eingabe
        # des Nutzers.
        #

        if self._suppress_read:
            return

        #
        # Ab hier stammt der Text vom Nutzer. Die Herkunftszeile darüber
        # gälte dann für etwas, das nicht mehr dasteht - `_suppress_read`
        # sorgt dafür, dass das Auffangen selbst hier nicht vorbeikommt.
        #

        self.clip_state.setText("")

        self._read_timer.start()

    def _read_quiet(self):

        self._read(quiet=True)

    def _forget_reading(self):
        """
        Alles vergessen, was aus dem eingefügten Text kam.

        Eigene Methode, weil es zwei Anlässe dafür gibt und beide
        dasselbe meinen: das Feld wurde geleert (von Hand oder nach dem
        Übernehmen). Zweimal ausgeschrieben liefen sie beim nächsten
        neuen Feld auseinander, und was übrig bliebe, wäre ein Befund
        ohne Text darüber.
        """

        self._parsed = None

        self._rebuild_run(keep=False)

        self.problem.setText("")

        self.details.setText("")

        self._draw_result()

    def _clear_input(self):

        self._suppress_read = True

        self._read_timer.stop()

        self.input.setPlainText("")

        self._suppress_read = False

        #
        # Die Herkunftszeile geht mit. Sie sagt, woher der Text im Feld
        # kam - über ein leeres Feld ist das keine Auskunft mehr,
        # sondern ein Rest.
        #

        self.clip_state.setText("")

        self._forget_reading()

    def _read(self, quiet: bool = False):
        """
        Den eingefügten Text lesen - und in den offenen Lauf legen.

        `quiet` unterscheidet die beiden Anlässe, und der Unterschied
        ist genau einer: **ob ein Fehler gesagt wird.** Nebenher
        gelesen wird bei jedem Zeichen (`_on_input_changed`), und wer
        gerade tippt, hat noch nichts falsch gemacht. Ein Befund
        dagegen ist in beiden Fällen willkommen - er verlangt nichts
        und beantwortet die Frage, ob der Text angekommen ist.

        **Gesammelt statt ersetzt** (seit 3.3.0): eine eingefügte
        Zielausrüstung löscht die vorher gelesene Gewichtung nicht.
        Genau das war die zweite Runde durch dasselbe Feld, die den
        Nutzer zwang, sich die technische Trennung zu merken.
        """

        text = self.input.toPlainText()

        self._ensure_run()

        if not text.strip():

            #
            # Ein leeres Feld ist kein Fehler, sondern der
            # Ausgangszustand - auch dann, wenn der Nutzer den Text
            # gerade selbst herausgelöscht hat.
            #

            self._forget_reading()

            return

        #
        # ZUERST DIE ZIELAUSRUESTUNG. Beide Sorten Text kommen aus
        # demselben Sim und in dasselbe Feld; unterschieden werden sie
        # an ihrer Gestalt, nicht daran, in welches Feld jemand
        # eingefügt hat.
        #
        # `parse_target()` ist dabei die STRENGERE von beiden: sie
        # erkennt nur eine Adresse, einen Base64-Rumpf oder JSON. Eine
        # getippte Gewichtung ("Hit 1.77") ist keins davon und fällt
        # deshalb sicher an `parse()` durch - andersherum wäre es
        # nicht so.
        #

        if self._read_target(text, quiet=quiet):
            return

        self._read_weights(text, quiet=quiet)

    def _fail(self, message: str, quiet: bool):
        """
        Ein Lesefehler - und was er **nicht** anfasst.

        Der Lauf bleibt, wie er ist: wer nach der Gewichtung Unsinn
        einfügt, hat die Gewichtung nicht zurückgenommen. Bis 3.2.0
        wurde sie hier mit gelöscht, und das war von aussen ein
        stilles Verschwinden.
        """

        self.problem.setText("" if quiet else message)

        self._draw_result()

    def _read_weights(self, text: str, quiet: bool = False):

        parsed = parse(text)

        if parsed.problem:

            self._fail(parsed.problem, quiet)

            return

        weights, negatives = normalize(parsed.weights)

        if not weights:

            self._fail(
                "Darin steht keine brauchbare Gewichtung — alle Werte "
                "sind null oder negativ.",
                quiet,
            )

            return

        self._parsed = parsed

        self._run = sim_run.with_weights(
            self._ensure_run(),
            weights,
            parsed.source or "sim",
            parsed.sim_class or "",
        )

        self.problem.setText("")

        self.details.setText(
            " ".join(self._note_lines(parsed, negatives, weights)),
        )

        self._draw_result()

    def _read_target(self, text: str, quiet: bool = False) -> bool:
        """
        Den eingefügten Text als Sim-**Ergebnis** lesen.

        Gibt `True` zurück, wenn er eins war - dann hat `_read()` hier
        nichts mehr zu tun. `False` heisst "das war keine
        Zielausrüstung" und ist ausdrücklich kein Fehler: dasselbe Feld
        liest auch Gewichtungen.
        """

        target = parse_target(text)

        if target is None or not target.known:
            return False

        if not target.usable:

            #
            # Erkannt, aber unbrauchbar - das ist etwas anderes als
            # "nicht erkannt", und es führt zu einem anderen nächsten
            # Schritt: im Sim erst optimieren, dann exportieren.
            #

            self._fail(
                "Erkannt als "
                + target.source_label
                + ", aber darin steht weder ein Sockelstein noch eine "
                "Umschmiedung. Im Sim erst optimieren lassen (Zahnrad "
                "neben Suggest Reforges, Include gems anhaken), dann "
                "exportieren. "
                + (" ".join(target.problems) if target.problems else ""),
                quiet,
            )

            return True

        self._run = sim_run.with_target(self._ensure_run(), target)

        self.problem.setText(
            " ".join(target.problems) if target.problems else ""
        )

        self._draw_result()

        return True

    def _note_lines(self, parsed, negatives, weights) -> list[str]:
        """
        Was neben den Gewichten noch zu sagen ist - und alles davon
        wird gesagt, nicht verschwiegen: wer es nicht sieht, hält das
        Ergebnis für vollständig.

        WARUM DAS HIER VIER GETRENNTE SÄTZE SIND.

        Bis 2.5.0 stand alles unter einer Überschrift ("kennt
        WeintCodex nicht"), und die war für den häufigsten Fall
        schlicht falsch: Angriffskraft und Waffenschaden kennt es sehr
        wohl. Der Satz las sich wie eine Lücke in unseren Tabellen -
        und wurde genau so gemeldet. Vier Fälle, vier Antworten, und
        drei davon verlangen nichts:

        * mit null gewichtet   -> der Sim hat sie angesehen
        * hier nicht verwertbar -> kein Stein, keine Verzauberung,
                                   keine Umschmiedung bewegt sie
        * nicht erkannt        -> das ist der Fall für eine Meldung
        * unter 1 gerundet     -> vorhanden, aber zu klein für die
                                   Skala des Addons
        """

        lines: list[str] = []

        if negatives:

            lines.append(
                "Negative Gewichte gibt es hier nicht — auf 0 gesetzt: "
                + ", ".join(STAT_LABELS.get(key, key) for key in negatives)
                + "."
            )

        #
        # Was in der Liste fehlt, weil die Quelle es mit null bewertet
        # hat. Ohne diesen Satz ist das von "die App hat den Wert
        # verloren" nicht zu unterscheiden - dieselbe Linie wie
        # `stars == 0` im Analyzer.
        #

        if parsed.zeroed:

            lines.append(
                "Mit null gewichtet (bringt diesem Charakter laut Sim "
                "nichts): "
                + ", ".join(
                    STAT_LABELS.get(key, key)
                    for key in STAT_ORDER
                    if key in parsed.zeroed
                )
                + "."
            )

        #
        # Und was unter 1 rutscht: vorhanden, aber auf der Skala des
        # Addons (grösstes Gewicht = 100, ganze Zahlen) nicht mehr
        # darstellbar. Auch das ist ein stilles Verschwinden.
        #

        rounded = [
            key
            for key in STAT_ORDER
            if parsed.weights.get(key, 0) > 0 and not weights.get(key)
        ]

        if rounded:

            lines.append(
                "Zu klein für die Skala (unter 1 von 100): "
                + ", ".join(STAT_LABELS.get(key, key) for key in rounded)
                + "."
            )

        if parsed.unusable:

            lines.append(
                "Hier nicht verwertbar: "
                + ", ".join(parsed.unusable)
                + ". Diese Werte gewichtet der Sim mit, aber kein "
                "Sockelstein, keine Verzauberung und keine Umschmiedung "
                "bewegt sie — es gäbe hier nichts, was ein Gewicht "
                "darauf steuern könnte."
            )

        if parsed.unknown:

            lines.append(
                "Nicht erkannt (kennt WeintCodex nicht): "
                + ", ".join(parsed.unknown)
                + "."
            )

        if parsed.caps:

            named = " · ".join(
                f"{STAT_LABELS.get(cap.stat, cap.stat)} "
                f"{_percent(cap.percent)} %"
                for cap in parsed.caps
            )

            lines.append(
                f"Grenzen aus dem Sim: {named}. Sie werden nicht "
                f"übernommen — eine Grenze gilt für alle dieser "
                f"Spezialisierung und steht im Spec-Profil des Addons, "
                f"das sie beim Sockeln und Umschmieden auch durchsetzt."
            )

        if parsed.caps_ignored:

            lines.append(
                "Nicht gelesene Grenzen: "
                + ", ".join(parsed.caps_ignored)
                + "."
            )

        if parsed.limits:

            lines.append(
                "Schwellen aus dem Sim: "
                + " · ".join(parsed.limits)
                + ". Auch sie werden nicht übernommen — die "
                "Tempo-Schwellen rechnet das Addon selbst aus."
            )

        return lines

    # --------------------------------------------------
    # Schritt 3: der Befund
    # --------------------------------------------------

    def _effective_run(self):
        """
        Der offene Lauf **plus dem, was für genau ihn schon abgelegt
        ist**.

        WARUM DAS NOETIG IST. Wer die Gewichtung übernimmt und danach
        die Zielausrüstung einfügt, hat einen vollständigen Lauf - die
        erste Hälfte liegt nur schon im Speicher statt im Feld. Ohne
        diese Zusammenführung stünde dort „Gewichtung fehlt", obwohl
        sie bereitliegt, und der Satz darunter schickte ihn in den Sim
        für etwas, das er längst geholt hat.

        **Zusammengeführt wird nur bei gleicher Kennung.** Ein Eintrag
        aus einem anderen Lauf ist keine Hälfte dieses Laufs - er ist
        genau die Mischung, vor der Schritt 4 warnt. Und ohne Kennung
        (ältere Ablage, von Hand getippt) wird nichts behauptet:
        `belongs()` ist dann falsch, und es bleibt beim Feld.
        """

        run = self._run

        if run is None or not run.run_id:
            return run

        entry = self.weights_store_entry()

        target = self.target_gear_store_entry()

        if not run.have_weights and entry is not None:

            if str(getattr(entry, "run_id", "")) == run.run_id:
                run = sim_run.with_weights(
                    run,
                    dict(entry.weights),
                    entry.source or "sim",
                    run.weights_class,
                    now=entry.created,
                )

        if not run.have_target and target is not None:

            if str(getattr(target, "run_id", "")) == run.run_id:
                run = sim_run.with_target(run, target.gear, now=target.created)

        return run

    def _validation(self, run=None):
        """
        Der Befund über den offenen Lauf.

        `target_expected` ist die eine Stelle, an der der Heiler-Weg
        hier überhaupt vorkommt: QE Live gibt keinen Zielzustand
        heraus, und einen zu vermissen wäre eine Aufforderung ins
        Leere.
        """

        return sim_run.validate(
            self._effective_run() if run is None else run,
            expected_spec=self.selected_spec(),
            target_expected=self._healer() is None,
        )

    def _draw_result(self):
        """
        Die vier Zeilen von Schritt 3 - aus **einer** Rechnung.

        Die Sätze stehen in `core/sim_run.py`; hier stehen sie nur.
        Zwei Fassungen desselben Satzes liefen ab der ersten Änderung
        auseinander, und die falsche stünde dann bei dem, der einen
        Fehler sucht.
        """

        #
        # ZWEI FRAGEN, ZWEI LAEUFE. „Steht hier etwas?" beantwortet der
        # EINGEFUEGTE Lauf - sonst stünde nach jedem Übernehmen ein
        # Befund über ein leeres Feld. „Ist es vollständig?" beantwortet
        # der Lauf samt dem, was für ihn schon abgelegt ist.
        #

        pasted = sim_run.validate(
            self._run,
            expected_spec=self.selected_spec(),
            target_expected=self._healer() is None,
        )

        run = self._effective_run()

        validation = self._validation(run)

        if pasted.state == sim_run.EMPTY:

            self.result.setText("")

            self.parts.setText("")

            self.notes.setText("")

            self.hint.setText("")

            self.apply_button.setEnabled(False)

            self.apply_button.setText("Sim-Ergebnis übernehmen")

            return

        self.result.setText(sim_run.headline(validation))

        self.parts.setText(sim_run.parts_line(validation))

        zeilen = [
            sim_run.source_line(run),
            sim_run.change_line(validation),
        ]

        klasse = sim_run.class_note(run, self.selected_spec())

        if klasse:
            zeilen.append(klasse)

        if "other_spec" in validation.notes:

            zeilen.append(
                "Die Ausgabe gehört zu "
                + spec_label(run.target.spec_key)
                + " — übernommen wird sie für die oben gewählte "
                "Spezialisierung."
            )

        if "foreign" in validation.notes:

            zeilen.append(
                f"{validation.foreign_slots} Teile kennt deine gemeldete "
                "Ausrüstung nicht (oder es steckt dort inzwischen etwas "
                "anderes) — für die gilt das Ziel im Spiel nicht, dort "
                "rechnet WeintCodex weiter selbst."
            )

        if run.have_weights:
            zeilen.append(_weights_text(run.weights))

        self.notes.setText(" ".join(line for line in zeilen if line))

        self.hint.setText(sim_run.next_step(validation))

        #
        # DER KNOPF SAGT, WORAUF MAN SICH EINLAESST. Bei einer fremden
        # Klasse heisst er anders, statt gesperrt zu sein: vielleicht
        # simmt jemand für seinen Zweitcharakter, und ein toter Knopf
        # beantwortet die Frage nicht, warum er tot ist.
        #

        self.apply_button.setEnabled(pasted.usable)

        self.apply_button.setText(
            "Trotzdem übernehmen"
            if validation.state == sim_run.MISMATCH
            else "Sim-Ergebnis übernehmen"
        )

    # --------------------------------------------------
    # Übernehmen: beide Auskünfte, ein Klick
    # --------------------------------------------------

    def _apply(self):
        """
        Was im Lauf liegt, ablegen und zustellen - **in einem Zug**.

        Bis 3.2.0 waren das zwei Knöpfe in zwei Karten, und wer den
        zweiten vergaß, bekam im Spiel eine halbe Auskunft, der man das
        nicht ansieht. Jetzt legt ein Klick ab, was da ist; was fehlt,
        stand vorher als Satz da und fehlt danach immer noch - aber es
        blockiert nicht, was schon vorliegt.
        """

        run = self._run

        if run is None:
            return

        key = self.selected_spec()

        if not key:
            return

        sheet = self.selected_character()

        name = str(sheet.get("name", ""))

        realm = str(sheet.get("realm", ""))

        stamp = int(time.time())

        getan: list[str] = []

        if run.have_weights and self.store is not None:

            entry = self.store.put(
                WeightSet(
                    spec_key=key,
                    weights=dict(run.weights),
                    character=name,
                    realm=realm,
                    source=run.weights_source or "sim",
                    created=stamp,
                    run_id=run.run_id,
                    started_at=run.started_at if run.input_gear else 0,
                )
            )

            #
            # Sofort zustellen statt auf den Sync-Takt zu warten: wer
            # hier drückt, will gleich `/reload` tippen (dieselbe
            # Überlegung wie beim "Fertig" der WeakAuras-Seite).
            #

            if self.sync is not None:
                self.sync.publish_now()

            getan.append(f"Gewichtung für {spec_label(entry.spec_key)}")

        if run.have_target and self.target_store is not None:

            ziel = self.target_store.put(
                TargetSet(
                    gear=run.target,
                    spec_key=key,
                    character=name or run.target.character,
                    realm=realm or run.target.realm,
                    created=stamp,
                    run_id=run.run_id,
                    started_at=run.started_at if run.input_gear else 0,
                )
            )

            if self.target_sync is not None:
                self.target_sync.publish_now()

            getan.append(f"Zielausrüstung ({len(ziel.items)} Teile)")

        if not getan:
            return

        self._clear_input()

        self.refresh()

        #
        # UND GLEICH IN DIE ZWISCHENABLAGE (seit 3.1.1).
        #
        # *Übernehmen* und *Ins Spiel übertragen* sind zwei Klicks für
        # eine Absicht: wer übernimmt, will es ins Spiel bringen. Der
        # Zeitpunkt ist auch der einzige, an dem die Frage "welcher der
        # beiden Strings ist meiner" gar nicht erst entsteht. Erst nach
        # `refresh()`, denn das Feld wird dort gefüllt; und über
        # denselben Weg wie der Knopf in Schritt 4, damit ein System
        # ohne Zwischenablage denselben Satz bekommt statt eines
        # stillen Nichts.
        #

        self._copy_transfer()

        logger = getattr(self.manager, "logger", None)

        if logger is not None:

            logger.success(
                "Sim-Ergebnis übernommen: "
                + " · ".join(getan)
                + (f" · Lauf {run.run_id}" if run.run_id else "")
            )

    def _remove(self):
        """
        Das Sim-Ergebnis dieser Spezialisierung verwerfen - **beides**.

        Zwei Entfernen-Knöpfe waren die Möglichkeit, eine Hälfte
        stehenzulassen, und genau diese Hälfte ergibt später die
        Mischung aus zwei Läufen, vor der Schritt 4 warnt. Wer
        verwerfen will, verwirft den Lauf.
        """

        key = self.selected_spec()

        weg = False

        if self.store is not None and self.store.remove(key):

            #
            # Auch das Löschen wird zugestellt: im Spiel verschwindet
            # der Vorschlag dadurch, dass er in der nächsten Zustellung
            # fehlt.
            #

            if self.sync is not None:
                self.sync.publish_now()

            weg = True

        if self.target_store is not None and self.target_store.remove(key):

            if self.target_sync is not None:
                self.target_sync.publish_now()

            weg = True

        if not weg:
            return

        self.copy_state.setText("")

        self.refresh()

    # --------------------------------------------------
    # Schritt 4: der eine Ausgang
    # --------------------------------------------------

    def target_gear_store_entry(self):
        """
        Der abgelegte Zielzustand der gewählten Spezialisierung.

        Eine Zeile, damit die Seite und ihr Testlauf dieselbe Frage auf
        demselben Weg stellen - zwei Zugriffe auf denselben Speicher
        liefen irgendwann auseinander.
        """

        if self.target_store is None:
            return None

        return self.target_store.get(self.selected_spec())

    def weights_store_entry(self):

        if self.store is None:
            return None

        return self.store.get(self.selected_spec())

    def _addon_version(self) -> str:

        return str(getattr(self.manager.state, "addon_version", "") or "")

    def _combined_allowed(self) -> bool:

        found = getattr(self.manager.state, "addon_found", False)

        if not found:
            return False

        version = _version_tuple(self._addon_version())

        return bool(version) and version >= COMBINED_SINCE

    def _delivery_lines(self) -> list[str]:
        """
        Die Umschläge, die ins Importfeld des Spiels gehören - je einer
        pro Zeile, Gewichtung zuerst.

        **Zusammen nur, wenn das Addon sie zusammen lesen kann.** Ein zu
        altes verschluckt den zweiten still (siehe `COMBINED_SINCE`), und
        eine Zielausrüstung, die nie ankam, sieht im Spiel genauso aus
        wie eine, die es nicht gibt.
        """

        lines: list[str] = []

        entry = self.weights_store_entry()

        if entry is not None:
            lines.append(build_transfer(entry))

        target = self.target_gear_store_entry()

        if target is not None:
            lines.append(build_target_transfer(target))

        if len(lines) > 1 and not self._combined_allowed():
            return lines[:1]

        return lines

    def _draw_delivery(self):
        """
        Was bereitliegt, aus welchem Lauf, und der eine Weg ins Spiel.

        **Zwei Wege, und beide stehen da** - wie seit 2.8.0: die
        Companion hat bereits zugestellt (wirkt nach dem nächsten
        `/reload`), und derselbe Inhalt liegt als String bereit (wirkt
        sofort). Der Nutzer wählt nicht zwischen ihnen; er liest, was
        gilt.
        """

        entry = self.weights_store_entry()

        target = self.target_gear_store_entry()

        stored = sim_run.stored_state(entry, target)

        lines = self._delivery_lines()

        self.transfer.setPlainText("\n".join(lines))

        self.transfer.setEnabled(bool(lines))

        self.copy_button.setEnabled(bool(lines))

        self.remove_button.setEnabled(bool(entry or target))

        self._draw_stored(entry, target)

        self._draw_run_line(entry, target)

        if not lines:

            self.delivery_warn.setText("")

            self.delivery_hint.setText(
                "Sobald oben etwas übernommen ist, steht hier beides: "
                "die Zustellung ins Spiel und der String zum Einfügen "
                "ohne Neuladen."
            )

            return

        beides = entry is not None and target is not None

        #
        # ZWEI WARNUNGEN, EINE ZEILE - UND DIE ERSTE HAT VORRANG. Ein zu
        # altes Addon verschluckt die zweite Zeile; das ist der Fall,
        # der jetzt gerade etwas verliert. Zwei verschiedene Läufe
        # nebeneinander sind der Fall, der später etwas Falsches sagt.
        #

        if beides and not self._combined_allowed():

            version = self._addon_version()

            self.delivery_warn.setText(
                "Hier steht nur die Gewichtung: dein WeintCodex "
                + (f"({version}) " if version and version != "-" else "")
                + "liest aus einem eingefügten Text nur die erste Zeile "
                "und verschluckt die zweite stillschweigend. Ab 3.1.2.0 "
                "gehen beide zusammen — bis dahin holt ein /reload im "
                "Spiel ohnehin beides, denn zugestellt ist es längst."
            )

        else:

            self.delivery_warn.setText(sim_run.mixed_note(stored))

        self.delivery_hint.setText(
            "Zugestellt ist es schon — im Spiel liegt es nach dem "
            "nächsten /reload bereit (die Gewichtung unter Charakter → "
            "Priorisierung, auf deinen Klick). Ohne Neuladen: Ins Spiel "
            "übertragen kopiert den String, und im Spiel unter Import "
            "eingefügt wirkt er sofort, auch mitten in einer Gruppe."
        )

    def _draw_stored(self, entry, target):
        """
        Was bereitliegt - eine Zeile für den Lauf, eine für die Zahlen.

        Die Überschrift der Seite hängt daran: sie ist die kürzeste
        Antwort auf „bin ich fertig".
        """

        key = self.selected_spec()

        teile: list[str] = []

        if entry is None:

            teile.append("Gewichtung fehlt")

            self.stored_weights.setText("")

        else:

            teile.append("Gewichtung ✓")

            self.stored_weights.setText(_weights_text(entry.weights))

        if self._healer() is None:

            teile.append(
                "Optimierte Ausrüstung ✓" if target is not None
                else "Optimierte Ausrüstung fehlt"
            )

        if entry is None and target is None:

            self.stored.setText(
                f"Für {spec_label(key)} liegt noch nichts bereit."
            )

            self.header.setTitle("Sim-Ergebnis übernehmen.")

            return

        zahlen = ""

        if target is not None:

            steine = sum(1 for gem in _all_gems(target) if gem)

            #
            # LEERE PLAETZE SIND KEINE TEILE. Sie überleben die Ablage
            # ohnehin nicht (`target_gear_store` schreibt nur belegte),
            # und frisch übernommen stünde hier sonst eine andere Zahl
            # als nach dem nächsten Start.
            #

            zahlen = " · {} Teile, {} Sockelsteine, {} Umschmiedungen".format(
                sum(1 for item in target.items if not item.empty),
                steine,
                sum(1 for item in target.items if item.reforging),
            )

        self.stored.setText(
            "Bereit für WeintCodex: " + " · ".join(teile) + zahlen + "."
        )

        self.header.setTitle(
            f"Sim-Ergebnis für {spec_label(key)} liegt bereit."
            if (entry is not None and (target is not None or self._healer()))
            else f"Für {spec_label(key)} fehlt noch ein Teil."
        )

    def _draw_run_line(self, entry, target):
        """
        Aus welchem Lauf das Abgelegte stammt.

        Ohne Kennung steht hier **nichts** - jeder Eintrag von vor
        3.3.0 hat keine, und eine erfundene wäre schlimmer als keine.
        """

        laeufe = []

        for eintrag in (entry, target):

            kennung = str(getattr(eintrag, "run_id", "") or "")

            if kennung and kennung not in laeufe:
                laeufe.append(kennung)

        if not laeufe:

            self.run_line.setText("")

            return

        wann = ""

        for eintrag in (target, entry):

            if eintrag is not None and getattr(eintrag, "created", 0):

                wann = " · übernommen " + time.strftime(
                    "%d.%m.%Y", time.localtime(eintrag.created)
                )

                break

        self.run_line.setText("Aus Sim-Lauf " + " und ".join(laeufe) + wann)

    def _copy_transfer(self):
        """
        Den String in die Zwischenablage - der Weg **ohne** `/reload`.
        """

        text = self.transfer.toPlainText()

        if not text:
            return

        clipboard = QGuiApplication.clipboard()

        if clipboard is None:

            #
            # Kein Zwischenspeicher (kommt auf einem X-losen System
            # vor): dann steht der String im Feld darüber und lässt
            # sich von Hand markieren. Ein Knopf, der stumm nichts
            # tut, ist der schlechtere Ausgang.
            #

            self.copy_state.setText(
                "Kopieren geht auf diesem System nicht — der Text steht "
                "oben und lässt sich markieren."
            )

            return

        clipboard.setText(text)

        #
        # NICHT ZURUECKLESEN. Was hier hineingeht, ist der Weg *ins
        # Spiel*; die Automatik in Schritt 3 würde es sonst gleich
        # wieder ansehen. `recognize()` weist einen WCIMPORT-String zwar
        # ab - aber sich darauf zu verlassen hiesse, einen stillen
        # Fehler zu bauen, falls sich das je ändert.
        #

        self._clip_seen = text

        #
        # Die Zahl steht dabei, weil sie die eine Frage beantwortet, die
        # man vor dem Einfügen hat: ist das jetzt beides?
        #

        anzahl = len(text.splitlines())

        self.copy_state.setText(
            ("Beide Zeilen kopiert" if anzahl > 1 else "Kopiert")
            + ". Im Spiel unter Import einfügen — das wirkt sofort, "
            "ohne /reload. Zugestellt ist es ohnehin: ein /reload holt "
            "es genauso."
        )


# --------------------------------------------------


def _sheet_key(sheet: dict) -> str:

    name = str(sheet.get("name", "")).strip()

    realm = str(sheet.get("realm", "")).strip()

    return f"{name}-{realm}" if realm else name


def _percent(value: float) -> str:

    return f"{value:.1f}".replace(".", ",")


def _weights_text(weights: dict[str, int]) -> str:

    return " · ".join(
        f"{STAT_LABELS.get(key, key)} {value}"
        for key, value in ordered(weights)
    )
