import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'senin_cok_gizli_anahtarin'

# Veritabanı bağlantısı ve tablo oluşturma/güncelleme fonksiyonu
def get_db_connection():
    db_path = os.path.join(os.getcwd(), 'ajans.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def veritabani_hazirla():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Oyuncular tablosunu oluşturuyoruz (Eğer yoksa)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oyuncular (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # Eğer tablo önceden varsa ama yeni kolonlar yoksa, onları ekliyoruz (Migration)
    try:
        cursor.execute("ALTER TABLE oyuncular ADD COLUMN kullanici_adi TEXT UNIQUE")
    except sqlite3.OperationalError:
        pass  # Zaten varsa hata vermesini engelle

    try:
        cursor.execute("ALTER TABLE oyuncular ADD COLUMN sifre TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

veritabani_hazirla()

@app.route('/')
def index():
    conn = get_db_connection()
    oyuncular = conn.execute('SELECT * FROM oyuncular').fetchall()
    conn.close()
    return render_template('index.html', oyuncular=oyuncular)

# Ortak Giriş Sayfası (Yönetici ve Oyuncu Girişi)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')

        # 1. Yönetici Giriş Kontrolü
        if kullanici_adi == 'admin' and sifre == 'admin123':
            session['logged_in'] = True
            session['role'] = 'admin'
            flash('Yönetici olarak başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('index'))

        # 2. Oyuncu Giriş Kontrolü
        conn = get_db_connection()
        oyuncu = conn.execute('SELECT * FROM oyuncular WHERE kullanici_adi = ? AND sifre = ?', 
                              (kullanici_adi, sifre)).fetchone()
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

# Oyuncu Detay / Profil Sayfası
@app.route('/oyuncu/<int:id>')
def profil(id):
    conn = get_db_connection()
    oyuncu = conn.execute('SELECT * FROM oyuncular WHERE id = ?', (id,)).fetchone()
    conn.close()
    if oyuncu is None:
        flash('Oyuncu bulunamadı!', 'danger')
        return redirect(url_for('index'))
    return render_template('profil.html', oyuncu=oyuncu)

# Yönetici: Oyuncu Ekleme (Kullanıcı Adı ve Şifre Alanlarıyla Birlikte)
@app.route('/ekle', methods=['GET', 'POST'])
def ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Bu işlem için yönetici yetkisi gerekiyor!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        isim = request.form.get('isim')
        yas = request.form.get('yas')
        cinsiyet = request.form.get('cinsiyet')
        boy = request.form.get('boy')
        kilo = request.form.get('kilo')
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        sehir = request.form.get('sehir')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')
        deneyim = request.form.get('deneyim')
        kullanici_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO oyuncular (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, kullanici_adi, sifre)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (isim, yas, cinsiyet, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, kullanici_adi, sifre))
            conn.commit()
            flash('Yeni oyuncu ve giriş bilgileri başarıyla eklendi!', 'success')
        except sqlite3.IntegrityError:
            flash('Bu kullanıcı adı zaten alınmış! Lütfen farklı bir kullanıcı adı deneyin.', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('index'))

    return render_template('ekle.html')

# Oyuncu Kendi Profilini Düzenleme Fonksiyonu
@app.route('/profil/duzenle/<int:id>', methods=['GET', 'POST'])
def profil_duzenle(id):
    # Güvenlik kontrolü: Sadece admin veya o profilin asıl sahibi olan oyuncu düzenleyebilir
    if not session.get('logged_in'):
        flash('Önce giriş yapmalısınız!', 'danger')
        return redirect(url_for('login'))
        
    if session.get('role') == 'oyuncu' and session.get('oyuncu_id') != id:
        flash('Sadece kendi profilinizi düzenleyebilirsiniz!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    oyuncu = conn.execute('SELECT * FROM oyuncular WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        yas = request.form.get('yas')
        boy = request.form.get('boy')
        kilo = request.form.get('kilo')
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        sehir = request.form.get('sehir')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')
        deneyim = request.form.get('deneyim')
        sifre = request.form.get('sifre') # Şifresini de değiştirebilsin

        conn.execute('''
            UPDATE oyuncular 
            SET yas = ?, boy = ?, kilo = ?, goz_rengi = ?, sac_rengi = ?, sehir = ?, telefon = ?, eposta = ?, deneyim = ?, sifre = ?
            WHERE id = ?
        ''', (yas, boy, kilo, goz_rengi, sac_rengi, sehir, telefon, eposta, deneyim, sifre, id))
        conn.commit()
        conn.close()
        flash('Profil başarıyla güncellendi!', 'success')
        return redirect(url_for('profil', id=id))

    conn.close()
    return render_template('profil_duzenle.html', oyuncu=oyuncu)

# Oyuncu Silme (Sadece Admin yapabilir)
@app.route('/sil/<int:id>')
def sil(id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    conn.execute('DELETE FROM oyuncular WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Oyuncu kaydı başarıyla silindi.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)