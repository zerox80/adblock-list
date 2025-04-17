# Brave Filter List Generator (from DDG TDS)

## Beschreibung

Dieses Python-Skript generiert automatisch eine benutzerdefinierte, Adblock Plus (ABP)-kompatible Filterliste für Webbrowser wie Brave. Die Liste basiert auf den Daten des DuckDuckGo Tracker Radar (TDS) und konzentriert sich auf die häufigsten Tracking- und Werbedomains.

## Zweck und Motivation

Das Ziel dieses Skripts ist es, eine relativ kleine (ca. 200 Einträge), aber effektive Filterliste zu erstellen. Sie fokussiert sich auf die am weitesten verbreiteten Tracker, die von DuckDuckGo identifiziert wurden. Dies soll einen soliden Grundschutz der Privatsphäre bieten, potenziell mit weniger Ressourcenverbrauch und einem geringeren Risiko, Webseiten zu beeinträchtigen ("Site Breakage"), als massive, umfassende Blocklisten. Die Liste enthält zusätzlich wichtige manuelle Regeln für große Plattformen.

## Funktionsweise

Das Skript führt die folgenden Schritte aus:

1.  **Daten abrufen:** Lädt die aktuellste `extension-mv3-tds.json`-Datei von der angegebenen DuckDuckGo GitHub-URL herunter.
    * Quelle: `https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/refs/heads/main/web/v6/extension-mv3-tds.json`
2.  **Daten parsen:** Extrahiert Tracker-Domains und zugehörige Informationen (wie Kategorien, Verbreitungshinweise etc.) aus der JSON-Struktur.
3.  **Filtern & Priorisieren:**
    * Filtert Einträge heraus, die keine Tracker oder Werbenetzwerke sind (basierend auf Kategorien oder anderen Flags in den TDS-Daten – *Details ggf. im Code anpassen*).
    * **Schließt Domains aus**, die als Content Delivery Networks (CDNs) bekannt sind oder wahrscheinlich Webseiten beschädigen könnten. Diese Ausschlüsse sind üblicherweise in Listen (`EXCLUSION_LIST_CDN`, `EXCLUSION_LIST_BREAKAGE`) im Skript definiert.
    * **Ordnet** die verbleibenden Domains basierend auf ihrer Verbreitung ("Prevalence"). Die genaue Metrik dafür wird aus den TDS-Daten abgeleitet (*Details ggf. im Code prüfen/anpassen*).
    * Wählt die **Top-N** (z. B. 200, konfigurierbar über `NUM_DOMAINS`) Domains aus der priorisierten Liste aus.
4.  **Regeln generieren:**
    * Formatiert die ausgewählten Domains in die Adblock Plus Filter-Syntax (z. B. `||domain.com^`).
    * Fügt eine vordefinierte Liste **manueller Regeln** (gespeichert in `MANUAL_RULES`) am Anfang der Liste ein (z. B. für Facebook, Google Analytics mit spezifischen Ausnahmen).
    * Erstellt einen Standard-**Header** (Titel, Beschreibung, Quelle, Zeitstempel, Domainanzahl, Warnung) für die Filterliste.
5.  **Ausgabe schreiben:** Speichert die vollständige Filterliste in der angegebenen Ausgabedatei (z. B. `brave-custom-filter.txt`, konfigurierbar über `OUTPUT_FILE`).

## Abhängigkeiten

* Python 3.x
* Die `requests`-Bibliothek zum Herunterladen der Daten. Installieren mit:
    ```bash
    pip install requests
    ```
* Eine aktive Internetverbindung zum Abrufen der DDG TDS-Daten.

## Konfiguration (im Skript anpassen)

Die folgenden Variablen können normalerweise direkt am Anfang des Python-Skripts angepasst werden:

* `SOURCE_URL`: URL zur DDG TDS `extension-mv3-tds.json`.
* `OUTPUT_FILE`: Dateiname für die generierte Filterliste (z. B. `'brave-custom-filter.txt'`).
* `NUM_DOMAINS`: Die gewünschte Anzahl automatisch generierter Domains (z. B. `200`).
* `MANUAL_RULES`: Eine Python-Liste oder der Pfad zu einer Datei, die die manuell hinzuzufügenden Regeln enthält.
* `EXCLUSION_LIST_CDN`: Eine Python-Liste mit Domains/Mustern, die als CDN ausgeschlossen werden sollen.
* `EXCLUSION_LIST_BREAKAGE`: Eine Python-Liste mit Domains/Mustern, die als potenzielle "Site Breaker" ausgeschlossen werden sollen.

## Benutzung

Führe das Skript einfach über die Kommandozeile aus:

```bash
python dein_skript_name.py
