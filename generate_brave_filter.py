import requests
import json
from datetime import datetime
# import operator # Nicht mehr benötigt
# import re # Nicht mehr benötigt

# --- Konfiguration ---
# TARGET_COUNT ist nicht mehr relevant für die Auswahl, da keine Priorisierung mehr stattfindet
# TARGET_COUNT = 200
OUTPUT_FILENAME = "brave_custom_filter_ddg_simple.txt" # Name angepasst, da Logik vereinfacht
# URL zur DuckDuckGo Tracker Data Set (TDS) JSON-Datei
# *** Verwendet die domain_map.json wie gewünscht ***
# Diese URL wird nur für die Dokumentation im Header verwendet, wenn die lokale Datei gelesen wird.
TRACKER_DATA_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-radar/main/build-data/generated/domain_map.json"
# Lokaler Dateipfad zur hochgeladenen Datei
INPUT_FILENAME = "domain_map.json" # <- Name der hochgeladenen Datei

# Manuelle Liste von Domains/Substrings, die *niemals* geblockt werden sollen (CDNs, essentielle Dienste)
KNOWN_GOOD_DOMAINS_SUBSTRINGS = [
    # Wichtige CDNs
    "akamai", "akamaized.net", "akamaitechnologies.com", "akstat.io",
    "amazonaws.com", "azureedge.net", "azurefd.net", "cloudfront.net",
    "cloudflare.com", "cloudflare.net", "cdnjs.cloudflare.com",
    "fastly.net", "fastly.com", "fbcdn.net", "gcore.com",
    "googleusercontent.com", "googlevideo.com", "gstatic.com",
    "googleapis.com", "ajax.googleapis.com", "fonts.googleapis.com",
    "hcaptcha.com", "jsdelivr.net", "licdn.com", "microsoft.com",
    "msecnd.net", "pinimg.com", "twimg.com", "unpkg.com",
    "vimeo.com", "vimeocdn.com", "wp.com", "wix.com", "zdassets.com",
    "zohopublic.com", "github.com", "github.io", "gitlab.com", "apple.com",
    "images-amazon.com", "ssl-images-amazon.com",
    # Recaptcha (als Ausnahme von google.com)
    "google.com/recaptcha",
    # Login / Identity Provider
    "accounts.google.com", "appleid.apple.com", "facebook.com/dialog/",
    "github.com/login", "login.microsoftonline.com", "okta.com", "onelogin.com",
    # Payment Gateways
    "paypal.com", "stripe.com", "braintreegateway.com", "adyen.com",
]

# Domains, die zwar tracken, aber deren Blockieren oft zu Problemen führt
POTENTIAL_BREAKERS = [
    "googletagmanager.com",
    # "youtube.com", # Vorsichtiger mit Substring-Ausschluss bei googleusercontent.com
    "ytimg.com", "instagram.com", "linkedin.com", "pinterest.com",
    "reddit.com", "tiktok.com", "twitter.com", "whatsapp.com",
    "whatsapp.net", "messenger.com", "facebook.com", "google.com",
]

# --- Hilfsfunktionen ---
def is_domain_allowed(domain):
    """Prüft, ob eine Domain aufgrund der Ausschlusslisten übersprungen werden soll."""
    if not domain: # Leere Domains überspringen
        return True
    domain_lower = domain.lower()
    # Kombiniere beide Ausschlusslisten für die Prüfung
    exclusion_list = KNOWN_GOOD_DOMAINS_SUBSTRINGS + POTENTIAL_BREAKERS
    for substring in exclusion_list:
        sub_lower = substring.lower()
        # Prüft auf exakte Übereinstimmung oder spezifische Pfade/Protokolle
        if sub_lower == domain_lower:
            # print(f"Skipping '{domain}' because it exactly matches excluded entry '{sub_lower}'")
            return True
        # Prüft komplexere Fälle wie 'google.com/recaptcha' in 'www.google.com/recaptcha/...'
        if '/' in sub_lower and sub_lower in domain_lower:
             # print(f"Skipping '{domain}' because it contains excluded path '{sub_lower}'")
             return True

        # Prüft, ob die Domain mit ".substring" endet (wenn substring selbst eine Domain ist)
        # ODER ob die Domain exakt dem Substring entspricht (erneut, falls Substring eine Domain ist)
        # Schließt aber den Fall aus, dass der Substring nur ein Teil ist (z.B. 'go' in 'google.com')
        # Stellt sicher, dass der substring einen Punkt enthält, um TLDs auszuschließen
        if '.' in sub_lower and (domain_lower == sub_lower or domain_lower.endswith('.' + sub_lower)):
             # print(f"Skipping '{domain}' because it matches or ends with specific excluded domain '{sub_lower}'")
             return True

        # Prüft auf generische Substrings (wie 'akamai'), aber nur, wenn kein Punkt enthalten ist
        # (um TLDs wie 'com' nicht fälschlich als Substring zu werten)
        if '.' not in sub_lower and sub_lower in domain_lower:
             # print(f"Skipping '{domain}' because it contains generic excluded substring '{sub_lower}'")
             return True
    return False

# --- Hauptlogik ---
print(f"Loading domain map from local file: {INPUT_FILENAME}...")
domain_map = {}
try:
    # Lese die lokale Datei, die du hochgeladen hast
    with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
        domain_map = json.load(f)

    if not isinstance(domain_map, dict):
        print("Error: Loaded data is not a dictionary (JSON map).")
        exit(1)
    print(f"Successfully loaded and parsed data. Found {len(domain_map)} domain entries in the map.")
except FileNotFoundError:
    print(f"Error: Input file '{INPUT_FILENAME}' not found.")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Error parsing JSON data from file '{INPUT_FILENAME}': {e}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred while reading the file: {e}")
    exit(1)

if not domain_map:
    print("No domain data found in the JSON file.")
    exit(1)

print("Processing domains from map...")
filtered_domains = set() # Verwende ein Set für automatische Deduplizierung

for domain, entity_info in domain_map.items():
    # Füge die Hauptdomain hinzu, wenn sie nicht ausgeschlossen ist
    if not is_domain_allowed(domain):
        filtered_domains.add(domain)

    # Füge auch Aliase hinzu, falls vorhanden und nicht ausgeschlossen
    # Stelle sicher, dass entity_info ein Dictionary ist, bevor auf 'aliases' zugegriffen wird
    if isinstance(entity_info, dict):
        aliases = entity_info.get('aliases', [])
        if isinstance(aliases, list):
            for alias_domain in aliases:
                 if not is_domain_allowed(alias_domain):
                     filtered_domains.add(alias_domain)
        # Es scheint keine 'domains'-Liste innerhalb der entity_info in domain_map.json zu geben
        # Konzentrieren wir uns auf den Schlüssel (die Domain) und ggf. 'aliases'

# Sortiere die Domains alphabetisch für konsistente Ausgabe
# Stelle sicher, dass None-Werte (falls irgendwie vorhanden) nicht zum Absturz führen
# Konvertiere alle Elemente sicherheitshalber zu Strings vor dem Sortieren
valid_strings_for_sorting = [str(d) for d in filtered_domains if d is not None]
sorted_filtered_domains = sorted(valid_strings_for_sorting)


print(f"Found {len(sorted_filtered_domains)} domains after filtering known good/breakers.")
# Hinweis: TARGET_COUNT wird nicht mehr verwendet, um die Liste zu kürzen.

# --- Filterliste generieren ---
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# Beschreibung im Header angepasst
header = f"""! Title: Custom Brave Filter List (Simplified from DDG Tracker Radar GitHub)
! Description: Automatically generated list based on domains found in DuckDuckGo's domain_map.json. Excludes known CDNs and potential site breakers. NO prioritization based on prevalence/category applied.
! Source: {INPUT_FILENAME} (processed from {TRACKER_DATA_URL} structure)
! Updated: {current_time}
! Domain Count: {len(sorted_filtered_domains)}
!
! WARNING: Use at your own risk. While efforts were made to avoid breaking sites, some breakage is always possible with filter lists. This list might be large and less targeted than prevalence-based lists.
!-------------------------------------------------------------------\n
"""

filter_lines = []
for domain in sorted_filtered_domains:
    # Extra Sicherheitscheck, um sicherzustellen, dass es ein gültiger Domain-String ist
    if isinstance(domain, str) and '.' in domain:
        filter_lines.append(f"||{domain}^")
    else:
        print(f"Skipping invalid entry during output generation: {domain}")


# Manuell hinzugefügte Regeln (bleiben bestehen)
manual_rules = """
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
"""

# Kombiniere Header, manuelle Regeln und generierte Liste
output_content = header + manual_rules + "\n! --- Automatically generated rules (from domain_map.json, filtered) ---\n" + "\n".join(filter_lines)

# --- In Datei schreiben ---
try:
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(output_content)
    # Ausgabe-Log angepasst
    print(f"\nSuccessfully wrote {len(filter_lines)} automatically generated rules (+ manual rules) to '{OUTPUT_FILENAME}'")
except IOError as e:
    print(f"\nError writing to file '{OUTPUT_FILENAME}': {e}")
