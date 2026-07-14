import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "nova_gizli_anahtar_12345")

# Render üzerindeki kalıcı disk klasörü veya yerel klasör
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================================================================
# VERİTABANI VE TABLOLARI SIFIRDAN OTOMATİK KURAN MEKANİZMA
# =========================================================================
def veritabanini_kur():
    db_yolu = "ajans.db"
    conn = sqlite3.connect(db_yolu)
    cursor = conn.cursor()
    
    # 1. Oyuncular Tablosu (Sitenin ana tablosu)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oyuncular (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        yas INTEGER,
        cinsiyet TEXT,
        boy INTEGER,
        kilo INTEGER,
        goz_rengi TEXT,
        sac_rengi TEXT,
        deneyim TEXT,
        foto_yolu TEXT,
        telefon TEXT,
        eposta TEXT,
        sehir TEXT
    )
    """)
    
    # 2. Kullanıcılar/Yöneticiler Tablosu (Giriş paneli için)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT UNIQUE NOT NULL,
        sifre TEXT NOT NULL,
        yetki TEXT DEFAULT 'user'
    )
    """)
    
    # Eğer hiç kullanıcı yoksa varsayılan admin ekleyelim
    cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO kullanicilar (kullanici_adi, sifre, yetki) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin")
        )
        
    conn.commit()
    conn.close()
    print("Veritabanı ve tablolar başarıyla kuruldu!")

# Uygulama açılırken veritabanını hazırla
try:
    veritabanini_kur()
except Exception as e:
    print("Veritabanı başlatılırken hata oluştu:", e)

def get_db_connection():
    conn = sqlite3.connect("ajans.db")
    conn.row_factory = sqlite3.Row
    return conn

# =========================================================================
# SAYFA YÖNLENDİRMELERİ (ROUTES)
# =========================================================================

# 1. Ana Sayfa (Oyuncu Listesi)
@app.route('/')
def ana_sayfa():
    conn = get_db_connection()
    oyuncular = conn.execute("SELECT * FROM oyuncular").fetchall()
    conn.close()
    return render_template('index.html', oyuncular=oyuncular)

# 2. Oyuncu Detay Sayfası
@app.route('/oyuncu/<int:id>')
def oyuncu_detay(id):
    conn = get_db_connection()
    oyuncu = conn.execute("SELECT * FROM oyuncular WHERE id = ?", (id,)).fetchone()
    conn.close()
    if oyuncu is None:
        flash("Oyuncu bulunamadı!", "danger")
        return redirect(url_for('ana_sayfa'))
    return render_template('profil.html', oyuncu=oyuncu)

# 3. Yönetici Giriş Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?",
            (kullanici_adi, sifre)
        ).fetchone()
        conn.close()
        
        # Çevre değişkenlerinden gelen admin kontrolü
        env_admin = os.environ.get("ADMIN_USER", "emirhan")
        env_pass = os.environ.get("ADMIN_PASS", "emirhan41")
        
        if user or (kullanici_adi == env_admin and sifre == env_pass):
            session['logged_in'] = True
            session['username'] = kullanici_adi
            flash("Başarıyla giriş yaptınız!", "success")
            return redirect(url_for('ana_sayfa'))
        else:
            flash("Hatalı kullanıcı adı veya şifre!", "danger")
            
    return render_template('login.html')

# 4. Çıkış Yap
@app.route('/logout')
def logout():
    session.clear()
    flash("Oturum kapatıldı.", "info")
    return redirect(url_for('ana_sayfa'))

# 5. Yeni Oyuncu Ekleme (Sadece Giriş Yapmış Kullanıcılar)
@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in'):
        flash("Bu işlem için giriş yapmalısınız!", "warning")
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        isim = request.form['isim']
        yas = request.form['yas']
        cinsiyet = request.form['cinsiyet']
        boy = request.form['boy']
        kilo = request.form['kilo']
        goz_rengi = request.form['goz_rengi']
        sac_rengi = request.form['sac_rengi']
        deneyim = request.form['deneyim']
        telefon = request.form['telefon']
        eposta = request.form['eposta']
        sehir = request.form['sehir']
        
        # Fotoğraf yükleme işlemleri
        foto_yolu = "default.jpg"
        if 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto_yolu = filename

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO oyuncular (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, deneyim, foto_yolu, telefon, eposta, sehir)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, deneyim, foto_yolu, telefon, eposta, sehir))
        conn.commit()
        conn.close()
        
        flash("Yeni oyuncu başarıyla eklendi!", "success")
        return redirect(url_for('ana_sayfa'))
        
    return render_template('ekle.html')

# 6. Oyuncu Silme
@app.route('/sil/<int:id>')
def oyuncu_sil(id):
    if not session.get('logged_in'):
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute("DELETE FROM oyuncular WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Oyuncu başarıyla silindi.", "success")
    return redirect(url_for('ana_sayfa'))

if __name__ == '__main__':
    # Render üzerinde PORT çevre değişkeni kullanılır, yerelde 5000 portu
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)