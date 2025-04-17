#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import os

# --- Konfiguration ---

# Quelle der Tracker-Daten
SOURCE_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/refs/heads/main/web/v6/extension-mv3-tds.json"

# Name der Ausgabe-Filterlistendatei
OUTPUT_FILE = "brave-custom-filter.txt"

# Maximale Anzahl automatisch zu generierender Domains (zusätzlich zu den manuellen)
NUM_DOMAINS = 200

# Kategorien, die von der automatischen Generierung ausgeschlossen werden sollen
# (Basierend auf Kategorien in der extension-mv3-tds.json)
# Beispiele: "CDN", "Analytics", "Advertising", "Social Network", "Customer Interaction" etc.
# Passe diese Liste nach Bedarf an. Eine leere Liste schließt keine Kategorien aus.
# Wir starten mal konservativ und schließen nur CDNs aus, die oft für Funktionalität gebraucht werden.
EXCLUDED_CATEGORIES = [
    "CDN",
    # Füge hier weitere Kategorien hinzu, die du ausschließen möchtest, z.B.:
    # "Embedded Content", # Kann manchmal Seiten beschädigen
    # "Online Payment", # Vorsicht bei Zahlungsanbietern
]

# Manuell definierte Regeln (wird immer am Anfang der Liste eingefügt)
# Exakt kopiert aus deinem ursprünglichen Beispiel
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
        response = requests.get(url, timeout=20) # Timeout erhöht
        response.raise_for_status() # Prüft auf HTTP-Fehler
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

def generate_filter_list(tds_data, manual_rules, excluded_categories, num_domains):
    """Generiert den Inhalt der Filterliste."""
    if not tds_data or 'trackers' not in tds_data:
        print("Error: Invalid or missing tracker data.")
        return None

    generated_domains = set()
    print(f"Processing trackers. Excluding categories: {excluded_categories}")

    # Gehe durch die Tracker-Domains im TDS-Datensatz
    for domain, tracker_info in tds_data.get('trackers', {}).items():
        if len(generated_domains) >= num_domains:
            print(f"Reached target number of {num_domains} domains.")
            break

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

    print(f"Collected {len(generated_domains)} domains for automatic rules.")

    # Konvertiere Domains in ABP-Regeln und sortiere sie alphabetisch
    generated_rules = sorted([f"||{domain}^" for domain in generated_domains])

    # Erstelle den Header
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""! Title: Custom Brave Filter List (Prioritized from DDG TDS)
! Description: Automatically generated list of ~{len(generated_rules)} tracking/ad domains based on DuckDuckGo TDS (extension-mv3-tds.json structure). Prioritized by selecting top eligible entries. Excludes categories: {', '.join(excluded_categories) if excluded_categories else 'None'}.
! Source: {SOURCE_URL} (structure based on TDS)
! Updated: {now}
! Domain Count (automatically generated): {len(generated_rules)}
!
! WARNING: Use at your own risk. While efforts were made to avoid breaking sites, some breakage is always possible with filter lists.
!-------------------------------------------------------------------
"""

    # Kombiniere Header, manuelle Regeln und generierte Regeln
    # Füge Leerzeilen zur besseren Lesbarkeit ein
    full_list_content = header + "\n" + \
                        "\n".join(MANUAL_RULES) + "\n\n" + \
                        f"! --- Automatically generated rules (Top {len(generated_rules)} prioritized, excluding certain categories) ---\n" + \
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
    print("Starting filter list generation...")

    # 1. Daten holen
    tds_data = fetch_tds_data(SOURCE_URL)
    if not tds_data:
        print("Failed to fetch tracker data. Exiting.")
        return # Beenden, wenn Daten nicht geladen werden können

    # 2. Filterliste generieren
    filter_content = generate_filter_list(tds_data, MANUAL_RULES, EXCLUDED_CATEGORIES, NUM_DOMAINS)
    if not filter_content:
        print("Failed to generate filter list content. Exiting.")
        return # Beenden bei Fehler

    # 3. Filterliste in Datei schreiben
    write_filter_list(filter_content, OUTPUT_FILE)

    print("Filter list generation finished.")

# --- Skriptausführung ---

if __name__ == "__main__":
    main()
