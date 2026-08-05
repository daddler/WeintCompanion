"""
Statische Referenzdaten des Analyzers: Encounter, Instanzen und
Schwierigkeitsgrade (`encounters.py`), die Wertung, ob ein Treffer
vermeidbar war (`avoidable.py`), die Spezialisierungen samt Rolle
(`specs.py`) und die Fähigkeitsnamen in beiden Sprachen
(`player_abilities.py`).

Die beiden letzten Tabellen gibt es, weil der Lektionskatalog in einer
Sprache geschrieben ist und die Datenquelle in einer anderen
antwortet - ein Unterschied, der ohne Übersetzung lautlos zu "keine
Daten" führt.

Bewusst als Python-Module statt als JSON: so werden sie von
PyInstaller automatisch mitgepackt und brauchen keinen zusätzlichen
`datas`-Eintrag in WeintCompanion.spec.
"""
