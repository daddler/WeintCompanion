VERSION = "0.8.7"


def parse_version(value):
    """
    Zerlegt eine Versionsangabe in ein Zahlen-Tupel, fehlende Teile
    werden mit 0 aufgefüllt - "0.8" und "0.8.0" ergeben so denselben
    Wert (0, 8, 0). Ohne das würden GitHub-Tags wie "v0.8" (statt
    "v0.8.0") beim reinen String-Vergleich als andere Version gelten
    und fälschlich ein "Update verfügbar" bzw. "Changelog nicht
    gefunden" auslösen.
    """

    value = (
        (value or "")
        .strip()
        .lower()
        .removeprefix("v")
    )

    numbers = []

    for part in value.split("."):

        digits = ""

        for char in part:

            if char.isdigit():
                digits += char
            else:
                break

        numbers.append(
            int(digits) if digits else 0
        )

    while len(numbers) < 3:
        numbers.append(0)

    return tuple(numbers)


def versions_equal(a, b):

    return parse_version(a) == parse_version(b)
