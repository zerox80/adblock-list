import requests
import json
from datetime import datetime
# import operator # Nicht mehr benötigt
# import re # Nicht mehr benötigt

# --- Konfiguration ---
TARGET_COUNT = 200  # Ungefähre Anzahl der gewünschten Domains (wird jetzt wieder verwendet!)
OUTPUT_FILENAME = "brave_custom_filter_ddg_prioritized.txt" # Name angepasst
# *** Verwendet die NEUE URL / Datei mit vollen TDS-Daten ***
TRACKER_DATA_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/refs/heads/main/web/v6/extension-mv3-tds.json"
INPUT_FILENAME = "extension-mv3-tds.json" # <- Name der hochgeladenen Datei

# Kategorien, die wir priorisieren wollen (Groß-/Kleinschreibung wird ignoriert)
PRIORITY_CATEGORIES = [
    "Advertising",
    "Analytics",
    "Audience Measurement",
    "Marketing",
    "Third-Party Analytics",
    "Social Network",
    "Customer Interaction",
    # Weniger kritische hinzufügen, falls mehr benötigt wird
    "Embedded Content",
    "Online Payment",
    "Obscure",
    "CDN", # Normalerweise nicht blockieren, aber zur Vollständigkeit
]

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
    "googletagmanager.com", # GTM ist oft problematisch, wird aber oft als Tracker gelistet
    "ytimg.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "reddit.com",
    "tiktok.com",
    "twitter.com",
    "whatsapp.com",
    "whatsapp.net",
    "messenger.com",
    "facebook.com",
    "google.com", # Die Hauptdomains nur blockieren, wenn unbedingt nötig
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
        # Stellt sicher, dass der substring einen Punkt enthält, um TLDs auszuschließen
        if '.' in sub_lower and (domain_lower == sub_lower or domain_lower.endswith('.' + sub_lower)):
             # print(f"Skipping '{domain}' because it matches or ends with specific excluded domain '{sub_lower}'")
             return True

        # Prüft auf generische Substrings (wie 'akamai'), aber nur, wenn kein Punkt enthalten ist
        if '.' not in sub_lower and sub_lower in domain_lower:
             # print(f"Skipping '{domain}' because it contains generic excluded substring '{sub_lower}'")
             return True
    return False

def get_category_priority(categories):
    """Gibt einen Prioritätsscore basierend auf den Kategorien zurück. Höher ist besser."""
    if not categories:
        return 0
    prio = 99 # Startwert für niedrige Priorität
    for cat in categories:
        cat_lower = cat.lower()
        for i, prio_cat in enumerate(PRIORITY_CATEGORIES):
            if prio_cat.lower() == cat_lower:
                prio = min(prio, i) # Niedrigster Index (höchste Priorität in der Liste) zählt
                break # Sobald eine Übereinstimmung gefunden wurde
    # Wenn eine Prioritätskategorie gefunden wurde (prio < 99)
    if prio < 99:
        # Höherer Score für Kategorien weiter oben in der Liste
        return len(PRIORITY_CATEGORIES) - prio
    return 0 # Keine der Prioritätskategorien gefunden

# --- Hauptlogik ---
print(f"Loading tracker data from local file: {INPUT_FILENAME}...")
data = {}
try:
    # Lese die lokale Datei, die du hochgeladen hast
    with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Zugriff auf die Tracker-Daten unter dem Schlüssel 'trackers'
    trackers = data.get('trackers', {})
    if not isinstance(trackers, dict):
        print("Error: 'trackers' key found, but its value is not a dictionary.")
        exit(1)

    print(f"Successfully loaded and parsed data. Found {len(trackers)} tracker entries.")
except FileNotFoundError:
    print(f"Error: Input file '{INPUT_FILENAME}' not found.")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Error parsing JSON data from file '{INPUT_FILENAME}': {e}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred while reading the file: {e}")
    exit(1)

if not trackers:
    print("No tracker data found under the 'trackers' key in the JSON file.")
    exit(1)

print("Processing tracker entries...")
domain_data = []

# Iteriere durch die Tracker-Einträge (Schlüssel sind oft Domains/Bezeichner)
for tracker_key, entity_data in trackers.items():
    # Manchmal ist die 'domain' explizit angegeben, sonst den Schlüssel verwenden
    primary_domain = entity_data.get('domain', tracker_key)

    # Sammle alle relevanten Domains für diese Entität
    candidate_domains = set()
    if primary_domain and '.' in primary_domain:
         candidate_domains.add(primary_domain)

    # Es gibt keine explizite 'domains'-Liste in dieser Struktur,
    # aber wir müssen Domains aus 'rules' extrahieren
    rules = entity_data.get('rules', [])
    default_action = entity_data.get('default', 'ignore')
    should_block_entity = default_action == 'block'

    temp_rule_domains = set()
    for rule_entry in rules:
         rule_domain_pattern = rule_entry.get('rule')
         rule_action = rule_entry.get('action', default_action)

         if rule_action == 'block':
             should_block_entity = True # Wenn irgendeine Regel blockt, ist die Entität relevant

         # Versuche, eine saubere Domain aus dem Regel-Pattern zu extrahieren
         # Dies ist eine Vereinfachung: Regex-Patterns können komplex sein
         if rule_domain_pattern:
             # Entferne Regex-Zeichen am Anfang/Ende und Pfade
             # Beispiel: "||example\\.com^" -> "example.com"
             # Beispiel: "sub\\.example\\.com\\/path" -> "sub.example.com"
             cleaned_domain = rule_domain_pattern.replace('\\.', '.').replace('\\/', '/')
             # Entferne häufige Adblock-Syntax-Zeichen
             cleaned_domain = cleaned_domain.lstrip('|').lstrip('.').rstrip('^')
             # Finde den Domain-Teil (bis zum ersten '/')
             domain_part = cleaned_domain.split('/')[0]
             # Einfache Prüfung, ob es wie eine Domain aussieht
             if '.' in domain_part and not any(c in domain_part for c in ['*', '?', '[', '(', ')', '+', '{', '}']):
                 temp_rule_domains.add(domain_part)

    # Füge die extrahierten Regel-Domains hinzu
    candidate_domains.update(temp_rule_domains)

    # Wenn weder Standard noch irgendeine Regel 'block' ist, überspringe die Entität
    if not should_block_entity:
        continue

    # Extrahiere die relevanten Daten für die Priorisierung
    owner_info = entity_data.get('owner', {})
    owner = owner_info.get('name', tracker_key) # Fallback auf tracker_key
    categories = entity_data.get('categories', [])
    # 'prevalence' ist manchmal sehr klein, multiplizieren mit 100 für bessere Lesbarkeit/Vergleichbarkeit
    prevalence = entity_data.get('prevalence', 0.0) * 100
    priority_score = get_category_priority(categories)

    # Verarbeite und filtere alle Kandidaten-Domains für diese Entität
    for domain in candidate_domains:
        if not is_domain_allowed(domain):
            domain_data.append({
                'domain': domain,
                'prevalence': prevalence,
                'priority': priority_score,
                'categories': categories,
                'owner': owner
            })

# --- Deduplizierung und Sortierung ---
# Duplikate entfernen (eine Domain kann von mehreren Entitäten/Regeln kommen)
# Bevorzuge den Eintrag mit höherer Priorität, dann höherer Prävalenz
unique_domains = {}
for item in domain_data:
    domain = item['domain']
    if domain not in unique_domains or \
       (item['priority'] > unique_domains[domain]['priority']) or \
       (item['priority'] == unique_domains[domain]['priority'] and item['prevalence'] > unique_domains[domain]['prevalence']):
        unique_domains[domain] = item

# Sortieren nach Priorität (höchste zuerst), dann Prävalenz (höchste zuerst)
sorted_domains = sorted(unique_domains.values(),
                        key=lambda x: (x['priority'], x['prevalence']),
                        reverse=True)

print(f"Found {len(sorted_domains)} potential domains after processing and filtering.")

# Top N auswählen
top_domains = sorted_domains[:TARGET_COUNT]

print(f"Selected top {len(top_domains)} domains based on priority and prevalence for the filter list.")

# --- Filterliste generieren ---
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") # Zeitzone hinzugefügt
# Header angepasst, um die Priorisierung zu erwähnen
header = f"""! Title: Custom Brave Filter List (Prioritized from DDG TDS)
! Description: Automatically generated list of ~{TARGET_COUNT} tracking/ad domains based on DuckDuckGo TDS ({INPUT_FILENAME} structure). Prioritized by category and prevalence. Excludes known CDNs and potential site breakers.
! Source: {INPUT_FILENAME} (structure from {TRACKER_DATA_URL})
! Updated: {current_time}
! Domain Count: {len(top_domains)}
!
! WARNING: Use at your own risk. While efforts were made to avoid breaking sites, some breakage is always possible with filter lists.
!-------------------------------------------------------------------\n
"""

filter_lines = []
for item in top_domains:
    # Stelle sicher, dass nur gültige Domains hinzugefügt werden
    if isinstance(item.get('domain'), str) and '.' in item.get('domain'):
        filter_lines.append(f"||{item['domain']}^")
    else:
         print(f"Skipping invalid entry during output generation: {item.get('domain')}")


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
output_content = header + manual_rules + "\n! --- Automatically generated rules (Top {len(top_domains)} prioritized) ---\n" + "\n".join(filter_lines)

# --- In Datei schreiben ---
try:
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(output_content)
    print(f"\nSuccessfully wrote {len(filter_lines)} prioritized rules (+ manual rules) to '{OUTPUT_FILENAME}'")
except IOError as e:
    print(f"\nError writing to file '{OUTPUT_FILENAME}': {e}")
