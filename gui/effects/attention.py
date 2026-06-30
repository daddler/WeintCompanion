class AttentionEffect:

    def __init__(self, widget):

        self.widget = widget

    # --------------------------------------------------

    def hover(self):

        #
        # Hover nur, wenn keine Warnung oder Fehler aktiv ist
        #

        if getattr(self.widget, "_state", "normal") != "normal":
            return

        self.widget.update_style(
            hover=True
        )

    # --------------------------------------------------

    def normal(self):

        #
        # Hover wieder entfernen
        #

        self.widget.update_style(
            hover=False
        )