#!/bin/bash

# Instal Chromium untuk Playwright (hanya sekali saat startup)
python -m playwright install chromium

# Jalankan aplikasi Flask
python app.py