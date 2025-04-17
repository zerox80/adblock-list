#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import os

# --- Konfiguration ---

# Quelle der Tracker-Daten
SOURCE_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/refs/heads/main/web/v6/extension-mv3-tds.json"

# Name der Ausgabe-Filterlistendatei
OUTPUT_FILE = "brave-custom-filter_max.txt" # Geänderter Name zur Unterscheidung

# Maximale Anzahl automatisch zu generierender Domains --> ENTFERNT / NICHT MEHR RELEVANT
# NUM_DOMAINS = 200 # Auskommentiert/Entfernt, da wir das Maximum wollen

# Kategorien, die von der automatischen Generierung ausgeschlossen werden sollen
# (Basierend auf Kategorien in der extension-mv3-tds.json)
EXCLUDED_CATEGORIES = [
    "CDN",
]

# Manuell definierte Regeln (wird immer am Anfang der Liste eingefügt)
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

# --- Hilfsfunktionen ---

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
    """Generiert den Inhalt der Filterliste (maximale Anzahl)."""
    if not tds_data or 'trackers' not in tds_data:
        print("Error: Invalid or missing tracker data.")
        return None

    generated_domains = set()
    print(f"Processing trackers. Excluding categories: {excluded_categories}")
    # print(f"Targeting approximately {num_domains} automatically generated domains.") # Entfernt

    # Gehe durch die Tracker-Domains im TDS-Datensatz
    for domain, tracker_info in tds_data.get('trackers', {}).items():

        # --- BEGRENZUNGSBLOCK WURDE HIER ENTFERNT ---
        # if len(generated_domains) >= num_domains:
        #     print(f"Reached target number of {num_domains} domains.")
        #     break
        # --- ENDE DER ENTFERNTEN BEGRENZUNG ---

        # Überspringe Domains ohne Info oder Domain-Namen (sollte nicht vorkommen)
        if not tracker_info or not domain:
            continue

        # Prüfe auf ausgeschlossene Kategorien
        categories = tracker_info.get('categories', [])
        if any(cat in excluded_categories for cat in categories):
            # print(f"Skipping {domain} due to excluded category: {categories}")
            continue

        # Füge die Domain zur Liste hinzu (Set verhindert Duplikate)
        generated_domains.add(domain)

    # Meldung nach der Schleife (gibt immer die Gesamtzahl aus)
    print(f"Collected {len(generated_domains)} domains for automatic rules (maximum possible with current exclusions).")

    # Konvertiere Domains in ABP-Regeln und sortiere sie alphabetisch
    generated_rules = sorted([f"||{domain}^" for domain in generated_domains])

    # Erstelle den Header
    actual_generated_count = len(generated_rules)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header angepasst: Kein Target mehr erwähnt
    header = f"""! Title: Custom Brave Filter List (Maximal, Prioritized from DDG TDS)
! Description: Automatically generated list of {actual_generated_count} tracking/ad domains based on DuckDuckGo TDS (extension-mv3-tds.json structure). Includes all eligible entries. Excludes categories: {', '.join(excluded_categories) if excluded_categories else 'None'}.
! Source: {SOURCE_URL} (structure based on TDS)
! Updated: {now}
! Domain Count (automatically generated): {actual_generated_count}
!
! WARNING: Use at your own risk. While efforts were made to avoid breaking sites, some breakage is always possible with filter lists, especially larger ones.
!-------------------------------------------------------------------
"""

    # Kombiniere Header, manuelle Regeln und generierte Regeln
    full_list_content = header + "\n" + \
                        "\n".join(MANUAL_RULES) + "\n\n" + \
                        f"! --- Automatically generated rules (All {actual_generated_count} eligible domains found, excluding certain categories) ---\n" + \
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
    print("Starting filter list generation (maximum domains)...") # Angepasst

    # 1. Daten holen
    tds_data = fetch_tds_data(SOURCE_URL)
    if not tds_data:
        print("Failed to fetch tracker data. Exiting.")
        return

    # 2. Filterliste generieren (OHNE num_domains)
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
