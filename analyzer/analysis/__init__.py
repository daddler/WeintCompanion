"""
Ableitungen aus den Rohdaten einer Quelle.

Diese Schicht sitzt zwischen `analyzer/data/` (Referenzwissen) und
`analyzer/providers/` (Beschaffung): sie nimmt rohe Zeilen, wendet
Referenzdaten darauf an und liefert die Modelle aus
`analyzer/models.py`.

Der Zweck ist Vermeidung von Doppelarbeit. Sowohl der
WarcraftLogs-Mapper als auch die Wiedergabe müssen Ranglisten bauen,
Schaden einordnen und Meter umrechnen - täten sie das jeweils selbst,
gäbe es zwei Auswertungen, die langsam auseinanderdriften. Genau das
soll die Architektur des Projekts verhindern.

Wie der ganze Analyzer: kein Qt, kein Netzwerk, keine Datei-Zugriffe.
"""
