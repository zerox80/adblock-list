#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import os

# --- Konfiguration ---

# Quelle der Tracker-Daten
SOURCE_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/refs/heads/main/web/v6/extension-mv3-tds.json"

# Name der Ausgabe-Filterlistendatei
OUTPUT_FILE = "brave-custom-filter_safe.txt" # Neuer Name für die "sicherere" Liste

# Kategorien, die von der automatischen Generierung ausgeschlossen werden sollen
# <<< HIER WERDEN MEHR KATEGORIEN AUSGESCHLOSSEN, UM KOMPATIBILITÄT ZU ERHÖHEN >>>
EXCLUDED_CATEGORIES = [
    "CDN",
    "Customer Interaction", # Chat-Widgets, Support-Systeme etc.
    "Embedded Content",     # Eingebettete Inhalte, Widgets etc.
    "Social Network",       # Soziale Widgets, Logins etc. (zusätzlich zu manuellen Regeln)
    "Online Payment",       # Zahlungsanbieter
    # "Analytics",          # Sehr viele Tracker, aber manchmal für Seiten wichtig? -> Vorerst NICHT ausgeschlossen
    # "Essential",          # Falls diese Kategorie existiert
]

# Manuell definierte Regeln (bleiben unverändert)
MANUAL_RULES = """
! --- Manually added rules for major platforms (blocking off-site tracking) ---
||connect.facebook.net^
||facebook.com^$domain=~facebook.com|~fb.com|~fbcdn.net|~messenger.com|~instagram.com|~whatsapp.com
||google-analytics.com^
||analytics.google.com^
||adservice.google.com^
||googletagmanager.com^
||googlesyndication.com^
||doubleclick.net^
||googleadservices.com^
||google.com/ads^
||google.com/pagead^
||youtube.com/api/stats/atr^^
||youtube.com/api/stats/playback^^
||youtube.com/api/stats/watchtime^^
||ads.linkedin.com^
||linkedin.com/li/track^
||linkedin.com^$domain=~linkedin.com|~licdn.com
||platform.twitter.com^
||ads-twitter.com^
||twitter.com^$domain=~twitter.com|~twimg.com
||ads.pinterest.com^
||pinterest.com^$domain=~pinterest.com|~pinimg.com
||bat.bing.com^
||ads.microsoft.com^
""".strip().split('\n') # Als Liste von Strings speichern

# --- Hilfsfunktionen --- (Keine Änderungen hier nötig)

def fetch_tds_data(url):
    """Lädt die TDS JSON-Daten von der angegebenen URL."""
    try:
        print(f"Fetching tracker data from URL: {url}...")
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        print("Tracker data downloaded successfully.")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Error: Timeout while fetching data from {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON data from response.")
        return None

# Funktion OHNE num_domains Parameter
def generate_filter_list(tds_data, manual_rules, excluded_categories):
    """Generiert den Inhalt der Filterliste (maximale Anzahl nach Ausschlüssen)."""
    if not tds_data or 'trackers' not in tds_data:
        print("Error: Invalid or missing tracker data.")
        return None

    generated_domains = set()
    excluded_categories_set = set(excluded_categories) # Effizienter für Abfragen
    print(f"Processing trackers. Excluding categories: {', '.join(excluded_categories) if excluded_categories else 'None'}")

    # Gehe durch die Tracker-Domains im TDS-Datensatz
    for domain, tracker_info in tds_data.get('trackers', {}).items():
        # Überspringe Domains ohne Info oder Domain-Namen
        if not tracker_info or not domain:
            continue

        # Prüfe auf ausgeschlossene Kategorien
        categories = tracker_info.get('categories', [])
        if not excluded_categories_set.isdisjoint(categories): # Prüft auf Überschneidung
            # print(f"Skipping {domain} due to excluded category: {set(categories).intersection(excluded_categories_set)}")
            continue

        # Füge die Domain zur Liste hinzu
        generated_domains.add(domain)

    print(f"Collected {len(generated_domains)} domains for automatic rules (maximum possible with current exclusions).")

    # Konvertiere Domains in ABP-Regeln und sortiere sie alphabetisch
    generated_rules = sorted([f"||{domain}^" for domain in generated_domains])

    # Erstelle den Header
    actual_generated_count = len(generated_rules)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""! Title: Custom Brave Filter List (Safe, Prioritized from DDG TDS)
! Description: Automatically generated list of {actual_generated_count} tracking/ad domains based on DuckDuckGo TDS. Includes all eligible entries after EXCLUDING potentially problematic categories for better compatibility.
! Excluded Categories: {', '.join(excluded_categories) if excluded_categories else 'None'}.
! Source: {SOURCE_URL} (structure based on TDS)
! Updated: {now}
! Domain Count (automatically generated): {actual_generated_count}
!
! WARNING: Use at your own risk. While efforts were made to increase compatibility by excluding more categories, some breakage might still occur. This list blocks less than the 'maximal' version.
!-------------------------------------------------------------------
"""

    # Kombiniere Header, manuelle Regeln und generierte Regeln
    full_list_content = header + "\n" + \
                        "\n".join(MANUAL_RULES) + "\n\n" + \
                        f"! --- Automatically generated rules (All {actual_generated_count} eligible domains found, excluding specified categories) ---\n" + \
                        "\n".join(generated_rules)

    return full_list_content

def write_filter_list(content, filename):
    """Schreibt den Inhalt in die angegebene Datei."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully wrote filter list to: {os.path.abspath(filename)}")
        return True
    except IOError as e:
        print(f"Error writing filter list to file {filename}: {e}")
        return False

# --- Hauptlogik ---

def main():
    """Hauptfunktion des Skripts."""
    print("Starting filter list generation (safe version, excluding more categories)...")

    # 1. Daten holen
    tds_data = fetch_tds_data(SOURCE_URL)
    if not tds_data:
        print("Failed to fetch tracker data. Exiting.")
        return

    # 2. Filterliste generieren
    filter_content = generate_filter_list(tds_data, MANUAL_RULES, EXCLUDED_CATEGORIES)
    if not filter_content:
        print("Failed to generate filter list content. Exiting.")
        return

    # 3. Filterliste in Datei schreiben
    write_filter_list(filter_content, OUTPUT_FILE)

    print("Filter list generation finished.")

# --- Skriptausführung ---

if __name__ == "__main__":
    main()
