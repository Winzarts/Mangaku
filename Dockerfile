# Gunakan base image resmi Playwright untuk Python
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set direktori kerja
WORKDIR /app

# Salin requirements.txt (kalau ada)
COPY requirements.txt .

# Install dependencies Python
RUN pip install --no-cache-dir -r requirements.txt || true

# Salin semua file project ke container
COPY . .

# Install browser yang dibutuhkan oleh Playwright
RUN playwright install --with-deps

# Jalankan script utama (ubah sesuai file-mu)
CMD ["python", "app.py"]
