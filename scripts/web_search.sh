#!/bin/bash
# Helper script for SearXNG searches

QUERY=$1
if [ -z "$QUERY" ]; then
    echo "Usage: $0 <query>"
    exit 1
fi

# URL encode the query
ENCODED_QUERY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$QUERY'''))")

curl -s "http://192.168.1.84:8005/search?q=$ENCODED_QUERY&format=json"
