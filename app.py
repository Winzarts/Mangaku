from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests
import os
from config import BASE_URL, HEADERS, TIMEOUT, API_BASE

app = Flask(__name__)

def get_dynamic_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process"
            ]
        )
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        page.goto(url, timeout=TIMEOUT)
        page.wait_for_selector("div.bge", timeout=TIMEOUT)
        html = page.content()
        browser.close()
    return html

# --- STATUS API ---
@app.route("/", methods=["GET"])
def API_Status():
    return jsonify({
        "Message": "API is running",
        "Status": "Online",
        "Response": "200"
    })

# --- DETAIL KOMIK ---
@app.route('/manga/<slug>/', methods=['GET'])
def get_manga_detail(slug):
    url = f"{BASE_URL}/manga/{slug}/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(resp.text, 'html.parser')

    title_tag = soup.select_one('#Judul span[itemprop="name"]')
    title = title_tag.text.strip() if title_tag else ""

    short_desc_tag = soup.select_one('#Judul p.j2')
    short_description = short_desc_tag.text.strip() if short_desc_tag else ""

    long_desc_tag = soup.select_one('#Judul p[itemprop="description"]')
    long_description = long_desc_tag.text.strip() if long_desc_tag else ""

    sinopsis_tag = soup.select_one('#Judul p.desc')
    sinopsis = sinopsis_tag.text.strip() if sinopsis_tag else ""

    chapters = []
    for row in soup.select('#Daftar_Chapter tbody tr'):
        cols = row.find_all('td')
        if not cols:
            continue

        a_tag = cols[0].select_one('a')
        if not a_tag:
            continue

        chapter_title = a_tag.text.strip()
        raw_url = a_tag.get('href', '')

        # 🔹 Ekstrak slug chapter dari href (biasanya seperti /manga/owari-no-seraph-chapter-151/)
        chapter_slug = raw_url.strip('/').split('/')[-1].replace(f"{slug}-", "")

        # 🔹 Buat URL API lokal agar sesuai dengan route isi chapter
        chapter_url = f"{API_BASE}/manga/{slug}/{chapter_slug}/"

        views = cols[1].text.strip() if len(cols) > 1 else ""
        date = cols[2].text.strip() if len(cols) > 2 else ""

        chapters.append({
            "title": chapter_title,
            "url": chapter_url,
            "views": views,
            "date": date
        })

    return jsonify({
        "title": title,
        "short_description": short_description,
        "long_description": long_description,
        "sinopsis": sinopsis,
        "chapters": chapters
    })


# --- ISI CHAPTER ---
@app.route('/manga/<slug>/<chapter_slug>/', methods=['GET'])
def manga_content(slug, chapter_slug):
    url = f'{BASE_URL}/{slug}-{chapter_slug}/'

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, 'html.parser')

    title_elem = soup.select_one("#Judul header h1")
    chapter_title = title_elem.text.strip() if title_elem else chapter_slug

    date_elem = soup.select_one("table.tbl tr:nth-child(2) td:nth-child(2)")
    release_date = date_elem.text.strip() if date_elem else ""

    full_title_elem = soup.select_one("table.tbl tr:nth-child(1) td:nth-child(2)")
    full_title = full_title_elem.text.strip() if full_title_elem else ""

    page_images = []
    for img in soup.select("#Baca_Komik img.klazy"):
        src = img.get("src")
        if src and src.startswith("https://img.komiku.org"):
            page_images.append(src.strip())

    return jsonify({
        "slug": slug,
        "chapter_slug": chapter_slug,
        "chapter_title": chapter_title,
        "release_date": release_date,
        "full_title": full_title,
        "page_images": page_images
    })

# --- KOMIK BY GENRE ---
@app.route('/genre/<slug>/', methods=['GET'])
def get_manga_by_genre(slug):
    orderby = request.args.get('orderby', 'update')
    limit = int(request.args.get('limit', 30))
    page = 1
    manga_list = []

    try:
        while len(manga_list) < limit:
            url = f"{BASE_URL}/genre/{slug}/?orderby={orderby}&page={page}"
            html = get_dynamic_html(url)
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("div.bge")
            if not items:
                break

            for manga in items:
                title_tag = manga.select_one("div.kan h3")
                img_tag = manga.select_one("div.bgei img")
                link_tag = manga.select_one("div.bgei a")

                if not (title_tag and img_tag and link_tag):
                    continue

                title = title_tag.get_text(strip=True)
                raw_link = link_tag["href"]
                link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
                img = img_tag["src"]

                tipe_tag = manga.select_one("div.tpe1_inf b")
                tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""

                genre_tag = manga.select_one("div.tpe1_inf")
                genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

                pembaca_tag = manga.select_one("span.judul2 span b")
                pembaca = pembaca_tag.get_text(strip=True) if pembaca_tag else ""

                waktu_tag = manga.select_one("span.judul2")
                waktu = ""
                if waktu_tag:
                    teks = waktu_tag.get_text(strip=True)
                    if "|" in teks:
                        waktu = teks.split("|")[1].strip()

                deskripsi_tag = manga.select_one("div.kan p")
                deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

                new_links = manga.select("div.new1 a")
                awal = f"{API_BASE}{new_links[0]['href']}" if len(new_links) >= 1 else None
                terbaru = f"{API_BASE}{new_links[-1]['href']}" if len(new_links) >= 1 else None

                manga_list.append({
                    "title": title,
                    "type": tipe,
                    "genre": genre_text,
                    "readers": pembaca,
                    "updated": waktu,
                    "description": deskripsi,
                    "thumbnail": img,
                    "link": link,
                    "chapter_awal": awal,
                    "chapter_terbaru": terbaru
                })

                if len(manga_list) >= limit:
                    break

            page += 1

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(manga_list)

# --- LIST SEMUA KOMIK ---
@app.route("/list-semua-komik", methods=["GET"])
def list_semua():
    page = int(request.args.get("page", 1))
    url = f"{BASE_URL}/daftar-komik/page/{page}/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, "html.parser")
    manga_data = []

    for item in soup.select('div.ls4'):
        a_title = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select('span.ls4s')

        if a_title:
            title = a_title.text.strip()
            manga_url = f"{API_BASE}{a_title['href']}"

            genres = []
            if span_genre:
                for g in span_genre:
                    text = g.text.replace('Genre : ', '').strip()
                    genres.extend([x.strip() for x in text.split(',') if x.strip()])

            manga_data.append({
                "title": title,
                "url": manga_url,
                "thumbnail": img.get('data-src') if img else None,
                "genres": genres
            })
    
    return jsonify({
        "page": page,
        "count" : len(manga_data),
        "List_Manga": manga_data
    })

# --- FITUR SEARCH ---
@app.route("/search", methods=["GET"])
def search_komik():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Parameter 'q' diperlukan, contoh /search?tokidoki+bosotto"}),400
    
    url = f"{BASE_URL}/?post_type=manga&s={query.replace(' ', '+')}"

    try:
        html = get_dynamic_html(url)
    except Exception as e:
        return jsonify({"error": str(e)}),500
    
    soup = BeautifulSoup(html, 'html.parser')
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")

        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        raw_link = link_tag.get("href", "")
        link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
        img = img_tag.get("src")

        tipe_tag = manga.select_one("div.tpe1_inf b")
        tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""

        genre_tag = manga.select_one("div.tpe1_inf")
        genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

        deskripsi_tag = manga.select_one("div.kan p")
        deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre_text,
            "description": deskripsi,
            "thumbnail": img,
            "link": link
        })

    if not manga_list:
        return jsonify({"message": f"tidak menemukan hasil untuk '{query}'"}),404
    
    return jsonify({
        "query": query,
        "results": manga_list,
        "count": len(manga_list)
    })

# --- LIST KOMIK TERBARU ---
@app.route('/latest', methods=['GET'])
def latest_komik():
    url = f"{BASE_URL}/pustaka/?orderby=modified&tipe=&genre=&genre2=&status="

    try:
        html = get_dynamic_html(url)  # Gunakan Selenium/Playwright jika dinamis
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")

        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        full_link = link_tag["href"]

        # 🔹 Ambil slug dari URL, misal: https://komiku.org/manga/one-piece/ → one-piece
        slug = full_link.strip("/").split("/")[-1]

        img = img_tag["src"]

        # 🔹 Tipe (Manga, Manhwa, Manhua) dan genre
        tipe_tag = manga.select_one("div.tpe1_inf b")
        tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""
        genre_tag = manga.select_one("div.tpe1_inf")
        genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

        # 🔹 Pembaca dan waktu update
        info_span = manga.select_one("span.judul2")
        pembaca, waktu = "", ""
        if info_span:
            teks = info_span.get_text(strip=True)
            if "|" in teks:
                pembaca = teks.split("|")[0].strip().replace("pembaca", "").strip()
                waktu = teks.split("|")[1].strip()
            else:
                pembaca = teks.strip()

        # 🔹 Deskripsi singkat
        deskripsi_tag = manga.select_one("div.kan p")
        deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

        # 🔹 Chapter awal & terbaru → ubah ke format API
        full_link = link_tag["href"]
        slug = full_link.strip("/").split("/")[-1]

        new_links = manga.select("div.new1 a")
        awal, terbaru = None, None
        if new_links:
            raw_awal = new_links[0].get('href', '').strip().strip('/')
            raw_terbaru = new_links[-1].get('href', '').strip().strip('/')

            awal_frag = raw_awal.split('/')[-1] if raw_awal else ""
            terbaru_frag = raw_terbaru.split('/')[-1] if raw_terbaru else ""

            prefix = f"{slug}-"
            chapter_awal_slug = awal_frag[len(prefix):] if awal_frag.startswith(prefix) else awal_frag
            chapter_terbaru_slug = terbaru_frag[len(prefix):] if terbaru_frag.startswith(prefix) else terbaru_frag

            if chapter_awal_slug:
                awal = f"{API_BASE}/manga/{slug}/{chapter_awal_slug}/"
            if chapter_terbaru_slug:
                terbaru = f"{API_BASE}/manga/{slug}/{chapter_terbaru_slug}/"


        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre_text,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": f"{API_BASE}/manga/{slug}/",  # 🔹 link ke detail manga
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST KOMIK TERPOPULER ---
@app.route("/popular", methods=["GET"])
def popular_komik():
    url = f"{BASE_URL}/pustaka/?orderby=meta_value_num&tipe=&genre=&genre2=&status="
    try:
        html = get_dynamic_html(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")
        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        raw_link = link_tag["href"]
        link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
        img = img_tag["src"]
        tipe = manga.select_one("div.tpe1_inf b").get_text(strip=True)
        genre = manga.select_one("div.tpe1_inf").get_text(strip=True).replace(tipe, "").strip()
        pembaca = manga.select_one("span.judul2 span b").get_text(strip=True)
        waktu = manga.select_one("span.judul2").get_text(strip=True).split("|")[1].strip() if "|" in manga.select_one("span.judul2").get_text() else ""
        deskripsi = manga.select_one("div.kan p").get_text(strip=True)

        new_links = manga.select("div.new1 a")
        awal = f"{API_BASE}{new_links[0]['href']}" if len(new_links) >= 1 else None
        terbaru = f"{API_BASE}{new_links[-1]['href']}" if len(new_links) >= 1 else None

        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": link,
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST GENRE ---
@app.route("/genre/", methods=["GET"])
def List_Genre():
    url = f"{BASE_URL}/pustaka/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e :
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, "html.parser")
    genre_list = []

    for opt in soup.select("select[name='genre'] option"):
        slug = opt.get("value", "").strip()
        genre = opt.get_text(strip=True)

        if not slug:
            continue

        api_link = f"{API_BASE}/genre/{slug}"

        genre_list.append({
            "genre": genre,
            "slug": slug,
            "url": api_link
        })

    return jsonify(genre_list)

# --- LIST SEMUA MANGA ---
@app.route("/list-manga", methods=["GET"])
def semua_manga():
    url = f"{BASE_URL}/daftar-komik/?tipe=manga"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, "html.parser")
    manga_data = []

    for item in soup.select('div.ls4'):
        a_title = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select('span.ls4s')

        if a_title:
            title = a_title.text.strip()
            manga_url = f"{API_BASE}{a_title['href']}"

            genres = []
            if span_genre:
                for g in span_genre:
                    text = g.text.replace('Genre : ', '').strip()
                    genres.extend([x.strip() for x in text.split(',') if x.strip()])

            manga_data.append({
                "title": title,
                "url": manga_url,
                "thumbnail": img.get('data-src') if img else None,
                "genres": genres
            })
    
    return jsonify({
        "count" : len(manga_data),
        "List_Manga": manga_data
    })

# --- LIST SEMUA MANHWA ---
@app.route("/list-manhwa", methods=["GET"])
def semua_manhwa():
    url = f"{BASE_URL}/daftar-komik/?tipe=manhwa"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, "html.parser")
    manga_data = []

    for item in soup.select('div.ls4'):
        a_title = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select('span.ls4s')

        if a_title:
            title = a_title.text.strip()
            manga_url = f"{API_BASE}{a_title['href']}"

            genres = []
            if span_genre:
                for g in span_genre:
                    text = g.text.replace('Genre : ', '').strip()
                    genres.extend([x.strip() for x in text.split(',') if x.strip()])

            manga_data.append({
                "title": title,
                "url": manga_url,
                "thumbnail": img.get('data-src') if img else None,
                "genres": genres
            })
    
    return jsonify({
        "count" : len(manga_data),
        "List_Manga": manga_data
    })

# --- LIST SEMUA MANHUA ---
@app.route("/list-manhua", methods=["GET"])
def semua_manhua():
    url = f"{BASE_URL}/daftar-komik/?tipe=manhua"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, "html.parser")
    manga_data = []

    for item in soup.select('div.ls4'):
        a_title = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select('span.ls4s')

        if a_title:
            title = a_title.text.strip()
            manga_url = f"{API_BASE}{a_title['href']}"

            genres = []
            if span_genre:
                for g in span_genre:
                    text = g.text.replace('Genre : ', '').strip()
                    genres.extend([x.strip() for x in text.split(',') if x.strip()])

            manga_data.append({
                "title": title,
                "url": manga_url,
                "thumbnail": img.get('data-src') if img else None,
                "genres": genres
            })
    
    return jsonify({
        "count" : len(manga_data),
        "List_Manga": manga_data
    })

# --- LIST MANGA TERPOPULER ---
@app.route('/popular-manga', methods=['GET'])
def popular_manga():
    url = f"{BASE_URL}/pustaka/?orderby=meta_value_num&tipe=manga"
    try:
        html = get_dynamic_html(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")
        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        raw_link = link_tag["href"]
        link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
        img = img_tag["src"]
        tipe = manga.select_one("div.tpe1_inf b").get_text(strip=True)
        genre = manga.select_one("div.tpe1_inf").get_text(strip=True).replace(tipe, "").strip()
        pembaca = manga.select_one("span.judul2 span b").get_text(strip=True)
        waktu = manga.select_one("span.judul2").get_text(strip=True).split("|")[1].strip() if "|" in manga.select_one("span.judul2").get_text() else ""
        deskripsi = manga.select_one("div.kan p").get_text(strip=True)

        new_links = manga.select("div.new1 a")
        awal = f"{API_BASE}{new_links[0]['href']}" if len(new_links) >= 1 else None
        terbaru = f"{API_BASE}{new_links[-1]['href']}" if len(new_links) >= 1 else None

        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": link,
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST MANHUA TERPOPULAR ---
@app.route("/popular-manhua", methods=["GET"])
def popular_manhua():
    url = f"{BASE_URL}/pustaka/?orderby=meta_value_num&tipe=manhua"
    try:
        html = get_dynamic_html(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")
        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        raw_link = link_tag["href"]
        link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
        img = img_tag["src"]
        tipe = manga.select_one("div.tpe1_inf b").get_text(strip=True)
        genre = manga.select_one("div.tpe1_inf").get_text(strip=True).replace(tipe, "").strip()
        pembaca = manga.select_one("span.judul2 span b").get_text(strip=True)
        waktu = manga.select_one("span.judul2").get_text(strip=True).split("|")[1].strip() if "|" in manga.select_one("span.judul2").get_text() else ""
        deskripsi = manga.select_one("div.kan p").get_text(strip=True)

        new_links = manga.select("div.new1 a")
        awal = f"{API_BASE}{new_links[0]['href']}" if len(new_links) >= 1 else None
        terbaru = f"{API_BASE}{new_links[-1]['href']}" if len(new_links) >= 1 else None

        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": link,
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST MANHWA TERPOPULER ---
@app.route("/popular-manhwa", methods=["GET"])
def popular_manhwa():
    url = f"{BASE_URL}/pustaka/?orderby=meta_value_num&tipe=manhwa"
    try:
        html = get_dynamic_html(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")
        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        raw_link = link_tag["href"]
        link = f"{API_BASE}{raw_link}" if raw_link.startswith('/') else raw_link
        img = img_tag["src"]
        tipe = manga.select_one("div.tpe1_inf b").get_text(strip=True)
        genre = manga.select_one("div.tpe1_inf").get_text(strip=True).replace(tipe, "").strip()
        pembaca = manga.select_one("span.judul2 span b").get_text(strip=True)
        waktu = manga.select_one("span.judul2").get_text(strip=True).split("|")[1].strip() if "|" in manga.select_one("span.judul2").get_text() else ""
        deskripsi = manga.select_one("div.kan p").get_text(strip=True)

        new_links = manga.select("div.new1 a")
        awal = f"{API_BASE}{new_links[0]['href']}" if len(new_links) >= 1 else None
        terbaru = f"{API_BASE}{new_links[-1]['href']}" if len(new_links) >= 1 else None

        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": link,
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST MANGA TERUPDATE ---
@app.route("/latest-manga", methods=["GET"])
def latest_manga():
    url = f"{BASE_URL}/pustaka/?orderby=modified&tipe=manga&genre=&genre2=&status="

    try:
        html = get_dynamic_html(url)  # Gunakan Selenium/Playwright jika dinamis
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")

        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        full_link = link_tag["href"]

        # 🔹 Ambil slug dari URL, misal: https://komiku.org/manga/one-piece/ → one-piece
        slug = full_link.strip("/").split("/")[-1]

        img = img_tag["src"]

        # 🔹 Tipe (Manga, Manhwa, Manhua) dan genre
        tipe_tag = manga.select_one("div.tpe1_inf b")
        tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""
        genre_tag = manga.select_one("div.tpe1_inf")
        genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

        # 🔹 Pembaca dan waktu update
        info_span = manga.select_one("span.judul2")
        pembaca, waktu = "", ""
        if info_span:
            teks = info_span.get_text(strip=True)
            if "|" in teks:
                pembaca = teks.split("|")[0].strip().replace("pembaca", "").strip()
                waktu = teks.split("|")[1].strip()
            else:
                pembaca = teks.strip()

        # 🔹 Deskripsi singkat
        deskripsi_tag = manga.select_one("div.kan p")
        deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

        # 🔹 Chapter awal & terbaru → ubah ke format API
        full_link = link_tag["href"]
        slug = full_link.strip("/").split("/")[-1]

        new_links = manga.select("div.new1 a")
        awal, terbaru = None, None
        if new_links:
            raw_awal = new_links[0].get('href', '').strip().strip('/')
            raw_terbaru = new_links[-1].get('href', '').strip().strip('/')

            awal_frag = raw_awal.split('/')[-1] if raw_awal else ""
            terbaru_frag = raw_terbaru.split('/')[-1] if raw_terbaru else ""

            prefix = f"{slug}-"
            chapter_awal_slug = awal_frag[len(prefix):] if awal_frag.startswith(prefix) else awal_frag
            chapter_terbaru_slug = terbaru_frag[len(prefix):] if terbaru_frag.startswith(prefix) else terbaru_frag

            if chapter_awal_slug:
                awal = f"{API_BASE}/manga/{slug}/{chapter_awal_slug}/"
            if chapter_terbaru_slug:
                terbaru = f"{API_BASE}/manga/{slug}/{chapter_terbaru_slug}/"


        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre_text,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": f"{API_BASE}/manga/{slug}/",  # 🔹 link ke detail manga
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST MANHUA TERUPDATE ---
@app.route("/latest-manhua", methods=["GET"])
def latest_manhua():
    url = f"{BASE_URL}/pustaka/?orderby=modified&tipe=manhua&genre=&genre2=&status="

    try:
        html = get_dynamic_html(url)  # Gunakan Selenium/Playwright jika dinamis
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")

        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        full_link = link_tag["href"]

        # 🔹 Ambil slug dari URL, misal: https://komiku.org/manga/one-piece/ → one-piece
        slug = full_link.strip("/").split("/")[-1]

        img = img_tag["src"]

        # 🔹 Tipe (Manga, Manhwa, Manhua) dan genre
        tipe_tag = manga.select_one("div.tpe1_inf b")
        tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""
        genre_tag = manga.select_one("div.tpe1_inf")
        genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

        # 🔹 Pembaca dan waktu update
        info_span = manga.select_one("span.judul2")
        pembaca, waktu = "", ""
        if info_span:
            teks = info_span.get_text(strip=True)
            if "|" in teks:
                pembaca = teks.split("|")[0].strip().replace("pembaca", "").strip()
                waktu = teks.split("|")[1].strip()
            else:
                pembaca = teks.strip()

        # 🔹 Deskripsi singkat
        deskripsi_tag = manga.select_one("div.kan p")
        deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

        # 🔹 Chapter awal & terbaru → ubah ke format API
        full_link = link_tag["href"]
        slug = full_link.strip("/").split("/")[-1]

        new_links = manga.select("div.new1 a")
        awal, terbaru = None, None
        if new_links:
            raw_awal = new_links[0].get('href', '').strip().strip('/')
            raw_terbaru = new_links[-1].get('href', '').strip().strip('/')

            awal_frag = raw_awal.split('/')[-1] if raw_awal else ""
            terbaru_frag = raw_terbaru.split('/')[-1] if raw_terbaru else ""

            prefix = f"{slug}-"
            chapter_awal_slug = awal_frag[len(prefix):] if awal_frag.startswith(prefix) else awal_frag
            chapter_terbaru_slug = terbaru_frag[len(prefix):] if terbaru_frag.startswith(prefix) else terbaru_frag

            if chapter_awal_slug:
                awal = f"{API_BASE}/manga/{slug}/{chapter_awal_slug}/"
            if chapter_terbaru_slug:
                terbaru = f"{API_BASE}/manga/{slug}/{chapter_terbaru_slug}/"


        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre_text,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": f"{API_BASE}/manga/{slug}/",  # 🔹 link ke detail manga
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

# --- LIST MANHWA TERUPDATE ---
@app.route("/latest-manhwa", methods=["GET"])
def latest_manhwa():
    url = f"{BASE_URL}/pustaka/?orderby=modified&tipe=manhwa&genre=&genre2=&status="

    try:
        html = get_dynamic_html(url)  # Gunakan Selenium/Playwright jika dinamis
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(html, "html.parser")
    manga_list = []

    for manga in soup.select("div.bge"):
        title_tag = manga.select_one("div.kan h3")
        img_tag = manga.select_one("div.bgei img")
        link_tag = manga.select_one("div.bgei a")

        if not (title_tag and img_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        full_link = link_tag["href"]

        # 🔹 Ambil slug dari URL, misal: https://komiku.org/manga/one-piece/ → one-piece
        slug = full_link.strip("/").split("/")[-1]

        img = img_tag["src"]

        # 🔹 Tipe (Manga, Manhwa, Manhua) dan genre
        tipe_tag = manga.select_one("div.tpe1_inf b")
        tipe = tipe_tag.get_text(strip=True) if tipe_tag else ""
        genre_tag = manga.select_one("div.tpe1_inf")
        genre_text = genre_tag.get_text(strip=True).replace(tipe, "").strip() if genre_tag else ""

        # 🔹 Pembaca dan waktu update
        info_span = manga.select_one("span.judul2")
        pembaca, waktu = "", ""
        if info_span:
            teks = info_span.get_text(strip=True)
            if "|" in teks:
                pembaca = teks.split("|")[0].strip().replace("pembaca", "").strip()
                waktu = teks.split("|")[1].strip()
            else:
                pembaca = teks.strip()

        # 🔹 Deskripsi singkat
        deskripsi_tag = manga.select_one("div.kan p")
        deskripsi = deskripsi_tag.get_text(strip=True) if deskripsi_tag else ""

        # 🔹 Chapter awal & terbaru → ubah ke format API
        full_link = link_tag["href"]
        slug = full_link.strip("/").split("/")[-1]

        new_links = manga.select("div.new1 a")
        awal, terbaru = None, None
        if new_links:
            raw_awal = new_links[0].get('href', '').strip().strip('/')
            raw_terbaru = new_links[-1].get('href', '').strip().strip('/')

            awal_frag = raw_awal.split('/')[-1] if raw_awal else ""
            terbaru_frag = raw_terbaru.split('/')[-1] if raw_terbaru else ""

            prefix = f"{slug}-"
            chapter_awal_slug = awal_frag[len(prefix):] if awal_frag.startswith(prefix) else awal_frag
            chapter_terbaru_slug = terbaru_frag[len(prefix):] if terbaru_frag.startswith(prefix) else terbaru_frag

            if chapter_awal_slug:
                awal = f"{API_BASE}/manga/{slug}/{chapter_awal_slug}/"
            if chapter_terbaru_slug:
                terbaru = f"{API_BASE}/manga/{slug}/{chapter_terbaru_slug}/"


        manga_list.append({
            "title": title,
            "type": tipe,
            "genre": genre_text,
            "readers": pembaca,
            "updated": waktu,
            "description": deskripsi,
            "thumbnail": img,
            "link": f"{API_BASE}/manga/{slug}/",  # 🔹 link ke detail manga
            "chapter_awal": awal,
            "chapter_terbaru": terbaru
        })

    return jsonify(manga_list)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
