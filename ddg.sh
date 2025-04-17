#!/usr/bin/env bash
# 1) JSON mit allen Trackern laden (v6 für Extensions/MV3)
# 2) Nach Prävalenz sortieren und Top 200 Domains auswählen
# 3) CDNs (fastly, cloudflare, jsdelivr, …) herausfiltern
# 4) uBO/Brave‑Syntax auf „first-party“ setzen

curl -s 'https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/main/web/v6/extension-tds.json' \
  | jq -r '
      .trackers
      | sort_by(.prevalence)
      | reverse
      | map(.domain)
      | unique
      | .[]' \
  | grep -viE 'cdn|akamai|cloudflare|edgekey|fastly|jsdelivr' \
  | head -n 200 \
  | sed -e 's|^||||' -e 's|$|^$first-party|' \
  > ddg_first_party_blocklist.txt
