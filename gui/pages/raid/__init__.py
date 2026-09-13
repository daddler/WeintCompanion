"""
Die vier Perspektiven des Raid Centers.

Jede Datei hier ist eine **Ansicht** und keine Seite: sie trägt keinen
eigenen Kopf, keine eigene Quellenzeile, keinen eigenen
Archiv-Umschalter und keine eigene Wiedergabesteuerung. All das steht
einmal im Raid Center darüber (`gui/pages/raid_center.py`) und bleibt
beim Wechsel zwischen den Ansichten stehen - das ist der ganze Zweck
des Umbaus.

Bis 3.6.0 waren es drei Seiten (`weinttv.py`, `academy.py`,
`archive.py`), jede mit eigenem Kopf, eigener Quellenzeile, eigener
Wartekarte und eigenem Archiv-Umschalter. Sie zeigten denselben
Snapshot und dieselbe Archivauswahl, sagten das aber nirgends - und
jede von ihnen beantwortete die Frage "welcher Kampf ist das hier"
anders.
"""
