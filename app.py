import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client

app = Flask(__name__)

# --- GİZLİ ANAHTARLAR ---
app.secret_key = os.environ.get("SECRET_KEY", "gizli_anahtar_2026")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- YARDIMCI FONKSİYON ---
def get_current_user():
    if not session.get('logged_in'): return None
    user_id = session.get('user_id')
    return supabase.table("kullanicilar").select("*").eq("id", user_id).execute().data[0]

# --- ROTALAR ---

@app.route('/')
def index():
    oyuncular = supabase.table("oyuncular").select("*").execute().data
    return render_template('index.html', oyuncular=oyuncular)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eposta = request.form.get('kullanici_adi')
        sifre = request.form.get('password')
        user = supabase.table("kullanicilar").select("*").or_(f"email.eq.{eposta},username.eq.{eposta}").execute().data
        if user and user[0]['password'] == sifre:
            session.update({'logged_in': True, 'user_id': user[0]['id'], 'username': user[0]['username'], 'role': user[0].get('role'), 'oyuncu_id': user[0].get('oyuncu_id')})
            return redirect(url_for('index'))
        flash("Hatalı giriş")
    return render_template('login.html')

@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        yeni_oyuncu = {
            "isim": request.form.get('isim'),
            "yas": int(request.form.get('yas')) if request.form.get('yas') else None,
            "boy": request.form.get('boy'),
            "kilo": request.form.get('kilo'),
            "sehir": request.form.get('sehir'),
            "foto_url": request.form.get('resim_url'),
            "deneyim": request.form.get('deneyim'),
            "cinsiyet": request.form.get('cinsiyet'),
            "goz_rengi": request.form.get('goz_rengi'),
            "sac_rengi": request.form.get('sac_rengi'),
            "telefon": request.form.get('telefon'),
            "eposta": request.form.get('eposta')
        }
        supabase.table("oyuncular").insert(yeni_oyuncu).execute()
        return redirect(url_for('index'))
    return render_template('ekle.html')

@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # Veriyi çek
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    if not res.data: return "Oyuncu bulunamadı", 404
    oyuncu = res.data[0]
    
    if request.method == 'POST':
        guncel_veri = {
            "isim": request.form.get('isim'),
            "yas": int(request.form.get('yas')) if request.form.get('yas') else None,
            "boy": request.form.get('boy'),
            "kilo": request.form.get('kilo'),
            "sehir": request.form.get('sehir'),
            "foto_url": request.form.get('resim_url'),
            "deneyim": request.form.get('deneyim'),
            "cinsiyet": request.form.get('cinsiyet'),
            "goz_rengi": request.form.get('goz_rengi'),
            "sac_rengi": request.form.get('sac_rengi'),
            "telefon": request.form.get('telefon'),
            "eposta": request.form.get('eposta')
        }
        supabase.table("oyuncular").update(guncel_veri).eq("id", oyuncu_id).execute()
        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))
        
    return render_template('duzenle.html', oyuncu=oyuncu)

@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    oyuncu = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute().data[0]
    return render_template('oyuncu_detay.html', oyuncu=oyuncu)

@app.route('/oyuncu/sil/<int:oyuncu_id>', methods=['POST'])
def oyuncu_sil(oyuncu_id):
    supabase.table("oyuncular").delete().eq("id", oyuncu_id).execute()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))