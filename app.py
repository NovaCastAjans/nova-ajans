import os
import uuid
import math
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client
from dotenv import load_dotenv

# .env dosyasındaki gizli anahtarları yükle
load_dotenv()

app = Flask(__name__)
# Gizli anahtarı çevre değişkenlerinden güvenli bir şekilde alıyoruz
app.secret_key = os.getenv("SECRET_KEY", "nova_ajans_varsayilan_anahtar_2026")

# Supabase bağlantı bilgileri (.env dosyasından çekiliyor)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Boş veya hatalı sayısal girdileri veritabanı için None (NULL) yapan yardımcı fonksiyon
def safe_int(val):
    if not val or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

@app.route('/')
def index():
    # URL'den gelen sayfa numarası (varsayılan: 1)
    page = int(request.args.get('page', 1))
    per_page = 16 # Her sayfada gösterilecek oyuncu sayısı
    
    # Filtre Parametreleri
    arama = request.args.get('q', '')
    cinsiyet = request.args.get('cinsiyet', '')
    yas_min = safe_int(request.args.get('yas_min'))
    yas_max = safe_int(request.args.get('yas_max'))
    sehir = request.args.get('sehir', '')
    
    # count="exact" ile toplam kayıt sayısını da istiyoruz
    query = supabase.table("oyuncular").select("*", count="exact")
    
    # Filtreleri Uygula
    if arama:
        query = query.ilike("isim", f"%{arama}%")
    if cinsiyet:
        query = query.eq("cinsiyet", cinsiyet)
    if yas_min is not None:
        query = query.gte("yas", yas_min)
    if yas_max is not None:
        query = query.lte("yas", yas_max)
    if sehir:
        query = query.ilike("sehir", f"%{sehir}%")
        
    # Sayfalandırma (Pagination) Limit ve Offset Ayarı
    start = (page - 1) * per_page
    end = start + per_page - 1
    query = query.range(start, end)
        
    res = query.execute()
    
    all_players = res.data if res.data else []
    
    # Toplam sayfa sayısını hesapla
    total_count = res.count if hasattr(res, 'count') and res.count is not None else len(all_players)
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    
    kurucu = None
    oyuncular_listesi = []
    
    # ID'si 29 olan "Kurucu" profilini ayırıp özel bölüme, diğerlerini genel listeye gönderiyoruz
    for o in all_players:
        if o.get('id') == 29:
            kurucu = o
        else:
            oyuncular_listesi.append(o)
            
    # Eğer arama yapıldıysa ve kurucu arama kriterine uymuyorsa kurucu bölümünü gizle
    if arama and kurucu:
        if arama.lower() not in kurucu.get('isim', '').lower():
            kurucu = None
            
    return render_template('index.html', 
                           oyuncular=oyuncular_listesi, 
                           kurucu=kurucu, 
                           arama_sorgusu=arama, 
                           secili_cinsiyet=cinsiyet,
                           yas_min=yas_min if yas_min is not None else '',
                           yas_max=yas_max if yas_max is not None else '',
                           secili_sehir=sehir,
                           current_page=page,
                           total_pages=total_pages)

@app.route('/basvuru', methods=['GET', 'POST'])
def basvuru():
    if request.method == 'POST':
        yeni_basvuru = {
            "isim": request.form.get('isim'),
            "yas": safe_int(request.form.get('yas')),
            "boy": safe_int(request.form.get('boy')),
            "telefon": request.form.get('telefon'),
            "deneyim": request.form.get('deneyim')
        }
        supabase.table("basvurular").insert(yeni_basvuru).execute()
        flash("Başvurunuz alındı, teşekkürler!", "success")
        return redirect(url_for('index'))
    return render_template('basvuru.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        k_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        
        user = supabase.table("kullanicilar").select("*").ilike("kullanici_adi", k_adi).execute().data
        
        if user and str(user[0].get('sifre')) == str(sifre):
            yetki = user[0].get('yetki', 'admin') 
            oyuncu_id = user[0].get('id', None) 
            
            session.update({'logged_in': True, 'role': yetki, 'oyuncu_id': oyuncu_id, 'kullanici_adi': k_adi})
            return redirect(url_for('index'))
        else:
            flash("Hatalı kullanıcı adı veya şifre", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/ekle', methods=['GET', 'POST'])
def oyuncu_ekle():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        resim_url = None
        file = request.files.get('resim')
        
        if file and file.filename != '':
            try:
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                file_data = file.read()
                
                supabase.storage.from_("oyuncu-resimleri").upload(
                    path=filename,
                    file=file_data,
                    file_options={"content-type": file.content_type}
                )
                
                resim_url_res = supabase.storage.from_("oyuncu-resimleri").get_public_url(filename)
                if isinstance(resim_url_res, str):
                    resim_url = resim_url_res
                else:
                    resim_url = getattr(resim_url_res, 'public_url', str(resim_url_res))
            except Exception as e:
                flash(f"Resim yüklenirken bir hata oluştu: {str(e)}", "danger")

        yeni_oyuncu = {
            "isim": request.form.get('isim'),
            "yas": safe_int(request.form.get('yas')),
            "cinsiyet": request.form.get('cinsiyet'),
            "boy": safe_int(request.form.get('boy')),
            "kilo": safe_int(request.form.get('kilo')),
            "goz_rengi": request.form.get('goz_rengi'),
            "sac_rengi": request.form.get('sac_rengi'),
            "sehir": request.form.get('sehir'),
            "telefon": request.form.get('telefon'),
            "eposta": request.form.get('eposta'),
            "deneyim": request.form.get('deneyim'),
            "resim_url": resim_url
        }
        
        oyuncu_res = supabase.table("oyuncular").insert(yeni_oyuncu).execute()
        
        if oyuncu_res.data:
            yeni_oyuncu_id = oyuncu_res.data[0]['id']
            k_adi = request.form.get('kullanici_adi')
            sifre = request.form.get('sifre')
            
            if k_adi and sifre:
                yeni_kullanici = {
                    "kullanici_adi": k_adi,
                    "sifre": sifre,
                    "yetki": "oyuncu",
                    "id": yeni_oyuncu_id 
                }
                supabase.table("kullanicilar").insert(yeni_kullanici).execute()
                
        return redirect(url_for('index'))
    return render_template('ekle.html')

@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    
    if session.get('role') != 'admin' and session.get('oyuncu_id') != oyuncu_id:
        flash("Bu profili düzenleme yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        guncel = {
            "isim": request.form.get('isim'),
            "yas": safe_int(request.form.get('yas')),
            "cinsiyet": request.form.get('cinsiyet'),
            "boy": safe_int(request.form.get('boy')),
            "kilo": safe_int(request.form.get('kilo')),
            "goz_rengi": request.form.get('goz_rengi'),
            "sac_rengi": request.form.get('sac_rengi'),
            "sehir": request.form.get('sehir'),
            "telefon": request.form.get('telefon'),
            "eposta": request.form.get('eposta'),
            "deneyim": request.form.get('deneyim')
        }
        
        file = request.files.get('resim')
        if file and file.filename != '':
            try:
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                file_data = file.read()
                
                supabase.storage.from_("oyuncu-resimleri").upload(
                    path=filename,
                    file=file_data,
                    file_options={"content-type": file.content_type}
                )
                
                resim_url_res = supabase.storage.from_("oyuncu-resimleri").get_public_url(filename)
                if isinstance(resim_url_res, str):
                    guncel["resim_url"] = resim_url_res
                else:
                    guncel["resim_url"] = getattr(resim_url_res, 'public_url', str(resim_url_res))
            except Exception as e:
                flash(f"Yeni resim yüklenirken hata oluştu: {str(e)}", "danger")

        supabase.table("oyuncular").update(guncel).eq("id", oyuncu_id).execute()
        
        k_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        
        if k_adi and sifre:
            mevcut_kullanici = supabase.table("kullanicilar").select("*").eq("id", oyuncu_id).execute().data
            if mevcut_kullanici:
                supabase.table("kullanicilar").update({
                    "kullanici_adi": k_adi,
                    "sifre": sifre
                }).eq("id", oyuncu_id).execute()
            else:
                supabase.table("kullanicilar").insert({
                    "kullanici_adi": k_adi,
                    "sifre": sifre,
                    "yetki": "oyuncu",
                    "id": oyuncu_id
                }).execute()

        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))
    
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    oyuncu_veri = res.data[0]
    
    kullanici_res = supabase.table("kullanicilar").select("*").eq("id", oyuncu_id).execute()
    kullanici_veri = kullanici_res.data[0] if kullanici_res.data else {}
    
    return render_template('duzenle.html', oyuncu=oyuncu_veri, kullanici=kullanici_veri)

@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    return render_template('oyuncu_detay.html', oyuncu=res.data[0])

@app.route('/oyuncu/sil/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_sil(oyuncu_id):
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    
    if session.get('role') != 'admin':
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for('index'))
        
    supabase.table("kullanicilar").delete().eq("id", oyuncu_id).execute()
    supabase.table("oyuncular").delete().eq("id", oyuncu_id).execute()
    return redirect(url_for('index'))

@app.route('/hakkimizda')
def hakkimizda():
    res = supabase.table("sayfalar").select("*").eq("sayfa_adi", "hakkimizda").execute()
    sayfa_verisi = res.data[0] if res.data else {"baslik": "Hakkımızda", "icerik": "HAKIMIZDA"}
    return render_template('hakkimizda.html', sayfa=sayfa_verisi)

@app.route('/admin/duzenle/<sayfa_adi>', methods=['GET', 'POST'])
def admin_duzenle(sayfa_adi):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        yeni_baslik = request.form.get('baslik')
        yeni_icerik = request.form.get('icerik')
        
        kontrol = supabase.table("sayfalar").select("*").eq("sayfa_adi", sayfa_adi).execute()
        
        if kontrol.data:
            supabase.table("sayfalar").update({
                "baslik": yeni_baslik,
                "icerik": yeni_icerik
            }).eq("sayfa_adi", sayfa_adi).execute()
        else:
            supabase.table("sayfalar").insert({
                "sayfa_adi": sayfa_adi,
                "baslik": yeni_baslik,
                "icerik": yeni_icerik
            }).execute()
        
        flash(f"{sayfa_adi} sayfası güncellendi!", "success")
        return redirect(url_for('hakkimizda')) 

    res = supabase.table("sayfalar").select("*").eq("sayfa_adi", sayfa_adi).execute()
    mevcut_veri = res.data[0] if res.data else {"baslik": "", "icerik": ""}
    return render_template('admin_duzenle.html', sayfa_adi=sayfa_adi, veri=mevcut_veri)

# ================= YENİ: BAŞVURU YÖNETİMİ =================
@app.route('/admin/basvurular')
def admin_basvurular():
    if session.get('role') != 'admin':
        flash("Bu sayfayı görüntüleme yetkiniz yok.", "danger")
        return redirect(url_for('index'))
    
    # En yeni başvuru en üstte gözüksün diye id'ye göre azalan (desc) sıraladık
    res = supabase.table("basvurular").select("*").order("id", desc=True).execute()
    return render_template('basvurular.html', basvurular=res.data)

@app.route('/admin/basvurular/sil/<int:b_id>', methods=['POST'])
def basvuru_sil(b_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    supabase.table("basvurular").delete().eq("id", b_id).execute()
    flash("Başvuru reddedildi ve listeden kaldırıldı.", "success")
    return redirect(url_for('admin_basvurular'))
# app.py dosyasında herhangi bir yere ekleyebilirsin
@app.route('/ping')
def ping():
    return "Pong! Site uyanık.", 200
if __name__ == '__main__':
    app.run(debug=True, port=5000)