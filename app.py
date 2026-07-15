import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

app = Flask(__name__)

# Güvenlik Anahtarı ve Supabase Ayarları (Render Çevre Değişkenleri ile Tam Uyumlu)
app.secret_key = os.environ.get("SECRET_KEY", "nova_cast_secret_key_987654")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- ORTAK KULLANICI BULMA FONKSİYONU ---
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
# 1. ANA SAYFA (SIRALAMA KURALI EKLENMİŞ HALİ)
# ==========================================
@app.route('/')
def index():
    arama_sorgusu = request.args.get('q', '').strip()
    oyuncular = []

    if not supabase:
        flash("Veri tabanı bağlantısı kurulamadı. Lütfen ortam değişkenlerini kontrol edin.", "danger")
        return render_template('index.html', oyuncular=[], arama_sorgusu=arama_sorgusu)

    try:
        # Arama sorgusu varsa filtreleyip en yeni eklenenden en eskiye doğru sıralıyoruz (order eklendi)
        if arama_sorgusu:
            response = (
                supabase.table("oyuncular")
                .select("*")
                .ilike("isim", f"%{arama_sorgusu}%")
                .order("id", desc=True)
                .execute()
            )
        # Arama sorgusu yoksa tüm oyuncuları en yeni eklenenden en eskiye sıralayarak getiriyoruz (order eklendi)
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
# 2. ÜYE OL / KAYIT OL SAYFASI
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        kullanici_adi = request.form.get('username', '').strip()
        eposta = request.form.get('email', '').strip()
        sifre = request.form.get('password')
        sifre_tekrar = request.form.get('password_confirm')

        if not kullanici_adi or not eposta or not sifre:
            flash("Lütfen tüm alanları doldurun.", "warning")
            return render_template('register.html')

        if sifre != sifre_tekrar:
            flash("Şifreler birbiriyle uyuşmuyor!", "danger")
            return render_template('register.html')

        hashed_password = generate_password_hash(sifre)

        try:
            # E-posta veya Kullanıcı adı önceden alınmış mı kontrol et
            check_user = supabase.table("kullanicilar").select("*").eq("email", eposta).execute()
            if check_user.data:
                flash("Bu e-posta adresi zaten kullanımda!", "danger")
                return render_template('register.html')

            yeni_kullanici = {
                "username": kullanici_adi,
                "email": eposta,
                "password": hashed_password,
                "role": "user"
            }

            # Kullanıcıyı ekle
            insert_response = supabase.table("kullanicilar").insert(yeni_kullanici).execute()
            
            if insert_response.data:
                flash("Kayıt işleminiz başarıyla tamamlandı! Giriş yapabilirsiniz.", "success")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"Kayıt esnasında bir hata oluştu: {str(e)}", "danger")

    return render_template('register.html')


# ==========================================
# 3. GİRİŞ YAP SAYFASI
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        # login.html'deki name="kullanici_adi" alanıyla tam uyumlu hale getirildi
        eposta_veya_kullanici = request.form.get('kullanici_adi', '').strip()
        sifre = request.form.get('password')

        try:
            # Hem e-posta hem kullanıcı adı alanında ara
            user_query = supabase.table("kullanicilar").select("*").or_(f"email.eq.{eposta_veya_kullanici},username.eq.{eposta_veya_kullanici}").execute()
            
            if user_query.data:
                user = user_query.data[0]
                if check_password_hash(user['password'], sifre):
                    session['logged_in'] = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user.get('role', 'user')

                    # Eğer bu kullanıcı bir oyuncu profiliyle ilişkiliyse
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
# 4. OYUNCU EKLEME SAYFASI (Yalnızca Admin)
# ==========================================
@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash("Bu sayfaya erişim yetkiniz bulunmamaktadır!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # ekle.html formundaki input "name" nitelikleri ve veritabanı sütunlarıyla eşleştirildi
        isim = request.form.get('isim')
        yas = request.form.get('yas')
        boy = request.form.get('boy')
        kilo = request.form.get('kilo')
        sehir = request.form.get('sehir')
        resim_url = request.form.get('resim_url')  # veya yüklenen dosya mantığı
        deneyimler = request.form.get('deneyim')
        cinsiyet = request.form.get('cinsiyet')
        goz_rengi = request.form.get('goz_rengi')
        sac_rengi = request.form.get('sac_rengi')
        telefon = request.form.get('telefon')
        eposta = request.form.get('eposta')

        yeni_oyuncu = {
            "isim": isim,
            "yas": int(yas) if yas else None,
            "boy": int(boy) if boy else None,
            "kilo": int(kilo) if kilo else None,
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
# 5. OYUNCU DETAY SAYFASI
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
# 6. OYUNCU GÜNCELLEME / DÜZENLEME
# ==========================================
@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    # Yetki kontrolü: Yalnızca admin veya profilin gerçek sahibi düzenleyebilir
    is_admin = session.get('role') == 'admin'
    is_owner = session.get('oyuncu_id') == oyuncu_id

    if not session.get('logged_in') or (not is_admin and not is_owner):
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    try:
        # Mevcut bilgileri çek
        response = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
        if not response.data:
            flash("Oyuncu bulunamadı!", "warning")
            return redirect(url_for('index'))
        
        oyuncu = response.data[0]

        if request.method == 'POST':
            # Veritabanı şemasıyla birebir uyumlu alanlar güncelleniyor
            guncel_veri = {
                "isim": request.form.get('isim'),
                "yas": int(request.form.get('yas')) if request.form.get('yas') else None,
                "boy": int(request.form.get('boy')) if request.form.get('boy') else None,
                "kilo": int(request.form.get('kilo')) if request.form.get('kilo') else None,
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
            flash("Oyuncu bilgileri başarıyla güncellendi.", "success")
            return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))

    except Exception as e:
        flash(f"Güncelleme sırasında hata oluştu: {str(e)}", "danger")
        return redirect(url_for('index'))

    return render_template('duzenle.html', oyuncu=oyuncu)


# ==========================================
# 7. OYUNCU SİLME (Yalnızca Admin)
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


# ==========================================
# 8. HAKKIMIZDA VE YARDIMCI SAYFALAR
# ==========================================
@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')


# ==========================================
# 9. GÜVENLİ ÇIKIŞ İŞLEMİ
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for('index'))


# ==========================================
# 10. UYGULAMA ÇALIŞTIRMA (PORT DİNAMİK)
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)