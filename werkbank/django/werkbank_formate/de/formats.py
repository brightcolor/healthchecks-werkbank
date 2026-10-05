"""Deutsche Zahlenformate für Healthchecks mit Dezimalpunkt.

Skripte von Healthchecks lesen Zahlen aus den Seiten, etwa den Zeitstempel im Log für
Live-Updates. Für Datum und Uhrzeit nimmt Django seine deutschen Vorgaben.
"""

DECIMAL_SEPARATOR = "."
THOUSAND_SEPARATOR = ""
NUMBER_GROUPING = 0
