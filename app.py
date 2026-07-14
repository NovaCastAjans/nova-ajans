import sqlite3
import os
from flask import Flask, render_template_string, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# .env dosyasındaki gizli şifreleri ve anahtarları yüklüyoruz
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'nova_ajans_cok_gizli_super_anahtar_2026')

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ajans.db')

# Yönetici Bilgileri (.env dosyasından çekilir, yoksa varsayılana düşer)
ADMIN_USER = os.getenv('ADMIN_USER', 'emirhan')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'emirhan41')

def veritabanini_hazirla():
    """Güvenli tablo yapısını hazırlar ve örnek verileri ekler."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oyuncular (
            username TEXT PRIMARY KEY,
            sifre TEXT NOT NULL,
            isim TEXT NOT NULL,
            yas INTEGER,
            boy TEXT,
            kilo TEXT,
            foto_url TEXT,
            deneyimler TEXT
        )
    ''')
    
    # Tablo boşsa güvenli (kriptolu) örnek verileri yerleştiriyoruz
    cursor.execute("SELECT COUNT(*) FROM oyuncular")
    if cursor.fetchone()[0] == 0:
        ornek_oyuncular = [
            ("ahmet123", generate_password_hash("12345"), "Ahmet Yılmaz", 24, "1.85", "78", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=400", "Dizi: Arka Sokaklar\nReklam: Banka Reklamı"),
            ("merve543", generate_password_hash("54321"), "Merve Çelik", 22, "1.70", "55", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=400", "Dizi: Yalı Çapkını\nReklam: Şampuan Reklamı"),
            ("emirhan99", generate_password_hash("9999"), "Emirhan Nizam", 25, "1.80", "75", "", "Nova Cast Ajans Kurucusu\nSinema: Başrol Oyuncusu")
        ]
        cursor.executemany('''
            INSERT INTO oyuncular (username, sifre, isim, yas, boy, kilo, foto_url, deneyimler)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ornek_oyuncular)
        conn.commit()
    conn.close()

def oyuncu_getir(username):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM oyuncular WHERE username = ?", (username,))
    oyuncu = cursor.fetchone()
    conn.close()
    return oyuncu

def tum_oyunculari_getir():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM oyuncular")
    oyuncular = cursor.fetchall()
    conn.close()
    return oyuncular

# --- HTML ŞABLONLARI ---

INDEX_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova Cast Ajans</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: sans-serif; }
        .hero { background: #1a1a1a; padding: 60px 0; text-align: center; border-bottom: 3px solid #ffc107; }
        .card { background-color: #1e1e1e; border: 1px solid #333; color: #fff; border-radius: 12px; margin-bottom: 20px; overflow: hidden; transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 8px 16px rgba(255,193,7,0.2); }
        .oyuncu-img { height: 320px; object-fit: cover; width: 100%; background-color: #2a2a2a; }
        .card-body { padding: 20px; text-align: center; }
        footer { background-color: #0a0a0a; border-top: 2px solid #ffc107; padding: 30px 0; margin-top: 50px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary">
        <div class="container">
            <a class="navbar-brand text-warning fw-bold" href="/">★ NOVA CAST AJANS</a>
            <div>
                {% if session.get('kullanici') %}
                    <a href="/profil" class="btn btn-warning btn-sm me-2">Panelim</a>
                    <a href="/logout" class="btn btn-outline-danger btn-sm">Çıkış</a>
                {% elif session.get('admin') %}
                    <a href="/admin" class="btn btn-danger btn-sm me-2">Yönetim Paneli</a>
                    <a href="/logout" class="btn btn-outline-danger btn-sm">Çıkış</a>
                {% else %}
                    <a href="/login" class="btn btn-outline-warning btn-sm">Oyuncu Girişi</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="hero">
        <h1 class="display-4 text-warning fw-bold">Geleceğin Yıldızlarını Keşfediyoruz</h1>
        <p class="lead">Dizi, Sinema ve Reklamda Türkiye'nin öncü ajansı.</p>
    </div>
    <div class="container my-5">
        <h2 class="text-center text-warning mb-5 fw-bold">Aktif Oyuncularımız</h2>
        <div class="row g-4">
            {% for oyuncu in oyuncular %}
            <div class="col-md-4 col-sm-6">
                <div class="card">
                    {% if oyuncu['foto_url'] %}
                        <img src="{{ oyuncu['foto_url'] }}" class="oyuncu-img" alt="{{ oyuncu['isim'] }}">
                    {% else %}
                        <div class="oyuncu-img d-flex align-items-center justify-content-center text-muted">
                            <svg width="80" height="80" fill="currentColor" class="bi bi-person-fill" viewBox="0 0 16 16">
                                <path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6"/>
                            </svg>
                        </div>
                    {% endif %}
                    <div class="card-body">
                        <h4 class="text-warning fw-bold m-0">{{ oyuncu['isim'] }}</h4>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    <footer>
        <div class="container text-center">
            <h4 class="text-warning">Nova Cast Agency</h4>
            <p>Kurucu: <strong>Emirhan Nizam</strong></p>
            <p>📍 Kayseri / Merkez | 📞 +90 541 644 97 34</p>
        </div>
    </footer>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giriş - Nova Cast</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #fff; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 15px; padding: 40px; width: 100%; max-width: 400px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h3 class="text-center text-warning mb-4 fw-bold">GİRİŞ PANELİ</h3>
        
        {% if hata_mesaji %}
            <div class="alert alert-danger py-2 text-center" role="alert">
                {{ hata_mesaji }}
            </div>
        {% endif %}

        <form action="/login" method="POST">
            <div class="mb-3">
                <label class="form-label text-muted">Kullanıcı Adı</label>
                <input type="text" class="form-control bg-dark text-white border-secondary" name="username" required>
            </div>
            <div class="mb-4">
                <label class="form-label text-muted">Şifre</label>
                <input type="password" class="form-control bg-dark text-white border-secondary" name="password" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold text-dark">Giriş Yap</button>
        </form>
        <div class="text-center mt-3">
            <a href="/" class="text-warning text-decoration-none small">← Ana Sayfaya Dön</a>
        </div>
    </div>
</body>
</html>
"""

PROFIL_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oyuncu Paneli - {{ oyuncu['isim'] }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #fff; }
        .profile-container { background-color: #1e1e1e; border-radius: 15px; padding: 40px; border: 1px solid #333; margin-top: 50px; }
        .info-box { background-color: #252525; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #ffc107; }
        .profile-img { width: 100%; max-height: 400px; object-fit: cover; border-radius: 12px; border: 2px solid #333; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary">
        <div class="container">
            <span class="navbar-brand text-warning fw-bold">★ NOVA OYUNCU PANELİ</span>
            <div>
                <a href="/" class="btn btn-outline-warning btn-sm me-2">Ana Sayfa</a>
                <a href="/logout" class="btn btn-danger btn-sm">Güvenli Çıkış</a>
            </div>
        </div>
    </nav>
    <div class="container">
        <div class="profile-container">
            <div class="row align-items-center">
                <div class="col-md-4 text-center mb-4 mb-md-0">
                    {% if oyuncu['foto_url'] %}
                        <img src="{{ oyuncu['foto_url'] }}" class="profile-img" alt="{{ oyuncu['isim'] }}">
                    {% else %}
                        <div class="profile-img bg-dark d-flex align-items-center justify-content-center text-muted" style="height: 350px;">
                            <svg width="100" height="100" fill="currentColor" class="bi bi-person" viewBox="0 0 16 16">
                                <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0m4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4m-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10s-3.516.68-4.168 1.332c-.678.678-.83 1.418-.832 1.664z"/>
                            </svg>
                        </div>
                    {% endif %}
                </div>
                <div class="col-md-8">
                    <h1 class="text-warning fw-bold mb-3">{{ oyuncu['isim'] }}</h1>
                    <span class="badge bg-warning text-dark px-3 py-2 fs-6 mb-4">Aktif Oyuncu Profili</span>
                    
                    <div class="row">
                        <div class="col-4">
                            <div class="info-box">
                                <small class="text-muted d-block">Yaş</small>
                                <strong class="fs-5">{{ oyuncu['yas'] }}</strong>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="info-box">
                                <small class="text-muted d-block">Boy</small>
                                <strong class="fs-5">{{ oyuncu['boy'] }} m</strong>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="info-box">
                                <small class="text-muted d-block">Kilo</small>
                                <strong class="fs-5">{{ oyuncu['kilo'] }} kg</strong>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-5 p-4 bg-dark rounded border border-secondary">
                <h4 class="text-warning mb-3">Kariyer & Deneyimler</h4>
                <p class="fs-5" style="white-space: pre-line;">{{ oyuncu['deneyimler'] }}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yönetici Paneli - Nova Cast</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #fff; padding-bottom: 50px; }
        .admin-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 30px; }
        .table-dark { --bs-table-bg: #1e1e1e; }
        /* Label tasarımı ile kutuların üzerinde ne olduğu mobil görünümde de netleşsin */
        .form-label { font-size: 0.85rem; color: #aaa; margin-bottom: 4px; font-weight: 500; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark border-bottom border-secondary">
        <div class="container">
            <span class="navbar-brand text-danger fw-bold">⚙️ NOVA MOBİL ADMİN</span>
            <a href="/" class="btn btn-outline-warning btn-sm">Ana Sayfaya Dön</a>
        </div>
    </nav>
    <div class="container mt-4">
        <h2 class="text-warning mb-4">Oyuncu Yönetim Paneli</h2>
        
        <!-- YENİ OYUNCU EKLEME FORMU -->
        <div class="admin-card">
            <h4 class="text-warning mb-3">Yeni Oyuncu Ekle</h4>
            <form action="/admin/ekle" method="POST">
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">Kullanıcı Adı</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="username" placeholder="Örn: ahmet123" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Giriş Şifresi</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="sifre" placeholder="Örn: 12345" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Oyuncu Adı Soyadı</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="isim" placeholder="Örn: Ahmet Yılmaz" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Yaş</label>
                        <input type="number" class="form-control bg-dark text-white border-secondary" name="yas" placeholder="Örn: 24" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Boy (Metre)</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="boy" placeholder="Örn: 1.85" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Kilo (kg)</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="kilo" placeholder="Örn: 78" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Oyuncu Fotoğraf Linki (Fotoğraf URL)</label>
                        <input type="text" class="form-control bg-dark text-white border-secondary" name="foto_url" placeholder="Örn: https://link.com/foto.jpg (Boş Kalabilir)">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Kariyer, Projeler & Deneyimler</label>
                        <textarea class="form-control bg-dark text-white border-secondary" name="deneyimler" rows="2" placeholder="Dizi, Reklam veya Tiyatro geçmişini satır satır yazabilirsiniz..."></textarea>
                    </div>
                    <div class="col-12 mt-4">
                        <button type="submit" class="btn btn-success fw-bold px-4">Oyuncuyu Kaydet</button>
                    </div>
                </div>
            </form>
        </div>

        <!-- OYUNCU LİSTESİ -->
        <div class="table-responsive">
            <table class="table table-dark table-striped align-middle border border-secondary">
                <thead>
                    <tr>
                        <th>Kullanıcı Adı</th>
                        <th>Kriptolu Şifre (Özet)</th>
                        <th>İsim</th>
                        <th>Yaş/Boy/Kilo</th>
                        <th>İşlem</th>
                    </tr>
                </thead>
                <tbody>
                    {% for oyuncu in oyuncular %}
                    <tr>
                        <td><code>{{ oyuncu['username'] }}</code></td>
                        <td><small class="text-muted">Kriptolu Güvenli Şifre</small></td>
                        <td><strong>{{ oyuncu['isim'] }}</strong></td>
                        <td>{{ oyuncu['yas'] }}y / {{ oyuncu['boy'] }}m / {{ oyuncu['kilo'] }}kg</td>
                        <td>
                            <a href="/admin/sil/{{ oyuncu['username'] }}" class="btn btn-danger btn-sm" onclick="return confirm('Bu oyuncuyu silmek istediğine emin misin?')">Sil</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# --- YÖNLENDİRMELER (ROUTELER) ---

@app.route('/')
def ana_sayfa():
    oyuncular = tum_oyunculari_getir()
    return render_template_string(INDEX_HTML, oyuncular=oyuncular)

@app.route('/login', methods=['GET', 'POST'])
def login():
    hata = None
    if request.method == 'POST':
        kullanici_adi = request.form['username']
        sifre = request.form['password']
        
        # 1. Yönetici Giriş Kontrolü
        if kullanici_adi == ADMIN_USER and sifre == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('admin_paneli'))
            
        # 2. Oyuncu Giriş Kontrolü
        oyuncu = oyuncu_getir(kullanici_adi)
        if oyuncu and check_password_hash(oyuncu['sifre'], sifre):
            session['kullanici'] = kullanici_adi
            return redirect(url_for('profil_sayfasi'))
        else:
            hata = "Hatalı kullanıcı adı veya şifre girdiniz!"
            
    return render_template_string(LOGIN_HTML, hata_mesaji=hata)

@app.route('/profil')
def profil_sayfasi():
    # Oturum açılmamışsa login sayfasına atar
    if 'kullanici' not in session:
        return redirect(url_for('login'))
        
    kullanici_adi = session['kullanici']
    oyuncu_verisi = oyuncu_getir(kullanici_adi)
    return render_template_string(PROFIL_HTML, oyuncu=oyuncu_verisi)

# --- GÜVENLİ YÖNETİCİ SAYFALARI (SADECE ADMİN ERİŞEBİLİR) ---

@app.route('/admin')
def admin_paneli():
    # Güvenlik Kontrolü: Admin değilse login sayfasına at
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    oyuncular = tum_oyunculari_getir()
    return render_template_string(ADMIN_HTML, oyuncular=oyuncular)

@app.route('/admin/ekle', methods=['POST'])
def admin_oyuncu_ekle():
    # Güvenlik Kontrolü: Sadece admin ekleyebilir, oyuncular sızamaz
    if not session.get('admin'):
        return redirect(url_for('ana_sayfa'))
        
    username = request.form['username']
    kriptolu_sifre = generate_password_hash(request.form['sifre'])
    isim = request.form['isim']
    yas = request.form['yas']
    boy = request.form['boy']
    kilo = request.form['kilo']
    foto_url = request.form['foto_url']
    deneyimler = request.form['deneyimler']
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO oyuncular (username, sifre, isim, yas, boy, kilo, foto_url, deneyimler)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, kriptolu_sifre, isim, yas, boy, kilo, foto_url, deneyimler))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('admin_paneli'))

@app.route('/admin/sil/<username>')
def admin_oyuncu_sil(username):
    # Güvenlik Kontrolü: Sadece admin silebilir
    if not session.get('admin'):
        return redirect(url_for('ana_sayfa'))
        
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM oyuncular WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_paneli'))

@app.route('/logout')
def logout():
    session.pop('kullanici', None)
    session.pop('admin', None)
    return redirect(url_for('ana_sayfa'))

if __name__ == '__main__':
    veritabanini_hazirla()
    app.run(host='0.0.0.0', port=5000, debug=True)