#!/usr/bin/env bash
# Tebra Interactive Scraper Launcher
cd "$(dirname "$0")" || exit 1
python3 tebra_scraper.py "$@"
