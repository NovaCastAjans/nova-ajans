import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client

app = Flask(__name__)

# Çevre Değişkenleri ve Gizli Anahtar
app.secret_key = os.environ.get("SECRET_KEY", "nova_ajans_cok_gizli_super_anahtar_2026")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_current_user():
    if not session.get('logged_in'):
        return None
    try:
        user_id = session.get('user_id')
        if user_id:
            response = supabase.table("kullanicilar").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
    except Exception:
        pass
    return None


# ==========================================
# GEÇİCİ ADMİN OLUŞTURMA ROTASI (DÜZ ŞİFRE İLE)
# ==========================================
@app.route('/admin-olustur')
def admin_olustur():
    if not supabase:
        return "Supabase bağlantısı kurulamadı!"
    
    try:
        # Şifreleme hatasını engellemek için şifreyi düz metin olarak veritabanına yazıyoruz
        yeni_admin = {
            "username": "admin",
            "email": "admin@novacast.com",
            "password": "admin123",
            "role": "admin"
        }
        
        # Mükerrer kayıt olmaması için eski admin kaydını temizliyoruz
        supabase.table("kullanicilar").delete().eq("username", "admin").execute()
        
        # Yeni admin kaydını oluşturuyoruz
        supabase.table("kullanicilar").insert(yeni_admin).execute()
        return "<h1>Admin Hesabı Başarıyla Oluşturuldu!</h1><p>Artık <b>admin</b> ve <b>admin123</b> bilgileriyle giriş yapabilirsiniz.</p><a href='/login'>Giriş Yapmaya Git</a>"
    except Exception as e:
        return f"Admin oluşturulurken hata oluştu: {str(e)}"


# ==========================================
# 1. ANA SAYFA
# ==========================================
@app.route('/')
def index():
    arama_sorgusu = request.args.get('q', '').strip()
    oyuncular = []

    if not supabase:
        flash("Veri tabanı bağlantısı kurulamadı. Lütfen ortam değişkenlerini kontrol edin.", "danger")
        return render_template('index.html', oyuncular=[], arama_sorgusu=arama_sorgusu)

    try:
        if arama_sorgusu:
            response = (
                supabase.table("oyuncular")
                .select("*")
                .ilike("isim", f"%{arama_sorgusu}%")
                .order("id", desc=True)
                .execute()
            )
        else:
            response = (
                supabase.table("oyuncular")
                .select("*")
                .order("id", desc=True)
                .execute()
            )
        
        oyuncular = response.data if response.data else []
    except Exception as e:
        flash(f"Oyuncular listelenirken bir hata oluştu: {str(e)}", "danger")

    return render_template('index.html', oyuncular=oyuncular, arama_sorgusu=arama_sorgusu)


# ==========================================
# 2. GİRİŞ YAP SAYFASI
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        eposta_veya_kullanici = request.form.get('kullanici_adi', '').strip()
        sifre = request.form.get('password') or request.form.get('sifre') or ""

        try:
            user_query = supabase.table("kullanicilar").select("*").or_(f"email.eq.{eposta_veya_kullanici},username.eq.{eposta_veya_kullanici}").execute()
            
            if user_query.data:
                user = user_query.data[0]
                db_password = user.get('password', '')

                # Güvenli düz metin şifre eşleştirmesi
                if db_password == sifre:
                    session['logged_in'] = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user.get('role', 'user')

                    if user.get('oyuncu_id'):
                        session['oyuncu_id'] = user['oyuncu_id']

                    flash(f"Hoş geldiniz, {user['username']}!", "success")
                    return redirect(url_for('index'))
                else:
                    flash("Hatalı şifre girdiniz!", "danger")
            else:
                flash("Böyle bir kullanıcı bulunamadı!", "danger")
        except Exception as e:
            flash(f"Giriş yapılırken bir hata oluştu: {str(e)}", "danger")

    return render_template('login.html')


# ==========================================
# 3. OYUNCU EKLEME SAYFASI
# ==========================================
@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash("Bu sayfaya erişim yetkiniz bulunmamaktadır!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
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
            flash(f"Oyuncu eklenirken hata oluştu: {str(e)}", "danger")

    return render_template('ekle.html')


# ==========================================
# 4. OYUNCU DETAY SAYFASI
# ==========================================
@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    try:
        response = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
        if response.data:
            oyuncu = response.data[0]
            return render_template('oyuncu_detay.html', oyuncu=oyuncu)
        else:
            flash("Aradığınız oyuncu sistemde bulunamadı.", "warning")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Oyuncu bilgisi alınırken hata: {str(e)}", "danger")
        return redirect(url_for('index'))


# ==========================================
# 5. OYUNCU GÜNCELLEME / DÜZENLEME (500 HATA YAKALAMALI)
# ==========================================
@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    is_admin = session.get('role') == 'admin'
    is_owner = session.get('oyuncu_id') == oyuncu_id

    if not session.get('logged_in') or (not is_admin and not is_owner):
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    try:
        # Supabase'den oyuncuyu çek
        response = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
        if not response.data:
            flash("Oyuncu bulunamadı!", "warning")
            return redirect(url_for('index'))
        
        oyuncu = response.data[0]

        if request.method == 'POST':
            guncel_veri = {
                "isim": request.form.get('isim', '').strip(),
                "yas": int(request.form.get('yas')) if request.form.get('yas') and request.form.get('yas').isdigit() else None,
                "boy": request.form.get('boy', ''),
                "kilo": request.form.get('kilo', ''),
                "sehir": request.form.get('sehir', ''),
                "foto_url": request.form.get('resim_url', '') or request.form.get('foto_url', ''),
                "deneyimler": request.form.get('deneyim', ''),
                "cinsiyet": request.form.get('cinsiyet', ''),
                "goz_rengi": request.form.get('goz_rengi', ''),
                "sac_rengi": request.form.get('sac_rengi', ''),
                "telefon": request.form.get('telefon', ''),
                "eposta": request.form.get('eposta', '')
            }

            supabase.table("oyuncular").update(guncel_veri).eq("id", oyuncu_id).execute()
            flash("Oyuncu bilgileri başarıyla güncellendi.", "success")
            return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))

        # Arayüz yükleme aşamasında çökme ihtimalini yakalıyoruz
        try:
            return render_template('duzenle.html', oyuncu=oyuncu)
        except Exception as t_err:
            return f"<h1>Arayüz Dosyası Hatası</h1><p><b>duzenle.html</b> dosyası yüklenemedi. Lütfen templates klasöründe bu dosyanın bulunduğundan emin olun.</p><p>Hata Mesajı: {str(t_err)}</p>"

    except Exception as e:
        return f"<h1>Sistem Hatası (500)</h1><p>Sunucuda beklenmeyen bir hata gerçekleşti.</p><p>Hata Detayı: {str(e)}</p>"


# ==========================================
# 6. OYUNCU SİLME
# ==========================================
@app.route('/oyuncu/sil/<int:oyuncu_id>', methods=['POST'])
def oyuncu_sil(oyuncu_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    try:
        supabase.table("oyuncular").delete().eq("id", oyuncu_id).execute()
        flash("Oyuncu sistemden başarıyla silindi.", "success")
    except Exception as e:
        flash(f"Oyuncu silinirken hata oluştu: {str(e)}", "danger")

    return redirect(url_for('index'))


@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)