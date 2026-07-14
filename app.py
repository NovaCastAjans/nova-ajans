import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'senin_cok_gizli_anahtarin'

# Render'a eklediğimiz DATABASE_URL linkini yakalıyoruz, bulamazsa hata vermemesi için geçici bir boşluk veriyoruz
DATABASE_URL = os.environ.get('DATABASE_URL')

# Supabase PostgreSQL Bağlantı Fonksiyonu
def get_db_connection():
    if not DATABASE_URL:
        # Eğer bilgisayarda denerken link yoksa hata vermesini önlemek için yerel kontrol
        raise Exception("DATABASE_URL ortam değişkeni bulunamadı. Lütfen Render ortamını veya .env dosyasını kontrol edin.")
    
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Supabase üzerinde tabloları otomatik hazırlayan fonksiyon
def veritabani_hazirla():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Oyuncular tablosunu PostgreSQL uyumlu oluşturuyoruz
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oyuncular (
            id SERIAL PRIMARY KEY,
            isim TEXT NOT NULL,
            yas INTEGER,
            cinsiyet TEXT,
            boy INTEGER,
            kilo INTEGER,
            goz_rengi TEXT,
            sac_rengi TEXT,
            sehir TEXT,
            telefon TEXT,
            eposta TEXT,
            deneyim TEXT,
            kullanici_adi TEXT UNIQUE,
            sifre TEXT
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Uygulama ayağa kalktığında veritabanı otomatik tetiklensin
try:
    veritabani_hazirla()
except Exception as e:
    print(f"Veritabanı kurulum hatası: {e}")

@app.route('/')
def index():
    arama_sorgusu = request.args.get('q', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    if arama_sorgusu:
        # PostgreSQL'de büyük/küçük harf duyarlılığını aşmak için ILIKE kullanıyoruz
        cursor.execute(
            'SELECT * FROM oyuncular WHERE isim ILIKE %s', 
            ('%' + arama_sorgusu + '%',)
        )
        oyuncular = cursor.fetchall()
    else:
        cursor.execute('SELECT * FROM oyuncular')
        oyuncular = cursor.fetchall()
        
    cursor.close()
    conn.close()
    
    return render_template('index.html', oyuncular=oyuncular, arama_sorgusu=arama_sorgusu)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')

        if kullanici_adi == 'admin' and sifre == 'admin123':
            session['logged_in'] = True
            session['role'] = 'admin'
            flash('Yönetici olarak başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('index'))

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM oyuncular WHERE kullanici_adi = %s AND sifre = %s', 
                       (kullanici_adi, sifre))
        oyuncu = cursor.fetchone()
        cursor.close()
        conn.close()

        if oyuncu:
            session['logged_in'] = True
            session['role'] = 'oyuncu'
            session['oyuncu_id'] = oyuncu['id']
            session['oyuncu_isim'] = oyuncu['isim']
            flash(f'Hoş geldiniz, {oyuncu["isim"]}!', 'success')
            return redirect(url_for('profil', id=oyuncu['id']))
        else:
            flash('Hatalı kullanıcı adı veya şifre!', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yapıldı.', 'info')
    return redirect(url_for('index'))

@app.route('/oyuncu/<int:id>')
def profil(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM oyuncular WHERE id = %s', (id,))
    oyuncu = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if oyuncu is None:
        flash('Oyuncu bulunamadı!', 'danger')
        return redirect(url_for('index'))
    return render_template('profil.html', oyuncu=oyuncu)

@app.route('/ekle', methods=['GET', 'POST'])
def ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Bu işlem için yönetici yetkisi gerekiyor!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        isim = request.form.get('isim')
        yas = request.form.get('yas') if request.form.get('yas') else None
        cinsiyet = request.form.get('cinsiyet')
        boy = request.form.get('boy') if request.form.get('boy') else None
        kilo = request.form.get('kilo') if request.form.get('kilo') else None
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        sehir = request.form.get('sehir')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')
        deneyim = request.form.get('deneyim')
        kullanici_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO oyuncular (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, kullanici_adi, sifre)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, kullanici_adi, sifre))
            conn.commit()
            flash('Yeni oyuncu ve giriş bilgileri başarıyla eklendi!', 'success')
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Bu kullanıcı adı zaten alınmış! Lütfen farklı bir kullanıcı adı deneyin.', 'danger')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('index'))

    return render_template('ekle.html')

@app.route('/profil/duzenle/<int:id>', methods=['GET', 'POST'])
def profil_duzenle(id):
    if not session.get('logged_in'):
        flash('Önce giriş yapmalısınız!', 'danger')
        return redirect(url_for('login'))
        
    if session.get('role') == 'oyuncu' and session.get('oyuncu_id') != id:
        flash('Sadece kendi profilinizi düzenleyebilirsiniz!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM oyuncular WHERE id = %s', (id,))
    oyuncu = cursor.fetchone()

    if request.method == 'POST':
        yas = request.form.get('yas') if request.form.get('yas') else None
        boy = request.form.get('boy') if request.form.get('boy') else None
        kilo = request.form.get('kilo') if request.form.get('kilo') else None
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        sehir = request.form.get('sehir')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')
        deneyim = request.form.get('deneyim')
        sifre = request.form.get('sifre')

        cursor.execute('''
            UPDATE oyuncular 
            SET yas = %s, boy = %s, kilo = %s, goz_rengi = %s, sac_rengi = %s, sehir = %s, telefon = %s, eposta = %s, deneyim = %s, sifre = %s
            WHERE id = %s
        ''', (yas, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, sifre, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Profil başarıyla güncellendi!', 'success')
        return redirect(url_for('profil', id=id))

    cursor.close()
    conn.close()
    return render_template('profil_duzenle.html', oyuncu=oyuncu)

@app.route('/sil/<int:id>')
def sil(id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM oyuncular WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Oyuncu kaydı başarıyla silindi.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)