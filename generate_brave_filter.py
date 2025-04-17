import requests
import json
from datetime import datetime
import operator
import re

# --- Konfiguration ---
TARGET_COUNT = 200  # Ungefähre Anzahl der gewünschten Domains
OUTPUT_FILENAME = "brave_custom_filter_ddg.txt"
# URL zur DuckDuckGo Tracker Data Set (TDS) JSON-Datei
# *** NEUE URL: Verwendet die Rohdaten direkt von GitHub ***
TRACKER_DATA_URL = "https://raw.githubusercontent.com/duckduckgo/tracker-radar/refs/heads/main/build-data/generated/domain_map.json"

# Kategorien, die wir priorisieren wollen (Groß-/Kleinschreibung wird ignoriert)
# Siehe: https://github.com/duckduckgo/tracker-radar/blob/main/docs/CATEGORIES.md
PRIORITY_CATEGORIES = [
    "Advertising",
    "Analytics",
    "Audience Measurement",
    "Marketing",
    "Third-Party Analytics",
    "Social Network",
    "Customer Interaction",
]

# Manuelle Liste von Domains/Substrings, die *niemals* geblockt werden sollen (CDNs, essentielle Dienste)
KNOWN_GOOD_DOMAINS_SUBSTRINGS = [
    # Wichtige CDNs
    "akamai",
    "akamaized.net",
    "akamaitechnologies.com",
    "akstat.io",
    "amazonaws.com",
    "azureedge.net",
    "azurefd.net",
    "cloudfront.net",
    "cloudflare.com",
    "cloudflare.net",
    "cdnjs.cloudflare.com",
    "fastly.net",
    "fastly.com",
    "fbcdn.net",
    "gcore.com",
    "googleusercontent.com",
    "googlevideo.com",
    "gstatic.com",
    "googleapis.com",
    "ajax.googleapis.com",
    "fonts.googleapis.com",
    "google.com/recaptcha",
    "hcaptcha.com",
    "jsdelivr.net",
    "licdn.com",
    "microsoft.com",
    "msecnd.net",
    "pinimg.com",
    "twimg.com",
    "unpkg.com",
    "vimeo.com",
    "vimeocdn.com",
    "wp.com",
    "wix.com",
    "zdassets.com",
    "zohopublic.com",
    "github.com",
    "github.io",
    "gitlab.com",
    "apple.com",
    "images-amazon.com",
    "ssl-images-amazon.com",
    # Login / Identity Provider
    "accounts.google.com",
    "appleid.apple.com",
    "facebook.com/dialog/",
    "github.com/login",
    "login.microsoftonline.com",
    "okta.com",
    "onelogin.com",
    # Payment Gateways
    "paypal.com",
    "stripe.com",
    "braintreegateway.com",
    "adyen.com",
]

# Domains, die zwar tracken, aber deren Blockieren oft zu Problemen führt
POTENTIAL_BREAKERS = [
    "googletagmanager.com",
    "youtube.com", # Diese spezifische URL wird oft für Tracking verwendet
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
    "google.com",
]

# --- Hilfsfunktionen ---
def is_domain_allowed(domain):
    """Prüft, ob eine Domain aufgrund der Ausschlusslisten übersprungen werden soll."""
    domain_lower = domain.lower()
    # Kombiniere beide Ausschlusslisten für die Prüfung
    exclusion_list = KNOWN_GOOD_DOMAINS_SUBSTRINGS + POTENTIAL_BREAKERS
    for substring in exclusion_list:
        # Prüft, ob der Domainname exakt einem Eintrag entspricht
        if domain_lower == substring:
            # print(f"Skipping '{domain}' because it exactly matches excluded entry '{substring}'")
            return True
        # Prüft, ob die Domain mit ".substring" endet (z.B. maps.google.com endet nicht mit .google.com, aber google.com schon)
        # Dies vermeidet das fälschliche Ausschließen von Subdomains, wenn nur die Hauptdomain ausgeschlossen werden soll.
        # Es sei denn, der Eintrag in der Ausschlussliste ist bereits eine Subdomain (z.B. zdassets.com)
        if '.' in substring: # Eintrag ist wahrscheinlich spezifisch
             if domain_lower == substring or domain_lower.endswith('.' + substring):
                 # print(f"Skipping '{domain}' because it matches or ends with specific excluded entry '{substring}'")
                 return True
        # Prüft, ob der Domainname einen Eintrag als *Bestandteil* enthält (vorsichtig verwenden!)
        # Hilfreich für 'akamai' in 'sub.akamai.net'
        elif substring in domain_lower:
             # print(f"Skipping '{domain}' because it contains excluded substring '{substring}'")
             return True # Behalte diese Prüfung für generische Begriffe wie 'akamai'
    return False


def get_category_priority(categories):
    """Gibt einen Prioritätsscore basierend auf den Kategorien zurück."""
    if not categories:
        return 0
    prio = 99
    for cat in categories:
        cat_lower = cat.lower()
        for i, prio_cat in enumerate(PRIORITY_CATEGORIES):
            if prio_cat.lower() == cat_lower:
                prio = min(prio, i)
                break
    if prio < 99:
        return len(PRIORITY_CATEGORIES) - prio
    return 0

# --- Hauptlogik ---
print(f"Fetching tracker data from {TRACKER_DATA_URL}...")
trackers = {}
try:
    # Hinzufügen eines User-Agent Headers kann manchmal helfen, Blockaden zu umgehen
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(TRACKER_DATA_URL, timeout=30, headers=headers)
    response.raise_for_status()
    data = response.json()
    # Die Struktur in tds.json ist etwas anders: 'trackers' enthält die Entitäten
    trackers = data.get('trackers', {})
    print(f"Successfully fetched and parsed data. Found {len(trackers)} tracker entities.")
except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Error parsing JSON data: {e}")
    exit(1)

if not trackers:
    print("No tracker data found in the JSON response.")
    exit(1)

print("Processing tracker domains...")
domain_data = []

for entity_name, entity_data in trackers.items():
    # Domains sind jetzt unter entity_data['domains'] zu finden, wenn vorhanden
    entity_domains = entity_data.get('domains', [])
    if not isinstance(entity_domains, list): # Manchmal ist es keine Liste
        entity_domains = []

    owner = entity_data.get('owner', {}).get('name', entity_name) # Nutze entity_name als Fallback
    categories = entity_data.get('categories', [])
    prevalence = entity_data.get('prevalence', 0.0) * 100 # Skalieren auf 0-100
    default_rule = entity_data.get('default', 'ignore')

    # Beziehe auch Domains aus den 'rules' ein, falls vorhanden
    # rules sind spezifischer, z.B. "sub.domain.com"
    rules = entity_data.get('rules', [])
    for rule_entry in rules:
        rule_domain = rule_entry.get('rule')
        # Nur ganze Domains extrahieren (keine Pfade oder Regex)
        if rule_domain and '.' in rule_domain and not any(c in rule_domain for c in ['/', '*', '^']):
             # Regel-spezifische Aktion prüfen (z.B. 'block')
             rule_action = rule_entry.get('action', default_rule)
             if rule_action == 'block' and rule_domain not in entity_domains:
                 entity_domains.append(rule_domain)

    if default_rule != 'block' and not any(r.get('action') == 'block' for r in rules):
        continue # Überspringe, wenn weder Standard noch irgendeine Regel 'block' ist

    priority_score = get_category_priority(categories)

    # Filtere Domains für diese Entität
    processed_entry_domains = []
    for domain in entity_domains:
        if domain and '.' in domain and not is_domain_allowed(domain):
            if domain not in processed_entry_domains: # Vermeide Duplikate innerhalb der Entität
                 processed_entry_domains.append(domain)

    # Füge die gefilterten Domains zur Gesamtliste hinzu
    for domain in processed_entry_domains:
        domain_data.append({
            'domain': domain,
            'prevalence': prevalence, # Beachte: Prävalenz gilt für die Entität
            'priority': priority_score,
            'categories': categories,
            'owner': owner
        })

# Duplikate entfernen (falls eine Domain durch Regeln und 'domains' doppelt vorkommt)
# und Einträge mit höherer Priorität/Prävalenz bevorzugen
unique_domains = {}
for item in domain_data:
    domain = item['domain']
    if domain not in unique_domains or \
       (item['priority'] > unique_domains[domain]['priority']) or \
       (item['priority'] == unique_domains[domain]['priority'] and item['prevalence'] > unique_domains[domain]['prevalence']):
        unique_domains[domain] = item

# Sortieren
sorted_domains = sorted(unique_domains.values(),
                        key=lambda x: (x['priority'], x['prevalence']),
                        reverse=True)

print(f"Found {len(sorted_domains)} potential domains meeting criteria.")

# Top N auswählen
top_domains = sorted_domains[:TARGET_COUNT]

print(f"Selected top {len(top_domains)} domains for the filter list.")

# --- Filterliste generieren ---
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
header = f"""! Title: Custom Brave Filter List (from DDG Tracker Radar GitHub)
! Description: Automatically generated list of ~{TARGET_COUNT} popular tracking/ad domains based on DuckDuckGo TDS (GitHub source). Excludes known CDNs and potential site breakers.
! Source: {TRACKER_DATA_URL}
! Updated: {current_time}
! Domain Count: {len(top_domains)}
!
! WARNING: Use at your own risk. While efforts were made to avoid breaking sites, some breakage is always possible with filter lists.
!-------------------------------------------------------------------\n
"""

filter_lines = []
for item in top_domains:
    filter_lines.append(f"||{item['domain']}^")

# Manuell hinzugefügte Regeln
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
""" # Habe ^ am Ende der googleusercontent-Regeln hinzugefügt

# Kombiniere Header, manuelle Regeln und generierte Liste
output_content = header + manual_rules + "\n! --- Automatically generated rules ---\n" + "\n".join(filter_lines)

# --- In Datei schreiben ---
try:
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(output_content)
    print(f"\nSuccessfully wrote {len(top_domains)} rules (+ manual rules) to '{OUTPUT_FILENAME}'")
except IOError as e:
    print(f"\nError writing to file '{OUTPUT_FILENAME}': {e}")
