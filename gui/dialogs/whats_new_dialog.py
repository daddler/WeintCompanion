"""
Einführung und "Was ist neu".

Dasselbe Fenster in zwei Betriebsarten:

- **Tour** - der vollständige Rundgang durch alle Bereiche der App,
  in Kapiteln. Er läuft beim allerersten Start und immer dann, wenn
  die Tour seit dem letzten Mal neu geschrieben wurde (`TOUR_EDITION`).
- **Changelog** - nach einem Update: genau das, was sich seit der
  zuletzt gesehenen Version geändert hat, gelesen aus `CHANGELOG.md`.

Warum es `TOUR_EDITION` gibt
----------------------------
Die alte Tour stammte aus 1.0 und bestand aus fünf Seiten: Dashboard,
Addon-Verwaltung, Discord, Einstellungen. Bis 2.8 sind WeintTV, die
Academy, das Archiv mit Wiedergabe, "Meine Charaktere", "Vorbereitung",
Simmen, WeakAuras und die Charakterzuordnung dazugekommen - und die
Einführung sprach von keinem davon. Wer sie einmal gesehen hatte, kannte
danach eine App, die es so nicht mehr gibt, und bekam sie auch nie wieder
zu Gesicht: ein Changelog-Popup beantwortet "was ist neu" und nicht
"was gibt es hier eigentlich alles".

Die Fassungsnummer steht deshalb **neben** `onboarding_seen_version` und
nicht darin: nicht jede Version schreibt die Tour um, und die meisten
sollen weiterhin nur das kurze Popup zeigen.

Wie die Texte geschrieben sind
------------------------------
Nach denselben Regeln wie die Patchnotes (siehe CLAUDE.md): kein
Dateiname, kein Funktionsname, kein Konfigurationsschlüssel; Wirkung vor
Ursache; kurze Sätze. Seitennamen sind ausdrücklich erlaubt - sie sind
Bedienung, nicht Innenleben.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.backend_config import app_url, feedback_url
from core.browser import open_url
from core.changelog_reader import format_changelog_body, read_changelog_sections
from core.version import VERSION, versions_equal

from gui.theme import tokens
from gui.theme.fonts import font
from gui.theme.icons import tinted_pixmap
from gui.theme.theme_manager import theme
from gui.widgets.eyebrow import eyebrow_label
from gui.widgets.hero_banner import HeroButton

#
# Fassung der Tour. Steigt sie, bekommen ALLE die Einführung noch
# einmal - siehe Modulkopf.
#

TOUR_EDITION = 3

REPO_URL = "https://github.com/daddler/WeintCodex"


@dataclass(frozen=True)
class TourPage:
    """
    Eine Seite der Einführung.

    `icon` ist der Dateiname ohne Endung unter `resources/icons/` - die
    Seite färbt ihn selbst im Akzent ein, statt ein fertiges Bild
    entgegenzunehmen. `action` ist ein optionaler Knopf (Beschriftung,
    Adresse); ihn hat genau eine Seite, und deshalb ist er optional und
    keine eigene Seitenklasse.
    """

    icon: str

    chapter: str

    title: str

    body: str

    action: tuple[str, ...] = field(default_factory=tuple)


#
# ==========================================================
# Der Rundgang
# ==========================================================
#

TOUR_PAGES: tuple[TourPage, ...] = (

    # ------------------------------------------------------
    # Erste Schritte
    # ------------------------------------------------------

    TourPage(
        "companion", "Erste Schritte",
        "Willkommen bei WeintCompanion 3",
        "WeintCompanion ist die App zum Addon WeintCodex. Sie hält das "
        "Addon aktuell, sichert deine Spielstände, wertet eure Raids aus "
        "und bringt das Ergebnis zurück ins Spiel.\n\n"
        "Zusammen sind es drei Teile: das Addon im Spiel, diese App auf "
        "deinem Rechner und der WeintCodex-Bot auf Discord. Was der Bot "
        "weiß, kommt über diese App ins Spiel — und was du im Spiel "
        "einträgst, kommt auf demselben Weg zurück.\n\n"
        "Dieser Rundgang geht einmal durch alles. Er dauert ein paar "
        "Minuten, und du kannst ihn jederzeit abbrechen: unter "
        "Einstellungen → Allgemein steht er als „Einführung erneut "
        "ansehen“ wieder bereit.",
    ),

    TourPage(
        "dashboard", "Erste Schritte",
        "So ist das Fenster aufgebaut",
        "Links steht die Navigationsspalte, in drei Gruppen: RAID "
        "(Übersicht, WeintTV, Academy, Archiv), CHARAKTER (Meine "
        "Charaktere, Vorbereitung, Simmen, WeakAuras, Charakterzuordnung) "
        "und SYSTEM (Addon & Updates, Verbindungen, Einstellungen, "
        "Protokoll).\n\n"
        "Auf einem schmalen Fenster klappt die Spalte auf Symbole "
        "zusammen; die Beschriftung wird dann zum Tooltip. WeintTV und "
        "das Archiv klappen sie immer ein — beide brauchen die Breite.\n\n"
        "Das Aussehen bestimmst du selbst: unter Einstellungen → "
        "Erscheinungsbild wählst du die Akzentfarbe, die Dichte "
        "(komfortabel oder kompakt) und ob Bewegungen reduziert werden "
        "sollen.\n\n"
        "Ganz unten links siehst du, ob ein Discord-Konto verknüpft ist.",
    ),

    TourPage(
        "discord", "Erste Schritte",
        "Discord verbinden",
        "Vieles läuft auch ohne, aber das Meiste wird damit erst "
        "nützlich. Verknüpft wird unter Einstellungen → Discord: ein "
        "Klick, der Browser öffnet sich, du bestätigst — fertig. Dein "
        "Discord-Passwort sieht diese App dabei nie.\n\n"
        "Danach kommen der Raidtermin und die Anmeldung auf die "
        "Übersicht, die Auswertung eurer Raids wird abrufbar, und der "
        "Gildenkalender findet den Weg ins Addon.\n\n"
        "Was du sehen darfst, hängt an deiner Discord-Rolle. Fehlt eine "
        "Freigabe, wird der Bereich nicht versteckt, sondern erklärt sich "
        "— sonst wüsstest du nicht, wonach du fragen sollst. Vergeben "
        "wird sie in Discord von der Raidleitung, nicht hier.\n\n"
        "Du musst nicht: ohne Discord bleibt alles nutzbar, was deinen "
        "eigenen Rechner betrifft — Addon installieren, aktualisieren, "
        "sichern, WeakAuras eintragen, simmen. Leer bleiben nur die "
        "Bereiche, die von aussen kommen. Verbinden und Trennen geht "
        "jederzeit unter *Einstellungen → Discord*, und beides löscht "
        "nichts von dem, was schon hier liegt.\n\n"
        "Bleibt die Verbindung stumm, siehst du das unter Verbindungen: "
        "dort steht, was zuletzt versucht wurde und woran es hing.",
    ),

    # ------------------------------------------------------
    # Addon & Updates
    # ------------------------------------------------------

    TourPage(
        "software", "Addon & Updates",
        "Das Addon installieren und aktualisieren",
        "Unter Addon & Updates liegt die Hauptaufgabe dieser App. Sie "
        "sucht deine WoW-Installation selbst; findet sie keine, stellst "
        "du den Pfad unter Einstellungen → Allgemein ein.\n\n"
        "Es gibt zwei Kanäle, die unabhängig voneinander sind: das "
        "Addon im Spiel und diese App. Beide melden sich, wenn eine neue "
        "Fassung bereitsteht — auf der Übersicht, in der "
        "Navigationsspalte und als Einblendung.\n\n"
        "Vor jeder Aktualisierung wird gesichert, und zwar beides: der "
        "Addon-Ordner und deine Spielstände. Nur eines davon ist "
        "unwiederbringlich — Bossnotizen, Twinkliste, Fortschritt und "
        "WeakAuras stehen nirgends sonst.\n\n"
        "Zurückgeholt wird ein Backup unter Einstellungen → Backups. Die "
        "Spielstände kommen dabei nur auf ausdrückliches Verlangen "
        "zurück: sie waren beim Update nie weg, und sie stillschweigend "
        "zu überschreiben nähme dir unbemerkt eine Woche Fortschritt.\n\n"
        "Heruntergeladene Archive und Backups räumt niemand von selbst "
        "weg. Sammelt sich zu viel an, sagt die App Bescheid und zeigt "
        "dir, wo du aufräumst.",
    ),

    TourPage(
        "changelog", "Addon & Updates",
        "Was in deiner Fassung steckt",
        "Über dem Update-Knopf steht immer der Text zu der Fassung, die "
        "du gerade **hast** — nicht zu der, die bereitsteht. Das ist "
        "Absicht: was ein Update mitbringt, liest du hinter „Alle "
        "Änderungen ansehen“, und beides an derselben Stelle wäre nicht "
        "auseinanderzuhalten.\n\n"
        "Die vollständige Historie beider Teile — App und Addon — findest "
        "du in derselben Ansicht. Der Addon-Changelog reist im "
        "Addon-Paket mit, deshalb steht er auch ohne Netzverbindung "
        "vollständig zur Verfügung.\n\n"
        "Nach jedem Update zeigt dir dieses Fenster kurz, was sich "
        "geändert hat. Abschalten kannst du das unten links; über "
        "Einstellungen → Allgemein holst du es zurück.",
    ),

    # ------------------------------------------------------
    # Raid & Analyse
    # ------------------------------------------------------

    TourPage(
        "dashboard", "Raid & Analyse",
        "Die Übersicht",
        "Die Startseite beantwortet vier Fragen auf einen Blick.\n\n"
        "**Wann ist der nächste Raid** — mit Countdown, und für jeden "
        "anstehenden Raidtag getrennt. Mittwoch und Donnerstag sind zwei "
        "Anmeldungen; wer für den einen zugesagt hat, ist beim anderen "
        "nicht automatisch dabei.\n\n"
        "**Wer geht mit** — die Aufstellung als Reihe von Plätzen, je "
        "Rolle, besetzte in Klassenfarbe. Darunter steht, wie viele Plätze "
        "offen sind und welcher Art. Und ein Merkzeichen sagt dir, ob "
        "**du** dich für diesen Tag schon eingetragen hast.\n\n"
        "**Was war der letzte Pull** — mit Verlauf über dieselbe Boss- "
        "Begegnung. Er überlebt einen Neustart der App, kommt also auch "
        "am Morgen nach dem Raid noch.\n\n"
        "**Steht alles bereit** — Addon gefunden, Updates, Verbindung. "
        "„Erneut prüfen“ fragt sofort nach, statt auf den nächsten "
        "Durchlauf zu warten.",
    ),

    TourPage(
        "weinttv", "Raid & Analyse",
        "WeintTV",
        "Die Tiefenanalyse eines Pulls: Bosslebenspunkte, Schaden und "
        "Heilung im Vergleich, Tode und Kampfwiederbelebungen, "
        "vermeidbarer Schaden mit der Gegenmaßnahme dazu, Wirkungsdauern "
        "deiner Effekte, Laufwege in Metern, Cooldown-Nutzung, "
        "Verbrauchsgüter und Mechanikfehler.\n\n"
        "Alles davon liest **einen** Datenstand — ein vollständiges Bild "
        "eines Augenblicks. Kein Fenster rechnet selbst etwas aus. Genau "
        "das verhindert, dass WeintTV und die Academy zwei verschiedene "
        "Antworten auf dieselbe Frage geben.\n\n"
        "Bleibt eine Karte leer, sagt sie dazu, warum: kein Raid, kein "
        "laufender Pull, oder diese Datenquelle liefert die Zahlen "
        "schlicht nicht. Das sind drei völlig verschiedene Auskünfte, und "
        "nur bei der letzten ist nichts zu machen.\n\n"
        "Ein Klick auf einen Spieler führt in die Academy zu genau "
        "diesem Spieler.",
    ),

    TourPage(
        "academy", "Raid & Analyse",
        "Die Academy",
        "Aus demselben Datenstand entsteht deine Bewertung: sechs "
        "Bereiche mit Sternen — Rotation, Bewegung, Cooldowns, "
        "Mechaniken, Überleben, Leistung — und daraus ein Trainingsplan "
        "mit konkreten Lektionen.\n\n"
        "Bewertet wird immer **gegen deine eigene Rolle**. Einen Tank am "
        "Schadensranking zu messen wäre auf Dauer ein Stern, und beim "
        "erlittenen Schaden erst recht: der meiste davon ist bei ihm die "
        "Aufgabe und kein Fehler.\n\n"
        "Eine Regel solltest du kennen: **null Sterne heißt „keine "
        "Daten“**, nicht „schlecht“. Ohne Vergleichsgruppe — etwa als "
        "einziger Heiler im Zehner — bleibt ein Bereich unbewertet, statt "
        "dir eine Bestnote zu geben, die nichts misst.\n\n"
        "Die Lernkurve zeichnet deine aufgezeichneten Pulls über die Zeit "
        "und bestimmt mit, welcher Bereich im Plan oben steht. Aufzeichnet "
        "wird nur, was fertig ist: mittendrin bewegt sich jede Bewertung "
        "im Sekundentakt.\n\n"
        "Was du im Spiel abhakst, kommt hier an — und umgekehrt. Drei "
        "Tage in Folge mit einer gewerteten Übung an der Trainingspuppe "
        "haken die Rotationslektion ab.",
    ),

    TourPage(
        "archiv", "Raid & Analyse",
        "Archiv und Wiedergabe",
        "Statt des laufenden Kampfes lässt sich auch ein längst "
        "abgeschlossener ansehen: Bericht wählen, Pull wählen, fertig. "
        "WeintTV und die Academy zeigen ihn dann genauso wie einen "
        "laufenden.\n\n"
        "Und mit dem Abspielknopf läuft er Sekunde für Sekunde ab. Weil "
        "jede Bewertung nur den gezeigten Augenblick liest, bewertet die "
        "Academy dabei automatisch mit: du siehst, an welcher Stelle es "
        "gekippt ist.\n\n"
        "Zwei Dinge dazu: Trashgruppen tauchen nicht auf, sie sind keine "
        "Pulls. Und einen Pull zu holen dauert — der Bot liest dafür "
        "Zehntausende Einzelereignisse. Die App wartet geduldig und sagt, "
        "worauf sie wartet, statt vorzeitig aufzugeben.",
    ),

    TourPage(
        "sync", "Raid & Analyse",
        "Woher die Zahlen kommen",
        "Unter Einstellungen → Module stellst du die Datenquelle ein.\n\n"
        "**Simulation** ist die Vorgabe: ein vollständiger 25-Mann-Pull, "
        "der immer gleich abläuft. Er ist da, damit sich WeintTV und die "
        "Academy auch außerhalb der Raidzeit ansehen lassen — und er "
        "zeigt alles, was die Ansichten können.\n\n"
        "**WarcraftLogs** ist die echte Quelle. Gelesen wird sie über den "
        "Bot und nicht von hier: so liegen die Zugangsdaten auf einem "
        "Rechner statt auf fünfundzwanzig, und ihr teilt euch ein "
        "Kontingent. Nötig ist nur, dass irgendwer im Raid hochlädt — "
        "dein Rechner muss nichts mitschreiben.\n\n"
        "Simulation und echte Berichte landen nie in derselben Lernkurve. "
        "Die Karte sagt darunter, welche der beiden sie zeigt.\n\n"
        "Umschalten kannst du jederzeit unter *Einstellungen → Module*. "
        "Es geht dabei nichts verloren: beide Kurven bleiben liegen, du "
        "siehst nur die zur gewählten Quelle.",
    ),

    # ------------------------------------------------------
    # Deine Charaktere
    # ------------------------------------------------------

    TourPage(
        "charaktere", "Deine Charaktere",
        "Meine Charaktere",
        "Was das Addon über deine Ausrüstung weiß, steht hier: "
        "Gegenstandsstufe, fehlende Verzauberungen, leere Sockel, offene "
        "Plätze aus der Best-in-Slot-Liste — je Charakter, mit "
        "Klassenwappen.\n\n"
        "Geurteilt wird dabei im Spiel und nicht hier. Welche "
        "Verzauberung optimal ist und welcher Stein falsch sitzt, "
        "entscheidet das Addon, wo Spec-Profil, Grenzen und der echte "
        "Gegenstands-Tooltip existieren. Diese Seite zeichnet es nur. "
        "Zwei Bewertungen derselben Sache laufen irgendwann auseinander, "
        "und dann widersprechen sich Spiel und Schreibtisch.\n\n"
        "Der Ring zeigt die Bereitschaft. Wurde nichts geprüft, bleibt er "
        "leer und sagt das — eine Null wäre eine Messung, die niemand "
        "vorgenommen hat. Offene BiS-Plätze zählen bewusst nicht mit: sie "
        "hängen am Würfelglück und nicht an deiner Vorbereitung.\n\n"
        "Aufgeführt werden Charaktere ab Stufe 90. Wie viele ausgeblendet "
        "sind, steht darunter — sonst wäre ein verschwundener Twink von "
        "einem Fehler nicht zu unterscheiden.",
    ),

    TourPage(
        "vorbereitung", "Deine Charaktere",
        "Vorbereitung",
        "Dieselben Daten, andere Frage: was fehlt vor dem Raid noch, "
        "über alle deine Charaktere zusammen.\n\n"
        "Gezeigt wird, was zu erledigen ist — fehlende Verzauberungen, "
        "leere Sockel, Steine mit dem Urteil „falsch“ oder „über Cap“. "
        "Was nur eine Abwägung ist, steht auf der Charakterseite im "
        "Spiel: eine Liste, auf der Dinge stehen, die man nicht braucht, "
        "wird nicht benutzt.\n\n"
        "Aktualisiert wird das, sobald du dich im Spiel anmeldest oder "
        "die Ausrüstung wechselst.",
    ),

    TourPage(
        "sim", "Deine Charaktere",
        "Simmen",
        "Weder diese App noch das Addon simmt selbst — ein Sim, der nur "
        "so aussieht, wäre schlimmer als keiner. Was ein Sim liefert und "
        "was gebraucht wird, sind die Wertegewichte: damit rechnet das "
        "Addon an drei Stellen, bei Sockeln, Verzauberungen und beim "
        "Umschmieden.\n\n"
        "Für Schadensausteiler ist die Adresse wowsims.com/mop. Diese "
        "Seite öffnet sie **mit deiner Ausrüstung**: einen Knopf im Spiel "
        "unter Charakter → Simmen, ein Neuladen, und die sechzehn Teile "
        "sind drüben. Das Ergebnis fügst du hier ein und schickst es ins "
        "Spiel — als Vorschlag, der erst auf deinen Klick gilt.\n\n"
        "Für Heiler ist es questionablyepic.com/live. Die Seite schaltet "
        "dann von selbst um und sagt, was dort anders läuft: die "
        "Ausrüstung wandert über die Zwischenablage, und eine Gewichtung "
        "je Charakter gibt es dort nicht.\n\n"
        "Grenzen wie das Trefferkap reisen nicht mit. Sie gelten für "
        "jeden gleich und stehen im Spec-Profil des Addons; weicht der "
        "Sim ab, wird es genannt und nicht übernommen.",
    ),

    TourPage(
        "weakauras", "Deine Charaktere",
        "WeakAuras",
        "Hier trägst du eine WeakAura ein, und im Spiel steht sie in "
        "derselben Liste wie die mitgelieferten. Vorher brauchte es dafür "
        "ein Addon-Release, das alle erst installieren mussten — für eine "
        "Aura, die bis Mittwoch gebraucht wird, war das kein Weg.\n\n"
        "Zwei Reichweiten: nur für dich, oder über den Bot für die ganze "
        "Gilde freigegeben. Freigeben ist eine eigene Handlung und keine "
        "Voreinstellung.\n\n"
        "Die Liste zeigt auch die mitgelieferten Auren, damit sich eine "
        "davon aktualisieren lässt. Ihr Import-String reist dabei nicht "
        "mit — das Krieger-Paket allein sind rund 56 kB —, du trägst also "
        "den neuen ein.\n\n"
        "Im Spiel sichtbar wird alles nach dem nächsten Neuladen: WoW "
        "liest seine gespeicherten Daten während des Spiels nicht "
        "erneut.",
    ),

    TourPage(
        "charaktere", "Deine Charaktere",
        "Charakterzuordnung",
        "Der Kalender-Invite im Spiel lädt echte Charakternamen ein. Den "
        "kennt der Bot aber nur von Spielern, die diese App verknüpft und "
        "ihre Twinkliste gepflegt haben — für alle anderen schickte er "
        "den Discord-Namen weiter, und den gibt es im Spiel nicht. Die "
        "Einladung lief still ins Leere und zählte sogar als "
        "erfolgreich.\n\n"
        "Auf dieser Seite trägt die Raidleitung die fehlenden Namen von "
        "Hand nach. Gildenfremde können die App kaum nutzen; für sie war "
        "das kein Übergangszustand.\n\n"
        "Ohne die Raidlead-Rolle ist die Seite gesperrt und erklärt, "
        "wofür sie da wäre. Sie verschwindet nicht — ein Bereich, der je "
        "nach Rolle gar nicht existiert, lässt sich weder erklären noch "
        "erfragen.",
    ),

    # ------------------------------------------------------
    # Zum Schluss
    # ------------------------------------------------------

    TourPage(
        "settings", "Zum Schluss",
        "Einstellungen — was an und was aus?",
        "Die Einstellungen sind in Abschnitte geteilt: Allgemein, "
        "Erscheinungsbild, Discord, Module, Backups und Über. "
        "**Nichts davon ist endgültig** — jeder Schalter lässt sich dort "
        "jederzeit wieder umlegen, und keiner löscht dabei etwas.\n\n"
        "**Discord verbinden** (Discord): verbunden kommen Raidtermin, "
        "Anmeldung und die Auswertung eurer Raids herein, und der "
        "Gildenkalender findet den Weg ins Spiel. Getrennt funktioniert "
        "alles weiter, was deinen eigenen Rechner betrifft — Addon "
        "installieren, aktualisieren, sichern —, aber die Übersicht bleibt "
        "leer. Trennen löscht nichts von dem, was schon hier liegt.\n\n"
        "**Automatisch starten** (Allgemein): an ist die App beim Anmelden "
        "schon da und hat den Raidtermin und ein wartendes Update parat. "
        "Aus musst du daran denken, sie zu öffnen — sonst ändert sich "
        "nichts.\n\n"
        "**In den Infobereich minimieren** (Allgemein): an läuft sie "
        "weiter, wenn du das Fenster schließt, und meldet ein Update als "
        "Sprechblase. Aus beendet das Schließen die App.\n\n"
        "**Datenquelle** (Module): *Simulation* zeigt einen vollständigen "
        "Beispiel-Pull, damit sich WeintTV und die Academy auch ausserhalb "
        "der Raidzeit ansehen lassen. *WarcraftLogs* zeigt eure echten "
        "Kämpfe, braucht aber ein verknüpftes Discord-Konto und jemanden "
        "im Raid, der hochlädt. Umschalten geht jederzeit; die Lernkurven "
        "der beiden bleiben getrennt.\n\n"
        "**Diese Einführung** (Allgemein): hier holst du sie zurück, und "
        "hier schaltest du auch das Fenster nach jedem Update ab.\n\n"
        "Einer ist im Ernstfall wichtig: unter Discord lässt sich die "
        "**Adresse des Bots** überschreiben. Der Bot zieht gelegentlich "
        "auf einen anderen Rechner um, und ohne diese Möglichkeit hülfe "
        "dann nur ein neues Programm. Eine unbrauchbare Adresse wird "
        "abgelehnt statt übernommen.\n\n"
        "Unter Protokoll steht, was die App zuletzt getan hat. Wenn etwas "
        "nicht klappt, ist das die Auskunft, die weiterhilft — und genau "
        "die, die man einer Meldung beilegt.",
    ),

    TourPage(
        "discord_mark", "Zum Schluss",
        "Sag uns, was nicht stimmt",
        "Das war der Rundgang. Du holst ihn jederzeit unter "
        "Einstellungen → Allgemein zurück.\n\n"
        "**Und jetzt die Bitte:** WeintCodex und WeintCompanion leben "
        "davon, dass gemeldet wird, was daneben liegt. Besonders bei den "
        "**Sockelsteinen** im Spiel — dort sind die Empfehlungen noch "
        "nicht überall verlässlich, und ohne Rückmeldung fällt kein "
        "einziger dieser Fälle auf.\n\n"
        "Schreib im Discord der Gilde, was dir aufgefallen ist: welche "
        "Spezialisierung, was vorgeschlagen wurde, was du erwartet "
        "hättest. Ein Screenshot dazu, und die Sache ist meistens in "
        "einer Fassung erledigt.\n\n"
        "Das gilt genauso für alles andere: fehlende Erklärungen, Knöpfe, "
        "die niemand findet, Texte, die man zweimal lesen muss. Vielen "
        "Dank — und viel Erfolg im Raid.",
        action=("Feedback im Discord", feedback_url()),
    ),

)


class _DialogPage(QWidget):
    """
    Eine Seite: Symbol, Kapitel, Titel, Fließtext, optionaler Knopf.

    Der Fließtext steht **linksbündig**. Zentriert war er, solange eine
    Seite aus zwei Sätzen bestand; ein Absatz über fünf Zeilen ist so
    nicht mehr zu lesen, weil jede Zeile woanders anfängt.
    """

    def __init__(self, page: TourPage):

        super().__init__()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(tokens.SPACE[1])

        #
        # Symbol im Akzent. Der Dialog ist modal und lebt nur, solange
        # er offen ist - hier beim Bauen zu lesen ist deshalb dasselbe
        # wie beim Zeichnen: die Akzentfarbe kann sich nicht ändern,
        # während er vor einem steht.
        #

        icon_label = QLabel()

        icon_label.setPixmap(
            tinted_pixmap(page.icon, theme().accent_base(), 34)
        )

        icon_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(icon_label)

        if page.chapter:

            layout.addWidget(
                eyebrow_label(page.chapter, theme().accent_base())
            )

        title_label = QLabel(page.title)

        title_label.setFont(font("section"))

        title_label.setWordWrap(True)

        title_label.setStyleSheet(
            f"color:{tokens.WHITE};background:transparent;"
        )

        layout.addWidget(title_label)

        body_label = QLabel(_render_emphasis(page.body))

        body_label.setFont(font("body"))

        body_label.setWordWrap(True)

        body_label.setTextFormat(Qt.RichText)

        body_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        body_label.setStyleSheet(
            f"color:{tokens.TEXT['secondary']};background:transparent;"
        )

        layout.addWidget(body_label)

        if len(page.action) == 2:

            label, url = page.action

            button = HeroButton(label, primary=False)

            button.clicked.connect(
                lambda: open_url(url, app_url=app_url(url))
            )

            row = QHBoxLayout()

            row.addWidget(button)
            row.addStretch()

            layout.addSpacing(tokens.SPACE[0])
            layout.addLayout(row)

        layout.addStretch()


def _render_emphasis(text: str) -> str:
    """
    `**fett**` wird fett, Absätze bleiben Absätze.

    Bewusst kein Markdown-Renderer: der Text ist von Hand geschrieben
    und braucht genau eine Auszeichnung. Alles andere wird vorher
    maskiert, sonst nähme ein `<` in einem Satz dem Label den Rest der
    Seite weg.
    """

    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    parts = safe.split("**")

    #
    # Ungerade Positionen liegen zwischen zwei Sternenpaaren. Bei einer
    # unpaarigen Anzahl wird der Rest fett - aber er wird auch wieder
    # geschlossen. Ein offenes <b> nähme sonst alles darunter mit.
    #

    rendered = "".join(
        f"<b>{part}</b>" if index % 2 else part
        for index, part in enumerate(parts)
    )

    return rendered.replace("\n\n", "<br><br>").replace("\n", "<br>")


class WhatsNewDialog(QDialog):
    """
    Das Fenster selbst. Mit nur einer Seite blendet sich die
    Zurück/Weiter-Navigation auf einen einzelnen Schließen-Knopf
    herunter.
    """

    #
    # Größer als bis 2.8 (560 x 480): der Rundgang trägt jetzt echte
    # Erklärungen statt zweier Sätze je Seite. Bleibt unter dem
    # Fenstermindestmaß (960 x 640), damit er auch dort vollständig
    # hineinpasst.
    #

    WIDTH = 700

    HEIGHT = 620

    def __init__(
        self,
        pages: list[TourPage],
        finish_label: str = "Fertig",
        skippable: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._dont_show_again = False

        self.setWindowTitle("WeintCompanion")

        self.setModal(True)

        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(f"""
        QDialog{{
            background:{tokens.SURFACE["card"]};
            border:1px solid {tokens.BORDER["strong"]};
            border-radius:{tokens.RADIUS["lg"]}px;
        }}
        """)

        root = QVBoxLayout(self)

        root.setContentsMargins(32, 28, 32, 22)
        root.setSpacing(tokens.SPACE[2])

        self.stack = QStackedWidget()

        for page in pages:
            self.stack.addWidget(_DialogPage(page))

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )

        scroll.setWidget(self.stack)

        self._scroll = scroll

        root.addWidget(scroll, 1)

        #
        # Fortschritt. Bei zwanzig Seiten sagen Punkte allein nicht mehr,
        # wo man ist - die Zahl daneben schon.
        #

        self._dots: list[QLabel] = []

        self._progress = QLabel()

        if len(pages) > 1:

            dots_row = QHBoxLayout()

            dots_row.setAlignment(Qt.AlignHCenter)
            dots_row.setSpacing(5)

            for _ in pages:

                dot = QLabel()

                dot.setFixedSize(6, 6)

                self._dots.append(dot)

                dots_row.addWidget(dot)

            self._progress.setFont(font("micro"))

            self._progress.setStyleSheet(
                f"color:{tokens.TEXT['muted']};background:transparent;"
            )

            dots_row.addSpacing(tokens.SPACE[2])
            dots_row.addWidget(self._progress)

            root.addLayout(dots_row)

        footer = QHBoxLayout()

        footer.setSpacing(tokens.SPACE[2])

        self.checkbox = QCheckBox("Nicht mehr automatisch anzeigen")

        self.checkbox.toggled.connect(self._set_dont_show_again)

        footer.addWidget(self.checkbox)

        footer.addStretch()

        self._finish_label = finish_label

        #
        # EIN AUSGANG, DER VON ANFANG AN SICHTBAR IST.
        # Der Rundgang ist vollständig und damit lang. Wer ihn nicht
        # jetzt lesen will, darf nicht siebzehnmal auf "Weiter" klicken
        # müssen - sonst schließt er das Fenster und findet nie wieder
        # her. Deshalb steht daneben, wo er wieder auftaucht.
        #

        self.skip_button = HeroButton("Später", primary=False)

        self.skip_button.setToolTip(
            "Einstellungen → Allgemein → Einführung erneut ansehen"
        )

        self.skip_button.clicked.connect(self.accept)

        self._skippable = skippable

        self.skip_button.setVisible(skippable)

        footer.addWidget(self.skip_button)

        self.back_button = HeroButton("Zurück", primary=False)

        self.back_button.clicked.connect(self._go_back)

        self.next_button = HeroButton(finish_label, primary=True)

        self.next_button.clicked.connect(self._go_next)

        footer.addWidget(self.back_button)
        footer.addWidget(self.next_button)

        root.addLayout(footer)

        self.stack.currentChanged.connect(self._update_nav)

        self._update_nav()

    # --------------------------------------------------

    def showEvent(self, event):
        """
        Nach vorn holen.

        Ein modaler Dialog, den man nicht sieht, ist kein Dialog mehr,
        sondern ein hängendes Programm: `exec()` wartet in einer eigenen
        Ereignisschleife, und der Nutzer sieht nur ein Fenster, das nicht
        weitergeht. Genau so lief der 2.0.3-Start unter Windows. Die
        Ursache ist inzwischen beseitigt (siehe `MainWindow.showEvent`),
        aber dieser Dialog erscheint bei jedem Update genau einmal - und
        wenn er dann einmal hinter etwas liegt, ist die App für den
        Nutzer kaputt. Zwei Zeilen Versicherung sind das wert.
        """

        super().showEvent(event)

        self.raise_()

        self.activateWindow()

    @property
    def dont_show_again(self) -> bool:
        return self._dont_show_again

    def _set_dont_show_again(self, checked: bool):
        self._dont_show_again = checked

    # --------------------------------------------------

    def _update_nav(self):

        index = self.stack.currentIndex()
        last = self.stack.count() - 1

        self.back_button.setVisible(index > 0)

        self.next_button.setText(
            self._finish_label if index == last else "Weiter"
        )

        #
        # Auf der letzten Seite gibt es nichts mehr zu überspringen -
        # dort heißt der Hauptknopf ohnehin "Los geht's". Gefragt wird
        # dabei die gespeicherte Absicht und nicht der aktuelle Zustand
        # des Knopfes: sonst käme er beim Zurückblättern nicht wieder.
        #

        self.skip_button.setVisible(self._skippable and index < last)

        accent = theme().accent_base()

        for i, dot in enumerate(self._dots):

            color = accent if i == index else tokens.BORDER["strong"]

            dot.setStyleSheet(
                f"background:{color};border-radius:3px;"
            )

        if self._dots:
            self._progress.setText(f"{index + 1} / {self.stack.count()}")

        #
        # Jede Seite beginnt oben. Ohne das bliebe die Bildlaufposition
        # der vorigen stehen, und eine kurze Seite nach einer langen
        # sähe leer aus.
        #

        bar = self._scroll.verticalScrollBar()

        if bar is not None:
            bar.setValue(0)

    def _go_back(self):

        self.stack.setCurrentIndex(
            self.stack.currentIndex() - 1
        )

    def _go_next(self):

        index = self.stack.currentIndex()

        if index >= self.stack.count() - 1:

            self.accept()
            return

        self.stack.setCurrentIndex(index + 1)


# --------------------------------------------------
# Orchestrierung
# --------------------------------------------------


def _build_tour_pages() -> list[TourPage]:

    return list(TOUR_PAGES)


def _build_changelog_pages(since_version: str) -> list[TourPage]:

    sections = read_changelog_sections(VERSION, since_version=since_version)

    if not sections:

        return [TourPage(
            "changelog", "",
            f"Was ist neu in {VERSION}",
            "Diese Version enthält allgemeine Verbesserungen.",
        )]

    return [
        TourPage(
            "changelog", "",
            f"Was ist neu in {version}",
            format_changelog_body(body),
        )
        for version, body in sections
    ]


def _remember_tour(config) -> None:
    """
    Die Fassung der Tour vermerken.

    Gesehen ist gesehen: vermerkt wird beim Zeigen und nicht erst beim
    Durchklicken bis zur letzten Seite. Wer nach drei Seiten genug hat,
    hat die Tour trotzdem bekommen - und bekäme sie sonst bei jedem
    Start erneut, was genau die Sorte Fenster ist, die man irgendwann
    ungelesen wegklickt.
    """

    config.data["onboarding_tour_edition"] = TOUR_EDITION


def show_tour(manager, parent=None) -> None:
    """
    Zeigt den Rundgang unabhängig vom gespeicherten Zustand - für den
    Knopf in Einstellungen → Allgemein.
    """

    dialog = WhatsNewDialog(
        _build_tour_pages(),
        finish_label="Los geht's",
        skippable=True,
        parent=parent,
    )

    _remember_tour(manager.config)

    dialog.exec()

    if dialog.dont_show_again:
        manager.config.data["whats_new_enabled"] = False

    manager.config.save()


def show_whats_new_if_needed(manager, parent=None) -> None:
    """
    Wird einmal beim Start aufgerufen (siehe gui/main_window.py).

    Drei Fälle, in dieser Reihenfolge:

    1. Die Tour wurde noch nie gezeigt, oder seither neu geschrieben
       (`TOUR_EDITION`) - dann der vollständige Rundgang. Das gilt
       ausdrücklich auch für langjährige Nutzer: die Einführung von 1.0
       beschrieb eine App, die es so nicht mehr gibt.
    2. Sonst: die aktuelle Version ist bereits bestätigt - nichts.
    3. Sonst: die Änderungen seit der zuletzt gesehenen Version.
    """

    config = manager.config

    if not config.data.get("whats_new_enabled", True):
        return

    seen_version = config.data.get("onboarding_seen_version", "")

    try:
        seen_edition = int(config.data.get("onboarding_tour_edition") or 0)
    except (TypeError, ValueError):
        seen_edition = 0

    #
    # Wer die App zum ersten Mal startet, hat auch keine Fassung
    # vermerkt - beide Bedingungen führen zur Tour, und die zweite
    # deckt die erste mit ab.
    #

    if seen_edition < TOUR_EDITION:

        pages = _build_tour_pages()
        finish_label = "Los geht's"
        skippable = True

        _remember_tour(config)

    elif seen_version and versions_equal(seen_version, VERSION):

        return

    else:

        pages = _build_changelog_pages(seen_version)
        finish_label = "Schließen"
        skippable = False

    dialog = WhatsNewDialog(
        pages,
        finish_label=finish_label,
        skippable=skippable,
        parent=parent,
    )

    dialog.exec()

    config.data["onboarding_seen_version"] = VERSION

    if dialog.dont_show_again:
        config.data["whats_new_enabled"] = False

    config.save()
