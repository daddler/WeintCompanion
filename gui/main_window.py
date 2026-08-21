from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QScrollArea,
    QSystemTrayIcon,
)

from core.companion_manager import CompanionManager
from core.resources import Resources

from gui.controllers.update_runner import UpdateRunner
from gui.dialogs.discord_link_prompt import show_discord_link_prompt_if_needed
from gui.dialogs.whats_new_dialog import show_whats_new_if_needed

from gui.layout.breakpoints import LayoutState, resolve as resolve_layout

from gui.theme import tokens
from gui.theme.motion import curve, duration, is_reduced
from gui.theme.theme_manager import theme

from gui.widgets.nav_column import NavColumn
from gui.widgets.toast import ToastHost
from gui.widgets.title_bar import TitleBar

from gui.navigation import PageId, build_page_specs


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        #
        # --------------------------------------------------
        # Fenster
        # --------------------------------------------------
        #
        # Rahmenlos: die Titelleiste kommt seit 2.0 von der Anwendung
        # selbst (gui/widgets/title_bar.py). Was dabei verloren geht,
        # muss ersetzt werden - Ziehen und Maximieren übernimmt die
        # Titelleiste, die Größenänderung an den Kanten dieses Fenster
        # (siehe _resize_edge weiter unten).
        #

        self.setWindowTitle("WeintCompanion")

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window
        )

        self.resize(*tokens.WINDOW_DEFAULT)

        #
        # Bis 1.7 stand das Minimum auf 1500 x 900, weil das Dashboard
        # diese Höhe brauchte. Auf einem 1366er Bildschirm ließ sich
        # das Fenster dadurch nicht vollständig anzeigen. 2.0 löst das
        # über Haltepunkte statt über ein großes Minimum.
        #

        self.setMinimumSize(*tokens.WINDOW_MIN)

        self.setWindowIcon(
            QIcon(Resources.icon())
        )

        #
        # Für die Kantengriffe: welche Kante gerade gezogen wird und
        # wo das Fenster beim Ansetzen stand.
        #

        self._resize_edges = Qt.Edges()

        self._resize_origin: QPoint | None = None

        self._resize_geometry = None

        self.setMouseTracking(True)

        #
        # --------------------------------------------------
        # Companion Manager
        # --------------------------------------------------
        #

        self.manager = CompanionManager()

        self.manager.initialize()

        #
        # --------------------------------------------------
        # System-Tray ("In Tray minimieren")
        # --------------------------------------------------
        #

        self._force_quit = False

        self._tray_hint_shown = False

        self.tray_icon = None

        self._init_tray()

        self.manager.tray_settings_changed.connect(
            self._on_tray_setting_changed
        )

        #
        # Welche Fassung je Kanal (Addon/Companion) schon als Meldung
        # angekündigt wurde - siehe _announce_updates().
        #

        self._announced_updates: dict[str, str] = {}

        #
        # Siehe _on_state_changed(): verhindert, dass eine Seite über
        # ihr eigenes refresh() eine neue Prüfung auslöst.
        #

        self._refreshing_state = False

        #
        # --------------------------------------------------
        # Root Widget
        # --------------------------------------------------
        #
        # Ohne einen expliziten, opaken Hintergrund bleibt dieses
        # zentrale Widget (und alles, was sich per "background:
        # transparent" darauf verlässt) im echten Rendering-Backing-
        # Store transparent (Alpha 0) statt dunkel gefüllt - auf dem
        # Bildschirm bisher zufällig unsichtbar, weil der Alpha-Kanal
        # dort ignoriert wird, aber z. B. bei Screenshots/Grabs oder
        # Compositing-Fenstermanagern als weißer/durchsichtiger
        # Hintergrund sichtbar. WA_StyledBackground erzwingt, dass
        # das "background"-Stylesheet dieses Widgets tatsächlich
        # gemalt wird.
        #

        root = QWidget()

        root.setObjectName("rootWidget")

        root.setAttribute(Qt.WA_StyledBackground, True)

        #
        # Der einzige echte umlaufende Rahmen im ganzen Programm neben
        # den Eingabefeldern: er ersetzt den Rahmen, den sonst der
        # Fenstermanager zeichnet, und trennt das Fenster vom
        # Bildschirmhintergrund.
        #

        root.setStyleSheet(
            f"""
            QWidget#rootWidget{{
                background:{tokens.SURFACE["base"]};
                border:1px solid {tokens.BORDER["base"]};
            }}
            """
        )

        self.setCentralWidget(root)

        self.window_layout = QVBoxLayout(root)

        self.window_layout.setContentsMargins(0, 0, 0, 0)

        self.window_layout.setSpacing(0)

        #
        # --------------------------------------------------
        # Titelleiste
        # --------------------------------------------------
        #

        self.title_bar = TitleBar(self)

        self.window_layout.addWidget(self.title_bar)

        body = QWidget()

        self.root_layout = QHBoxLayout(body)

        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.root_layout.setSpacing(0)

        self.window_layout.addWidget(body, 1)

        #
        # --------------------------------------------------
        # Seitenregistrierung
        # --------------------------------------------------
        #
        # Eine einzige Liste beschreibt Reihenfolge, Icon, Gruppe,
        # Beschriftung und Klasse jeder Seite (siehe gui/navigation.py).
        # Sowohl die Navigationsspalte als auch der Seitenstapel
        # entstehen daraus - dadurch können beide nicht mehr
        # auseinanderlaufen.
        #

        self.page_specs = build_page_specs()

        self._specs_by_id = {
            spec.page_id: spec
            for spec in self.page_specs
        }

        #
        # --------------------------------------------------
        # Navigationsspalte
        # --------------------------------------------------
        #

        self.nav = NavColumn(self.manager, self.page_specs)

        self.root_layout.addWidget(self.nav)

        #
        # --------------------------------------------------
        # Content Container
        # --------------------------------------------------
        #

        self.content = QFrame()

        self.content.setObjectName("contentContainer")

        self.content.setAttribute(Qt.WA_StyledBackground, True)

        self.content.setStyleSheet(
            f"QFrame#contentContainer{{background:{tokens.SURFACE['base']};}}"
        )

        self.content_layout = QVBoxLayout(self.content)

        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_layout.setSpacing(0)

        self.root_layout.addWidget(self.content, 1)

        #
        # --------------------------------------------------
        # Seiten
        # --------------------------------------------------
        #

        self.pages = QStackedWidget()

        self.content_layout.addWidget(self.pages)

        #
        # Seiten entstehen erst beim ersten Betreten.
        #
        # Sie alle hier zu bauen kostete beim Start rund zwei Sekunden,
        # in denen das Fenster noch nicht steht - und zwar für Seiten,
        # von denen der Nutzer meist nur eine einzige ansieht. Der
        # Löwenanteil geht an WeintTV und die Academy: beide legen ihre
        # Listen- und Tabellenzeilen bewusst im Voraus an, damit das
        # spätere Neuzeichnen im Sekundentakt flackerfrei bleibt (siehe
        # gui/widgets/tv/ranking_list.py). Das ist richtig so - es
        # gehört nur nicht in den Programmstart.
        #
        # Ein leerer Platzhalter je Seite hält die Reihenfolge des
        # Stapels stabil, denn dessen Index IST die PageId (siehe
        # gui/navigation.py). _ensure_page() tauscht ihn beim ersten
        # Betreten gegen die echte Seite.
        #

        self.pages_by_id: dict[PageId, QWidget] = {}

        self._placeholders: dict[PageId, QWidget] = {}

        for spec in self.page_specs:

            placeholder = QWidget()

            self._placeholders[spec.page_id] = placeholder

            self.pages.addWidget(placeholder)

        #
        # Bleibt als Attribut erhalten, wird aber nicht mehr aus der
        # Einfügereihenfolge abgeleitet, sondern aus der Registry.
        #

        self.SETTINGS_PAGE_INDEX = int(PageId.SETTINGS)

        #
        # Die zuletzt gezeigte Seite - nötig, um ihr beim Verlassen
        # on_leave() melden zu können, und um die Richtung des
        # Seitenübergangs zu bestimmen.
        #

        self._current_page = None

        self._current_page_id: PageId | None = None

        self._page_animation = None

        #
        # Haltepunkte
        #

        self._layout_state = LayoutState()

        #
        # Meldungsstreifen statt Dialogen (§6.5). Der Wirt hängt am
        # Fenster und nicht an einer Seite: eine Meldung über ein
        # abgeschlossenes Update soll auch dann erscheinen, wenn der
        # Nutzer inzwischen woanders ist.
        #

        self.toasts = ToastHost(self)

        #
        # Ein Update-Läufer für die ganze Anwendung. Er wird beim
        # Aufbau an jede Seite gereicht, die ihn haben will
        # (`set_update_runner`), damit die Übersicht und "Addon &
        # Updates" nicht zwei nebeneinander laufende Installationen
        # anstoßen können.
        #

        self.update_runner = UpdateRunner(self.manager, self)

        #
        # Navigation
        #

        self.nav.pageChanged.connect(self.change_page)

        self.nav.avatarClicked.connect(
            lambda: self.open_settings_section("discord")
        )

        #
        # Ergebnisse einer Prüfung erreichen die Oberfläche von selbst.
        # Vor 2.0.1 hing `refresh()` ausschließlich am Seitenwechsel:
        # `full_refresh()` läuft im Hintergrund und ist erst fertig,
        # nachdem die Übersicht schon gezeichnet wurde - ein gefundenes
        # Update war deshalb praktisch nie beim ersten Hinsehen da,
        # sondern erst, wenn man die Seite verließ und erneut betrat.
        #
        # Erst hier verbunden und nicht oben beim Manager: der Slot
        # zeichnet die Navigationsspalte mit, und die entsteht in dieser
        # Zeile darüber. Ein Signal aus dem Arbeits-Thread kann während
        # __init__ ohnehin nicht ankommen (die Event-Loop läuft noch
        # nicht), aber die Reihenfolge soll das nicht voraussetzen.
        #

        self.manager.state_changed.connect(self._on_state_changed)

        #
        # Startseite - und damit die einzige Seite, die beim Start
        # tatsächlich gebaut wird.
        #

        self.change_page(PageId.OVERVIEW)

        #
        # Die Start-Popups werden hier NICHT angestoßen, sondern erst
        # aus showEvent() heraus - siehe _queue_startup_popups().
        #

        self._startup_popups_queued = False

    # --------------------------------------------------
    # Meldungen
    # --------------------------------------------------

    def notify(self, text: str, variant: str = "ok", action: str = ""):
        """
        Eine Meldung unten rechts einblenden.

        Der Weg für alles, was bisher ein Dialog gewesen wäre.
        Fehlermeldungen (`variant="error"`) bleiben stehen, bis sie
        weggeklickt werden - eine Fehlermeldung, die von selbst geht,
        ist eine, die niemand gelesen hat.
        """

        return self.toasts.post(text, variant, action)

    # --------------------------------------------------
    # Scroll Wrapper
    # --------------------------------------------------

    def wrap_page(self, widget):

        scroll = QScrollArea()

        scroll.setWidget(widget)

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea > QWidget > QWidget{background:transparent;}"
        )

        return scroll

    # --------------------------------------------------
    # Seiten auf Abruf
    # --------------------------------------------------

    def _ensure_page(self, page_id):
        """
        Die Seite zu `page_id` - gebaut, falls sie noch ein
        Platzhalter ist.

        Alles, was früher in der Aufbauschleife stand, passiert hier:
        das benannte Attribut (`self.overview`, `self.settings`, ...),
        der Scroll-Rahmen und die seitenübergreifenden Signale. Damit
        gibt es weiterhin genau eine Stelle, an der eine Seite
        entsteht - sie läuft nur nicht mehr zwangsläufig beim Start.

        `None` für ein unbekanntes Ziel: die Methode hängt über
        change_page() an Qt-Signalen, und eine Ausnahme in einem Slot
        ist schwer zu verfolgen. Die Navigation bricht dann lieber
        ab, als auf einer falschen Seite zu landen.
        """

        try:
            page_id = PageId(int(page_id))

        except ValueError:
            return None

        page = self.pages_by_id.get(page_id)

        if page is not None:
            return page

        spec = self._specs_by_id[page_id]

        page = spec.page_factory(self.manager)

        self.pages_by_id[page_id] = page

        if spec.attribute:

            setattr(self, spec.attribute, page)

        #
        # Den Platzhalter gegen die Seite tauschen, ohne die
        # Reihenfolge anzutasten: der Index im Stapel IST die PageId.
        # insertWidget() an genau dieser Stelle, dann den Platzhalter
        # entfernen - andersherum rutschten alle folgenden Seiten um
        # eine Position nach vorn.
        #

        placeholder = self._placeholders.pop(page_id)

        self.pages.insertWidget(
            int(page_id),
            self.wrap_page(page) if spec.scroll else page,
        )

        self.pages.removeWidget(placeholder)

        placeholder.deleteLater()

        #
        # Seitenübergreifende Sprünge, weiterhin duck-getypt: eine
        # neue Seite, die springen können soll, braucht nur das
        # Signal und keine Änderung hier.
        #

        if hasattr(page, "pageRequested"):

            page.pageRequested.connect(self.change_page)

        if hasattr(page, "playerRequested"):

            page.playerRequested.connect(self.open_academy_for)

        if hasattr(page, "openSettingsSection"):

            page.openSettingsSection.connect(self.open_settings_section)

        if hasattr(page, "set_update_runner"):

            page.set_update_runner(self.update_runner)

        return page

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def change_page(self, index: int):

        index = int(index)

        #
        # Erst bauen, dann umschalten - sonst zeigte der Stapel den
        # leeren Platzhalter.
        #

        if self._ensure_page(index) is None:
            return

        page_id = PageId(index)

        spec = self._specs_by_id[page_id]

        #
        # Richtung des Übergangs: nach unten in der Navigation heißt
        # von rechts herein. Ohne die Richtung wäre der Versatz
        # beliebig und würde nichts über die Herkunft aussagen.
        #

        previous = self._current_page_id

        direction = 0

        if previous is not None and previous != page_id:

            direction = 1 if int(page_id) > int(previous) else -1

        self.nav.setCurrentPage(index)

        #
        # Die verlassene Seite abmelden, bevor die neue kommt.
        # Seiten mit laufender Datenquelle (WeintTV, Academy) beenden
        # so ihren Poll, sobald sie nicht mehr sichtbar sind.
        #

        if (
            self._current_page is not None
            and hasattr(self._current_page, "on_leave")
        ):

            self._current_page.on_leave()

        #
        # Seite wechseln
        #

        self.pages.setCurrentIndex(index)

        #
        # Dichte Ansichten bekommen die volle Breite: WeintTV muss
        # 25 Zeilen ohne Scrollen unterbringen und klappt die
        # Navigationsspalte deshalb ein. Die Wahl des Nutzers bleibt
        # gespeichert und gilt wieder, sobald er die Ansicht verlässt.
        #

        self._apply_forced_nav(spec)

        current = self.pages.currentWidget()

        if current is None:
            return

        #
        # Die meisten Seiten stecken in einem QScrollArea-Wrapper
        # (siehe wrap_page) - Übersicht, WeintTV und Archiv bewusst
        # nicht (siehe scroll=False in der Registry).
        #

        page = (
            current.widget()
            if isinstance(current, QScrollArea)
            else current
        )

        self._current_page = page

        self._current_page_id = page_id

        #
        # Anmelden (optional) und aktualisieren - vor der Animation,
        # damit die Seite bereits ihren Inhalt trägt, wenn sie
        # eingeblendet wird.
        #

        if hasattr(page, "on_enter"):

            page.on_enter()

        if hasattr(page, "refresh"):

            page.refresh()

        if direction:
            self._animate_page(current, direction)

        #
        # Navigationsspalte ebenfalls aktualisieren
        #

        self.nav.refresh()

    def _on_state_changed(self):
        """
        Eine Prüfung ist durch - die Anzeige nachziehen.

        Nur die **sichtbare** Seite: die übrigen sind entweder noch
        Platzhalter oder ziehen beim nächsten Betreten ohnehin nach
        (`change_page()` ruft `refresh()`). Alle zu zeichnen hieße,
        WeintTV und die Academy im Hintergrund arbeiten zu lassen -
        genau das, was `_attached` dort verhindert.

        Die Navigationsspalte immer, denn ihr Abzeichen ist der
        einzige Hinweis, der auch außerhalb der Übersicht sichtbar ist.
        """

        #
        # Wiedereintrittssperre. Eine Seite, deren `refresh()` selbst
        # eine Prüfung anstößt, schließt sonst einen Kreis: die Prüfung
        # meldet ihren neuen Zustand, das Fenster zeichnet die Seite
        # neu, die Seite prüft wieder. Genau das ist mit
        # ConnectionsPage.refresh() passiert, das ein blockierendes
        # `full_refresh()` enthielt - bis zur Rekursionsgrenze.
        #
        # Die Seite dort ist korrigiert; die Sperre bleibt, weil der
        # Fehler von einer einzelnen Seite ausgeht und das ganze Fenster
        # lahmlegt.
        #

        if self._refreshing_state:
            return

        self._refreshing_state = True

        try:
            self._refresh_after_state_change()

        finally:
            self._refreshing_state = False

    def _refresh_after_state_change(self):

        page = self._current_page

        if page is not None and hasattr(page, "refresh"):

            try:
                page.refresh()

            except Exception as exc:

                #
                # Ein Fehler beim Zeichnen darf die Prüfung nicht in
                # einen Absturz verwandeln; der Slot hängt an einem
                # Signal aus einem Arbeits-Thread.
                #

                self.manager.logger.error(
                    f"Anzeige konnte nicht aktualisiert werden: {exc}"
                )

        self.nav.refresh()

        self._announce_updates()

    def _announce_updates(self):
        """
        Ein gefundenes Update einmal als Meldung einblenden.

        Der dritte Weg neben der Systemzeile der Übersicht und dem
        Abzeichen in der Navigation - und der einzige, der den Nutzer
        erreicht, ohne dass er hinsieht. `notify()` gab es seit 2.0,
        aufgerufen hat es niemand.

        Gemerkt wird die **Fassung**, über die schon berichtet wurde,
        nicht bloß "schon gemeldet": nach einem Addon-Update soll die
        nächste Version wieder eine Meldung bekommen. Ohne dieses Gedenken
        würde eine zweite Prüfung dasselbe erneut ankündigen -
        `state_changed` kommt beim Start, bei jedem Druck auf
        "Erneut prüfen" und seit 2.3.3 aus der Hintergrundwache
        (`core/update_watch.py`), also auch dann, wenn niemand gefragt
        hat. Genau dafür ist das Gedenken gebaut: die Wache prüft alle
        fünfzehn Minuten, meldet aber nur, wenn sich die Antwort
        geändert hat, und dieselbe Fassung wird auch dann nur einmal
        angekündigt.

        Ist das Fenster im Tray geparkt, geht die Meldung zusätzlich als
        Sprechblase des Tray-Symbols hinaus. Eine Einblendung unten
        rechts in einem Fenster, das niemand sieht, ist keine Meldung -
        und "in den Tray minimieren" ist genau die Betriebsart, in der
        eine Fassung stundenlang bereitliegen kann.
        """

        state = self.manager.state

        pending = []

        if state.update_available:

            pending.append(
                ("addon", state.github_version, "WeintCodex")
            )

        if state.companion_update_available:

            pending.append(
                ("app", state.companion_latest_version, "WeintCompanion")
            )

        for key, version, label in pending:

            if self._announced_updates.get(key) == version:
                continue

            self._announced_updates[key] = version

            text = f"{label} {version} steht bereit."

            toast = self.notify(text, "warn", "Öffnen")

            if toast is not None and hasattr(toast, "actionTriggered"):

                toast.actionTriggered.connect(self._open_addon_page)

            self._announce_in_tray(text)

    def _announce_in_tray(self, text: str):
        """
        Dieselbe Nachricht als Sprechblase - nur, wenn das Fenster
        gerade nicht zu sehen ist.

        `isVisible()` allein reicht nicht: ein in die Taskleiste
        minimiertes Fenster gilt Qt weiterhin als sichtbar, ist für den
        Nutzer aber ebenso weg wie ein geparktes.
        """

        if self.tray_icon is None or not self.tray_icon.isVisible():
            return

        if self.isVisible() and not self.isMinimized():
            return

        try:

            self.tray_icon.showMessage(
                "WeintCompanion",
                text,
                QSystemTrayIcon.Information,
                10_000,
            )

        except Exception as exc:

            #
            # Sprechblasen sind nicht auf jedem Schreibtisch möglich
            # (manche Linux-Umgebungen liefern gar keine). Das darf die
            # Prüfung nicht in einen Absturz verwandeln - die
            # Einblendung im Fenster steht ohnehin schon.
            #

            self.manager.logger.info(
                f"Tray-Meldung nicht möglich: {exc}"
            )

    def _open_addon_page(self):

        self.change_page(PageId.ADDON)

    def _apply_forced_nav(self, spec):
        """
        Ob diese Seite die Navigationsspalte einklappt.

        Zwei Gründe können das verlangen - die Seite selbst und der
        Haltepunkt. Beide laufen über `set_forced_collapsed`, das die
        Wahl des Nutzers unberührt lässt.
        """

        self.nav.set_forced_collapsed(
            spec.force_collapsed_nav
            or self._layout_state.nav_collapsed
        )

    def _animate_page(self, widget, direction: int):
        """
        motion.page: Deckkraft 0 -> 1 und ein Versatz von 12 px in
        Navigationsrichtung, parallel (180 ms, OutCubic).
        """

        ms = duration("page")

        if ms <= 0 or is_reduced():

            #
            # Bei reduzierter Bewegung ohne Versatz und ohne
            # Überblendung. Ein zurückgelassener Opazitätseffekt
            # würde die Seite dauerhaft halbdurchsichtig lassen.
            #

            widget.setGraphicsEffect(None)

            return

        #
        # Zuerst die Animation des vorigen Seitenwechsels beenden.
        # Klickt jemand schnell durch die Navigation, liefen sonst
        # zwei Gruppen gleichzeitig auf `pos` derselben Seite - und
        # die ältere setzte den Versatz noch einmal, nachdem die
        # neuere ihn schon zurückgenommen hatte.
        #

        previous = self._page_animation

        self._page_animation = None

        if previous is not None:

            try:
                previous.stop()

            except RuntimeError:
                #
                # Bereits von Qt gelöscht (DeleteWhenStopped, s.u.).
                #
                pass

        effect = QGraphicsOpacityEffect(widget)

        widget.setGraphicsEffect(effect)

        fade = QPropertyAnimation(effect, b"opacity", self)

        fade.setDuration(ms)

        fade.setEasingCurve(QEasingCurve(curve("page")))

        fade.setStartValue(0.0)

        fade.setEndValue(1.0)

        start = widget.pos()

        slide = QPropertyAnimation(widget, b"pos", self)

        slide.setDuration(ms)

        slide.setEasingCurve(QEasingCurve(curve("page")))

        slide.setStartValue(
            QPoint(start.x() + 12 * direction, start.y())
        )

        slide.setEndValue(start)

        group = QParallelAnimationGroup(self)

        group.addAnimation(fade)

        group.addAnimation(slide)

        #
        # Den Effekt am Ende wieder entfernen: ein dauerhaft
        # angehängter QGraphicsOpacityEffect zwingt Qt, die ganze
        # Seite in eine Zwischenebene zu rendern - bei WeintTV mit
        # vier Bildern je Sekunde ist das dauerhaft teuer.
        #

        def finished():

            widget.setGraphicsEffect(None)

            self._page_animation = None

        group.finished.connect(finished)

        #
        # `DeleteWhenStopped`, weil die Gruppe sonst als Kind des
        # Fensters liegen bleibt - eine je Seitenwechsel, für die
        # gesamte Laufzeit des Programms, jede mit zwei
        # Unteranimationen. Nachgemessen: 40 Wechsel, 40 Gruppen.
        # Deshalb muss `finished()` die Referenz auch räumen: nach
        # dem Löschen wäre `self._page_animation` ein Zeiger auf ein
        # nicht mehr vorhandenes C++-Objekt.
        #

        group.start(QParallelAnimationGroup.DeleteWhenStopped)

        self._page_animation = group

    # --------------------------------------------------
    # Haltepunkte
    # --------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        state = resolve_layout(self.width(), self._layout_state)

        if state == self._layout_state:
            return

        self._layout_state = state

        spec = (
            self._specs_by_id.get(self._current_page_id)
            if self._current_page_id is not None
            else None
        )

        self.nav.set_forced_collapsed(
            (spec.force_collapsed_nav if spec else False)
            or state.nav_collapsed
        )

        #
        # Seiten, die sich für die Breite interessieren, melden sich
        # duck-getypt - genau wie bei on_enter/on_leave. Eine Seite,
        # die nichts umzubauen hat, braucht nichts zu tun.
        #

        for page in self.pages_by_id.values():

            if hasattr(page, "on_layout_changed"):

                page.on_layout_changed(state)

    # --------------------------------------------------
    # Größenänderung an den Fensterkanten
    # --------------------------------------------------
    #
    # Was beim rahmenlosen Fenster sonst der Fenstermanager erledigt.
    # Eine Zone von 6 px an jeder Kante: schmal genug, um nicht mit
    # dem Inhalt zu kollidieren, breit genug, um sie zu treffen.

    def _resize_edge(self, position) -> Qt.Edges:

        margin = 6

        x = position.x()

        y = position.y()

        edges = Qt.Edges()

        if x <= margin:
            edges |= Qt.LeftEdge

        elif x >= self.width() - margin:
            edges |= Qt.RightEdge

        if y <= margin:
            edges |= Qt.TopEdge

        elif y >= self.height() - margin:
            edges |= Qt.BottomEdge

        return edges

    def _cursor_for(self, edges: Qt.Edges):

        if edges in (
            Qt.LeftEdge | Qt.TopEdge,
            Qt.RightEdge | Qt.BottomEdge,
        ):
            return Qt.SizeFDiagCursor

        if edges in (
            Qt.RightEdge | Qt.TopEdge,
            Qt.LeftEdge | Qt.BottomEdge,
        ):
            return Qt.SizeBDiagCursor

        if edges & (Qt.LeftEdge | Qt.RightEdge):
            return Qt.SizeHorCursor

        if edges & (Qt.TopEdge | Qt.BottomEdge):
            return Qt.SizeVerCursor

        return Qt.ArrowCursor

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton and not self.isMaximized():

            edges = self._resize_edge(event.position())

            if edges:

                self._resize_edges = edges

                self._resize_origin = event.globalPosition().toPoint()

                self._resize_geometry = self.geometry()

                event.accept()

                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self._resize_origin is None:

            if not self.isMaximized():

                self.setCursor(
                    self._cursor_for(
                        self._resize_edge(event.position())
                    )
                )

            super().mouseMoveEvent(event)

            return

        delta = event.globalPosition().toPoint() - self._resize_origin

        geometry = self._resize_geometry.adjusted(0, 0, 0, 0)

        minimum = self.minimumSize()

        if self._resize_edges & Qt.LeftEdge:

            #
            # Die linke Kante darf nur so weit nach rechts, wie die
            # Mindestbreite es erlaubt - sonst zöge das Fenster seine
            # rechte Kante mit und wanderte über den Bildschirm.
            #

            left = min(
                geometry.left() + delta.x(),
                geometry.right() - minimum.width(),
            )

            geometry.setLeft(left)

        if self._resize_edges & Qt.RightEdge:

            geometry.setRight(geometry.right() + delta.x())

        if self._resize_edges & Qt.TopEdge:

            top = min(
                geometry.top() + delta.y(),
                geometry.bottom() - minimum.height(),
            )

            geometry.setTop(top)

        if self._resize_edges & Qt.BottomEdge:

            geometry.setBottom(geometry.bottom() + delta.y())

        self.setGeometry(geometry)

        event.accept()

    def mouseReleaseEvent(self, event):

        self._resize_edges = Qt.Edges()

        self._resize_origin = None

        self._resize_geometry = None

        self.unsetCursor()

        super().mouseReleaseEvent(event)

    # --------------------------------------------------
    # Start-Popups
    # --------------------------------------------------

    def showEvent(self, event):
        """
        Der einzige Ort, an dem die Start-Popups angestoßen werden.

        **Warum an der Sichtbarkeit und nicht am Konstruktor.** Bis
        2.0.4 stand im Konstruktor ein `QTimer.singleShot(0,
        self._show_startup_popups)`. Der Kommentar dort sagte, das
        geschehe, "damit das Fenster zuerst sichtbar wird" - und
        genau das hat es nicht getan. app.py baut das Fenster hinter
        dem Startbildschirm und ruft zwischen Bau und `show()` ein
        `processEvents()` auf, um den Ladebalken weiterzuzeichnen.
        Ein 0-ms-Timer feuert dort sofort: der modale Dialog ging
        also auf, **bevor** das Fenster überhaupt gezeigt wurde, und
        `exec()` blieb in seiner eigenen Ereignisschleife stehen.
        Unter Windows lag er dabei unter dem Startbildschirm, der als
        `WindowStaysOnTopHint` darüber liegt und mangels
        `splash.close()` nie verschwand: die App hing sichtbar bei
        "Übersicht wird gezeichnet …", während der Dialog unsichtbar
        auf eine Antwort wartete.

        Ein Timer im Konstruktor sagt "später". Gebraucht wird aber
        "wenn das Fenster steht" - und das weiß nur das Fenster
        selbst. Deshalb hängt der Anstoß jetzt an `showEvent`. app.py
        schließt den Startbildschirm, bevor es die Kontrolle an die
        Ereignisschleife zurückgibt, und ruft aus `_stage()` keine
        Ereignisschleife mehr auf - beides zusammen macht diesen
        Zustand unmöglich statt nur unwahrscheinlich.
        """

        super().showEvent(event)

        self._queue_startup_popups()

    def _queue_startup_popups(self):
        """
        Genau einmal je Fensterleben - `showEvent` feuert auch nach
        jedem Wiederherstellen aus dem Tray.
        """

        if self._startup_popups_queued:
            return

        self._startup_popups_queued = True

        QTimer.singleShot(0, self._show_startup_popups)

    def _show_startup_popups(self):
        """
        "Was ist neu", danach ggf. der Discord-Verknüpfungshinweis -
        beide unabhängig vom asynchronen CompanionManager-Init (siehe
        CLAUDE.md: `initialize()` läuft über einen eigenen
        `QTimer.singleShot`), da beide nur lokal vorhandene Daten
        brauchen (gebündeltes CHANGELOG.md bzw. discord_account.json)
        und nicht auf `full_refresh()` warten müssen. Die beiden
        `exec()`-Aufrufe laufen nacheinander, nie gleichzeitig.
        """

        show_whats_new_if_needed(self.manager, self)

        show_discord_link_prompt_if_needed(self.manager, self)

    # --------------------------------------------------
    # Zu einem Settings-Unterabschnitt springen
    # --------------------------------------------------
    # Genutzt vom Discord-Statusbutton in der Navigationsspalte sowie
    # vom "WoW starten"-Button der Übersicht, wenn unter Linux noch
    # kein Start-Befehl hinterlegt ist.

    def open_settings_section(self, key: str):

        settings = self._ensure_page(PageId.SETTINGS)

        self.change_page(self.SETTINGS_PAGE_INDEX)

        if hasattr(settings, "show_section"):

            settings.show_section(key)

    def open_academy_for(self, player_name: str):
        """
        Aus WeintTVs Analyse heraus einen Spieler in der Academy
        öffnen.

        Die Reihenfolge ist entscheidend: erst den Charakter setzen,
        dann die Seite wechseln. `change_page()` löst `on_enter()` und
        `refresh()` aus, die aus dem aktuellen Snapshot neu zeichnen -
        andersherum stünde für einen Moment der falsche Charakter auf
        der Seite.
        """

        academy = self._ensure_page(PageId.ACADEMY)

        if hasattr(academy, "show_player"):

            academy.show_player(player_name)

        self.change_page(PageId.ACADEMY)

    # --------------------------------------------------
    # System-Tray
    # --------------------------------------------------

    def _init_tray(self):

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(
            QIcon(Resources.icon()),
            self,
        )

        self.tray_icon.setToolTip("WeintCompanion")

        menu = QMenu()

        open_action = QAction("Öffnen", menu)

        open_action.triggered.connect(
            self._restore_from_tray
        )

        menu.addAction(open_action)

        menu.addSeparator()

        quit_action = QAction("Beenden", menu)

        quit_action.triggered.connect(
            self._quit_from_tray
        )

        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

        self.tray_icon.activated.connect(
            self._on_tray_activated
        )

        #
        # Eine Sprechblase über ein wartendes Update ist ein Hinweis,
        # den man anklicken können muss - sonst hat man ihn gelesen und
        # sucht danach selbst. Gemeldet wird von hier aus nur das (siehe
        # `_announce_updates`), also führt der Klick dorthin.
        #

        self.tray_icon.messageClicked.connect(
            self._open_addon_page_from_tray
        )

        self._apply_tray_visibility()

    def _apply_tray_visibility(self):

        if self.tray_icon is None:
            return

        enabled = self.manager.config.data.get(
            "minimize_to_tray",
            False,
        )

        self.tray_icon.setVisible(enabled)

    def _on_tray_setting_changed(self, enabled: bool):

        self._apply_tray_visibility()

        #
        # Wird das Feature deaktiviert, während das Fenster gerade
        # im Tray "geparkt" ist, würde es sonst unerreichbar bleiben
        # (kein Tray-Icon mehr, kein sichtbares Fenster).
        #

        if not enabled and not self.isVisible():

            self._restore_from_tray()

    def _on_tray_activated(self, reason):

        if reason not in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        ):
            return

        if self.isVisible() and not self.isMinimized():

            self.hide()

        else:

            self._restore_from_tray()

    def _restore_from_tray(self):

        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _open_addon_page_from_tray(self):

        self._restore_from_tray()

        self.change_page(PageId.ADDON)

    def _quit_from_tray(self):

        self._force_quit = True

        self._shutdown_services()

        QApplication.quit()

    # --------------------------------------------------

    def _shutdown_services(self):
        """
        Hintergrunddienste beim Beenden geordnet stoppen.

        Der RaidDataThread ist zwar ein Daemon und würde den Prozess
        nicht am Leben halten - ihn trotzdem sauber zu beenden
        verhindert, dass er noch einen Snapshot veröffentlicht,
        während die Widgets bereits abgebaut werden.

        Die Pulsuhr ist ein QTimer mit 16 ms: bliebe er laufen,
        weckte er den Prozess weiter, während die Anwendung schon
        abgebaut wird.
        """

        self.manager.raid_data.shutdown()

        from gui.motion.pulse_clock import pulse_clock

        pulse_clock().stop()

    # --------------------------------------------------
    # Fenster minimieren/schließen -> Tray
    # --------------------------------------------------

    def changeEvent(self, event):

        if event.type() == QEvent.WindowStateChange:

            minimize_to_tray = self.manager.config.data.get(
                "minimize_to_tray",
                False,
            )

            if (
                self.isMinimized()
                and minimize_to_tray
                and self.tray_icon is not None
                and self.tray_icon.isVisible()
            ):

                #
                # Direktes hide() aus dem Minimieren-Übergang heraus
                # verhält sich auf manchen Compositorn unzuverlässig
                # (Taskleisten-Icon bleibt hängen) - ein Tick später
                # im nächsten Event-Loop-Durchlauf ist der sichere Weg.
                #

                QTimer.singleShot(0, self.hide)

        super().changeEvent(event)

    def closeEvent(self, event):

        minimize_to_tray = self.manager.config.data.get(
            "minimize_to_tray",
            False,
        )

        if (
            not self._force_quit
            and minimize_to_tray
            and self.tray_icon is not None
            and self.tray_icon.isVisible()
        ):

            event.ignore()

            self.hide()

            if not self._tray_hint_shown:

                self.tray_icon.showMessage(
                    "WeintCompanion",
                    "Läuft im Hintergrund weiter - über das "
                    "Tray-Symbol wieder öffnen.",
                    QSystemTrayIcon.Information,
                    3000,
                )

                self._tray_hint_shown = True

            return

        self._shutdown_services()

        super().closeEvent(event)
