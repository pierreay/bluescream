#!/bin/bash

# * About

# Upload a file to a Google server.

# * Script

if [[ $# -lt 1 ]]; then
    echo "$0 FILENAME"
    exit 1
fi

if [[ -z "$KAREL_KEY" ]]; then
    echo "Set KAREL_KEY variable to key for Google API"
    exit 1
fi

curl --progress-bar -X POST --header 'Push-ID: feeds/ibkydxrc7nrnja' --header "$KAREL_KEY" https://content-push.googleapis.com/upload/ -o /dev/null -T "$1"
md5sum "$1"
