import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client

app = Flask(__name__)
# Render üzerindeki SECRET_KEY değişkenini önceliklendir
app.secret_key = os.environ.get("SECRET_KEY", "nova_ajans_cok_gizli_super_anahtar_2026")

# Supabase Bağlantısı
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

@app.route('/')
def index():
    arama = request.args.get('q', '')
    query = supabase.table("oyuncular").select("*")
    if arama:
        query = query.ilike("isim", f"%{arama}%")
    res = query.execute()
    return render_template('index.html', oyuncular=res.data, arama_sorgusu=arama)

@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        k_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        # Kullanıcı kontrolü
        user = supabase.table("kullanicilar").select("*").eq("kullanici_adi", k_adi).execute().data
        if user and user[0].get('sifre') == sifre:
            session.update({'logged_in': True, 'role': user[0].get('yetki'), 'oyuncu_id': user[0].get('oyuncu_id')})
            return redirect(url_for('index'))
        flash("Hatalı kullanıcı adı veya şifre", "danger")
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
            "deneyimler": request.form.get('deneyim'),
            "cinsiyet": request.form.get('cinsiyet'),
            "telefon": request.form.get('telefon'),
            "eposta": request.form.get('eposta')
        }
        supabase.table("oyuncular").insert(yeni_oyuncu).execute()
        return redirect(url_for('index'))
    return render_template('ekle.html')

@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    if not res.data: return "Oyuncu bulunamadı", 404
    return render_template('oyuncu_detay.html', oyuncu=res.data[0])

@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        guncel = {
            "isim": request.form.get('isim'),
            "yas": int(request.form.get('yas')) if request.form.get('yas') else None,
            "boy": request.form.get('boy'),
            "kilo": request.form.get('kilo'),
            "deneyimler": request.form.get('deneyim')
        }
        supabase.table("oyuncular").update(guncel).eq("id", oyuncu_id).execute()
        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))
    
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    return render_template('duzenle.html', oyuncu=res.data[0])

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