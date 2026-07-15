import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

app = Flask(__name__)

# Çevre Değişkenleri
app.secret_key = os.environ.get("SECRET_KEY", "nova_ajans_cok_gizli_super_anahtar_2026")[cite: 1]
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_current_user():
    if not session.get('logged_in'):[cite: 4]
        return None
    try:
        user_id = session.get('user_id')[cite: 4]
        if user_id:
            response = supabase.table("kullanicilar").select("*").eq("id", user_id).execute()[cite: 4]
            if response.data:[cite: 4]
                return response.data[0][cite: 4]
    except Exception:
        pass
    return None


# ==========================================
# 1. ANA SAYFA (SIRALAMA DÜZELTİLDİ)
# ==========================================
@app.route('/')
def index():
    arama_sorgusu = request.args.get('q', '').strip()[cite: 4]
    oyuncular = []

    if not supabase:
        flash("Veri tabanı bağlantısı kurulamadı. Lütfen ortam değişkenlerini kontrol edin.", "danger")[cite: 4]
        return render_template('index.html', oyuncular=[], arama_sorgusu=arama_sorgusu)[cite: 4]

    try:
        # Arama sorgusu varsa filtreleyip "id"ye göre en yeni ekleneni en üstte gösterir
        if arama_sorgusu:
            response = (
                supabase.table("oyuncular")
                .select("*")
                .ilike("isim", f"%{arama_sorgusu}%")
                .order("id", desc=True)
                .execute()
            )
        # Arama sorgusu yoksa tüm oyuncuları en yeni eklenenden en eskiye doğru sıralar
        else:
            response = (
                supabase.table("oyuncular")
                .select("*")
                .order("id", desc=True)
                .execute()
            )
        
        oyuncular = response.data if response.data else [][cite: 4]
    except Exception as e:
        flash(f"Oyuncular listelenirken bir hata oluştu: {str(e)}", "danger")[cite: 4]

    return render_template('index.html', oyuncular=oyuncular, arama_sorgusu=arama_sorgusu)[cite: 4]


# ==========================================
# 2. GİRİŞ YAP SAYFASI (FORM UYUŞMAZLIĞI DÜZELTİLDİ)
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):[cite: 4]
        return redirect(url_for('index'))[cite: 4]

    if request.method == 'POST':
        # login.html'deki name="kullanici_adi" ile eşitlendi
        eposta_veya_kullanici = request.form.get('kullanici_adi', '').strip()
        sifre = request.form.get('password')[cite: 4]

        try:
            # Hem e-posta hem kullanıcı adı alanında ara
            user_query = supabase.table("kullanicilar").select("*").or_(f"email.eq.{eposta_veya_kullanici},username.eq.{eposta_veya_kullanici}").execute()[cite: 4]
            
            if user_query.data:[cite: 4]
                user = user_query.data[0][cite: 4]
                if check_password_hash(user['password'], sifre):[cite: 4]
                    session['logged_in'] = True[cite: 4]
                    session['user_id'] = user['id'][cite: 4]
                    session['username'] = user['username'][cite: 4]
                    session['role'] = user.get('role', 'user')[cite: 4]

                    if user.get('oyuncu_id'):[cite: 4]
                        session['oyuncu_id'] = user['oyuncu_id'][cite: 4]

                    flash(f"Hoş geldiniz, {user['username']}!", "success")[cite: 4]
                    return redirect(url_for('index'))[cite: 4]
                else:
                    flash("Hatalı şifre girdiniz!", "danger")[cite: 4]
            else:
                flash("Böyle bir kullanıcı bulunamadı!", "danger")[cite: 4]
        except Exception as e:
            flash(f"Giriş yapılırken bir hata oluştu: {str(e)}", "danger")[cite: 4]

    return render_template('login.html')[cite: 4]


# ==========================================
# 3. OYUNCU EKLEME SAYFASI (TABLO ŞEMASINA EŞİTLENDİ)
# ==========================================
@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':[cite: 4]
        flash("Bu sayfaya erişim yetkiniz bulunmamaktadır!", "danger")[cite: 4]
        return redirect(url_for('index'))[cite: 4]

    if request.method == 'POST':
        # ekle.html formundaki veriler ve SQLite/Supabase şeması eşleşti
        isim = request.form.get('isim')
        yas = request.form.get('yas')
        boy = request.form.get('boy')
        kilo = request.form.get('kilo')
        sehir = request.form.get('sehir')
        resim_url = request.form.get('resim_url')
        deneyimler = request.form.get('deneyim')
        cinsiyet = request.form.get('cinsiyet')
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')

        yeni_oyuncu = {
            "isim": isim,
            "yas": int(yas) if yas else None,
            "boy": boy,
            "kilo": kilo,
            "sehir": sehir,
            "foto_url": resim_url,
            "deneyimler": deneyimler,
            "cinsiyet": cinsiyet,
            "goz_rengi": goz_rengi,
            "sac_rengi": sac_rengi,
            "telefon": telefon,
            "eposta": eposta
        }

        try:
            supabase.table("oyuncular").insert(yeni_oyuncu).execute()
            flash(f"{isim} sisteme başarıyla eklendi.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Oyuncu eklenirken hata oluştu: {str(e)}", "danger")[cite: 4]

    return render_template('ekle.html')[cite: 4]


# ==========================================
# 4. OYUNCU DETAY SAYFASI
# ==========================================
@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    try:
        response = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()[cite: 4]
        if response.data:[cite: 4]
            oyuncu = response.data[0][cite: 4]
            return render_template('oyuncu_detay.html', oyuncu=oyuncu)[cite: 4]
        else:
            flash("Aradığınız oyuncu sistemde bulunamadı.", "warning")[cite: 4]
            return redirect(url_for('index'))[cite: 4]
    except Exception as e:
        flash(f"Oyuncu bilgisi alınırken hata: {str(e)}", "danger")[cite: 4]
        return redirect(url_for('index'))[cite: 4]


# ==========================================
# 5. OYUNCU GÜNCELLEME / DÜZENLEME
# ==========================================
@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    is_admin = session.get('role') == 'admin'[cite: 4]
    is_owner = session.get('oyuncu_id') == oyuncu_id[cite: 4]

    if not session.get('logged_in') or (not is_admin and not is_owner):[cite: 4]
        flash("Bu işlem için yetkiniz yok!", "danger")[cite: 4]
        return redirect(url_for('index'))[cite: 4]

    try:
        response = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()[cite: 4]
        if not response.data:[cite: 4]
            flash("Oyuncu bulunamadı!", "warning")[cite: 4]
            return redirect(url_for('index'))[cite: 4]
        
        oyuncu = response.data[0][cite: 4]

        if request.method == 'POST':
            guncel_veri = {
                "isim": request.form.get('isim'),
                "yas": int(request.form.get('yas')) if request.form.get('yas') else None,
                "boy": request.form.get('boy'),
                "kilo": request.form.get('kilo'),
                "sehir": request.form.get('sehir'),
                "foto_url": request.form.get('resim_url'),
                "deneyimler": request.form.get('deneyim'),
                "cinsiyet": request.form.get('cinsiyet'),
                "goz_rengi": request.form.get('goz_rengi'),
                "sac_rengi": request.form.get('sac_rengi'),
                "telefon": request.form.get('telefon'),
                "eposta": request.form.get('eposta')
            }

            supabase.table("oyuncular").update(guncel_veri).eq("id", oyuncu_id).execute()
            flash("Oyuncu bilgileri başarıyla güncellendi.", "success")[cite: 4]
            return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))[cite: 4]

    except Exception as e:
        flash(f"Güncelleme sırasında hata oluştu: {str(e)}", "danger")[cite: 4]
        return redirect(url_for('index'))[cite: 4]

    return render_template('duzenle.html', oyuncu=oyuncu)[cite: 4]


# ==========================================
# 6. OYUNCU SİLME
# ==========================================
@app.route('/oyuncu/sil/<int:oyuncu_id>', methods=['POST'])
def oyuncu_sil(oyuncu_id):
    if not session.get('logged_in') or session.get('role') != 'admin':[cite: 4]
        flash("Bu işlem için yetkiniz yok!", "danger")[cite: 4]
        return redirect(url_for('index'))[cite: 4]

    try:
        supabase.table("oyuncular").delete().eq("id", oyuncu_id).execute()[cite: 4]
        flash("Oyuncu sistemden başarıyla silindi.", "success")[cite: 4]
    except Exception as e:
        flash(f"Oyuncu silinirken hata oluştu: {str(e)}", "danger")[cite: 4]

    return redirect(url_for('index'))[cite: 4]


@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')[cite: 4]


@app.route('/logout')
def logout():
    session.clear()[cite: 4]
    flash("Başarıyla çıkış yaptınız.", "info")[cite: 4]
    return redirect(url_for('index'))[cite: 4]


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))[cite: 4]
    app.run(host='0.0.0.0', port=port, debug=True)[cite: 4]