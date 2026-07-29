"""
Die Schnittstelle jeder Raid-Datenquelle.

Der Vertrag ist absichtlich winzig - genau vier Dinge:

    start()          Quelle aktivieren (Datei öffnen, Zähler setzen)
    stop()           Quelle wieder freigeben
    snapshot()       aktuelles Gesamtbild liefern
    source_label     kurze Herkunftsbezeichnung für die Oberfläche

Zwei Regeln, an die sich jede Implementierung halten muss:

1. `snapshot()` darf niemals eine Ausnahme werfen. Kann die Quelle
   gerade nichts liefern, gibt sie `RaidSnapshot.empty(...)` zurück.
   Die Oberfläche muss deshalb nie Fehler behandeln, sondern rendert
   immer einen gültigen Snapshot.
2. `snapshot()` muss aus einem beliebigen Thread aufrufbar sein. Der
   RaidDataService ruft sie aus einem Hintergrund-Thread auf, während
   der Qt-Hauptthread das Ergebnis rendert.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from analyzer.models import RaidSnapshot


class RaidDataProvider(ABC):

    # --------------------------------------------------
    # Lebenszyklus
    # --------------------------------------------------

    @abstractmethod
    def start(self) -> None:
        """
        Quelle aktivieren. Mehrfaches Aufrufen muss folgenlos sein.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Quelle freigeben. Mehrfaches Aufrufen muss folgenlos sein.
        """

    # --------------------------------------------------
    # Daten
    # --------------------------------------------------

    @abstractmethod
    def snapshot(self) -> RaidSnapshot:
        """
        Aktuelles Gesamtbild. Wirft nie - siehe Modulkommentar.
        """

    # --------------------------------------------------
    # Beschreibung
    # --------------------------------------------------

    @property
    @abstractmethod
    def source_label(self) -> str:
        """
        Kurzer Herkunftstext, z. B. "Simulation" oder
        "Combat-Log (WoWCombatLog.txt)".
        """

    @property
    def live(self) -> bool:
        """
        Ob die Quelle echte Spieldaten liefert. Der Mock überschreibt
        das nicht und bleibt damit korrekt als "nicht live" markiert.
        """

        return False

    # --------------------------------------------------
    # Diagnose
    # --------------------------------------------------

    @property
    def status_text(self) -> str:
        """
        Optionale Zusatzinfo für die Oberfläche (erkannter Pfad,
        Grund für "keine Daten", ...). Standard: leer.
        """

        return ""
