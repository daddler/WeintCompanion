"""
Fahrpläne und Spielerprofile der Simulation.

Herausgezogen aus mock.py, weil die Tiefenauswertung deutlich mehr
feste Daten braucht als der ursprüngliche Pull: Wirkungsdauern,
Laufwege, erhaltener Schaden je Fähigkeit, Cooldown-Einsätze,
Wiederbelebungen, Unterbrechungen. In einer Datei mit dem Anbieter
zusammen wären das über tausend Zeilen, in denen die eigentliche Logik
untergeht.

Zwei Regeln, an die sich alles hier halten muss:

1. **Kein Zufall.** Jeder Wert ist eine geschlossene Funktion der
   Pull-Sekunde. Derselbe Zeitpunkt liefert immer denselben Snapshot -
   sonst wäre die Simulation nicht testbar und die Oberfläche würde
   flackern.
2. **In sich stimmig.** Ein vermeidbarer Treffer, der hier eingeplant
   ist, muss im erhaltenen Schaden auftauchen, als Mechanikfehler
   abgeleitet werden und in der Laufweg-Zeile als vermeidbarer Treffer
   mitgezählt werden. Wären diese Listen uneinig, wäre die Simulation
   kein gültiger Beweis für den Vertrag mehr - genau das prüft
   tests/test_mock_provider.py.

Die Fähigkeitsnamen sind die englischen aus analyzer/data/avoidable.py
für Horridon - so läuft die echte Einordnung durch und die Simulation
zeigt, was der Bot später liefern soll.
"""

from __future__ import annotations

from analyzer.models import (
    CD_DEFENSIVE,
    CD_HEAL,
    CD_PERSONAL,
    CD_RAID,
    MECHANIC_DEFENSIVE,
    MECHANIC_INTERRUPT,
    MECHANIC_MOVEMENT,
    MECHANIC_POSITIONING,
    UPTIME_DOT,
    UPTIME_HOT,
)


#
# --------------------------------------------------
# Tode und Wiederbelebungen
# --------------------------------------------------
#
# (Zeitpunkt, Spieler, Ursache)
#

DEATH_SCHEDULE: tuple[tuple[float, str, str], ...] = (

    (63.0, "Krallenwut", "Verheerender Schlag"),
    (129.0, "Bestienrufer", "Arkane Entladung"),

)


#
# (Zeitpunkt, Ziel, Wirker, Fähigkeit)
#
# Krallenwut wird 15 Sekunden nach dem Tod hochgeholt, Bestienrufer
# nicht mehr - so ist im Verlauf beides zu sehen: eine genutzte
# Ladung und ein Tod, der bis zum Ende bestehen bleibt.
#

RESURRECT_SCHEDULE: tuple[tuple[float, str, str, str], ...] = (

    (78.0, "Krallenwut", "Elvenne", "Wiedergeburt"),

)


#
# --------------------------------------------------
# Heldentum
# --------------------------------------------------
#
# (Beginn, Ende, Wirker, Bezeichnung)
#

HEROISM_WINDOWS: tuple[tuple[float, float, str, str], ...] = (

    (96.0, 136.0, "Kaldrun", "Heldentum"),

)


#
# --------------------------------------------------
# Mechanikfehler, die der "Bot" schon eingeordnet mitschickt
# --------------------------------------------------
#
# (Zeitpunkt, Spieler, Beschreibung, Anzahl, Schweregrad, Kategorie)
#
# Diese Liste bleibt unverändert gegenüber der ersten Fassung. Sie
# steht bewusst neben den abgeleiteten Fehlern: so läuft in der
# Simulation auch das Zusammenführen beider Quellen durch, samt der
# Regel, dass derselbe Fehler nicht doppelt gezählt wird.
#

MECHANIC_SCHEDULE: tuple[tuple[float, str, str, int, str, str], ...] = (

    (
        34.0, "Dolchtanz",
        "Im Flächenschaden stehen geblieben",
        2, "warning", MECHANIC_POSITIONING,
    ),
    (
        71.0, "Frostgrimm",
        "Unterbrechung verpasst",
        1, "error", MECHANIC_INTERRUPT,
    ),
    #
    # Bewusst dieselbe Fähigkeit, die weiter unten auch als
    # vermeidbarer Treffer eingeplant ist: so läuft in der Simulation
    # die Entdopplung zwischen Bot-Regel und abgeleitetem Fehler
    # tatsächlich durch, statt nur theoretisch zu existieren.
    #
    (
        108.0, "Windschritt",
        "Zerfetzender Ansturm nicht ausgewichen",
        3, "warning", MECHANIC_MOVEMENT,
    ),
    (
        147.0, "Arkanis",
        "Defensivfähigkeit nicht genutzt",
        1, "info", MECHANIC_DEFENSIVE,
    ),
    (
        158.0, "Krallenwut",
        "Zu spät aus der Zone gelaufen",
        1, "warning", MECHANIC_MOVEMENT,
    ),

)


#
# --------------------------------------------------
# Raid- und Heilcooldowns
# --------------------------------------------------
#
# (Name, Spieler, Abklingzeit, Einsatzzeitpunkte)
#
# Die Einsatzzeitpunkte gab es hier schon vorher - daraus fällt die
# Cooldown-Auswertung samt Heldentum-Ausrichtung ohne neue Daten ab.
#

RAID_COOLDOWNS: tuple[tuple[str, str, float, tuple[float, ...]], ...] = (

    ("Rallying Cry", "Grimmzahn", 180.0, (44.0,)),
    ("Anti-Magic Zone", "Seuchenherz", 120.0, (58.0, 141.0)),
    ("Spirit Link Totem", "Kaldrun", 180.0, (77.0,)),
    ("Power Word: Barrier", "Miraia", 180.0, (112.0,)),
    ("Smoke Bomb", "Silbermond", 180.0, (134.0,)),
    ("Stampeding Roar", "Krallenwut", 120.0, (26.0,)),

)


HEAL_COOLDOWNS: tuple[tuple[str, str, float, tuple[float, ...]], ...] = (

    ("Tranquility", "Elvenne", 180.0, (52.0,)),
    ("Divine Hymn", "Miraia", 180.0, (89.0,)),
    ("Healing Tide Totem", "Kaldrun", 180.0, (38.0, 158.0)),
    ("Revival", "Yunwei", 180.0, (121.0,)),
    ("Aura Mastery", "Torvald", 180.0, (103.0,)),

)


#
# --------------------------------------------------
# Persönliche Cooldowns
# --------------------------------------------------
#
# (Spieler, Name, Abklingzeit, Kategorie, Einsatzzeitpunkte)
#
# Absichtlich gemischt: einige Einsätze liegen im Heldentum-Fenster
# (96-136 s), andere klar daneben. Nur so hat die
# Ausrichtungsbewertung überhaupt beide Fälle zu bewerten - eine
# Simulation, in der alle alles richtig machen, beweist nichts.
#

PERSONAL_COOLDOWNS: tuple[tuple[str, str, float, str, tuple[float, ...]], ...] = (

    #
    # Vorbildlich: im Fenster gewirkt
    #

    ("Nachtblatt", "Celestial Alignment", 180.0, CD_PERSONAL, (98.0,)),
    ("Pyrothal", "Combustion", 45.0, CD_PERSONAL, (22.0, 99.0, 145.0)),
    ("Verdammnis", "Dark Soul: Misery", 120.0, CD_PERSONAL, (14.0, 137.0)),
    ("Seuchenherz", "Dark Transformation", 30.0, CD_PERSONAL,
     (18.0, 51.0, 97.0, 129.0, 161.0)),
    ("Arkanis", "Arcane Power", 90.0, CD_PERSONAL, (12.0, 104.0)),

    #
    # Verschenkt: am Fenster vorbei und/oder zu selten genutzt
    #

    ("Silbermond", "Shadow Blades", 180.0, CD_PERSONAL, (61.0,)),
    ("Falkenauge", "Rapid Fire", 300.0, CD_PERSONAL, (35.0,)),
    ("Schattenruf", "Shadowfiend", 180.0, CD_PERSONAL, (73.0,)),
    ("Sturmklinge", "Elemental Mastery", 90.0, CD_PERSONAL, (29.0,)),
    ("Lichthammer", "Avenging Wrath", 180.0, CD_PERSONAL, (155.0,)),
    ("Windschritt", "Energizing Brew", 60.0, CD_PERSONAL, (40.0,)),
    ("Krallenwut", "Berserk", 180.0, CD_PERSONAL, ()),
    ("Dolchtanz", "Adrenaline Rush", 180.0, CD_PERSONAL, (86.0,)),
    ("Feuerbrand", "Dark Soul: Instability", 120.0, CD_PERSONAL, (20.0,)),
    ("Frostgrimm", "Pillar of Frost", 60.0, CD_PERSONAL, (25.0, 91.0)),
    ("Bestienrufer", "Bestial Wrath", 60.0, CD_PERSONAL, (31.0,)),
    ("Donnerfaust", "Feral Spirit", 120.0, CD_PERSONAL, (47.0, 168.0)),
    ("Grimmzahn", "Recklessness", 180.0, CD_PERSONAL, (94.0,)),

    #
    # Tanks: Defensives
    #

    ("Bramborn", "Shield Wall", 120.0, CD_DEFENSIVE, (30.0, 152.0)),
    ("Bramborn", "Last Stand", 180.0, CD_DEFENSIVE, (67.0,)),
    ("Sigmara", "Fortifying Brew", 180.0, CD_DEFENSIVE, (55.0,)),
    ("Sigmara", "Guard", 30.0, CD_DEFENSIVE,
     (10.0, 44.0, 79.0, 113.0, 147.0)),

)


#
# --------------------------------------------------
# Erhaltener Schaden
# --------------------------------------------------
#
# (Spieler, Fähigkeit, Treffer-Zeitpunkte, Schaden je Treffer)
#
# Die Fähigkeitsnamen stammen aus analyzer/data/avoidable.py
# (Horridon). Vermeidbares und Unvermeidbares stehen bewusst
# gemischt: nur so ist die Aufteilung in der Oberfläche überhaupt
# sichtbar, und nur so kann die Academy "Überleben" sinnvoll
# bewerten.
#
# Tanks bekommen viel unvermeidbaren Schaden (das ist ihre Aufgabe) -
# genau daran zeigt sich, warum die Bewertung rollenrelativ arbeiten
# muss und nicht nach absoluter Schadenssumme gehen darf.
#

DAMAGE_TAKEN: tuple[tuple[str, str, tuple[float, ...], float], ...] = (

    #
    # Tanks: fast alles unvermeidbar
    #

    ("Bramborn", "Triple Puncture",
     (8.0, 24.0, 41.0, 58.0, 74.0, 91.0, 108.0, 124.0, 141.0, 158.0, 174.0),
     168000.0),
    ("Bramborn", "Melee",
     (6.0, 16.0, 26.0, 36.0, 46.0, 56.0, 66.0, 76.0, 86.0, 96.0,
      106.0, 116.0, 126.0, 136.0, 146.0, 156.0, 166.0, 176.0),
     42000.0),
    ("Sigmara", "Triple Puncture",
     (33.0, 50.0, 66.0, 83.0, 100.0, 116.0, 133.0, 150.0, 166.0),
     161000.0),
    ("Sigmara", "Melee",
     (11.0, 21.0, 31.0, 41.0, 51.0, 61.0, 71.0, 81.0, 91.0,
      101.0, 111.0, 121.0, 131.0, 141.0, 151.0, 161.0, 171.0),
     39000.0),

    #
    # Raidweiter, unvermeidbarer Schaden - trifft jeden
    #

    ("Nachtblatt", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Pyrothal", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Grimmzahn", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Silbermond", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Falkenauge", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Verdammnis", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Schattenruf", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Sturmklinge", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Lichthammer", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Seuchenherz", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Windschritt", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Krallenwut", "Dire Call", (37.0,), 54000.0),
    ("Arkanis", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Dolchtanz", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Feuerbrand", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Frostgrimm", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Bestienrufer", "Dire Call", (37.0, 88.0), 54000.0),
    ("Donnerfaust", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Elvenne", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Torvald", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Miraia", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Kaldrun", "Dire Call", (37.0, 88.0, 139.0), 54000.0),
    ("Yunwei", "Dire Call", (37.0, 88.0, 139.0), 54000.0),

    #
    # Vermeidbares. Wer hier auftaucht, hat einen Fehler gemacht -
    # und bekommt genau dafür in der Academy eine schlechtere
    # Bewertung in Movement bzw. Überleben.
    #

    ("Dolchtanz", "Double Swipe", (34.0, 112.0), 96000.0),
    ("Windschritt", "Rending Charge", (108.0, 121.0, 149.0), 78000.0),
    ("Krallenwut", "Blazing Sunlight", (158.0,), 132000.0),
    ("Frostgrimm", "Deadly Plague", (71.0,), 64000.0),
    ("Bestienrufer", "Venom Bolt Volley", (95.0, 118.0), 71000.0),
    ("Feuerbrand", "Rending Charge", (143.0,), 88000.0),
    ("Schattenruf", "Venom Bolt Volley", (66.0,), 71000.0),

)


#
# --------------------------------------------------
# Unterbrechungen und entfernte Effekte
# --------------------------------------------------
#
# (Spieler, Zeitpunkt, Ziel, Fähigkeit)
#

INTERRUPTS: tuple[tuple[str, float, str, str], ...] = (

    ("Silbermond", 28.0, "Gurubashi-Beschwörer", "Kick"),
    ("Windschritt", 49.0, "Farraki-Wüstenwandler", "Spear Hand Strike"),
    ("Grimmzahn", 84.0, "Drakkari-Schamane", "Pummel"),
    ("Silbermond", 106.0, "Gurubashi-Beschwörer", "Kick"),
    ("Seuchenherz", 133.0, "Amani-Schattenjäger", "Mind Freeze"),
    ("Windschritt", 165.0, "Farraki-Wüstenwandler", "Spear Hand Strike"),

)


DISPELS: tuple[tuple[str, float, str, str], ...] = (

    ("Miraia", 42.0, "Bramborn", "Dispel Magic"),
    ("Elvenne", 69.0, "Grimmzahn", "Nature's Cure"),
    ("Torvald", 97.0, "Sigmara", "Cleanse"),
    ("Miraia", 128.0, "Pyrothal", "Dispel Magic"),
    ("Kaldrun", 154.0, "Silbermond", "Purify Spirit"),

)


#
# --------------------------------------------------
# Wirkungsdauern
# --------------------------------------------------
#
# (Spieler, Fähigkeit, Art, Ziel-Uptime in Prozent, Richtwert)
#
# Der erreichte Wert steht bewusst mal über, mal unter dem Richtwert:
# die Rotationsbewertung soll in der Simulation sowohl gute als auch
# verbesserungswürdige Fälle zeigen. Nachtblatt und Verdammnis sind
# vorbildlich, Feuerbrand und Bestienrufer nicht.
#

UPTIMES: tuple[tuple[str, str, str, float, float], ...] = (

    ("Nachtblatt", "Moonfire", UPTIME_DOT, 97.0, 95.0),
    ("Nachtblatt", "Sunfire", UPTIME_DOT, 96.0, 95.0),
    ("Verdammnis", "Agony", UPTIME_DOT, 98.0, 95.0),
    ("Verdammnis", "Corruption", UPTIME_DOT, 97.0, 95.0),
    ("Verdammnis", "Unstable Affliction", UPTIME_DOT, 94.0, 95.0),
    ("Schattenruf", "Shadow Word: Pain", UPTIME_DOT, 91.0, 95.0),
    ("Schattenruf", "Vampiric Touch", UPTIME_DOT, 89.0, 95.0),
    ("Silbermond", "Rupture", UPTIME_DOT, 93.0, 95.0),
    ("Feuerbrand", "Immolate", UPTIME_DOT, 74.0, 95.0),
    ("Bestienrufer", "Serpent Sting", UPTIME_DOT, 68.0, 95.0),
    ("Falkenauge", "Serpent Sting", UPTIME_DOT, 88.0, 95.0),
    ("Krallenwut", "Rake", UPTIME_DOT, 82.0, 90.0),
    ("Krallenwut", "Rip", UPTIME_DOT, 79.0, 90.0),
    ("Pyrothal", "Ignite", UPTIME_DOT, 86.0, 85.0),
    ("Seuchenherz", "Blood Plague", UPTIME_DOT, 92.0, 95.0),
    ("Seuchenherz", "Frost Fever", UPTIME_DOT, 91.0, 95.0),
    ("Grimmzahn", "Rend", UPTIME_DOT, 84.0, 90.0),

    ("Elvenne", "Rejuvenation", UPTIME_HOT, 88.0, 80.0),
    ("Elvenne", "Lifebloom", UPTIME_HOT, 96.0, 95.0),
    ("Elvenne", "Wild Growth", UPTIME_HOT, 71.0, 70.0),
    ("Kaldrun", "Riptide", UPTIME_HOT, 82.0, 85.0),
    ("Kaldrun", "Earth Shield", UPTIME_HOT, 98.0, 95.0),
    ("Yunwei", "Renewing Mist", UPTIME_HOT, 76.0, 85.0),
    ("Torvald", "Beacon of Light", UPTIME_HOT, 94.0, 95.0),
    ("Miraia", "Power Word: Shield", UPTIME_HOT, 63.0, 60.0),

)


#
# --------------------------------------------------
# Laufwege und Aktivzeit
# --------------------------------------------------
#
# (Spieler, Meter über den ganzen Pull, Aktivzeit in Prozent)
#
# Nahkämpfer laufen mehr als Zauberer - das ist normal und genau der
# Grund, warum die Academy den Laufweg nur gegen die eigene Rolle und
# nur mit Toleranz bewertet. Wer auffällig weit über dem Schnitt
# liegt, hat entweder viel ausgewichen (gut) oder ist unnötig
# gelaufen (schlecht); erst zusammen mit den vermeidbaren Treffern
# ergibt die Zahl eine Aussage.
#

MOVEMENT_PROFILE: tuple[tuple[str, float, float], ...] = (

    ("Bramborn", 214.0, 96.0),
    ("Sigmara", 268.0, 94.0),

    ("Elvenne", 342.0, 88.0),
    ("Torvald", 318.0, 86.0),
    ("Miraia", 297.0, 89.0),
    ("Kaldrun", 356.0, 87.0),
    ("Yunwei", 381.0, 83.0),

    ("Nachtblatt", 364.0, 97.0),
    ("Pyrothal", 331.0, 95.0),
    ("Grimmzahn", 442.0, 93.0),
    ("Silbermond", 468.0, 96.0),
    ("Falkenauge", 309.0, 91.0),
    ("Verdammnis", 322.0, 98.0),
    ("Schattenruf", 348.0, 90.0),
    ("Sturmklinge", 336.0, 92.0),
    ("Lichthammer", 451.0, 89.0),
    ("Seuchenherz", 459.0, 94.0),
    ("Windschritt", 612.0, 87.0),
    ("Krallenwut", 487.0, 81.0),
    ("Arkanis", 288.0, 93.0),
    ("Dolchtanz", 594.0, 84.0),
    ("Feuerbrand", 316.0, 79.0),
    ("Frostgrimm", 471.0, 88.0),
    ("Bestienrufer", 301.0, 74.0),
    ("Donnerfaust", 463.0, 91.0),

)


#
# Aktionen pro Minute je Rolle - eine Kennzahl, die stark von der
# Spielweise abhängt und deshalb bewusst grob bleibt.
#

APM_BY_ROLE: dict[str, float] = {
    "tank": 38.0,
    "healer": 31.0,
    "dps": 42.0,
}


#
# --------------------------------------------------
# Nachschlagehilfen
# --------------------------------------------------
#


def movement_for(name: str) -> tuple[float, float]:
    """
    (Meter über den ganzen Pull, Aktivzeit in Prozent) eines Spielers.
    """

    for player, meters, active in MOVEMENT_PROFILE:

        if player == name:
            return meters, active

    return 0.0, 0.0


def damage_taken_for(name: str) -> tuple[tuple[str, tuple[float, ...], float], ...]:
    """
    Alle Schadenszeilen eines Spielers.
    """

    return tuple(
        (ability, times, per_hit)
        for player, ability, times, per_hit in DAMAGE_TAKEN
        if player == name
    )


def cooldowns_for(name: str) -> tuple[tuple[str, float, str, tuple[float, ...]], ...]:
    """
    Alle Cooldowns eines Spielers - persönliche, Raid- und Heilcooldowns
    zusammen, damit die Auswertung eine vollständige Liste je Spieler
    hat.
    """

    rows: list[tuple[str, float, str, tuple[float, ...]]] = [
        (ability, cooldown, category, casts)
        for player, ability, cooldown, category, casts in PERSONAL_COOLDOWNS
        if player == name
    ]

    for ability, player, cooldown, casts in RAID_COOLDOWNS:

        if player == name:
            rows.append((ability, cooldown, CD_RAID, casts))

    for ability, player, cooldown, casts in HEAL_COOLDOWNS:

        if player == name:
            rows.append((ability, cooldown, CD_HEAL, casts))

    return tuple(rows)


def uptimes_for(name: str, kind: str) -> tuple[tuple[str, float, float], ...]:
    """
    (Fähigkeit, erreichte Uptime, Richtwert) eines Spielers.
    """

    return tuple(
        (ability, reached, expected)
        for player, ability, entry_kind, reached, expected in UPTIMES
        if player == name and entry_kind == kind
    )
