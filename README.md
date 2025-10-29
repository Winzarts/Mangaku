# mangaku

**mangaku** adalah sebuah API berbasis Flask untuk melakukan scraping data manga/manhua/manhwa dari situs Komiku. API menyediakan berbagai endpoint untuk mendapatkan daftar komik, komik terbaru, berdasarkan genre, populer, dan melakukan pencarian.

## Teknologi  
- Flask – sebagai framework web Python  
- Selenium – untuk menangani halaman yang dimuat secara dinamis (HTMX)  
- python‑dotenv – untuk mengelola konfigurasi lingkungan dari file `.env`  
- BeautifulSoup4 – untuk parsing HTML  
- Requests – untuk melakukan request HTTP ke situs target  

## Fitur / Endpoint  
API menyediakan endpoint sebagai berikut:

| Endpoint                      | Keterangan                                            |
|------------------------------|--------------------------------------------------------|
| `/list-semua-komik`          | Mendapatkan daftar semua komik (manga/manhua/manhwa)  |
| `/latest`                    | Mendapatkan daftar komik terbaru (manga/manhua/manhwa)|
| `/genre`                     | Mendapatkan daftar genre komik                        |
| `/search`                    | Mencari komik berdasarkan kata kunci                   |
| `/popular`                   | Mendapatkan daftar komik populer (manga/manhua/manhwa)|
| `/list-manga`                | Mendapatkan daftar manga                              |
| `/list-manhua`               | Mendapatkan daftar manhua                             |
| `/list-manhwa`               | Mendapatkan daftar manhwa                             |
| `/latest-manga`              | Mendapatkan daftar manga terbaru                      |
| `/latest-manhua`             | Mendapatkan daftar manhua terbaru                     |
| `/latest-manhwa`             | Mendapatkan daftar manhwa terbaru                     |
| `/popular-manga`             | Mendapatkan daftar manga populer                      |
| `/popular-manhua`            | Mendapatkan daftar manhua populer                     |
| `/popular-manhwa`            | Mendapatkan daftar manhwa populer                     |

## Instalasi & Persiapan  
1. Clone repository ini:  
   ```bash
   git clone <URL_REPO_Anda>
   cd mangaku
