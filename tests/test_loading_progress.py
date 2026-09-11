"""
Der Fortschritt beim Holen eines Pulls.

Gemeldet wurde, dass beim Auswerten eines Logs nirgends steht, dass
man warten muss, wie lange es dauert und ab wann man weiterarbeiten
kann. Diese Datei sichert die drei Eigenschaften ab, ohne die die
Anzeige wieder zur Behauptung würde.
"""

from core import loading_progress as lp


# --------------------------------------------------
# Schätzung
# --------------------------------------------------


def test_a_longer_fight_gets_a_longer_estimate():
    """
    Der Bot liest den ganzen Ereignisstrom - ein
    Zwölf-Minuten-Garrosh kostet ihn ein Vielfaches eines
    Zwei-Minuten-Wipes. Eine feste Zahl wäre für den einen Fall
    Panikmache und für den anderen eine Lüge.
    """

    kurz = lp.estimate(120.0)

    lang = lp.estimate(720.0)

    assert lang > kurz


def test_the_estimate_stays_within_its_bounds():

    assert lp.estimate(0.0) >= lp.MIN_ESTIMATE

    assert lp.estimate(99_999.0) <= lp.MAX_ESTIMATE


def test_measurements_move_the_estimate():
    """
    Die Erfahrung mit dem eigenen Bot schlägt jede geratene
    Konstante.
    """

    ohne = lp.estimate(300.0)

    mit = lp.estimate(300.0, (200.0, 210.0, 205.0))

    assert mit > ohne


def test_a_single_measurement_does_not_take_over():
    """
    Eine einzelne Messung kann ein Ausreisser sein - etwa ein Abruf,
    der in einen Bot-Neustart lief.
    """

    ohne = lp.estimate(300.0)

    eine = lp.estimate(300.0, (lp.MAX_ESTIMATE,))

    viele = lp.estimate(300.0, (lp.MAX_ESTIMATE,) * 4)

    assert ohne < eine < viele


def test_nonsense_measurements_are_dropped():

    assert lp.blend((), -5.0) == ()

    assert lp.blend((), 10_000.0) == ()

    assert lp.blend((), 42.0) == (42.0,)


def test_only_the_last_measurements_count():

    gemessen = ()

    for value in range(1, 20):
        gemessen = lp.blend(gemessen, float(value))

    assert len(gemessen) == lp.MEMORY

    assert gemessen[-1] == 19.0


# --------------------------------------------------
# Balken
# --------------------------------------------------


def test_the_bar_never_reaches_the_end():
    """
    Ein Balken, der bei 100 % steht, während noch etwas läuft, ist
    die häufigste Lüge in Benutzeroberflächen überhaupt.
    """

    for elapsed in (0.0, 30.0, 60.0, 600.0, 6000.0):
        assert lp.share(elapsed, 60.0) < 1.0


def test_the_bar_only_ever_moves_forward():

    letzter = -1.0

    for elapsed in range(0, 600, 5):

        jetzt = lp.share(float(elapsed), 60.0)

        assert jetzt >= letzter

        letzter = jetzt


def test_without_an_estimate_the_bar_stays_empty():
    """
    Lieber ein leerer Balken als ein erfundener Stand - dieselbe
    Regel wie `stars == 0`.
    """

    assert lp.share(30.0, 0.0) == 0.0


# --------------------------------------------------
# Text
# --------------------------------------------------


def test_the_text_always_carries_a_moving_number():
    """
    Ohne eine Zahl, die sich bewegt, ist von aussen nicht zu
    unterscheiden, ob noch etwas läuft oder ob etwas hängt.
    """

    assert "12 s" in lp.progress_text(12.0, 60.0)

    assert "1:30 min" in lp.progress_text(90.0, 600.0)


def test_taking_longer_than_expected_is_said_out_loud():

    text = lp.progress_text(120.0, 60.0)

    assert lp.overdue(120.0, 60.0)

    assert "länger" in text

    assert "abbrechen" in text


def test_without_an_estimate_the_text_says_so_instead_of_guessing():

    text = lp.progress_text(20.0, 0.0)

    assert "nicht abschätzen" in text


def test_the_notes_answer_the_two_questions_that_were_missing():
    """
    Warum es dauert - und ab wann man weiterarbeiten kann. Beides
    stand bis 3.6.0 nirgends.
    """

    assert "WarcraftLogs" in lp.WHY_NOTE

    assert "von selbst" in lp.READY_NOTE
