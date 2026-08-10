"""
Charakternamen vergleichen.

Derselbe Spieler heißt je nach Quelle anders geschrieben:

* WarcraftLogs liefert bei realmfremden Spielern "Name-Realm", sonst
  den nackten Namen,
* der WoW-Client kennt über ``UnitName("player")`` nur den nackten
  Namen und den Realm getrennt davon,
* die Auswahl in der App speichert, was der Bericht geschrieben hat.

Verglichen wurde bisher nirgends - es wurde ``==`` benutzt und
gehofft. Das schlug lautlos fehl: eine Auswahl, die nicht exakt zu
einer Roster-Zeile passte, führte dazu, dass entweder der
alphabetisch erste Raider als "ich" galt oder ein Profil ganz ohne
Akteur entstand (``PlayerProfile.name`` == ``"-"``).

Die Datei liegt in ``analyzer/`` und nicht in ``core/``: sie ist
Wissen über Namen, nur stdlib, ohne Qt - und ``analyzer/academy/
evaluator.py`` braucht sie selbst, die Schichtung (``core`` darf
``analyzer`` importieren, nie umgekehrt) bleibt also intakt.

Drei Regeln, die Entscheidungen sind und keine Mechanik:

1. Der Realm wird von Leerzeichen befreit. ``GetRealmName()`` liefert
   "Die Aldor", WarcraftLogs schreibt "DieAldor".
2. Verglichen wird casefold, weil dieselbe Quelle denselben Namen
   nicht immer gleich schreibt.
3. **Ein fehlender Realm ist ein Platzhalter, kein Widerspruch.**
   ``names_equal("Aldrin", "Aldrin-Everlook")`` ist wahr. Anders
   ginge es nicht, denn der Client kennt nur den nackten Namen. Der
   Preis: zwei gleichnamige Spieler von verschiedenen Realms in einem
   Raid fallen zusammen - selten, während die strenge Variante den
   Normalfall bricht.

Dieselben drei Regeln stehen in ``core/names.lua`` des Addons. Sie
müssen gleich bleiben, sonst ist "ich" im Spiel jemand anderes als
"ich" auf dem Desktop.
"""

from __future__ import annotations


def split_name(value) -> tuple[str, str]:
    """
    "Name-Realm" -> ("Name", "Realm"). Ohne Bindestrich bleibt der
    Realm leer.

    Getrennt wird am **ersten** Bindestrich: Realmnamen dürfen welche
    enthalten ("Kirin-Tor"), Charakternamen nicht.
    """

    if not isinstance(value, str):
        return "", ""

    text = value.strip()

    if not text:
        return "", ""

    base, separator, realm = text.partition("-")

    if not separator:
        return base.strip(), ""

    return base.strip(), "".join(realm.split())


def normalize_name(value) -> str:
    """
    Vergleichsform der Basis (ohne Realm, casefold).

    Nur für Vergleiche und Schlüssel gedacht - angezeigt oder
    gespeichert wird immer die Schreibweise der Quelle.
    """

    return split_name(value)[0].casefold()


def names_equal(a, b) -> bool:
    """
    Derselbe Charakter? Der Realm zählt nur mit, wenn ihn **beide**
    Seiten mitbringen (Regel 3 im Modulkopf).
    """

    base_a, realm_a = split_name(a)
    base_b, realm_b = split_name(b)

    if not base_a or not base_b:
        return False

    if base_a.casefold() != base_b.casefold():
        return False

    if realm_a and realm_b:
        return realm_a.casefold() == realm_b.casefold()

    return True


def match_name(candidate, names) -> str | None:
    """
    Den passenden Eintrag aus `names` finden und **in dessen
    Schreibweise** zurückgeben.

    Das ist der eigentliche Zweck der Funktion: wer einen Namen
    weiterreicht, muss die Schreibweise der Quelle behalten, denn
    `evaluator.build_profile()` sucht den Akteur über genau diese
    Zeichenkette. Gäbe man den Suchbegriff zurück, fände die nächste
    Suche in derselben Quelle nichts mehr.

    Exakte Treffer gewinnen vor normalisierten - stünden "Aldrin" und
    "Aldrin-Everlook" beide im Roster, wäre sonst die Reihenfolge der
    Liste ausschlaggebend.
    """

    if not candidate or not names:
        return None

    entries = [entry for entry in names if isinstance(entry, str)]

    for entry in entries:
        if entry == candidate:
            return entry

    for entry in entries:
        if names_equal(entry, candidate):
            return entry

    return None
