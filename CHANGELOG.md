# Changelog

Alle nennenswerten Änderungen an WeintCompanion, von Version 0.7.2 bis 1.6.2.

## 2.4.2

**Die Discord-Verknüpfung bleibt jetzt, wo sie ist.**
Nach einem Neustart des Rechners war sie regelmässig wieder weg, und
der Hinweis „Discord noch nicht verknüpft" stand erneut da. Dafür
gab es drei Gründe, alle drei sind behoben.

Der erste: lehnt der Bot die Verknüpfung einmal ab, hebt die App sie
erst nach mehreren Ablehnungen auf — gemeint waren drei getrennte
Vorfälle. Tatsächlich reichte ein einziger. Eine Meldung ans Discord,
die nicht durchkommt, wird nämlich alle fünf Sekunden erneut
versucht, und damit war die Grenze nach einer Viertelminute
überschritten. Jetzt zählen nur Ablehnungen, die mindestens eine
Minute auseinanderliegen. Ein Bot, der gerade neu startet, kostet die
Verknüpfung nicht mehr.

Der zweite: die Datei mit der Verknüpfung wurde beim Speichern zuerst
geleert und dann neu geschrieben. Ein Absturz oder ein erzwungener
Neustart genau dazwischen liess eine leere Datei zurück — und die war
von „noch nie verbunden" nicht zu unterscheiden. Jetzt wird daneben
geschrieben und erst am Ende umgestellt, und es gibt eine Sicherung,
aus der die App sich holt, was noch da ist. Das gilt für Linux und
Windows gleichermassen.

Der dritte: hebt die App die Verknüpfung von sich aus auf, sagt sie
das jetzt im Protokoll. Bisher geschah es lautlos, und aufgefallen
ist es erst beim nächsten Start.

**Und verbinden heisst wieder verbinden.**
Wenn die Anmeldung schiefging, blieb auf der Seite „Browser öffnet
sich …" stehen und sonst passierte nichts. Jetzt steht der Grund da:
kein Browser gefunden (mit der Adresse zum Selbstöffnen), die
Anmeldung läuft schon in einem anderen Fenster, oder die Antwort des
Bots war unvollständig.

Der letzte Fall ist der wichtigste. Eine unvollständige Antwort wurde
bisher trotzdem gespeichert. Die App meldete danach „Verbunden als
…", während in Wahrheit kein einziger Abruf laufen konnte — Kalender,
Roster und Auswertung blieben leer, ohne dass irgendwo stand, warum.
Eine solche Antwort gilt jetzt als fehlgeschlagene Anmeldung.

### Technisch
- `AUTH_REJECTION_COOLDOWN` (60 s) in `core/discord_account.py`: eine
  Ablehnung zählt nur, wenn sie weit genug von der vorigen entfernt
  ist. Ohne das war `AUTH_REJECTIONS_BEFORE_UNLINK = 3` in fünfzehn
  Sekunden erreicht, weil eine fehlgeschlagene Zustellung in der
  Warteschlange des Addons liegen bleibt und im Sync-Takt erneut
  versucht wird (`core/sync_manager.py`)
- `DiscordAccountStore.save()` schreibt über eine Nebendatei mit
  `fsync()` und `os.replace()` und legt danach eine `.bak` an;
  `load()` holt daraus zurück, wenn die Hauptdatei fehlt oder nicht
  lesbar ist. `clear()` räumt beide weg, sonst käme eine getrennte
  Verknüpfung zurück
- `save()` wirft `DiscordAccountError` statt lautlos einen Eintrag
  ohne `companion_token` abzulegen; beide Aufrufer (Einstellungen und
  Einrichtung) behandeln das jetzt als Fehlschlag. Vorher flog eine
  Ausnahme mitten aus einem Qt-Slot und das `refresh()` darunter lief
  nie
- `is_usable()` ist die eine Antwort auf „ist ein Konto verknüpft".
  Vier Stellen prüften „steht da etwas", sieben Clients verlangten
  `companion_token` — der Eintrag ohne Token erfüllte das erste und
  nicht das zweite
- `parse_exchange_response()` in `core/discord_auth.py` prüft die
  Antwort des Bots, bewusst als reine Funktion neben `login()`
- `note_auth_rejected()` meldet die Aufhebung selbst über den Logger
  der App (`discord_account.set_logger()` in `CompanionManager`).
  Vier der fünf Aufrufer haben den Rückgabewert nie ausgewertet, der
  fünfte schrieb nach stdout
- `login()` wertet den Rückgabewert von `open_url()` aus und
  übersetzt ein belegtes Port 53682 in einen deutschen Satz
- `tests/test_discord_account.py` und das neue
  `tests/test_discord_auth.py` halten alle sechs Regeln fest

## 2.4.1

**Über dem Update-Knopf steht jetzt, was in deiner Fassung steckt.**
Bisher stand dort ein Text, der die Fassung beschrieb, die es zu
holen gibt — also etwas, das auf dem Rechner noch gar nicht liegt.
Beschriftet war er nicht, und deshalb war er von einer Beschreibung
dessen, was man gerade hat, nicht zu unterscheiden.

Jetzt steht eine Zeile darüber: „Das steckt in deiner Fassung 2.4.0:"
— und darunter die Notizen genau dazu. Was das Update mitbringt,
steht wie bisher hinter *Alle Änderungen ansehen*, einen Knopf weiter
und dort auch so benannt. Dasselbe gilt für die beiden Karten unter
*Addon & Updates*.

Liegen zu der laufenden Fassung keine Notizen vor, sagt die Karte
genau das. Der Text einer anderen Fassung rückt nie an diese Stelle
nach.

**Und die Änderungsnotizen selbst werden von hier an einfacher
geschrieben.** Sie waren für die Entwicklung geschrieben: mit
Dateinamen, Funktionsnamen und Sätzen über die Ursache eines Fehlers
statt über das, was man davon merkt. Wer die App benutzt, konnte
daraus oft nicht einmal ablesen, ob ihn eine Änderung überhaupt
betrifft. Künftig steht oben, was sich für dich ändert; das
Technische steht weiterhin da, aber unten unter *Technisch*.

### Technisch
- `update_note()` in `core/changelog_source.py` ersetzt `latest_entry()`
  und liest den Eintrag zur **installierten** Fassung. Fehlt er, ist die
  Antwort `None` statt des Eintrags einer anderen Fassung — dieselbe
  Linie wie `stars == 0`. Ohne das wäre beim Addon der Release-Text der
  neuen Fassung eingesprungen, sobald dem Addon-Ordner die
  `CHANGELOG.md` fehlt
- `UpdateRow` und `ComponentCard` tragen dafür eine eigene, gedämpfte
  Kopfzeile über dem Auszug; während eines laufenden Vorgangs wird sie
  ausgeblendet, weil der Fortschrittstext an derselben Stelle steht und
  keine Fassung meint
- Die Regeln für die Formulierung stehen in `CLAUDE.md` und gelten für
  beide Repositorys

## 2.4.0

**Ein wartendes Update sieht man jetzt, ohne danach zu suchen.**
Der Hinweis auf der Übersicht war eine Karte in Kartenfarbe auf einer
Karte in Kartenfarbe: gleiche Fläche, gleicher Radius, keine Kante. Auf
einer Seite, die daneben den nächsten Raid, die Aufstellung und den
letzten Pull trägt, stand ausgerechnet der eine Block, der eine
Entscheidung verlangt, am unauffälligsten da — und sein Knopf war ein
Umrissknopf neben dem vollflächigen „WoW starten" direkt darunter, also
die scheinbar zweitwichtigere von zwei Handlungen.

Der Hinweis trägt jetzt eine senkrechte Leiste in Akzentfarbe, eine
getönte Fläche mit feiner Kante, das Download-Symbol auf einer eigenen
Kachel und den Hauptknopf der Anwendung. Um die Karte liegt ein Ring,
der langsam heller und dunkler wird — im selben Takt wie der Warnpunkt
am Eintrag „Addon & Updates", denn beide lesen dieselbe Uhr; zwei
eigene Zeitgeber liefen gegeneinander und sähen nach einem Fehler aus.

Zwei Rücksichten sind dabei eingebaut. Läuft in WeintTV gerade ein Pull,
**steht der Ring still**: ein Update kann warten, ein laufender Kampf
nicht. Und wer unter Einstellungen → Erscheinungsbild „Bewegung
reduzieren" gewählt hat, bekommt den Ring in **voller** Stärke, nur
eben unbewegt — der Hinweis verschwindet nicht, er hört bloss auf, sich
zu bewegen.

## 2.3.5

**Die Übersicht sagt jetzt, ob du selbst schon eingetragen bist.**
Die Aufstellung stand da, die Zahlen standen da — nur die kleinste und
häufigste Frage vor einem Raidabend beantwortete die Karte nicht: habe
*ich* mich eigentlich schon angemeldet? „21 von 25 zugesagt" sagt das
nicht, und es lag auch nicht am Zufall: die Antwort des Bots nennt
bewusst keine Namen, es war aus ihr also gar nicht zu erkennen, wer von
den 21 man selbst ist. Wer sichergehen wollte, ging trotz aller Zahlen
noch einmal ins Discord.

Neben jedem Raidtag steht deshalb jetzt der eigene Stand: **ANGEMELDET**,
VIELLEICHT, ERSATZBANK, ABGEMELDET — oder, in Warnfarbe, **NICHT
ANGEMELDET**. Je Tag und nicht je Raid, denn Mittwoch und Donnerstag
sind zwei Anmeldungen: am Mittwoch zugesagt und am Donnerstag noch gar
nicht geantwortet ist genau der Fall, den eine gemeinsame Auskunft
verschluckt hätte.

Zwei Feinheiten, die nicht zufällig so sind. **Abgesagt zu haben ist
kein Fehler** und sieht deshalb auch nicht wie einer aus: eine Absage
ist eine Antwort, der Raidleiter weiss Bescheid, und es gibt nichts
mehr zu tun. In Warnfarbe steht allein die fehlende Anmeldung — der
einzige Fall, in dem noch jemand handeln muss. Und meldet der Bot dazu
nichts (ältere Fassung), steht dort **gar nichts**, statt eine fehlende
Anmeldung zu behaupten, die niemand geprüft hat.

Der Stand zieht sich von selbst nach: am Raidtag fragt die App im
Minutentakt, wer sich also im Discord einträgt, sieht es kurz darauf
auch hier. Sichtbar wird das Ganze, sobald der Bot in der neuen Fassung
läuft.

**Die Academy erkennt jetzt eine Lernkurve.**
Sie bewertete bisher ausschliesslich den Kampf, der gerade auf dem
Bildschirm stand — und beantwortete damit die eine Frage nicht, wegen
der es ein Lernzentrum gibt: *werde ich besser?* Drei Sterne in
Mechaniken sind ein Befund; drei Sterne nach fünf und vier sind eine
Entwicklung, und erst die zweite Auskunft sagt einem, ob sich das Üben
lohnt. Die Verlaufskarte unten auf der Übersicht sagte deshalb bis
jetzt ehrlich, dass es sie nicht gibt: eine Bewertung lebte nur für
den Moment ihrer Anzeige und wurde nirgends aufgehoben.

Ab dieser Fassung merkt sich die Anwendung jeden ausgewerteten Pull —
den Boss, den Tag und die Sterne der sechs Bereiche — und zeichnet
daraus die Kurve: die Gesamtbewertung durchgezogen, der über die
letzten Pulls schwächste Bereich gestrichelt daneben, darüber ein Satz
wie „Über 7 Pulls besser: 2,7 → 3,8 Sterne."

Aufgezeichnet wird still im Hintergrund, sobald WeintTV **oder** die
Academy geöffnet ist — wer den Abend über die Raidansicht laufen lässt
und erst danach in die Academy sieht, findet den ganzen Abend vor und
nicht nur den letzten Pull. Vier Regeln sorgen dafür, dass die Kurve
etwas taugt:

- **Nur beendete Pulls**, und nur ab einer halben Minute Kampf. Aus
  der Mitte eines Kampfes abgelesen beschriebe ein Punkt einen Pull,
  den es so nie gab; ein Wipe nach zwölf Sekunden misst den Pull und
  nicht den Spieler.
- **Jeder Pull genau einmal**, auch wenn man ihn im Archiv zweimal
  öffnet oder danach abspielt.
- **Keine erfundenen Punkte.** Ein Bereich, zu dem der Datenquelle die
  Angaben fehlten, hat an diesem Tag keinen Punkt — statt einer Null,
  die wie ein Einbruch aussähe.
- **Simulation und echte Berichte bleiben getrennt**, ebenso zwei
  Spezialisierungen: eine Rotationsbewertung als Frost sagt nichts
  über die Rotation als Feuer, und eine Linie durch beide zeigte einen
  Bruch, den nie jemand gespielt hat.

Und die Reihenfolge kommt aus dem Raidabend, nicht aus der Klickfolge:
wer im Archiv erst Pull 5 und dann Pull 2 ansieht, bekommt trotzdem
keine Kurve, die einen Rückschritt zeigt, den es nie gab.

**Der Trainingsplan folgt jetzt dem Muster statt dem Ausrutscher.**
Er wählte seine Bereiche allein nach den Sternen des gerade
angezeigten Kampfes. Ein einziger missratener Pull warf ihn damit
komplett um: wer acht Pulls lang bei vier Sternen in Mechaniken steht
und in diesem einen auf zwei fällt, bekam einen Plan, der nichts
anderes mehr kannte — obwohl da nichts zu üben war, was er nicht
längst konnte.

Sobald genug Pulls aufgezeichnet sind, entscheidet deshalb der
Durchschnitt über die Kurve, welche Bereiche der Plan aufgreift; für
Bereiche ohne Kurve zählt weiterhin der angezeigte Kampf. Stehen zwei
gleich da, kommt der zuerst, der **schwächer wird** — zwei Bereiche
auf drei Sternen sind nicht gleich dringend, wenn der eine steigt und
der andere fällt. Über dem Plan steht ein Satz, woher seine Auswahl
kommt, denn eine Auswahl, die den Sternen daneben widerspricht, sähe
sonst nach einem Fehler aus.

Zwei Dinge bleiben ausdrücklich, wie sie waren: die **Bewertungen**
selbst beschreiben weiter genau diesen Kampf (die Kurve ordnet, sie
bewertet nicht), und innerhalb des Plans steht weiter oben, was das
Log an diesem Kampf nachweislich bemängelt — ein belegter Fehler ist
dringender als ein Durchschnitt. Ohne aufgezeichnete Pulls verhält
sich der Plan exakt wie bisher. Der Plan im Spiel übernimmt dieselbe
Auswahl, er kommt aus derselben Stelle.

## 2.3.4

**Die Aufstellung auf der Übersicht zeigt endlich die Klassenfarben.**
Die Reihen mit den Plätzen gab es schon, aber jeder besetzte Platz
hatte dieselbe Farbe - man sah, *wie viele* zugesagt hatten, und nicht,
*was* zugesagt hatte. Das lag nicht an der Anzeige: der Bot schickte
nur Zahlen. Welche Klasse hinter einer Zusage steckt, wusste die
Anwendung nicht, und geraten hätte sie es nicht - eine erfundene Klasse
wäre in der Aufstellung von einer gemeldeten nicht zu unterscheiden
gewesen.

Der Bot nennt jetzt zu jeder Zusage Rolle und Klasse (weiterhin ohne
einen einzigen Namen - die stehen wie bisher nur im Roster hinter der
Raidlead-Rolle). Damit stehen die Tanks, die Heiler und der Schaden in
eigenen Reihen, jeder Platz in der Farbe seiner Klasse, und die noch
offenen Plätze dahinter als Lücke. Ein Blick sagt jetzt, ob die vier
fehlenden Zusagen Heiler oder Schaden sind - also genau das, wofür man
sonst ins Discord sieht.

Zwei Kleinigkeiten am Rand: Wer sich angemeldet hat, ohne für diesen
Raid eine Klasse zu wählen, erscheint mit der Klasse aus seiner letzten
Anmeldung - dieselbe Vorbelegung, die auch der Anmelde-Beitrag im
Discord zeigt. Und die deutschen Klassennamen aus dem Discord treffen
nun ebenfalls ihre Farbe; vorher wäre so eine Zeile grau geblieben, und
Grau heisst hier "keine Klasse gemeldet".

Wichtig: sichtbar wird das erst, wenn der Bot in der neuen Fassung
läuft. Bis dahin bleibt es beim bisherigen einen Streifen - die
Aufstellung stimmt dann, nur das Bild ist ärmer.

**Und beide Raidtage stehen jetzt untereinander.**
Mittwoch und Donnerstag sind zwei Anmeldungen - wer am Mittwoch
zusagt, muss am Donnerstag nicht können. Die Übersicht nannte aber nur
den nächsten Termin: am Dienstag also den Mittwoch, während der
Donnerstag daneben halb leer sein konnte, ohne dass es jemand sah. Der
Bot schickte beide Tage von Anfang an in derselben Antwort, sie
standen nur nie auf dem Bildschirm.

Jeder Tag hat nun seine eigene Zeile mit Datum und Uhrzeit, seine
eigene Zahl, seine eigene Aufstellung und seinen eigenen Satz darunter.
Die Zahl der Zusagen ist dafür aus dem Kopf der Karte in die Zeile
ihres Tages gewandert - bei zwei Terminen wäre oben nicht zu sehen,
welchen von beiden sie meint. Dass die Anmeldung geschlossen ist, steht
weiterhin genau einmal oben rechts: das gilt für den Raid und nicht für
einen seiner Tage.

Ein bereits gelaufener Tag kommt dabei nicht als "nächste Woche"
zurück. Der Bot nennt zu jedem Wochentag dessen nächstes Vorkommen, am
Donnerstag steht der Mittwoch dort also schon auf der kommenden Woche -
mit den Zusagen der vergangenen. Solange nur ein Termin angezeigt
wurde, fiel das nicht auf; untereinander wäre es eine Aufstellung zu
einem Datum, zu dem sie nicht gehört.

## 2.3.3

**Ein wartendes Update meldet sich jetzt von selbst.**
Bisher wurde genau zweimal nachgesehen: einmal beim Start und danach
nur noch, wenn jemand auf "Erneut prüfen" drückte. Wer die Anwendung
morgens öffnete und abends damit raidete, erfuhr von einer mittags
veröffentlichten Fassung nichts - nicht, weil die Anzeige fehlte,
sondern weil niemand mehr nachgefragt hat. Die drei Stellen, die ein
Update ansagen (die Systemzeile der Übersicht, das Abzeichen an
"Addon & Updates" und die Einblendung unten rechts), waren die ganze
Zeit da; sie hingen nur an einer Prüfung, die nicht mehr stattfand.

Im Hintergrund läuft nun alle fünfzehn Minuten eine Prüfung mit, und
sobald sie etwas Neues findet, ist es sofort auf dem Bildschirm -
ohne einen Klick. Angekündigt wird jede Fassung genau einmal: eine
Prüfung, die dasselbe Ergebnis liefert wie die letzte, sagt gar
nichts. Steht das Fenster im Tray, kommt die Meldung zusätzlich als
Sprechblase des Tray-Symbols, und ein Klick darauf holt das Fenster
zurück und öffnet "Addon & Updates". Eine Einblendung in einem
Fenster, das niemand sieht, ist keine Meldung - und "in den Tray
minimieren" ist genau die Betriebsart, in der eine Fassung
stundenlang bereitliegen kann.

**Der Stand der Anmeldungen aktualisiert sich mit.**
Die Aufstellung auf der Übersicht wurde zwar im Hintergrund abgeholt,
aber niemand zeichnete sie neu - sichtbar wurde die neue Zahl erst,
wenn man die Seite verliess und wieder betrat. Jetzt zieht die Karte
nach, sobald sich etwas geändert hat, und nur dann.

Der Takt richtet sich dabei nach dem Termin. Der *Termin* ändert sich
einmal pro Woche, der *Stand der Anmeldungen* am Raidtag im
Minutentakt - und genau dann sieht jemand hin. Ab sechs Stunden vor
dem Raid und für seine ganze Dauer wird deshalb jede Minute gefragt,
an den übrigen Tagen weiterhin träge alle fünf Minuten. Mitgezählt
wird ausserdem mehr als vorher: dass die Anmeldung geschlossen wurde,
dass sich der Sollbestand je Rolle geändert hat oder dass ein
zweiter Raid dazugekommen ist, blieb bislang unsichtbar, obwohl die
Karte all das anzeigt.

"Erneut prüfen" auf der Übersicht holt jetzt auch die Aufstellung neu
- der Knopf sitzt direkt daneben, und "erneut prüfen" heisst dort
alles, was die Seite zeigt.

## 2.3.2

**Die Discord-Verknüpfung überlebt jetzt ein Update des Bots.**
Bisher stand nach jedem Neustart des Bots in den Einstellungen wieder
"Nicht verbunden", und zwar bei allen gleichzeitig. Das war weder ein
Zufall noch ein Fehler dieser App: der Bot läuft auf einem Host ohne
dauerhaften Speicher, seine Datenbank ist nach jedem Deploy leer - und
in genau dieser Datenbank lag das Token, an dem er eine verknüpfte
Companion wiedererkennt. Für die App sah das aus, als hätte jemand die
Verbindung widerrufen, also hat sie das Konto lokal getrennt. Es gab
nichts, was der Nutzer hätte falsch machen können, und nichts, was er
hätte tun können, ausser sich wieder anzumelden.

Der Bot stellt das Token nun so aus, dass es sich selbst ausweist: er
prüft es an einer Signatur statt an einem Eintrag, den es nach einem
Neustart nicht mehr gibt. Ein Deploy, ein Umzug auf einen anderen
Rechner, ein geleertes Verzeichnis - die Verknüpfung bleibt.

Diese Seite trägt die zweite Hälfte davon bei: **eine einzelne
abgelehnte Anfrage hebt die Verknüpfung nicht mehr auf.** Ein "Token
ungültig" kann auch ein Bot sein, der gerade neu anläuft, oder ein
Serverfehler, der sich als Ablehnung ausgibt; beim Wort genommen
kostete das die Verbindung. Erst mehrere Ablehnungen kurz
hintereinander heissen zuverlässig, dass der Bot dieses Token wirklich
nicht kennt - bei einem Sync-Takt von fünf Sekunden ist das eine Frage
von Sekunden und verzögert die richtige Antwort nicht.

Einmal muss die Verbindung noch von Hand hergestellt werden: die
bereits ausgestellten Tokens der alten Art kann auch der neue Bot
nicht wiederbeleben. Danach ist Schluss damit.

## 2.3.1

**"Meine Charaktere" zeigt nur noch Charaktere auf Höchststufe.**
Bisher bekam jede Anmeldung im Spiel eine Karte - auch die des Twinks,
der gerade Stufe 34 erreicht hat. Wer nebenher vier Twinks hochspielt,
suchte die eine Höchststufe, um die es geht, zwischen vier Karten, die
mit dem nächsten Raidabend nichts zu tun haben. Dieselbe Regel gilt
für **Vorbereitung** und für die Kachel auf der Übersicht: alle drei
lesen dieselbe Liste und dürfen sich nicht darin unterscheiden, wen
sie meinen. Eine fehlende Verzauberung auf einem Twink ist keine
offene Stelle, sondern der Normalfall.

Vier Dinge gehören dazu, damit aus dem Ausblenden kein Fehlerbild
wird:

- **Ausgeblendet heisst nicht gelöscht.** Die Twinks bleiben
  gespeichert; wer einen hochspielt, findet ihn am Tag der
  Höchststufe mit seiner Vorgeschichte wieder und nicht als Neuzugang.
- **Die Fußzeile sagt, wie viele ausgeblendet sind**, und warum. Ein
  Charakter, der aus einer Liste verschwindet, in der er gestern noch
  stand, ist sonst von einem Fehler nicht zu unterscheiden.
- **"Nur Twinks gemeldet" ist ein eigener Leerzustand.** Der alte Satz
  ("Das Addon hat noch keinen Charakter gemeldet.") wäre dort schlicht
  falsch: gemeldet wurde etwas, es passt nur nicht zur Frage der
  Seite. Ist der gerade angemeldete Charakter selbst ein Twink, sagt
  das auch der Titel.
- **Eine fehlende Stufe zählt als hohe.** Die 0 im Feld heisst "nicht
  gemeldet" und nicht "Stufe 0" - eine ältere Addon-Version liesse
  einen Charakter sonst spurlos verschwinden. Dieselbe Linie wie
  `stars == 0` in der Academy: aus einer Datenlücke wird kein Befund.

Die Grenze liegt bei 90, der Höchststufe von MoP Classic. Wer seine
85er mitzählen will, setzt `characters_min_level` in der
`config.json`; ein unbrauchbarer Wert dort wird ignoriert statt
übernommen.

## 2.3.0

**Die Anmeldungen kamen im Spiel nicht an - und es lag nicht am Bot.**
Wer ingame auf *Anmeldungen abrufen* klickte, bekam den Stand vom
Login zurück. Jedes Mal. Die Ursache liegt in WoW selbst und war von
beiden Seiten aus unsichtbar:

WoW liest seine gespeicherten Variablen beim Laden **einmal** in den
Arbeitsspeicher. Bei einem `/reload` schreibt es sie **zuerst aus dem
Speicher zurück in die Datei** und liest sie erst danach wieder ein.
Genau dieses Zurückschreiben löscht alles, was die Companion in der
Zwischenzeit zugestellt hat - bevor das Addon es je zu sehen bekommt.
Der Knopf ingame löst ein `/reload` aus, konnte also prinzipiell nie
neue Daten holen.

Schlimmer als "nichts passiert": `DiscordRosterSync` merkt sich, was
es zuletzt geschickt hat, und schickt einen unveränderten Roster kein
zweites Mal. Die gelöschte Zustellung war damit **weg**, bis sich in
Discord inhaltlich etwas änderte. Die Anmeldeliste im Spiel konnte so
tage- bis wochenalt sein, ohne dass irgendwo etwas fehlte.

**Die Zustellung liegt jetzt zusätzlich als Lua-Datei im
Addon-Ordner** (`data/companion_live.lua`). Die führt WoW bei jedem
`/reload` neu aus und schreibt sie niemals zurück - das ist die
einzige Richtung Companion → Addon, die eine laufende Spielsitzung
überhaupt erreichen kann. Braucht **WeintCodex 2.3.0.0**.

Die gespeicherte Variable bleibt und wird weiter beschrieben: ein
Addon-Stand vor 2.3.0.0 kennt die Brücke nicht. Die Gegenrichtung
(Addon → Companion) war nie betroffen - dort ist WoW der Schreiber und
die Companion die Leserin, also genau herum.

### Was dabei nicht schiefgehen darf

- **Zugestellt wird immer die ganze Warteschlange**, nie ein Zuwachs:
  das Addon kann die Datei nicht leeren, ihr Inhalt *ist* der
  vollständige Stand.
- **Der Zeitstempel wandert nur bei inhaltlicher Änderung.** Sonst
  arbeitete das Addon bei jedem `/reload` dieselbe Zustellung erneut
  ein und meldete jeden Import ein weiteres Mal im Chat.
- **Erst schreiben, dann umbenennen.** Ein `/reload` kann in den
  Schreibvorgang fallen, und eine halb geschriebene Lua-Datei im
  Addon-Ordner ist ein Ladefehler des Addons.
- **Verglichen wird gegen die Datei, nicht gegen ein Gedächtnis.** Ein
  Addon-Update entpackt den leeren Auslieferungsstand darüber; ein
  reiner Speicher-Vergleich hielte die Zustellung danach für vorhanden
  und schriebe sie nie wieder. `AddonInbox.reassert()` läuft einmal
  pro Sync-Zyklus und zieht genau das nach - ohne belegten Kanal tut
  sie nichts, sonst nähme sie beim App-Start dem Addon den gültigen
  Stand des vorherigen Laufs weg.

Voller Vertrag in `docs/live-bridge.md`.

### Technisch

- `addon/live_bridge.py` ist die schreibende Hälfte,
  `addon/addon_inbox.py` bündelt beide Wege. Gerendert werden die
  Nachrichten für beide von **derselben** Funktion
  (`render_entries()` in `addon/inbox_writer.py`) - zwei Renderer
  wären zwei Formate, sobald einer erweitert wird, und der
  Unterschied fiele erst im Spiel auf
- `tests/test_live_bridge.py` prüft mit einem echten Lua-Interpreter,
  dass die geschriebene Datei gültiges Lua ist und die Nachrichten
  trägt. Sie liegt im Addon-Ordner und wird als Programmcode
  ausgeführt: ein Tippfehler im Serialisierer ist dort kein
  unlesbarer Datensatz, sondern ein Ladefehler

## 2.2.0

**Eine freigegebene WeakAura landet jetzt bei allen, nicht nur bei
dir.** 2.1.0 brachte die Seite, auf der sich eine Aura eintragen und
ins eigene WeintCodex stellen lässt - das half genau einer Person: der,
die sie getippt hat. Wer sie im Raid brauchte, bekam sie weiterhin als
Zeichenkette in den Chat kopiert.

Im Formular steht deshalb jetzt ein Schalter **„Für die Gilde
freigeben"**. Ist er an, wandert die Aura zusätzlich in eine
gemeinsame Bibliothek beim Discord-Bot; jede verknüpfte Companion holt
sie sich ab und stellt sie ihrem WeintCodex zu. Ingame steht sie dann
in derselben Liste wie die eigenen, mit dem Hinweis **„Gilde ·
<Autor>"** - wer eine Aura nicht selbst eingetragen hat, soll sehen,
woher sie kommt und wen er zu fragen hat.

**Freigeben ist eine eigene Handlung, keine Voreinstellung.** Alles,
was jemand tippt, ungefragt an 25 Leute zu schicken, wäre die Art
Überraschung, die man einmal erlebt und danach die Funktion meidet.

### Aufräumen, wenn jemand etwas falsch gemacht hat

Die Raidleitung kann jede Aura der Bibliothek **umkategorisieren,
umbenennen, sperren oder löschen** - in der Companion an der Zeile, in
Discord über `/weintaura`:

```
/weintaura liste       [alle]
/weintaura rubrik      kennung, rubrik
/weintaura umbenennen  kennung, name, [beschreibung]
/weintaura sperren     kennung
/weintaura freigeben   kennung
/weintaura loeschen    kennung
```

**Sperren ist der mildere Eingriff und meistens der richtige**: die
Aura wird nicht mehr ausgeliefert, bleibt aber in der Bibliothek -
inklusive des Belegs, was da eigentlich schiefging. Geloescht ist
geloescht, und der Autor hat sie danach nur noch in seiner eigenen
Companion.

Der **Importstring** lässt sich dabei ausdrücklich nicht ändern. Er
ist das Einzige, was außer dem Autor niemand nachprüfen kann; wer ihn
ersetzen will, gibt die Aura neu frei und ist damit als Urheber der
neuen Fassung sichtbar.

### Was daran nicht Geschmack ist

- **Ein nicht erreichbarer Bot löscht nichts.** Übernommen wird nur
  eine erfolgreiche Antwort - sonst verschwänden bei jeder
  Netzstörung sämtliche Gildenauren aus dem Spiel, ohne dass irgendwo
  etwas kaputt wäre. Eine *leere* Antwort räumt sehr wohl: genau so
  verschwindet eine gelöschte oder gesperrte Aura.
- **Bei gleicher Kennung gewinnt die eigene Fassung.** Wer seine
  eigene getippt hat, verliert sie nicht dadurch, dass jemand anderes
  unter derselben Kennung etwas freigibt. Die Zeile sagt es
  („eigene Fassung gewinnt"), sonst wäre nicht zu erklären, warum die
  freigegebene Aura ingame anders aussieht.
- **Eine vergebene Kennung wird benannt, nicht umgangen.** Der Bot
  antwortet mit dem Namen des bisherigen Autors; danach lässt sich
  „unter neuer Kennung freigeben" wählen. Still umzubenennen erzeugte
  eine zweite Aura, die aussieht wie die erste, und niemand wüsste,
  welche im Spiel gilt.
- **Nach dem Trennen des Discord-Kontos gehen die Gildenauren.** Sie
  gehören der Gilde, nicht diesem Rechner, und ließen sich ohne Konto
  auch nicht mehr aktualisieren. Die selbst eingetragenen bleiben -
  die hat niemand anderes.
- **Die Moderationsknöpfe werden nicht versteckt.** Ohne die
  Raidlead-Rolle antwortet der Bot mit 403, und das ist eine Antwort,
  keine Störung - dieselbe Regel wie auf der Seite
  Charakterzuordnung und im Addon (*lock, don't hide*).

Braucht **WeintCodex 2.2.0.0** für die Herkunftszeile (ältere
Addon-Versionen zeigen eine Gildenaura als eigene) und einen Bot mit
der Bibliothek. Kennt der Bot sie noch nicht, sagt die Seite das und
alles Lokale läuft unverändert weiter. Vertrag in
`docs/weakaura-bridge.md`.

## 2.1.0

**Eine WeakAura lässt sich jetzt hier eintragen und steht im Spiel zur
Auswahl.** Bis 2.0.12 ging das nur auf einem Weg: eine Lua-Datei im
Addon anlegen, sie in die `.toc` eintragen, eine Version schneiden, ein
Release veröffentlichen und warten, bis alle es installiert haben. Für
eine Aura, die zum nächsten Mittwoch gebraucht wird, ist das kein Weg.

Der neue Bereich **WeakAuras** (unter *Charakter*) nimmt Name, Rubrik,
Version, Beschreibung und den Export-String aus WeakAuras entgegen. Ein
Klick auf *Fertig* legt sie ab und stellt sie sofort ins Addon; im
Spiel steht sie nach dem nächsten `/reload` in derselben Liste wie die
mitgelieferten Auren und wird mit demselben Knopf installiert.

**Auch eine vorhandene Aura lässt sich aktualisieren, und zwar auch
eine mitgelieferte.** Das Addon meldet neuerdings, welche Auren es
kennt - ohne diese Meldung könnte diese Seite nur die Einträge
anbieten, die sie selbst angelegt hat, obwohl der häufigste Fall gerade
ein mitgeliefertes Klassenpaket mit einer neuen Fassung ist. Eine
Aktualisierung behält die Kennung der bisherigen Aura: im Spiel gewinnt
sie damit, statt daneben zu stehen.

### Was daran nicht Geschmack ist

- **Zugestellt wird immer die ganze Liste.** Eine gelöschte Aura
  verschwindet im Spiel dadurch, dass sie in der nächsten Zustellung
  fehlt. Eine Einzelnachricht könnte "es gibt mich nicht mehr" gar
  nicht ausdrücken, weil das Addon seine Inbox bei jedem Login leert.
  Deshalb wird auch eine leer gewordene Bibliothek zugestellt statt
  übersprungen - sonst bliebe genau die eine Aura für immer stehen,
  die ausdrücklich weg sollte.
- **„Im Spiel nach dem nächsten /reload" steht auf der Seite**, nicht
  in der Dokumentation. WoW liest seine gespeicherten Daten nur beim
  Laden; wer das nicht weiß, sucht die Aura und findet einen Fehler,
  wo keiner ist.
- **Der Export-String wird von Leerraum befreit, nicht abgewiesen.**
  Wer ihn aus Discord kopiert, bringt Zeilenumbrüche mit; ein
  WeakAuras-Export enthält selbst keine.
- **Ein fehlender `!WA:`-Vorspann ist ein Hinweis, keine Ablehnung.**
  Ältere WeakAuras-Versionen exportieren so, und ob eine Zeichenkette
  wirklich importierbar ist, weiß allein WeakAuras. Eine Prüfung, die
  richtige Eingaben abweist, ist schlimmer als eine, die eine falsche
  durchlässt.
- **Löschen fragt nach.** Der Importstring steht nur hier und im Spiel
  dessen, der ihn gebaut hat.

Braucht **WeintCodex 2.1.0.0**. Ältere Addon-Versionen kennen die
Nachricht nicht und ignorieren sie; die Katalogmeldung schickt das
Addon umgekehrt erst ab dieser Companion-Version. Der Vertrag steht in
`docs/weakaura-bridge.md`.

## 2.0.12

**Der Bot ist umgezogen - die Companion findet ihn wieder.** Sein
Hoster war stundenlang nicht in der Lage, die Anwendung neu zu bauen
("the server this operation needs isn't available"), sodass der Bot
auf einen anderen Rechner musste. Der Anbieter schreibt den Rechner in
den Hostnamen, also änderte sich die Adresse - am Bot selbst war
nichts anders. Die Companion trug die alte fest verdrahtet und lief
damit bei allem ins Leere, was über den Bot geht: Discord-Login,
Charaktere melden, Raidtermin, Aufstellung, WeintTV und Archiv,
Zugriffsprofil, Charakterzuordnung.

**Damit das nicht wieder eine Version kostet**, lässt sich die Adresse
jetzt überschreiben, ohne die Companion neu zu bauen: entweder über
die Umgebungsvariable `WEINTCODEX_BOT_URL` für einen schnellen
Versuch, oder dauerhaft über eine Datei `bot_url.txt` im
Konfigurationsverzeichnis, die nichts als die Adresse enthält. Ohne
beides gilt weiterhin der eingebaute Wert. Eine unbrauchbare Angabe
wird übergangen statt übernommen - eine kaputte Adresse ließe jeden
einzelnen Abruf stillschweigend scheitern, und der eingebaute Wert ist
immer noch der bessere Rateversuch.

Der Umzug war nötig, weil ein Bot ohne erreichbaren Bauserver keine
Aktualisierung mehr annimmt. Wer die Companion nicht aktualisiert,
erreicht den Bot bis dahin nicht mehr - die alte Adresse gibt es
nicht mehr.

## 2.0.11

**Im Discord dürfen jetzt mehrere Raids gleichzeitig laufen - die
Übersicht sagt es.** Bisher ging genau einer, und zwar mit Gewalt: der
Bot löschte beim Anlegen eines zweiten den ersten samt allen
Anmeldungen und ließ dessen Anmeldenachricht als funktionslosen
Knopfblock im Kanal stehen. Wer ein 10er-Main- und ein
25er-Twinkgefüge nebeneinander wollte, konnte das nicht.

Die Übersicht hat für den Termin genau einen Platz, und dort steht
weiterhin der nächste Raid - mit Datum, Zusagen und der Aufstellung wie
gehabt. Neu ist die Zeile darunter: *"Außerdem offen: 25er Twinks
(Donnerstag, 14.08. um 20:00 Uhr)"*. Ohne sie wäre ein parallel
laufender Raid in der App schlicht unsichtbar - man sähe nicht, dass
man sich noch woanders eintragen kann, und würde den Unterschied nie
bemerken.

Was dabei **nicht** passiert ist: die Antwort des Bots hat ihre Form
behalten. Eine Liste an der Wurzel hätte jede ausgelieferte
Companion-Fassung auf einen Schlag blind gemacht; die weiteren Raids
hängen deshalb als eigenes Feld daran, das eine ältere Fassung einfach
übergeht. Auch die Grenze des Vertrags bleibt, wo sie war: Titel,
Größe, Termine und Zahlen - keine Namen, keine Discord-IDs. Wer die
Namensliste will, braucht weiterhin die Raidlead-Rolle.

**Dazu gehört WeintCodex Bot vom selben Tag.** Dort liegt der eigentliche
Umbau: der Anmeldebestand hängt jetzt am Raid statt am Spieler, sodass
eine Abmeldung im 10er den 25er nicht mehr mitnimmt und derselbe
Spieler im einen heilen und im anderen Schaden fahren kann. Ein
dauerhaftes Menü im Anmelde-Channel macht die Raiderstellung außerdem
ohne Slash-Befehl möglich - jeder im Kanal darf einen Raid aufmachen,
verwalten darf ihn, wer ihn erstellt hat.

**Zwei Reminder-Fehler sind mit weg**, beide ohne sichtbares Symptom
und beide alt. Der Bot schickte nach jedem Neustart binnen einer Minute
eine Erinnerung für einen längst vergangenen Raid und pingte dabei alle
Member an: seine Datenbank lag versehentlich in der Versionierung, jeder
Deploy brachte damit den Raid des letzten Commits zurück, und die
Nachhol-Logik für verpasste Termine kannte keine Obergrenze - "der
Montag liegt hinter uns" trifft auf jeden vergangenen Montag zu.
Nachgeholt wird jetzt nur noch am Tag des Termins, und bei der
Raiderstellung lässt sich die Erinnerung ganz abschalten. Der zweite:
wer sich abgemeldet hatte, stand nach einem Neustart wieder als "keine
Rückmeldung" da - und bekam prompt den nächsten Reminder ab.

## 2.0.10

**Der Raidlead kann Discord-Konten jetzt selbst mit Charakteren
verbinden.** Der Kalender-Invite in WeintCodex lädt echte
Charakternamen ein. Der Bot kannte sie bisher nur von Spielern, die
die Companion verknüpft **und** ihre Twinkverwaltung gepflegt haben -
drei Voraussetzungen, von denen Gildenfremde die erste kaum erfüllen
können. Für alle anderen schickte er den Discord-Anzeigenamen weiter.
Den gibt es im Spiel nicht: die Einladung lief ins Leere, und weil
der Client den Fehlschlag nicht meldet, zählte sie sogar als
erfolgreich mit. Auffallen konnte die Lücke damit frühestens am
leeren Kalender.

Die neue Rubrik **Charakterzuordnung** schließt sie. Sie zeigt für
jede Anmeldung des laufenden Raids, mit welchem Charakter der Invite
sie erreicht und woher dieser Name stammt - offene Zuordnungen
zuerst, denn das ist die Frage, mit der man die Seite öffnet. Ein
fehlender Name lässt sich direkt in der Zeile eintragen, wahlweise
für eine bestimmte Klasse oder für jede, mit der sich der Account
anmeldet.

Zwei Regeln dahinter sind wichtig zu kennen. Die genauere Angabe
gewinnt vor der pauschalen: wer seine Twinks selbst gemeldet hat,
bekommt für seinen Magier nicht den eingetragenen Krieger eingeladen.
Und bei gleicher Genauigkeit gewinnt die Hand des Raidleads, denn sie
ist die Korrektur von eben, während eine Meldung Wochen alt sein
kann - ohne diesen Vorrang wäre ein falscher Twink in der Meldung
eines Spielers gar nicht mehr zu berichtigen.

Dieselben Zuordnungen lassen sich auch in Discord pflegen
(`/weintcharakter setzen`, `/weintcharakter liste`); beide schreiben
dieselbe Tabelle im Bot. Die Seite steht bei allen in der Spalte und
erklärt ohne die Raidlead-Rolle, wofür sie da wäre, statt zu
verschwinden - ein Bereich, den man nicht sieht, lässt sich weder
erklären noch danach fragen.

**Dazu gehört WeintCodex 2.0.1.0.** Der Bot sagt dem Addon jetzt zu
jeder Anmeldezeile, ob dort ein echter Charaktername steht. Das Addon
zeichnet solche Zeilen als offen, zählt in der Kalender-Vorschau
"21 von 25" statt "25 gesamt" und überspringt sie beim Erstellen des
Eintrags, statt eine Einladung abzuschicken, die nie ankommt. Bot und
Companion allein ändern daran nichts, das Addon allein auch nicht -
die Angabe ist in beide Richtungen verträglich.

## 2.0.9

**"Meine Charaktere" zeigt jetzt ein Bild.** Jede Karte trägt links
das Wappen ihrer Klasse in Klassenfarbe - an derselben Stelle und in
derselben Rolle wie das Porträt im Kopf der Charakterrubrik von
WeintCodex. Die Liste liest sich damit auf einen Blick statt Zeile
für Zeile: Wer fünf Twinks gemeldet hat, findet den richtigen an der
Farbe und am Zeichen, nicht am Namen.

Das 3D-Modell aus dem Spiel lässt sich auf dem Desktop nicht zeigen -
die Grafiken des Clients liegen nicht als Datei vor, und die
Ausrüstungsmeldung des Addons trägt weder Volk noch Geschlecht, aus
denen sich ein Abbild bauen ließe. Was sie trägt, ist die Klasse, und
die ist genau die Auskunft, die ein Porträt auf einen Blick gibt. Die
elf Wappen sind eigene Zeichnungen.

Meldet das Addon keine Klasse, bleibt die Kachel stehen und zeigt ein
neutrales Zeichen: Ein geratenes Wappen wäre von einem gemeldeten
nicht zu unterscheiden - dieselbe Regel, nach der ein Ring ohne
Messung "KEINE PRÜFUNG" sagt statt 0 %.

## 2.0.8

**Die Übersicht begrüßt dich jetzt persönlich.** Statt der festen
Rubrik "HEUTE" steht dort die Tageszeit und, wenn die App ihn kennt,
dein Name: "Guten Abend, Krallenwut". Welcher Charakter das ist,
meldet das Addon beim Anmelden im Spiel — geraten wird nichts, ohne
bekannten Namen grüßt die App eben ohne. Beides zieht im Minutentakt
nach, solange die Übersicht offen ist: aus "Guten Tag" wird um 18 Uhr
"Guten Abend", ohne dass die App dafür neu gestartet werden müsste.

**Der Satz darunter sagt, wann der nächste Raid ist** — und zwar in
Tagen, nicht in Stunden: "Morgen um 20:00 Uhr ist Raid.",
"Übermorgen um 20:00 Uhr ist Raid.", "Noch vier Tage bis zum nächsten
Raid." Der Countdown-Chip rechts nennt die Restzeit weiterhin auf die
Minute genau; was er nicht sagt, ist, ob "in 2 T 5 STD" nun ein Grund
ist, heute noch etwas vorzubereiten. Läuft der Raid gerade, steht das
da. Ist kein Termin bekannt, bleibt es bei "Alles bereit für den
nächsten Raid." — ein erfundener Mittwoch wäre von einem echten
Termin nicht zu unterscheiden.

Wartet nebenbei ein Update, hängt es als Halbsatz hinten dran
("Morgen ist Raid - ein Update wartet."), statt den Termin zu
verdrängen. Die Update-Karte steht ohnehin unmittelbar darunter,
nennt Addon und App beim Namen und trägt den Knopf dazu.

**"Erneut prüfen" gibt es jetzt auch auf der Übersicht.** Der Knopf
sitzt oben rechts neben dem Countdown und stößt dieselbe Prüfung an
wie der unter "Addon & Updates": beide Kanäle, Addon und Companion,
gegen GitHub. Bisher war die Übersicht die Seite, die ein wartendes
Update *ankündigt* (Karte, Systemzeile, Abzeichen), aber die einzige,
auf der man nicht nachsehen konnte, ob inzwischen etwas dazugekommen
ist.

Die Prüfung läuft dabei in einem eigenen Thread — ein Netzdurchgang
im Klick-Handler hätte das Fenster für seine Dauer eingefroren.

**Eine manuelle Prüfung fragt wirklich nach.** Die Antwort von GitHub
wird 15 Minuten lang zwischengespeichert, und das ist für die Prüfung
im Hintergrund richtig. Für den Knopf war es falsch: wer ihn drückt,
weiß gerade von einer neuen Fassung und bekam trotzdem die Antwort
von vorhin — ein Knopf, der nachweislich nichts tut. "Erneut prüfen"
verwirft den Zwischenspeicher jetzt, auf beiden Seiten.

## 2.0.7

**Die Aufstellung auf der Übersicht zeigt jetzt, wer fehlt** — nicht
nur, wie viele. Statt einer Zeile "10 von 25 zugesagt" steht dort die
Zusammensetzung, so wie sie im Entwurf der Übersicht immer gedacht
war: je Rolle eine Reihe von Plätzen, die besetzten in Klassenfarbe,
die offenen als Lücke, darunter ein Satz wie "Vier offene Plätze · 1
Heiler, 3 Schaden".

Das ist die Frage, wegen der man vor einem Raid überhaupt ins Discord
sieht. Vier offene Plätze sind harmlos, wenn es Schaden ist, und ein
abgesagter Abend, wenn einer davon der zweite Tank ist — die reine
Zahl beantwortet das nicht.

Rolle und Klasse liefert der Bot mit dem Termin, **Namen weiterhin
nicht**: beides steht als Symbol in der Anmeldung, die jeder im Kanal
lesen kann, während die Namensliste hinter der Raidlead-Rolle bleibt.
Meldet eine ältere Bot-Fassung keine Rollen, steht dort ein einziger
Streifen "zugesagt" mit den besetzten und den offenen Plätzen — eine
Aufteilung wird nicht geschätzt, denn drei geratene Reihen wären von
drei gemeldeten nicht zu unterscheiden.

**"Dein letzter Pull" kennt jetzt auch den Raid von gestern.** Bisher
las die Karte ausschließlich die Pulls mit, die *während der
laufenden Sitzung* endeten, während WeintTV oder die Academy geöffnet
war. Nach einem Neustart war diese Liste leer, und die Übersicht sagte
am Tag nach dem Raidabend "Noch kein Pull" — keine vorsichtige
Auskunft, sondern schlicht eine falsche: der Kampf hat stattgefunden,
die App hat an der falschen Stelle nachgesehen.

Findet sich in der Sitzung nichts, tritt jetzt der letzte Pull aus dem
WarcraftLogs-Archiv an diese Stelle, mit Boss, Ausgang, Dauer,
Pullnummer und der Kurve der letzten Versuche an demselben Boss. Die
laufende Sitzung hat weiterhin Vorrang — was gerade eben endete, ist
der letzte Kampf, auch wenn WarcraftLogs ihn noch nicht kennt.

Was ein Pull aus dem Archiv **nicht** mitbringt, ist die Bewertung:
dafür müsste der ganze Kampf geladen werden, was beim Bot Minuten
dauert. Die Sternreihe bleibt deshalb leer, und die Lektionskarte sagt
das ausdrücklich und nennt den Weg zur vollständigen Auswertung —
statt einen schwächsten Bereich zu benennen, den niemand gemessen hat.

Nebenbei behoben: die Karte las zwei Felder unter Namen, die es nie
gab (`boss` statt `encounter_name`, `boss_percent` statt
`boss_health_percent`). Selbst mit gefüllter Historie stand dort
"Kampf" ohne Kurve. Und beide Abrufe der Übersicht — Termin wie
letzter Pull — starteten nicht, wenn die App innerhalb der ersten
Minuten nach dem Hochfahren des Rechners geöffnet wurde.

## 2.0.6

**Das Fenster ließ sich unter Linux nicht mehr verschieben**, solange
es nicht maximiert war. Kein Absturz, keine Fehlermeldung — ein Zug
an der Titelleiste hatte schlicht keine Wirkung.

Die eigene Titelleiste (rahmenloses Fenster seit 2.0) verschob das
Fenster bisher von Hand: Mausposition merken, bei jeder Bewegung
`window.move()` auf die neue Position setzen. Das funktioniert unter
X11 und Windows, aber nicht unter Wayland — dort darf eine Anwendung
ihre eigene Fensterposition aus Sicherheitsgründen gar nicht setzen,
das ist Sache des Compositors. `move()` lief also einfach ins Leere,
ohne jede Rückmeldung. Da `app.py` beim Start zuerst den
Wayland-Treiber versucht, traf das jeden Linux-Nutzer auf einem
Wayland-Desktop (mittlerweile die Voreinstellung bei GNOME, KDE und
den meisten aktuellen Distributionen).

Die Titelleiste bittet jetzt stattdessen den Fenstermanager selbst um
das Verschieben (`QWindow.startSystemMove()`) — der einzige Weg, der
unter Wayland überhaupt vorgesehen ist, und funktioniert unverändert
unter X11 und Windows. Das Wiederherstellen eines maximierten
Fensters durch Ziehen an der Titelleiste bleibt unverändert per Hand
gesteuert.

## 2.0.5

**Nach dem Update auf 2.0.3 startete die App unter Windows nicht
mehr.** Der Ladebalken blieb bei "Übersicht wird gezeichnet …"
stehen, das Fenster kam nie — kein Absturz, keine Meldung, kein
Protokolleintrag. Die Ursache war eine Verkettung aus drei
Kleinigkeiten, von denen jede für sich harmlos aussah.

Das "Was ist neu"-Fenster erscheint nach jedem Update genau einmal.
Angemeldet wurde es bisher im Konstruktor des Hauptfensters, mit dem
Zusatz "gleich, aber nicht sofort" — in der Absicht, dass das
Fenster zuerst sichtbar wird. Genau das ist nicht passiert: der
Startbildschirm zeichnet seinen Balken weiter, indem er Qt bittet,
alles Anstehende zu erledigen, und dazu gehörte diese Anmeldung. Der
Dialog ging also auf, **bevor** das Fenster gezeigt wurde, und
wartete dann auf eine Antwort. Weil der Startbildschirm immer im
Vordergrund liegt und erst nach dem Fenster geschlossen wird, lag
der Dialog unsichtbar darunter. Für den Nutzer war die App damit
hängengeblieben — dabei wartete sie nur auf einen Klick, den
niemand sehen konnte.

Der Balken zeichnet sich jetzt selbst, statt Qt um das Abarbeiten
von allem Anstehenden zu bitten; ein Ladebalken soll zeichnen, nicht
Arbeit erledigen. Das Start-Fenster meldet sich erst, wenn das
Hauptfenster wirklich sichtbar ist — die Bedingung hängt damit an
der Sichtbarkeit selbst und nicht mehr an einer Zeitannahme. Der
Startbildschirm ist geschlossen, bevor irgendein Dialog erscheinen
kann, und der Dialog holt sich zusätzlich nach vorn.

*Wer noch auf 2.0.3 festhängt:* einmal Escape drücken (oder mit
Alt+Tab zum unsichtbaren Fenster wechseln und es schließen) — die
App startet dann normal weiter. Die neue Fassung lässt sich danach
wie gewohnt einspielen.

**"Aufstellung im Discord" öffnete unter Linux weiterhin den
Browser** — und dort eine Adresse, die es nirgends gibt:
`http://discord//-/channels/1311…`. Der Fehler saß nicht im Link,
sondern in der Frage, die die App gestellt hat. Sie hat `xdg-open`
mit `discord://…` aufgerufen und dessen Rückgabewert als Antwort
darauf gelesen, ob es für dieses Schema überhaupt ein Programm gibt.
Das ist er nicht: ist nichts eingetragen, reicht xdg-open die Adresse
an den Standard-Browser weiter und meldet trotzdem Erfolg. Der
Browser kennt das Schema nicht und macht eine http-Adresse daraus.

Die App fragt jetzt vorher, statt hinterher zu hoffen. Ist für
`discord://` ein Programm eingetragen, wird dessen Startzeile
gelesen und nur dann benutzt, wenn dort wirklich ein Discord-Client
steht — Firefox legt für ein einmal bestätigtes "Anwendung wählen"
einen Eintrag namens *Discord* an, der in Wahrheit Firefox startet,
und genau der hat den kaputten Link erzeugt. Ist nichts eingetragen,
wird die Anwendung selbst gesucht: ein Programm im Suchpfad,
Flatpak, Snap, ein Menüeintrag, eine AppImage in den üblichen Ordnern
— auch in dem, aus dem WeintCompanion selbst gestartet wurde.
Vesktop, WebCord und die anderen inoffiziellen Clients zählen dabei
mit; wer einen davon benutzt, soll nicht zugunsten des Browsers
übergangen werden.

Läuft Discord bereits, springt das offene Fenster in den
Anmelde-Beitrag, statt ein zweites zu öffnen. Findet sich keine
Anwendung, übernimmt weiterhin der Browser — dann aber mit der
`https`-Adresse, die dort auch funktioniert, statt mit dem Schema,
mit dem er nichts anfangen kann.

Unter Windows und macOS bleibt es beim Weg des Systems, denn dort
meldet der Öffner einen fehlenden Eintrag auch wirklich. Neu ist,
dass auch dort anschließend nach der Installation gesucht wird
(`%LOCALAPPDATA%\Discord`, `/Applications`), damit eine vorhandene
Anwendung ohne Schema-Zuordnung nicht doch im Browser endet.

## 2.0.3

**Ein gelöschter Testraid stand nach jedem Neustart wieder als
nächster Termin in der Übersicht.** Die Ursache lag nicht in der
Anzeige, sondern in der Frage, wen die App gefragt hat: den Bot, und
der wiederum nur seine eigene Datenbank. Wird die Anmeldenachricht in
Discord von Hand gelöscht (Rechtsklick → Nachricht löschen) statt über
"Raid löschen", bekommt der Bot davon nichts mit — der Datensatz
bleibt liegen und gilt weiter als laufende Anmeldung. In Discord fällt
das nicht auf, dort ist die Nachricht ja weg. In der Übersicht dagegen
stand daraufhin dauerhaft ein Termin, den es nicht mehr gab.

Der Bot sieht jetzt vor jeder Auskunft in Discord nach, ob es die
Anmeldung dort überhaupt noch gibt, und antwortet sonst mit "kein
Termin". Beim Start räumt er den zurückgebliebenen Datensatz
zusätzlich weg. Der Zweifelsfall zählt dabei als "vorhanden": nur wenn
Discord für jede bekannte Nachricht ausdrücklich "gibt es nicht"
sagt, gilt die Anmeldung als weg — eine kurz nicht erreichbare
Schnittstelle darf keinen laufenden Raid ausblenden.

**"Aufstellung im Discord" öffnete den Browser statt Discord.** Man
landete damit in einer zweiten, meist abgemeldeten Ansicht desselben
Servers, während die Anwendung daneben offen stand — und außerdem nur
auf dem Standardkanal, nicht dort, wo die Anmeldung steht. Der Knopf
springt jetzt in der Discord-Anwendung genau in den Anmelde-Beitrag;
wo er steht, sagt der Bot mit dem Termin zusammen. Wer Discord nur im
Browser nutzt, merkt nichts davon: gibt es für `discord://` kein
Programm, übernimmt weiterhin der Browser. Derselbe Weg gilt für den
Feedback-Link unter *Einstellungen → Über*.

## 2.0.2

**Der Knopf "Aufstellung im Discord" war tot.** Kein Fenster, keine
Meldung, kein Protokolleintrag - er tat schlicht nichts. Ursache war
eine Regel, die an zwei von drei Stellen befolgt wurde: im AppImage
erbt ein gestarteter Browser die mitgelieferten Bibliothekspfade der
Anwendung und stürzt sofort ab, weshalb der Discord-Login und der
Feedback-Link die Umgebung vorher bereinigen. Dieser eine Aufruf tat
es nicht, und `webbrowser.open()` bemerkt den Absturz nicht - es
sieht nur, dass es ein Hilfsprogramm gestartet hat. Das Öffnen einer
Adresse läuft jetzt an genau einer Stelle zusammen, und wenn gar kein
Browser gefunden wird, steht die Adresse im Protokoll statt nirgends.

**"Kein Termin bekannt", obwohl im Discord ein Termin stand.** Auch
das war kein Fehler in der Anzeige, sondern der Stand: der Chip wurde
einmal gebaut und danach nie wieder angefasst. Vom Gildenkalender
kannte die App nur zwei undurchsichtige Zeichenketten, die sie
ungeparst an das Addon weiterreicht - und die bekommt ohnehin nur, wer
die Raidlead-Rolle trägt.

Der Bot beantwortet die Frage jetzt eigens, für **jeden** verknüpften
Nutzer. Die Übersicht zeigt damit den nächsten Raidtermin mit
Countdown, Titel, Datum und Uhrzeit sowie die Zahl der Zusagen ("18
von 25 zugesagt · 2 vielleicht · 1 Ersatzbank"). Bewusst weiterhin
**ohne Namensliste**: der Termin und die Zahlen stehen im
Anmelde-Beitrag, den jeder im Kanal lesen kann, die Namen bleiben
hinter der Rolle. Wer sie sehen will, kommt über denselben Knopf ins
Discord. Ohne Antwort des Bots steht dort wie bisher, dass nichts
bekannt ist - ein erfundener Mittwoch wäre von einem echten nicht zu
unterscheiden.

**Updates lassen sich jetzt auf der Übersicht auslösen.** Ein
wartendes Update war an drei Stellen zu sehen - Systemzeile,
Abzeichen in der Navigation, Meldung beim Start - und an keiner davon
zu starten: jeder Weg endete auf "Addon & Updates". Oben auf der
Übersicht steht dafür jetzt eine Karte, die nennt, was die neue
Fassung bringt, und den Knopf gleich mitbringt. Sie erscheint nur,
wenn wirklich etwas ansteht.

**Der Changelog steht in der App.** Bisher zeigte die Addon-Karte
"Keine Änderungen gefunden." (der Text des Releases war tatsächlich
leer) und die Companion-Karte eine Handvoll Commit-Betreffs, also
Text, der für Entwickler geschrieben ist. Der neue Knopf "Änderungen"
öffnet die vollständige Liste **beider** Komponenten, jede Fassung
einzeln, mit Kennzeichnung der installierten und der neuen. Die Liste
des Addons kommt aus dem Addon-Ordner selbst und steht damit auch
ohne Internet vollständig zur Verfügung.

Damit das so bleibt, trägt ab sofort **jedes Release seinen
Changelog**: der Text auf GitHub wird aus der gepflegten Liste
erzeugt, und ein Tag ohne Eintrag lässt den Bau abbrechen, statt ein
Release ohne Beschreibung zu veröffentlichen.

## 2.0.1

**"Meine Charaktere" und "Vorbereitung" zeigen jetzt etwas.** Beide
Seiten standen in 2.0.0 leer, und das war ehrlich: über Ausrüstung
wusste die App schlicht nichts. Die Twinkliste, die das Addon meldet,
trägt Name, Klasse und Realm und wandert an den Bot weiter -
Gegenstandsstufe, Verzauberungen, Sockel und offene BiS-Plätze kamen
nirgends vor. Ein Fortschrittsring bei 0 % hätte deshalb eine Messung
behauptet, die es nicht gab.

WeintCodex **1.3.3.1** liefert diese Messung jetzt nach: beim Anmelden
und nach jedem Ausrüstungswechsel meldet das Addon den geprüften Stand
des gespielten Charakters. Die App sammelt diese Meldungen über
mehrere Anmeldungen zu einer Liste - wer seit zwei Wochen nicht auf
dem Zweitcharakter war, sieht ihn trotzdem.

- **Meine Charaktere** zeigt je Charakter Name in Klassenfarbe,
  Spezialisierung, Stufe, Gegenstandsstufe und wann er zuletzt gemeldet
  hat.
- **Vorbereitung** zeigt je Charakter einen Ring aus geprüften
  Verzauberungen und Sockeln, daneben die offenen BiS-Plätze und
  darunter die konkreten Mängel in der Reihenfolge, in der sie das
  Addon bewertet ("Finger 1: Verzauberung fehlt - Empfehlung: …").
- Auch die Kachel **Vorbereitung** auf der Übersicht rechnet jetzt mit
  echten Zahlen statt dauerhaft "keine Daten" zu zeigen.

Die Bewertung selbst - welche Verzauberung optimal ist, welcher Stein
falsch sitzt, welcher Wert über dem Cap liegt - entsteht im Spiel, wo
Spec-Profile, Caps und Sockelboni bekannt sind. Die App zeichnet sie
nur; damit können Spiel und Desktop nicht auseinanderlaufen. Und die
alte Unterscheidung bleibt: **ein Ring ohne Wert heißt "nicht
geprüft"** und wird als solcher beschriftet, statt als rote Null zu
erscheinen. Offene BiS-Plätze zählen bewusst nicht in den Ring - sie
hängen an Würfelglück, nicht an Vorbereitung.

**Laufwege, Cooldown-Nutzung, Raid- und Heil-Cooldowns bleiben nicht
mehr leer.** Die Auswertung auf dieser Seite war in Ordnung - eine
vertragskonforme Antwort erzeugt alle vier -, es fehlte die Lieferung.
Zwei Ursachen, beide im Bot behoben: optionale GraphQL-Argumente wurden
als `null` geschickt statt weggelassen, was den Server-Default
überschreibt (deshalb kam ausgerechnet der eine Ereignisstrom an, der
sein Argument ausdrücklich setzt); und der Fähigkeitskatalog kannte je
nur *eine* deutsche Schreibweise.

Für Letzteres hat auch diese Seite dazugelernt: ein Abgleich der beiden
unabhängig gepflegten Tabellen fand zwanzig Fähigkeiten mit
verschiedenen deutschen Namen - Seelenruhe/Gelassenheit,
Aufstieg/Aszendenz, Dunkle Seele/Finstere Seele, Neubelebung/Belebung.
Jede davon war über den Namen gematcht eine dauerhaft unerkannte Zeile,
und in der Oberfläche nicht davon zu unterscheiden, dass die Fähigkeit
nie gewirkt wurde. Beide Schreibweisen zählen jetzt.

**Leere Karten in WeintTVs Analyse sagen jetzt, warum sie leer sind.**
"Keine Raid-Cooldowns erkannt." war von "der Raid hat keine gezündet"
nicht zu unterscheiden. Liefert die Datenquelle andere Tiefenwerte
desselben Kampfes, aber diesen Block nicht, steht das jetzt auf der
Karte - für Laufwege, Cooldown-Nutzung, Raid- und Heil-Cooldowns.
Das ist dieselbe Regel, nach der null Sterne in der Academy
ausdrücklich "keine Daten" heißen und nicht "schlecht".

## 2.0.0

Ein komplettes Neudesign. Bernstein trägt jetzt die Bedeutung, Violett
nur noch das Licht - und die App zeigt an, was heute ansteht, statt
immer wieder denselben Installationsstatus.

**Die Startseite zeigt nicht mehr, ob die App funktioniert.** Bis 1.7
öffnete sich WeintCompanion auf einer Übersicht ihres eigenen
Installationszustands: WoW gefunden, Addon aktuell, Sync läuft. Das
ist genau einmal interessant, am ersten Tag - danach ist dort
dauerhaft alles grün, und der Bildschirm, den man bei jedem Start
zuerst sieht, sagt einem nichts, was man nicht schon weiß. Die neue
**Übersicht** zeigt stattdessen den nächsten Raidtermin mit Countdown
und Aufstellung, den letzten Pull mit dem schwächsten Bereich und
einer konkreten Lektion, und den Stand der Vorbereitung. Der
Installationsstatus ist nicht verschwunden, er sitzt nur noch als eine
einzige Zeile am Fuß der Seite - und klappt sich nur auf, wenn dort
tatsächlich etwas zu tun ist.

**WeintTV zeigt jetzt den ganzen Raid.** Die Ranglisten hörten bisher
nach Platz fünf auf - nicht aus Absicht, sondern aus Platznot: eine
Zeile brauchte mit ihrem eigenen Balken darunter rund 40 px, und 25
davon passten in kein 900 Pixel hohes Fenster. Die Klassenfarbe füllt
jetzt den Zeilenhintergrund selbst, wodurch eine Zeile mit 24 px
auskommt - alle 25 Plätze stehen bei 1440 × 900 ohne Scrollen da, die
eigene Zeile ist hervorgehoben, ein gefallener Spieler zeigt seinen
Todeszeitpunkt statt aus der Liste zu verschwinden.

**Die Academy zeigt den schwächsten Bereich, statt sechs gleich
gewichtete Zeilen aufzulisten.** Rotation, Movement, Cooldowns,
Mechaniken, Überleben und Leistung stehen jetzt als sechs Kacheln
nebeneinander, und genau eine - der Bereich, an dem sich Training am
meisten lohnt - hebt sich sichtbar ab.

**Drei Akzentfarben, zwei Dichten, ein Fenster ohne Systemrahmen.**
Bernstein, Arkan-Violett oder Jade lassen sich jederzeit umschalten
und wirken sofort - auch auf gemalte Ringe, Sparklines und Sterne.
Wer "Bewegung reduzieren" einschaltet, bekommt dieselbe App ohne
Animation: der LIVE-Punkt wird zum Quadrat, nichts versetzt sich mehr
beim Seitenwechsel. Das Fenstermindestmaß sinkt von 1500 × 900 auf
960 × 640.

**Kein Emoji mehr als Statusanzeige.** Die grünen, gelben und roten
Kreise sind gemalten Punkten gewichen, die die gewählte Akzentfarbe
tragen und auf jedem Rechner gleich aussehen - dasselbe gilt für Inter
und JetBrains Mono, die der App jetzt beiliegen, statt sich still auf
eine Systemschrift zu verlassen.

**Neu:** eine eigene Seite für Verbindungen (vormals
"Synchronisation"), ein kleines Immer-oben-Overlay mit Pull-Uhr,
Boss-Prozent und dem eigenen Rang, und eine vierschrittige Einrichtung
für den ersten Start - jederzeit über Einstellungen → Allgemein
erneut aufrufbar, genau wie die Willkommens-Tour.

## 1.7.0

Wer in der App einen Charakter auswählte, bekam im Spiel manchmal
**einen alten oder einen völlig fremden Charakter** zu sehen -
in der Academy wie in WeintTV.

Die Ursache war nicht ein Fehler, sondern dass es **vier voneinander
unabhängige Antworten auf „wer bin ich"** gab: die Auswahlbox, die
gespeicherte Auswahl, das ausgewertete Profil und der im Spiel
angemeldete Charakter. Nichts davon glich irgendetwas ab - und die
einzige verlässliche Quelle, der angemeldete Charakter, wurde nirgends
gefragt.

**Der alte Charakter.** Wechselte die Raid-Besetzung, füllte die
Academy-Seite ihre Auswahlliste neu und setzte die Auswahl nur, *wenn*
der gespeicherte Name noch vorkam. Fehlte er, stand die Box sichtbar
auf dem ersten Namen, während die Einstellung den alten behielt - und
die Zustellung ans Addon entsteht aus der Einstellung. Die App zeigte
also X und im Spiel stand Y. Nichts schlug dabei fehl, deshalb ist es
so lange unentdeckt geblieben. Die Auswahl wird jetzt an einer Stelle
entschieden **und festgeschrieben**; beides kann nicht mehr
auseinanderlaufen.

**Der fremde Charakter.** War noch nichts ausgewählt, nahm die App den
**alphabetisch ersten Raider** - bei jedem Bericht neu und ohne es je
festzuhalten. Diese Vermutung ging bis ins Spiel. Sie gibt es
weiterhin, aber nur noch als ausdrücklichen Vorschlag, der
festgeschrieben wird, bevor er wirkt: was ins Addon geht, hat der
Nutzer auch gesehen.

**Die Umkehrung: das Spiel sagt jetzt, wer spielt.** WeintCodex
1.3.3.0 meldet beim Login den angemeldeten Charakter, und die Auswahl
folgt ihm von selbst. Eine Auswahl von Hand behält Vorrang - aber nur
für den Charakter, auf dem sie getroffen wurde. „Ich habe als Alice
kurz Bobs Werte angesehen" gilt nicht mehr, wenn ich als Carol
einlogge. Der Schalter „Dem Spiel folgen" sitzt neben der Auswahl,
darunter steht, wer zuletzt angemeldet war.

**Eine Identität statt zwei.** Die Auswertung trug bisher zwei Namen:
`weinttv_report.me` den echten, `academy_state.character` den aus dem
Profil - und der ist wörtlich `"-"`, sobald der gewählte Spieler im
Pull nicht gefunden wurde. Das Addon bekam zwei Antworten auf dieselbe
Frage. Jetzt wird der Name genau einmal aufgelöst und überall
derselbe verwendet; ein neues Feld `hasActor` sagt dem Addon, ob der
Charakter im Pull überhaupt dabei war - null Sterne heissen „keine
Daten", nicht „schlecht".

**Ein Auswahlwechsel kommt sofort an.** Vorher wartete er auf den
nächsten Sync-Takt und fiel meist ganz aus, weil ohne geöffnete
WeintTV- oder Academy-Seite gar keine Auswertung vorliegt.

Der WeintTV-Spielerfilter bleibt absichtlich reine Anzeige: die
Raid-Ansicht ist dazu da, sich *andere* anzusehen, und ein Blick auf
den Kollegen darf die Ingame-Identität nicht umstellen. Damit man das
nicht verwechselt, steht der tatsächlich gewählte Academy-Charakter
jetzt daneben.

**Zur Update-Reihenfolge:** die App schreibt ihre Version in die
Addon-Inbox, und das Addon schickt die neue Nachricht erst ab 1.7.0.
Wer zuerst das Addon aktualisiert, bekommt also keine Fehlermeldungen -
nur die automatische Auswahl greift dann noch nicht.

## 1.6.2

Einen Pull aus dem Archiv auszuwählen endete zuverlässig mit **"Bot
nicht erreichbar: The read operation timed out"** - obwohl im Bot-Log
zu sehen war, dass derselbe Pull kurz darauf sehr wohl fertig
ausgewertet wurde. Aufgegeben hat also die App, nicht der Bot.

Drei Ursachen, alle drei behoben:

**Die App wartete zu kurz.** Für einen archivierten Pull liest der Bot
die vollständigen Ereignisströme des Kampfes - in einem gemessenen
Fall über 30.000 Ereignisse, seitenweise von WarcraftLogs geholt und
auf einem Host mit 0,15 vCPU ausgewertet. Dafür waren 15 Sekunden
angesetzt, dieselbe Spanne wie für eine dreizeilige Berichtsliste. Die
Zeitgrenzen richten sich jetzt nach dem, was der Bot für die jeweilige
Antwort tatsächlich tun muss.

**Die App ließ den Bot zwei Kämpfe gleichzeitig auswerten.** Mit der
Wahl eines Pulls wurde neben dem Pull selbst auch dessen Zeitleiste im
Voraus geholt - beide lesen dieselben Ereignisströme. Nebeneinander
konkurrierten sie um genau die Anfrage, auf die man gerade wartete.
Die Zeitleiste wird jetzt erst geholt, wenn der Pull da ist; der Zweck
des Vorabladens bleibt, die Wartezeit liegt weiterhin vor dem
Wiedergabe-Knopf statt hinter ihm.

**Aufgeben machte es schlimmer.** Brach die App den Abruf ab, verwarf
der Bot die halbfertige Arbeit und begann beim nächsten Versuch wieder
bei null - bei einem Abruf, der länger dauert als die Geduld der App,
wird daraus eine Schleife, die nie fertig wird. Der Bot rechnet einen
begonnenen Pull jetzt zu Ende und hält das Ergebnis einige Minuten
vor; ein zweiter Versuch ist damit sofort da.

Nebenbei sagen die Meldungen jetzt mehr: statt der englischen
httpx-Zeile steht dort, dass ein erneuter Versuch schneller ist, und
nennt der Bot einen Grund (etwa "WarcraftLogs hat nicht rechtzeitig
geantwortet"), steht der in der Oberfläche statt nur einer HTTP-Nummer.

## 1.6.1

Im Archiv lassen sich nur noch **Bosskämpfe** auswählen.

WarcraftLogs führt Trash in derselben Liste wie die Bosskämpfe. In der
Pull-Auswahl standen dadurch Dutzende Trashgruppen zwischen den paar
Kämpfen, die man tatsächlich ansehen will - eine Trashgruppe ist aber
kein Pull: kein Bossanteil, keine Pull-Nummer, die etwas bedeutet, und
keine Taktik, gegen die sich etwas bewerten ließe. Unterschieden wird
über die Encounter-ID, die bei Trash 0 ist; das ist das einzige
verlässliche Merkmal, denn der Name trägt dort irgendeinen Mob.

Gefiltert wird auf **beiden** Seiten: der Bot schickt Trash gar nicht
mehr mit, und die App verwirft es zusätzlich selbst. Ohne das zweite
hinge die Auswahl davon ab, wann jemand den Bot neu ausrollt.

Dieselbe Ursache steckte im Live-Betrieb: dort galt schlicht der
jüngste Eintrag als "aktueller Pull", und das ist an einem Raidabend
überwiegend eine Trashgruppe. WeintTV zeigte sie mitsamt Pull-Nummer,
Bossleiste und Academy-Bewertung an. Jetzt gilt der jüngste
**Bosskampf**; hat ein Bericht noch keinen, sagt der Bot das auch so,
statt eine Trashgruppe wie einen Pull aussehen zu lassen.

Außerdem, aus derselben Runde: Fähigkeiten werden jetzt über ihre
Spell-ID erkannt statt über den Namen. Ein Abgleich mit den Katalogen
des Bots fand 35 Spell-IDs, die auf beiden Seiten einen verschiedenen
deutschen Namen tragen - über den Namen gematcht wäre jede davon eine
dauerhaft unerkannte Zeile gewesen, und eine unerkannte Zeile sieht
genauso aus wie eine Fähigkeit, die nie benutzt wurde. Zwei Einträge
waren dabei schlicht falsch: Göttliche Gunst lief als Zorn der
Gerechtigkeit, und der Gedankenschinder wurde gegen die dreifache
Abklingzeit des Schattengeists gemessen. Der Nethersturm des
Arkan-Magiers fehlte ganz.

## 1.6.0

WeintTV und die WeintAcademy kennen jetzt die Fähigkeiten jeder
Spezialisierung.

Bisher konnten beide nur wiedergeben, was die Datenquelle geschickt
hat. Kam nichts, stand dort "Keine Angaben zu DoT-Uptimes" - und zwar
wortgleich für drei völlig verschiedene Sachverhalte: der Spieler hat
seinen DoT tatsächlich nie aufgelegt, die Quelle liefert diesen Block
nicht, oder es gibt für diesen Kampf gar keine Tiefenauswertung. Wer
seine HoT-Uptimes, DoT-Uptimes oder Cooldown-Einsätze vermisst hat,
konnte an der Oberfläche nicht erkennen, welcher der drei Fälle
vorlag.

Neu ist `analyzer/data/class_abilities.py`: alle 34
Spezialisierungen von Mists of Pandaria mit ihren DoTs, HoTs,
Selbstbuffs (bei Tanks die aktive Schadensminderung) und Cooldowns -
je mit Spell-ID, englischem und deutschem Namen, Richtwert und
Abklingzeit. Die Spell-IDs stammen aus dem Raidlog-Analyzer und sind
um die Spezialisierungen ergänzt, die dort keine hatten.

Was sich dadurch ändert:

- **Erkennung in drei Sprachen.** Jede gemeldete Zeile wird über
  Spell-ID, englischen und deutschen Namen erkannt - einer genügt.
  Ein deutscher Bericht ("Verjüngung") und ein englischer
  ("Rejuvenation") landen in derselben Zeile, und in der Oberfläche
  steht durchgängig der deutsche Name.
- **Richtige Einsortierung.** Ein HoT, den die Quelle unter die Buffs
  legt, landet trotzdem in der HoT-Karte. Vorher blieb sie leer,
  obwohl die Zahl da war.
- **Fehlendes wird sichtbar.** Liefert die Quelle eine Art von
  Wirkungsdauern, erscheinen die nicht gemeldeten Fähigkeiten der
  Spezialisierung mit null Prozent und dem Hinweis "nie aufgelegt" -
  ein Befund statt einer Leerstelle. Liefert sie diese Art gar nicht,
  wird auch nichts behauptet; stattdessen nennt der Platzhaltertext,
  was für diese Spezialisierung zu sehen wäre.
- **Talentabhängiges wird nie ergänzt.** Eine Zeile "Inkarnation - nie
  genutzt" bei jemandem ohne dieses Talent wäre ein Vorwurf für
  nichts.
- **Cooldown-Quoten sind fair geworden.** Gewertet wird nur noch, was
  auf Abklingzeit gehört. Ein ungenutzter Schildwall ist kein
  verschenkter Einsatz - vorher zog genau das die Bewertung von Tanks
  und Heilern nach unten, also der Rollen mit den meisten
  Defensivcooldowns.
- **Die Simulation zeigt jede Spezialisierung.** Bisher hatten nur
  siebzehn der fünfundzwanzig simulierten Spieler überhaupt
  Wirkungsdauern; ein Elementarschamane, ein Windwandler oder ein
  Arkanmagier hatte keine einzige Zeile. Jetzt bekommt jeder Spieler
  das, was seine Spezialisierung mitbringt.

## 1.5.2

Reiner Versionssprung, kein funktionaler Unterschied zu 1.5.1: der Tag
`v1.5.1` war auf den Stand vor dem Merge des Rotationstrainer-Fixes
gesetzt worden (`core/version.py` stand dort noch auf 1.5.0), und
genau das prüft `scripts/check_version.py` vor jedem Build - der
Build brach deshalb schon im Versionsabgleich ab, bevor irgendetwas
gepackt wurde. `v1.5.1` bleibt als kaputter Tag ohne Release stehen,
dieses Release trägt den Inhalt von 1.5.1 unter der nächsten
Versionsnummer nach.

## 1.5.1

Eine Übungssitzung am Trainingsdummy zählt erst ab drei Minuten.

Bisher genügten dreißig Sekunden, und die trugen dieselbe Tage-Serie
wie eine richtige Übungseinheit: dreimal kurz auf die Puppe geschlagen
hakte die Rotationslektion im Trainingsplan ab. `MIN_SESSION_SECONDS`
in `core/academy_dummy_sync.py` verwirft Sitzungen unter drei Minuten
jetzt schon vor der Serie. Die Zahl steht bewusst doppelt - WeintCodex
1.3.2.0 meldet nichts Kürzeres mehr, aber welche Addon-Version
installiert ist, entscheidet der Spieler, und eine ältere schickt
weiterhin kurze Sitzungen.

Die 23 Lektionen "Prioritätenliste an der Trainingspuppe üben" nennen
die Mindestdauer jetzt in ihren Schritten, statt sie stillschweigend
vorauszusetzen.

## 1.5.0

WeintTV und die WeintAcademy für Tanks, Heiler und Schadensausteiler
gleichermaßen.

Drei Fehler, die alle dasselbe Symptom hatten - es passierte nichts,
und niemand konnte sehen, dass etwas fehlte.

**Der Lektionskatalog kam im Echtbetrieb nie an.** Katalog und
Simulation führen die Spezialisierungen deutsch ("Vergeltung",
"Braumeister"), WarcraftLogs liefert sie englisch ("Retribution",
"Brewmaster"). Beim Nachschlagen traf deshalb kein einziger Schlüssel
zu: jeder Spieler bekam nur Rollen- und Allgemeinlektionen, ohne
Fehler und ohne Warnung, und in der Oberfläche war das nicht davon zu
unterscheiden, dass für seine Spezialisierung nichts hinterlegt ist.
`analyzer/data/specs.py` führt jetzt alle vierunddreißig
Spezialisierungen in beiden Sprachen samt Rolle.

**Tanks wurden gar nicht als Tanks erkannt**, wenn der Bot die Rolle
nicht mitschickte: geraten wurde aus Schaden gegen Heilung, und dabei
kann ein Tank nur als Schadensausteiler herauskommen. Er wird dann
gegen die Schadensrangliste der Schadensausteiler gemessen und bekommt
dauerhaft einen Stern, obwohl er seine Aufgabe erfüllt. Aus
"Protection", "Blood", "Guardian" oder "Brewmaster" folgt die Rolle
jetzt unmittelbar.

**Prüfkriterien, die eine Fähigkeit nennen, blieben in deutschen
Berichten dauerhaft "keine Daten".** WarcraftLogs gibt Fähigkeiten in
der Sprache des Clients zurück, der den Bericht hochgeladen hat -
derselbe Fehler, an dem auf der Bot-Seite schon einmal sämtliche
Cooldown-Listen gescheitert sind. `analyzer/data/player_abilities.py`
gleicht beide Sprachen ab.

Dazu die Lücke, die die Tankbewertung inhaltlich unbrauchbar machte:
der Snapshot kannte nur DoTs und HoTs. Die aktive Schadensminderung
eines Tanks - Schildblock, Mischen, Schild des Rechtschaffenen,
Knochenschild - ist weder das eine noch das andere, sie liegt auf ihm
selbst. In "Rotation" blieb deshalb allein die Aktivzeit übrig, also
ausgerechnet die Zahl, die über einen Tank am wenigsten aussagt. Es
gibt jetzt eigene Buff-Uptimes: in WeintTV als eigene Karte, in der
Academy als Rotationsbewertung der Tanks und als prüfbares Kriterium
der Lektionen. Wie alle Felder der Tiefenauswertung ist der Block
optional - fehlt er, steht dort "keine Daten" und keine schlechte
Note.

Zwei weitere Bewertungen waren zu freundlich: wer der einzige Spieler
seiner Rolle im Kampf war, wurde beim Platz in der Rangliste und beim
Laufweg mit sich selbst verglichen und bekam zwangsläufig die volle
Wertung. Das trifft regelmäßig den einzigen Tank und den einzigen
Heiler - also genau die beiden, denen eine geschenkte Bestnote am
wenigsten hilft. Ohne Vergleichsgruppe gibt es dort jetzt "keine
Daten".

Der Lektionskatalog ist von 165 auf 266 Lektionen gewachsen. Jede der
vierunddreißig Spezialisierungen hat jetzt eigene Inhalte zu Rotation
und Cooldowns, jede Klasse ihre Nutzfähigkeiten (Unterbrechung,
Seelenstein, Symbiose, Handzauber), und die fünf Tank- und sechs
Heiler-Spezialisierungen sind aus ihrem Zustand von ein bis zwei
Lektionen heraus. Auf der Rollenebene sind die Bereiche
dazugekommen, die vorher auf die allgemeinen Ratschläge fielen -
Überleben, Laufwege und Leistung für Heiler und Schadensausteiler,
Rotation, Cooldowns und Leistung für Tanks.

## 1.4.6

Der Wiedergabe-Knopf und die Ladezeiten.

Die Zeitleiste eines Pulls - die mit Abstand größte Antwort des Bots -
wurde erst auf Knopfdruck angefordert. Die gesamte Wartezeit lag damit
hinter dem Klick, und wer währenddessen ein zweites Mal drückte, löste
gar nichts aus: `start_replay()` brach bei laufendem Abruf wortlos ab.
Beides ist behoben. `RaidDataService.prefetch_timeline()` holt die
Zeitleiste jetzt schon beim Wählen des Pulls, parallel zum Abruf des
Pulls selbst, sodass die Wiedergabe im Normalfall ohne Wartezeit
startet; ein Druck während des Ladens wird vorgemerkt statt verworfen
(`ReplayState.starting`). Der Zeitleisten-Endpunkt bekommt außerdem
60 statt 15 Sekunden Zeit - dieselbe Frist wie für eine dreizeilige
Berichtsliste anzusetzen, war beim teuersten Abruf die knappste, und
das Ergebnis sah aus wie ein kaputter Knopf.

Während einer laufenden Wiedergabe waren Bericht- und Pull-Auswahl
nicht mehr bedienbar: `ArchivePicker` hängt an `replayChanged`, das
viermal je Sekunde gesendet wird, und leerte seine Auswahlfelder bei
jedem Takt - ein aufgeklapptes Dropdown klappte sofort wieder zu. Die
Felder werden jetzt nur noch neu gefüllt, wenn sich ihr Inhalt
wirklich geändert hat.

Dazu drei Ursachen für spürbare Trägheit, alle gemessen:

- `setStyleSheet()` verwirft in Qt die Stilberechnung eines Widgets
  und zeichnet neu, auch bei unverändertem Inhalt. Beim Zeichnen eines
  WeintTV-Snapshots kamen rund 280 solcher Aufrufe zusammen, drei
  Viertel der Rechenzeit eines Bildes. `gui/theme/restyle.py` setzt
  nur noch, was sich geändert hat: ein Bild kostet statt 25 nun 3,5 ms.
- WeintTV und die Academy hängen am selben `snapshotChanged` und
  zeichneten sich auch dann neu, wenn die jeweils andere Seite im
  Vordergrund war - bei laufender Wiedergabe dauerhaft doppelte
  Arbeit für ein Bild, das niemand sieht.
- Der Programmstart baute alle sieben Seiten im Voraus, obwohl meist
  nur eine angesehen wird; allein WeintTV und die Academy legen dabei
  ihre Listenzeilen auf Vorrat an. Seiten entstehen jetzt beim ersten
  Betreten (`MainWindow._ensure_page()`), der Start dauert statt rund
  vier nur noch knapp eine Sekunde.

## 1.4.5

Für niemanden in der Gilde kam ein Zugriffsprofil an: Discord-Rollen wie
"Admin", "Gildenleitung", "Klassen-Support" oder "Member" fehlten in der
Standard-Zuordnung Rolle → Rang, sodass `resolve_tier()` nie einen Rang
fand und im Addon (bewusst fail-open) immer alles offen blieb, statt echte
Freigaben zuzustellen. `core/access_roles.py`s `DEFAULT_ROLE_MAP` kennt jetzt
die tatsächlichen Rollennamen: Admin/Gildenleitung/Klassen-Support/Member als
gildeninterne Rollen bekommen "offizier", Raider/Friends als gildenexterne
Rollen "extern". Letzteres korrigiert nebenbei einen zu großzügigen
Alt-Stand, in dem "raider" fälschlich auf "mitglied" abgebildet war und
externen Mitraidern damit `materials.scan`/`loot.report`/`weinttv.raid`
freigegeben hätte.

## 1.4.4

Der Discord-Verknüpfungshinweis aus 1.4.3 hat seinen zweiten Absatz
abgeschnitten: Titel und Fließtext lagen direkt im Root-Layout, und
das wortumbrechende `QLabel` hat seine Höhe nicht zuverlässig an den
vollen Text angepasst, sodass der Hinweis auf die lokale Speicherung
der Anmeldedaten nicht mehr lesbar war. `gui/dialogs/discord_link_prompt.py`
packt Titel und Text jetzt - wie schon der "Was ist neu"-Dialog - in
eine `QScrollArea`, damit der Inhalt unabhängig von Schriftgröße oder
Zeilenzahl immer vollständig sichtbar bleibt.

## 1.4.3

Reiner Versionssprung wie schon bei 1.4.1: der Tag `v1.4.2` war
versehentlich auf einen veralteten Stand (`Version 1.2.6`, weit vor
der 1.4.2-Versionserhöhung) gesetzt worden, wodurch
`scripts/check_version.py` den Build zu Recht abgebrochen hat. Da
GitHub das Verschieben eines bereits veröffentlichten Tags per
Tag-Protection blockiert, gibt es statt eines korrigierten `v1.4.2`
diesen Patch-Tag - diesmal zusammen mit einer echten Änderung.

- Neu: Popup beim Programmstart, solange kein Discord-Account
  verknüpft ist (`gui/dialogs/discord_link_prompt.py`). Es weist
  darauf hin, dass der volle Funktionsumfang erst mit verknüpftem
  Discord-Account zur Verfügung steht und dass die Anmeldedaten
  ausschließlich lokal und temporär auf dem eigenen Rechner liegen.
  Schließbar wie jeder andere Dialog, erscheint aber - anders als das
  "Was ist neu"-Popup - bei jedem Start erneut, solange nicht
  verknüpft ist.

## 1.4.2

WeintCodex 1.3.0.0 bringt einen Rotationstrainer - ein kleines Fenster
im Addon, das live an einer Trainingspuppe die Prioritätenliste der
eigenen Spec abhakt. Diese Version verzahnt das mit dem Trainingsplan.

- Neu: Der Lektionskatalog bekommt pro DPS-Spec (alle 23) eine
  Rotations-Lektion "Prioritätenliste an der Trainingspuppe üben"
  (`analyzer/academy/lessons/classes/<klasse>.py`).
- Neu: `core/academy_dummy_sync.py` verarbeitet die vom Addon gemeldeten
  Übungssitzungen (`dummy_practice_session`, siehe
  `core/sync_manager.py`) und führt pro Charakter und Spec eine
  Tage-Serie. Drei aufeinanderfolgende Tage mit mindestens 80 %
  Trefferquote haken die zugehörige Lektion automatisch ab - über
  dieselbe Persistenz wie das manuell gesetzte Häkchen.
- `core/academy_service.py` speichert diese Serien jetzt zusätzlich
  unter `dummy_practice` in `academy_progress.json`.

## 1.4.1

Reiner Versionssprung: der Tag `v1.4.0` war versehentlich auf einen
Stand vor der 1.4.0-Versionserhöhung gesetzt worden, wodurch
`scripts/check_version.py` den Build zu Recht abbrach. Da GitHub das
Verschieben eines bereits veröffentlichten Tags per Tag-Protection
blockiert, gibt es statt eines korrigierten `v1.4.0` diesen Patch-Tag
auf demselben Funktionsstand. Kein Code hat sich gegenüber 1.4.0
geändert.

## 1.4.0

Wer mitraidet, aber nicht in der Gilde ist, kann WeintCompanion jetzt
gefahrlos bekommen: die App fragt die Discord-Rolle ab und stellt dem
Addon daraus ein Zugriffsprofil zu. WeintCodex 1.2.0.0 richtet danach
aus, welche Bereiche offenstehen - und verknüpft sich mit genau einer
Community, sodass sich die Daten zweier Gilden nicht mehr in derselben
SavedVariables-Datei vermischen können.

- Neu: Zugriffsprofil-Zustellung. Die Rollennamen kommen vom Bot
  (`GET /companion/access-profile`), die Zuordnung auf Rang und
  Freigaben passiert hier in `core/access_roles.py` - eine im Discord
  umbenannte Rolle lässt sich damit ohne neue Companion-Version
  nachziehen.
- Neu: Einstellung `access_role_map`, um die Zuordnung
  Rollenname → Rang zu überschreiben, und
  `access_profile_sync_enabled`, um die Zustellung abzuschalten.
- Neu: Nachrichten an das Addon tragen die Discord-Guild-ID. Das Addon
  verwirft damit Daten, die zu einer anderen Community gehören, statt
  sie einzuarbeiten - relevant, wenn in der App der verknüpfte
  Discord-Account gewechselt wird.
- Behoben: `SyncReader.remove_message()` baute die verbleibenden
  Nachrichten aus einer festen Feldliste neu auf und verlor dabei
  Felder, die es noch nicht kannte. Eine Nachricht, die auf den
  nächsten Zyklus wartete, verlor so still ihre Herkunftsangabe.
- Wichtig: Solange der Bot den Endpunkt nicht bereitstellt, wird kein
  Profil zugestellt und im Addon bleibt alles offen - genau wie vor
  WeintCodex 1.2.0.0. Der Vertrag steht in
  `docs/access-profile-bridge.md`.
- Wichtig: Das ist **keine Sicherheitsgrenze.** Die Zuordnungstabelle
  liegt wie die SavedVariables des Addons auf dem Rechner des Spielers.
  Der Nutzen ist zweierlei: die Community-Bindung verhindert das
  Vermischen zweier Gilden, und die Freigaben halten die Oberfläche
  ehrlich. Vertraulichkeit leistet das nicht - dafür müsste der Bot
  eine unberechtigte Nutzlast gar nicht erst ausliefern.

## 1.3.0

WeintTV und die Academy gibt es jetzt auch im Spiel - abgespeckt, für
alle, die nur einen Monitor haben und im Raid nicht dauernd aus WoW
heraus wollen. Diese Version stellt die Auswertung dem Addon zu; die
Anzeige selbst bringt WeintCodex 1.0.1.0 mit.

- Neu: Die zuletzt ausgewertete Analyse wird ins Addon gestellt -
  erhaltener und vermeidbarer Schaden samt "Was tun"-Hinweis,
  Wirkungsdauern, Aktivzeit, Laufwege, Cooldown-Nutzung,
  Unterbrechungen und Mechanikfehler. Dazu Sternebewertung,
  Trainingsplan und Lektionskatalog des gewählten Charakters.
- Neu: Bridge-Karte "WeintTV & Academy ingame" auf der Sync-Seite,
  mit der sich die Zustellung abschalten lässt.
- Neu: Ingame abgehakte Lektionen und abgewählte Katalogeinträge
  kommen zurück auf den Desktop - der Lernpfad ist damit auf beiden
  Seiten derselbe.
- Wichtig: Zugestellt wird, was WeintTV oder die Academy zuletzt
  ausgewertet haben. Der Raid-Datendienst wird dafür bewusst nicht
  dauerhaft gestartet, damit die Anwendung nicht im Hintergrund
  pollt, wenn niemand die beiden Seiten benutzt.
- Wichtig: Das Addon liest die Zustellung beim Login bzw. nach
  /reload - dieselbe Bedingung wie beim Raid-Roster-Import. Ein
  Live-Bild im Spiel ist technisch nicht möglich, WoW liest seine
  SavedVariables nur beim Laden ein.
- Intern: Die Inbox Richtung Addon hat jetzt Kanäle. Vorher hat jeder
  Absender die komplette Warteschlange ersetzt - mit zwei Absendern
  im selben Sync-Durchlauf hätte der zweite die Nachrichten des
  ersten gelöscht.
- Intern: Nutzlasten Richtung Addon dürfen verschachtelte Tabellen
  sein und werden als echtes Lua geschrieben. Ein Trennzeichen-Format
  wäre für Lektionstexte und Schadenshinweise nicht eindeutig
  gewesen - genau die Zeichen, die als Trenner taugen, kommen darin
  vor.

## 1.2.6

Der Wiedergabe-Knopf meldete für jeden Pull "Für diesen Pull liefert
der Bot keine Zeitleiste", und die Analyse blieb bei DoT-/HoT-Uptimes,
Laufwegen, Unterbrechungen und Cooldowns leer. Beides lag am Bot, der
die Daten nie geliefert hat - diese Version wertet aus, was er ab
sofort schickt.

- Wichtig: Diese Version wertet Daten aus, die erst ein
  aktualisierter WeintCodex-Bot liefert. Solange der Bot noch nicht
  aktualisiert ist, ändert sich in WeintTV und der Academy nichts.
- Fix: Die Wiedergabe hat nie funktionieren können - den Endpunkt für
  die Zeitleiste gab es im Bot schlicht nicht, und seine Antwort
  "nicht gefunden" erschien als "Für diesen Pull liefert der Bot keine
  Zeitleiste". Er ist jetzt umgesetzt.
- Fix: DoT-/HoT-Uptimes, Laufwege, Unterbrechungen und Dispels sowie
  Raid- und Heil-Cooldowns blieben leer, weil der Bot Fähigkeiten über
  ihren englischen Namen suchte. WarcraftLogs liefert die Namen aber
  in der Sprache des Berichts - in einem deutschen Log passte kein
  einziger. Erkannt wird jetzt über die Zauber-ID sowie den deutschen
  und den englischen Namen.
- Neu: Laufwege werden geliefert. Der Wert ist eine Schätzung aus den
  Positionsangaben der Kampfereignisse und ist als solche
  beschriftet - als Vergleich innerhalb eines Pulls belastbar, als
  absolute Zahl nicht.
- Die Bewertung, ob ein Treffer vermeidbar war, liegt wieder
  ausschließlich in der App. Der Bot schickt nur noch Treffer mit
  Zeitpunkt. Fähigkeiten ohne hinterlegte Regel erzeugen weiterhin
  keinen Eintrag - lieber eine Lücke als ein Vorwurf an jemanden, der
  nichts falsch gemacht hat.

## 1.2.5

Enthält alles aus 1.2.4 - dieses Release kam nie bei euch an: sein Tag
zeigte auf den Stand von 1.2.3, das Update installierte deshalb wieder
1.2.3 und bot sich danach erneut selbst an.

- Fix: Der Build bricht jetzt ab, wenn ein Tag nicht zu der im Code
  hinterlegten Version passt, statt ein Release mit falscher
  Versionsnummer zu veröffentlichen. Genau das hatte zuvor schon
  v1.2.0 und v1.2.1 getroffen.

## 1.2.4

- Fix: Der Wiedergabe-Knopf in WeintTV und der Academy funktioniert
  jetzt wirklich. Er blieb im Live-Modus unsichtbar, weil die
  Verfügbarkeit geprüft wurde, bevor die Datenquelle überhaupt
  bestand. Und selbst wenn eine Wiedergabe startete, stand sie
  danach still: die Uhr wurde aus dem Ladethread heraus gestartet,
  was Qt stillschweigend ablehnt.
- Fix: Ein Wechsel des Berichts, des Pulls oder der Datenquelle
  verwarf die bereits geladene Zeitleiste nicht - der nächste Druck
  auf Wiedergabe spielte deshalb den vorherigen Kampf ab, eingefroren
  bei 00:00.
- Fix: Ein Klick in die Zeitleiste (statt Ziehen am Regler) sprang
  nicht an die gewählte Stelle.
- Fix: Die Wiedergabe wird nicht mehr im Klick-Moment berechnet -
  die Oberfläche bleibt beim Start bedienbar.
- WeintTV: "Kampfereignisse" zeigt jetzt den ganzen Verlauf eines
  Pulls - zusätzlich zu Toden, Kampf-Rezz und Heldentum auch
  Unterbrechungen, Dispels, Mechanikfehler mit Zeitpunkt sowie
  Phasenwechsel und angesagte Bossfähigkeiten der Datenquelle.
- WeintTV: Liefert die Datenquelle keine Tiefenauswertung, steht dort
  jetzt ein erklärender Hinweis statt zehn leerer Karten - mit dem
  Unterschied zwischen "kein Raid", "kein Pull läuft" und "diese
  Quelle liefert nur Summen".
- WeintAcademy: Derselbe Hinweis erscheint bei der Bewertung, damit
  unbewertete Bereiche nicht wie ein Defekt aussehen.
- WeintTV: Aktivzeit nennt zusätzlich die längste Pause, Uptimes die
  Zahl der Anwendungen.

## 1.2.3

- Vorbereitung der WarcraftLogs-Anbindung für die Tiefenanalyse: der
  Vertrag mit dem WeintCodex Bot ist um DoT-/HoT-Uptimes,
  Cooldown-Nutzung sowie Unterbrechungen und Dispels ergänzt. Sobald der
  Bot diese Daten liefert, füllen sich die entsprechenden Karten in
  WeintTVs Analyse automatisch - bis dahin bleiben sie unverändert
  "keine Daten".

## 1.2.2

- Fix: Das Companion-Update blieb manchmal mit "Keine Prüfsumme für das
  Companion-Update verfügbar" stehen, obwohl der Release ganz normal eine
  Prüfsumme hatte. Ursache war eine Teilstring-Suche bei der Asset-Auswahl,
  die unter bestimmten Bedingungen die von der CI veröffentlichte
  ".sha256"-Datei selbst statt der eigentlichen Installationsdatei als "das
  Asset" erkennen konnte - danach lief die Suche nach deren eigener
  Prüfsumme zwangsläufig ins Leere und das Update wurde aus
  Sicherheitsgründen abgebrochen.

## 1.2.0

WeintTV und die WeintAcademy sind vollständig ausgebaut.

- WeintTV: Wiedergabe. Ein abgeschlossener Pull lässt sich Sekunde für
  Sekunde abspielen - mit Schieberegler, Pause und 1x bis 8x. WeintTV und
  die Academy zeigen dabei immer denselben Moment.
- WeintTV: Neue Karte "Kampfereignisse" im Live-Bereich. Tode,
  Kampf-Wiederbelebungen und Heldentum auf einer gemeinsamen Zeitachse -
  endlich ist ablesbar, WANN Heldentum lief und AUF WEN ein Rezz ging.
- WeintTV: Die Analyse ist von vier auf zehn Karten gewachsen - erhaltener
  Schaden mit Vermeidbarkeitsanteil, vermeidbarer Schaden je Fähigkeit samt
  Hinweis was zu tun war, DoT- und HoT-Uptimes, Laufwege, Aktivzeit,
  Cooldown-Nutzung über den ganzen Kampf sowie Unterbrechungen und Dispels.
- WeintTV: Spielerfilter in der Analyse. Ohne ihn wären 25 Spieler mal sechs
  Tabellen unlesbar.
- WeintTV: Ein Klick auf eine Analysezeile öffnet diesen Spieler in der
  Academy.
- Academy: "Rotation" bewertete bisher nur den Platz in der Schadensliste -
  das ist eine Ausrüstungsbewertung, keine Aussage über die Spielweise.
  Rotation misst jetzt Aktivzeit, Aktionen pro Minute und die
  Wirkungsdauern der eigenen Effekte. Der Rang bleibt sichtbar, aber als
  eigener Bereich "Leistung".
- Academy: Neuer Bereich "Überleben" - erhaltener Schaden und sein
  vermeidbarer Anteil, gemessen gegen die eigene Rolle. Ein Tank bekommt
  zwangsläufig den meisten Schaden ab; nach Summe zu bewerten hieße, ihn für
  seine Aufgabe zu bestrafen.
- Academy: Cooldowns werden jetzt tatsächlich bewertet - genutzte gegen
  mögliche Einsätze und der Anteil, der im Heldentum lag.
- Academy: Der Trainingsplan erkennt selbst, ob eine Lektion im gewählten Log
  eingehalten wurde: erfüllt, nicht erfüllt oder keine Daten, jeweils mit dem
  gemessenen Wert gegen das Ziel. Der eigene Haken bleibt daneben bestehen.
- Academy: Aus einem Befund springt man an die Sekunde der Wiedergabe, an
  der er entstanden ist.
- Academy: Der Katalog ist von 23 auf über 100 Lektionen gewachsen -
  allgemein, nach Rolle, je Klasse und Spezialisierung sowie bossbezogen.
  Jede lässt sich abwählen; standardmäßig sind alle aktiv, und neu
  hinzukommende Lektionen erscheinen automatisch.
- Academy: Fehlt einer Bewertung die Datengrundlage, zeigt sie das
  ausdrücklich an, statt eine Note zu erfinden.
- Die Einordnung "war dieser Treffer vermeidbar" liegt jetzt im Companion und
  nicht im Bot. Sie ist dreiwertig: was nicht hinterlegt ist, bleibt "nicht
  eingeordnet" - sonst bekäme jeder Boss ohne Referenzdaten automatisch eine
  tadellose Bewertung.
- Referenzdaten für alle vierzehn Bosse der Schlacht um Orgrimmar: welcher
  Schaden vermeidbar war, welcher zum Kampf gehört, was stattdessen zu tun
  gewesen wäre. Dazu Lektionen zu jedem dieser Kämpfe, die der Trainingsplan
  selbst gegen das Log prüft.
- Die Simulation liefert alle neuen Auswertungen mit, sodass sich beides auch
  außerhalb der Raidzeit ansehen lässt.
- Fix: Kampf-Wiederbelebungsladungen werden von den tatsächlich gewirkten
  Rezzes verbraucht, nicht von Todesfällen.
- Fix: Der Live/Archiv-Umschalter blieb während der Wiedergabe auf seinem
  alten Stand stehen.

## 1.1.5

- Neu: Die Bot-Anbindung liefert jetzt echte Daten für den "Analyse"-Bereich
  von WeintTV/WeintAcademy (Live und Archiv) - Heldentum, Verbrauchsgüter
  (Flask/Nahrung, Näherung) sowie genutzte Raid-/Heil-Cooldowns. Ein erster
  bossspezifischer Mechanikfehler (Immerseus) ist ebenfalls hinterlegt,
  weitere Bosse folgen schrittweise.

## 1.1.4

- Fix: Das Report-Dropdown des Archiv-Modus (WeintTV/WeintAcademy) zeigte bei
  mehreren gleichnamigen Berichten (z.B. wiederholt
  "Siege of Orgrimmar · Siege of Orgrimmar") keine Möglichkeit, sie
  auseinanderzuhalten. Zeigt jetzt Datum und Uhrzeit (lokal umgerechnet) vor
  Titel/Zone an.

## 1.1.3

- Fix: Der Release-Build von 1.1.2 schlug im Test-Schritt gelegentlich fehl
  (Race Condition beim schnellen Neustart der WarcraftLogs-Datenquelle -
  ein Hintergrund-Thread konnte unter ungünstigem Timing bis zu 60 Sekunden
  als Karteileiche stehen bleiben, statt sich sofort zu beenden). Reiner
  Build-/Interna-Fix, keine Auswirkung auf sichtbares App-Verhalten.

## 1.1.2

- Neu: **Archiv-Modus** für WeintTV und die WeintAcademy - zusätzlich zum
  Live-Feed lässt sich jetzt ein vergangener WarcraftLogs-Bericht auswählen
  und ein bestimmter Pull daraus ansehen (Bericht wählen, Pull darin wählen).
  Der Umschalter ist geteilt: ein Wechsel wirkt auf beiden Seiten gleich,
  damit WeintTV und Academy immer denselben Log betrachten. Setzt eine
  Discord-Verknüpfung voraus und wird erst nutzbar, sobald die
  entsprechende Bot-Anbindung live ist.

## 1.1.1

- Fix: Der Release-Build von 1.1.0 schlug im Test-Schritt fehl, weil zwei
  neu hinzugekommene Tests `core/raid_data_service.py` importierten, das auf
  Modulebene PySide6 lädt - die CI installiert für die Testsuite aber
  bewusst nur pytest, keine GUI-Abhängigkeiten. Reiner Build-/Test-Fix,
  keine Auswirkung auf die App selbst.

## 1.1.0

- Neu: **WeintTV** - ein Live-Dashboard für den Raid mit Bossleben,
  Pull-Timer, Schadens-/Heilrangliste, Tank-Übersicht, Cooldown- und
  Verbrauchsgüter-Status sowie erkannten Mechanikfehlern. Ein-/Ausschaltbar
  über Einstellungen → Module.
- Neu: **WeintAcademy** - leitet aus denselben Raiddaten ein persönliches
  Lernprofil ab (Sternebewertung für Rotation, Bewegung, Cooldowns und
  Mechaniken, relativ zur eigenen Rolle) und daraus einen Trainingsplan mit
  den nächsten sinnvollen Lektionen. Ebenfalls über Einstellungen → Module
  steuerbar.
- Neu: WeintTV und die Academy teilen sich eine gemeinsame Datenquelle, die
  sich in Einstellungen → Module umschalten lässt:
  - **Simulation** - ein deterministischer Beispiel-Pull, mit dem sich
    beide Ansichten jederzeit prüfen lassen, auch ohne laufenden Raid.
  - **WarcraftLogs** - liest den laufenden Livelog-Bericht über den
    WeintCodex-Bot (die App verbindet sich nicht selbst mit WarcraftLogs).
    Gilt für den gesamten Raid, unabhängig davon, ob dieser Rechner selbst
    mitloggt; die Werte sind durch die Art der Übertragung einige Sekunden
    im Verzug, was in der Oberfläche offen ausgewiesen wird. Setzt eine
    Discord-Verknüpfung voraus und wird erst nutzbar, sobald die
    entsprechende Bot-Anbindung live ist.
- Neu: Erkennung des WoW-Combat-Logs (Einstellungen → Module) als
  Grundlage für eine spätere Live-Auswertung direkt aus dem Kampfprotokoll.
- Aufräumen: Die Seitennavigation wurde auf eine einzige, zentrale Liste
  (`gui/navigation.py`) umgestellt - Sidebar und Seitenstapel können damit
  strukturell nicht mehr auseinanderlaufen.

## 1.0.1

- Neu: "Was ist neu"-Popup - erscheint einmalig nach dem Start und zeigt bei
  einer Neuinstallation eine kurze Tour durch Dashboard, Addon-Verwaltung,
  Sync/Discord-Bridges und Einstellungen. Bei einem Update auf eine neue
  Version werden stattdessen die Änderungen aus genau diesem Changelog
  angezeigt. Über die Checkbox im Dialog oder den Schalter in
  Einstellungen → Allgemein lässt sich das Popup dauerhaft abschalten bzw.
  die Tour jederzeit erneut aufrufen.
- Fix: Der Windows-Installer zeigte im Setup-Assistenten und unter "Apps &
  Features" weiterhin Version 0.9.1 an, obwohl die App selbst bereits auf
  1.0.0 stand.

## 1.0.0

Erster offizieller Release. Neben allgemeiner Politur enthält dieser Release
mehrere Härtungen, die vor einem offiziellen 1.0-Release notwendig waren:

- Sicherheit: Downloads (Companion-Self-Update und WeintCodex-Addon-Update)
  werden jetzt per SHA-256-Prüfsumme verifiziert, bevor sie ausgeführt bzw.
  installiert werden. Für das Companion-Self-Update ist eine gültige
  Prüfsumme jetzt zwingend erforderlich - ohne sie wird kein Update mehr
  heruntergeladen.
- Fix: Die Addon-Installation (core/installer.py) ersetzte die bestehende
  Version bisher per "erst löschen, dann kopieren" - ein Absturz mitten
  im Update konnte den Nutzer komplett ohne installiertes Addon
  zurücklassen. Die Installation läuft jetzt über einen atomaren Swap
  (neue Version erst vollständig danebenbauen, dann in einem Schritt
  tauschen); schlägt selbst das fehl, wird automatisch versucht, aus dem
  zuvor erstellten Backup wiederherzustellen.
- Fix: config.json und die WoW-SavedVariables-Datei werden jetzt
  atomar geschrieben (write-temp-then-rename) statt direkt überschrieben -
  ein Absturz mitten im Schreiben kann keine der beiden Dateien mehr
  beschädigen. Eine dennoch beschädigte config.json wird beim nächsten
  Start nach "config.json.bak" verschoben statt stillschweigend mit
  Standardwerten überschrieben zu werden.
- Fix: Ein einzelner fehlerhafter/abgeschnittener Eintrag in der
  Sync-Warteschlange des Addons (z. B. durch einen Lesezugriff mitten in
  einem Schreibvorgang von WoWs Lua-VM) bricht nicht mehr den kompletten
  Sync-Zyklus ab, sondern wird übersprungen.
- Aufräumen: totes, nicht mehr funktionierendes Auth-Scaffolding
  (core/auth/) entfernt - die tatsächliche Discord-Verknüpfung läuft
  bereits vollständig über core/discord_auth.py.
- macOS wird für 1.0 nicht offiziell unterstützt (kein Build/CI-Ziel,
  bestehende Codepfade sind ungetestet).

## 0.9.1

- Neu: Bridge "Charakter-Roster" ist jetzt aktiv. Wer in der Twinkverwaltung
  (WeintCodex-Addon) einen Charakter auswählt, wird automatisch an die
  Charakter-Datenbank des Bots gemeldet (Grundlage für den Klassen-Abgleich
  beim Gilden-Kalender-Invite). Standardmäßig aktiviert, Umschaltung über
  die Sync-Seite. Erfordert WeintCodex ab v0.9.9.26 (Auswahl wird sofort statt
  erst beim nächsten Login gemeldet).

## 0.9.0

- Fix: Die Bridge-Karten "Charakter-Roster" und "Gilden-Kalender" auf der
  Sync-Seite waren vertauscht - die als "Charakter-Roster" aktiv markierte
  Bridge trieb tatsächlich schon den Export der Raid-Anmeldung in den
  Ingame-Kalender an (Gilden-Kalender), während "Charakter-Roster" als
  Feature (Online-Status je Charakter) noch gar nicht existiert. Jetzt
  korrekt beschriftet: "Gilden-Kalender" ist aktiv, "Charakter-Roster"
  ist als geplant markiert.

## 0.8.9

- Neu: Bridge "Loot-Verteilung" - vom Addon erfasste Item-Zuteilungen
  (Episch+, per Würfel oder Meisterlooter vergeben) werden bei aktivierter
  Bridge automatisch an einen Discord-Kanal gemeldet. Standardmäßig
  deaktiviert, Umschaltung über die Sync-Seite.

## 0.8.8

- Fix: "Addon-Ordner öffnen" konnte auf KDE-Systemen (z. B. Nobara) lautlos
  fehlschlagen bzw. mit einem Absturz von "kde-open" enden. Ursache: von
  PyInstaller gesetzte Variablen wie QT_PLUGIN_PATH wurden an den
  gestarteten "xdg-open"-Prozess vererbt, wodurch dessen "kde-open" die
  Qt-Plattform-Plugins aus dem WeintCompanion-Bundle statt aus dem System
  zu laden versuchte und abstürzte. Diese Variablen werden jetzt zusätzlich
  aus der Umgebung externer Prozesse entfernt.

## 0.8.7

- Neu: Auf der Seite "Deine Installationen" wird jetzt neben WeintCodex auch
  WeintCompanion selbst gelistet - mit Versions-Diff (installiert → neueste),
  Changelog der installierten Version und einem Update-Button.

## 0.8.6

- Fix: Toggle-Schalter in den Einstellungen zeigten nach einem Neustart der
  App teils den falschen Zustand an.
- Installer-Version mit der App-Version synchronisiert.

## 0.8.5

- Neu: Autostart (App startet mit dem System) und "In den Tray minimieren"
  in den Allgemein-Einstellungen.

## 0.8.4

- Fix: Die "Über"-Buttons öffneten beim Klick lautlos keinen Browser mehr.

## 0.8.3

- Dashboard-UX: Der "WoW starten"-Button hebt sich stärker vom Hintergrund
  ab, leitet bei fehlendem Start-Befehl direkt zu den passenden
  Einstellungen weiter, gibt beim Speichern sichtbares Feedback und zeigt
  den Discord-Namen im Fenstertitel an.

## 0.8.2

- Dashboard: Die Seite kommt jetzt ohne Scrollen aus, der Zuschnitt des
  About-Banners wurde korrigiert.

## 0.8.1

- Fix: Der Versionsvergleich behandelte "v0.8" fälschlich als andere
  Version als "0.8.0" und löste dadurch unnötig "Update verfügbar" aus.

## 0.8.0

- Neu: Changelog-Panel im Dashboard, das die Änderungen der aktuell
  installierten Companion-Version anzeigt.

## 0.7.4

- Fix: Der Faugus-Start nutzte einen erfundenen `--start`-Flag statt der
  korrekten CLI und schlug dadurch fehl.

## 0.7.3

- Neu: "WoW starten"-Button, der Battle.net direkt aus dem Dashboard startet.
