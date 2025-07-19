from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0"}

@app.route('/')
def home():
    return "API ini Active"

@app.route('/list-manga', methods=['GET'])
def get_manga_list():
    page = int(request.args.get('page', 1))
    url = f"https://komiku.org/daftar-komik/page/{page}/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(resp.text, 'html.parser')
    manga_data = []

    for idx, item in enumerate(soup.select('div.ls4')):
        a_title = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select_one('span.ls4s')

        if a_title:
            title = a_title.text.strip()
            manga_url = f"https://komiku.org{a_title['href']}"

            genres = []
            if span_genre:
                text = span_genre.text.replace('Genre:', '').strip()
                genres = [g.strip() for g in text.split(',') if g.strip()]

            manga_data.append([
                ("id", idx),
                ("title", title),
                ("url", manga_url),
                ("thumbnail", img.get('data-src') if img else None),
                ("genres", genres)
            ])

    manga_data = sorted(manga_data, key=lambda x: x['title'].lower())

    return jsonify({
        "page": page,
        "count": len(manga_data),
        "komik": manga_data
    })

@app.route('/manga/<slug>', methods=['GET'])
def get_manga_detail(slug):
    url = f"https://komiku.org/manga/{slug}/"
    
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
    for a in soup.select('div.new1.sd.rd a'):
        chapter_title = a.text.strip().replace('\n', ' ')
        chapter_url = f"https://komiku.org{a.get('href')}"
        if "chapter" in chapter_url.lower():
            chapters.append({
                "title": chapter_title,
                "url": chapter_url
            })

    return jsonify({
        "slug": slug,
        "title": title,
        "short_description": short_description,
        "long_description": long_description,
        "sinopsis": sinopsis,
        "total_chapters": len(chapters),
        "chapters": chapters
    })

@app.route('/manga/<slug>/<chapter_slug>', methods=['GET'])
def manga_content(slug, chapter_slug):
    url = f'https://komiku.org/{slug}-{chapter_slug}/'

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    chapters = []

    header = soup.select_one('#Baca_Komik h2')

    pages = []
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

@app.route("/list-genres", methods=["GET"])
def get_list_genres():
    url = "https://komiku.org/pustaka/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}),500
    
    soup = BeautifulSoup(res.text, 'html.parser')
    genre_select = soup.find("select", attrs={"name": "genre"})

    genres = []
    if genre_select:
        options = genre_select.find_all("option")
    for opt in options:
        val = opt.get("value", "").strip()
        name = opt.text.strip()
        if val:
            genres.append({
                "value": val, 
                "name": name,
                "url" : f"https://komiku.org/genre/{val}/"
            })

    return jsonify({"genres": genres})

@app.route('/genre/<genre_slug>', methods=['GET'])
def get_manga_by_genre(genre_slug):
    page = int(request.args.get('page', 1))
    url = f'https://komiku.org/genre/{genre_slug}/page/{page}/'

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    soup = BeautifulSoup(resp.text, 'html.parser')
    manga_data = []

    for item in soup.select('div.ls4'):
        a = item.select_one('h4 a')
        img = item.select_one('div.ls4v img.lazy')
        span_genre = item.select_one('span.ls4s')

        if a:
            genres = []
            if span_genre:
                list_gen = [g.strip() for g in span_genre.text.replace('Genre:', '').split(',') if g.strip()]
                genres = list_gen

            manga_data.append({
                "title": a.text.strip(),
                "url": "https://komiku.org" + a['href'],
                "thumbnail": img.get('data-src') if img else None,
                "genres": genres
            })

    return jsonify({
        "genre": genre_slug,
        "page": page,
        "count": len(manga_data),
        "komik": manga_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=10000)
