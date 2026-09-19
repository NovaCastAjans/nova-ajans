import os
import base64
import uuid
import math
import random
import string
import ssl
import httpx
import pdfkit
import secrets
from datetime import date, datetime, timedelta
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from werkzeug.utils import secure_filename
from supabase import create_client, AsyncClientOptions
from dotenv import load_dotenv
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, grey, lightgrey, darkblue, navy
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
from PIL import Image
import time

os.environ['CURL_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nova_ajans_varsayilan_anahtar_2026")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

options = AsyncClientOptions()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

if SUPABASE_SERVICE_KEY:
    admin_options = AsyncClientOptions()
    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=admin_options)
else:
    supabase_admin = supabase

requests.packages.urllib3.disable_warnings()
import urllib3
urllib3.disable_warnings()

FONT_NAME = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_PATH = os.path.join("static", "fonts", "DejaVuSans.ttf")
if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_PATH))
        bold_path = FONT_PATH.replace('.ttf', '-Bold.ttf')
        if os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', bold_path))
            FONT_BOLD = 'DejaVu-Bold'
        FONT_NAME = 'DejaVu'
    except:
        pass

WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)


def safe_int(val):
    if not val or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def sertifika_kodu_uret():
    yil = datetime.now().year
    rastgele = secrets.token_hex(4).upper()
    return f"NCA-{yil}-{rastgele}"


@app.before_request
def log_page_view():
    if request.endpoint and not request.endpoint.startswith('static') and request.endpoint != 'ping':
        sayfa_adi = request.path
        oyuncu_id = None
        if request.endpoint == 'oyuncu_detay':
            oyuncu_id = request.view_args.get('oyuncu_id')
        ziyaretci_ip = request.remote_addr
        try:
            supabase.table('sayfa_goruntulenme').insert({
                'sayfa_adi': sayfa_adi,
                'oyuncu_id': oyuncu_id,
                'ziyaretci_ip': ziyaretci_ip
            }).execute()
        except Exception:
            pass


@app.route('/')
def index():
    page = int(request.args.get('page', 1))
    per_page = 16
    arama = request.args.get('q', '')
    cinsiyet = request.args.get('cinsiyet', '')
    yas_min = safe_int(request.args.get('yas_min'))
    yas_max = safe_int(request.args.get('yas_max'))
    sehir = request.args.get('sehir', '')

    meta_res = supabase.table('meta').select('*').eq('sayfa_adi', 'index').execute()
    meta = meta_res.data[0] if meta_res.data else None

    kurucu_res = supabase.table("oyuncular").select("*").eq("id", 29).execute()
    kurucu = kurucu_res.data[0] if kurucu_res.data else None
    if arama and kurucu:
        if arama.lower() not in kurucu.get('isim', '').lower():
            kurucu = None

    query = supabase.table("oyuncular").select("*", count="exact")
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

    start = (page - 1) * per_page
    end = start + per_page - 1
    query = query.range(start, end)
    res = query.execute()
    all_players = res.data if res.data else []
    total_count = res.count if hasattr(res, 'count') and res.count is not None else len(all_players)
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    oyuncular_listesi = [o for o in all_players if o.get('id') != 29]

    vitrin_oyuncular = []
    if page == 1:
        vitrin_query = supabase.table("oyuncular").select("*").eq("vitrin", True).limit(15)
        vitrin_res = vitrin_query.execute()
        vitrin_oyuncular = vitrin_res.data if vitrin_res.data else []

    return render_template('index.html',
                           oyuncular=oyuncular_listesi,
                           vitrin_oyuncular=vitrin_oyuncular,
                           kurucu=kurucu,
                           arama_sorgusu=arama,
                           secili_cinsiyet=cinsiyet,
                           yas_min=yas_min if yas_min is not None else '',
                           yas_max=yas_max if yas_max is not None else '',
                           secili_sehir=sehir,
                           current_page=page,
                           total_pages=total_pages,
                           meta=meta)


@app.route('/basvuru', methods=['GET', 'POST'])
def basvuru():
    meta_res = supabase.table('meta').select('*').eq('sayfa_adi', 'basvuru').execute()
    meta = meta_res.data[0] if meta_res.data else None

    if request.method == 'POST':
        foto_url = None
        foto = request.files.get('foto')
        if foto and foto.filename != '':
            try:
                ext = os.path.splitext(foto.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    filename = f"basvuru_{uuid.uuid4()}{ext}"
                    foto_data = foto.read()
                    supabase.storage.from_("basvuru-fotolari").upload(
                        path=filename,
                        file=foto_data,
                        file_options={"content-type": foto.content_type}
                    )
                    foto_url_res = supabase.storage.from_("basvuru-fotolari").get_public_url(filename)
                    if isinstance(foto_url_res, str):
                        foto_url = foto_url_res
                    elif isinstance(foto_url_res, dict):
                        foto_url = foto_url_res.get('publicUrl') or foto_url_res.get('publicURL')
                    else:
                        foto_url = str(foto_url_res)
            except Exception as e:
                print(f"Fotograf yukleme hatasi: {e}")
        yeni_basvuru = {
            "isim": request.form.get('isim'),
            "yas": safe_int(request.form.get('yas')),
            "boy": safe_int(request.form.get('boy')),
            "telefon": request.form.get('telefon'),
            "deneyim": request.form.get('deneyim'),
            "foto_url": foto_url
        }
        supabase.table("basvurular").insert(yeni_basvuru).execute()
        flash("Başvurunuz alındı, teşekkürler!", "success")
        return redirect(url_for('index'))
    return render_template('basvuru.html', meta=meta)


@app.route('/login', methods=['GET', 'POST'])
def login():
    meta_res = supabase.table('meta').select('*').eq('sayfa_adi', 'login').execute()
    meta = meta_res.data[0] if meta_res.data else None

    if request.method == 'POST':
        k_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        user = supabase.table("kullanicilar").select("*").ilike("kullanici_adi", k_adi).execute().data
        if user:
            if str(user[0].get('sifre')) == str(sifre):
                yetki = user[0].get('yetki', 'admin')
                raw_id = user[0].get('id')
                oyuncu_id = int(raw_id) if raw_id else None
                session['logged_in'] = True
                session['role'] = yetki
                session['oyuncu_id'] = oyuncu_id
                session['kullanici_adi'] = k_adi
                session.modified = True
                return redirect(url_for('index'))
        flash("Hatalı kullanıcı adı veya şifre", "danger")
    return render_template('login.html', meta=meta)


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
                resim_url = resim_url_res if isinstance(resim_url_res, str) else getattr(resim_url_res, 'public_url', str(resim_url_res))
            except Exception as e:
                flash(f"Resim yüklenirken hata: {str(e)}", "danger")

        ses_url = None
        ses_file = request.files.get('ses_dosyasi')
        if ses_file and ses_file.filename != '':
            try:
                ext = os.path.splitext(ses_file.filename)[1]
                ses_filename = f"ses_{uuid.uuid4()}{ext}"
                ses_data = ses_file.read()
                supabase.storage.from_("oyuncu-sesleri").upload(
                    path=ses_filename,
                    file=ses_data,
                    file_options={"content-type": ses_file.content_type}
                )
                ses_url_res = supabase.storage.from_("oyuncu-sesleri").get_public_url(ses_filename)
                ses_url = ses_url_res if isinstance(ses_url_res, str) else getattr(ses_url_res, 'public_url', str(ses_url_res))
            except Exception as e:
                flash(f"Ses dosyası yüklenirken hata: {str(e)}", "danger")

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
            "resim_url": resim_url,
            "ses_url": ses_url
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
                hos_mesaj = supabase.table('ayarlar').select('deger').eq('anahtar', 'hos_geldin_mesaji').execute()
                mesaj_metni = hos_mesaj.data[0]['deger'] if hos_mesaj.data else "Ajansımıza hoş geldiniz!"
                supabase.table('mesajlar').insert({
                    'alici_id': str(yeni_oyuncu_id),
                    'mesaj_metni': mesaj_metni
                }).execute()
        return redirect(url_for('index'))
    return render_template('ekle.html')


@app.route('/admin/mesaj_gonder', methods=['POST'])
def mesaj_gonder():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    alici_id = request.form.get('alici_id')
    mesaj = request.form.get('mesaj_metni')
    try:
        supabase.table('mesajlar').insert({
            'alici_id': alici_id,
            'mesaj_metni': mesaj
        }).execute()
        flash('Mesaj iletildi.', 'success')
    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('index'))


@app.route('/gelen_kutusu')
def gelen_kutusu():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('index'))
    kullanici_id = session.get('id') or session.get('oyuncu_id')
    try:
        response = supabase.table('mesajlar').select('*').eq('alici_id', str(kullanici_id)).order('tarih', desc=True).execute()
        mesajlar = response.data
    except:
        mesajlar = []
    return render_template('gelen_kutusu.html', mesajlar=mesajlar)


@app.route('/oyuncu/<int:oyuncu_id>')
def oyuncu_detay(oyuncu_id):
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    if not res.data:
        flash('Oyuncu bulunamadı.', 'danger')
        return redirect(url_for('index'))
    oyuncu = res.data[0]

    yorumlar = []
    try:
        yorumlar = supabase.table('yorumlar').select('*').eq('oyuncu_id', oyuncu_id).eq('onaylandi', True).order('created_at', desc=True).execute().data
    except:
        yorumlar = []

    ortalama_puan = 0
    if yorumlar:
        toplam = sum(y.get('puan', 0) for y in yorumlar if y.get('puan'))
        ortalama_puan = round(toplam / len(yorumlar), 1) if toplam else 0

    goruntulenme_sayisi = 0
    try:
        goruntulenme_sayisi = supabase.table('sayfa_goruntulenme').select('id', count='exact').eq('oyuncu_id', oyuncu_id).execute().count or 0
    except:
        goruntulenme_sayisi = 0

    sertifika_var = False
    sertifika_kodu = None
    try:
        sert_res = supabase.table('sertifikalar').select('sertifika_kodu, aktif').eq('oyuncu_id', oyuncu_id).execute()
        print(f"DEBUG Sertifika sorgusu oyuncu {oyuncu_id}: {sert_res.data}")
        if sert_res.data:
            for s in sert_res.data:
                if s.get('aktif') == True:
                    sertifika_var = True
                    sertifika_kodu = s.get('sertifika_kodu')
                    print(f"Aktif sertifika bulundu: {sertifika_kodu}")
                    break
    except Exception as e:
        print(f"Sertifika sorgu hatasi: {e}")

    meta = {
        'baslik': f"{oyuncu.get('isim', 'Oyuncu')} | Nova Cast Ajans",
        'aciklama': f"{oyuncu.get('isim')} profili",
        'anahtar_kelimeler': f"{oyuncu.get('isim')}, oyuncu, cast"
    }

    return render_template('oyuncu_detay.html',
                           oyuncu=oyuncu,
                           meta=meta,
                           yorumlar=yorumlar,
                           ortalama_puan=ortalama_puan,
                           goruntulenme_sayisi=goruntulenme_sayisi,
                           sertifika_var=sertifika_var,
                           sertifika_kodu=sertifika_kodu)


@app.route('/yorum/ekle', methods=['POST'])
def yorum_ekle():
    if not session.get('logged_in'):
        flash('Yorum yapmak için giriş yapmalısınız.', 'warning')
        return redirect(url_for('login'))

    oyuncu_id = request.form.get('oyuncu_id')
    yorum = request.form.get('yorum')
    puan = safe_int(request.form.get('puan'))

    if not yorum or not oyuncu_id:
        flash('Yorum ve puan zorunludur.', 'danger')
        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))

    try:
        kullanici_adi = session.get('kullanici_adi', 'Anonim')
        yetki = session.get('role', 'oyuncu')
        if yetki is None:
            yetki = 'oyuncu'

        supabase.table('yorumlar').insert({
            'oyuncu_id': int(oyuncu_id),
            'kullanici_adi': kullanici_adi,
            'yorum': yorum,
            'puan': puan if puan else None,
            'onaylandi': False,
            'yetki': yetki
        }).execute()
        flash('Yorumunuz admin onayına gönderildi.', 'success')
    except Exception as e:
        flash(f'Yorum gönderilirken hata: {str(e)}', 'danger')

    return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))


@app.route('/admin/yorumlar')
def admin_yorumlar():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    bekleyen = supabase.table('yorumlar').select('*, oyuncular(isim)').eq('onaylandi', False).order('created_at', desc=True).execute().data
    onaylanan = supabase.table('yorumlar').select('*, oyuncular(isim)').eq('onaylandi', True).order('created_at', desc=True).execute().data
    return render_template('admin_yorumlar.html', bekleyen=bekleyen, onaylanan=onaylanan)


@app.route('/admin/yorum/onay/<int:yorum_id>')
def yorum_onay(yorum_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    supabase.table('yorumlar').update({'onaylandi': True}).eq('id', yorum_id).execute()
    flash('Yorum onaylandı.', 'success')
    return redirect(url_for('admin_yorumlar'))


@app.route('/admin/yorum/sil/<int:yorum_id>')
def yorum_sil(yorum_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    supabase.table('yorumlar').delete().eq('id', yorum_id).execute()
    flash('Yorum silindi.', 'success')
    return redirect(url_for('admin_yorumlar'))


@app.route('/oyuncu/sil/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_sil(oyuncu_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    supabase.table("kullanicilar").delete().eq("id", oyuncu_id).execute()
    supabase.table("oyuncular").delete().eq("id", oyuncu_id).execute()
    return redirect(url_for('index'))


@app.route('/hakkimizda')
def hakkimizda():
    meta_res = supabase.table('meta').select('*').eq('sayfa_adi', 'hakkimizda').execute()
    meta = meta_res.data[0] if meta_res.data else None
    res = supabase.table("sayfalar").select("*").eq("sayfa_adi", "hakkimizda").execute()
    sayfa_verisi = res.data[0] if res.data else {"baslik": "Hakkımızda", "icerik": "HAKIMIZDA"}
    return render_template('hakkimizda.html', sayfa=sayfa_verisi, meta=meta)


@app.route('/admin/duzenle/<sayfa_adi>', methods=['GET', 'POST'])
def admin_duzenle(sayfa_adi):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        yeni_baslik = request.form.get('baslik')
        yeni_icerik = request.form.get('icerik')
        kontrol = supabase.table("sayfalar").select("*").eq("sayfa_adi", sayfa_adi).execute()
        if kontrol.data:
            supabase.table("sayfalar").update({"baslik": yeni_baslik, "icerik": yeni_icerik}).eq("sayfa_adi", sayfa_adi).execute()
        else:
            supabase.table("sayfalar").insert({"sayfa_adi": sayfa_adi, "baslik": yeni_baslik, "icerik": yeni_icerik}).execute()
        flash(f"{sayfa_adi} güncellendi!", "success")
        return redirect(url_for('hakkimizda'))
    res = supabase.table("sayfalar").select("*").eq("sayfa_adi", sayfa_adi).execute()
    mevcut_veri = res.data[0] if res.data else {"baslik": "", "icerik": ""}
    return render_template('admin_duzenle.html', sayfa_adi=sayfa_adi, veri=mevcut_veri)


@app.route('/admin/basvurular')
def admin_basvurular():
    if session.get('role') != 'admin':
        flash("Yetkiniz yok.", "danger")
        return redirect(url_for('index'))
    res = supabase.table("basvurular").select("*").order("id", desc=True).execute()
    return render_template('basvurular.html', basvurular=res.data)


@app.route('/admin/basvuru/onayla/<int:b_id>', methods=['POST'])
def basvuru_onayla(b_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('admin_basvurular'))
    basvuru_res = supabase.table("basvurular").select("*").eq("id", b_id).execute()
    if not basvuru_res.data:
        flash('Başvuru bulunamadı.', 'danger')
        return redirect(url_for('admin_basvurular'))
    basvuru = basvuru_res.data[0]
    yeni_oyuncu = {
        "isim": basvuru.get('isim'),
        "yas": basvuru.get('yas'),
        "boy": basvuru.get('boy'),
        "telefon": basvuru.get('telefon'),
        "deneyim": basvuru.get('deneyim'),
        "cinsiyet": None, "kilo": None, "goz_rengi": None, "sac_rengi": None, "sehir": None, "eposta": None, "resim_url": None
    }
    oyuncu_res = supabase.table("oyuncular").insert(yeni_oyuncu).execute()
    if not oyuncu_res.data:
        flash('Oyuncu eklenirken hata.', 'danger')
        return redirect(url_for('admin_basvurular'))
    yeni_oyuncu_id = oyuncu_res.data[0]['id']
    base_username = basvuru.get('isim', '').replace(' ', '').lower()
    username = f"{base_username}{random.randint(100, 999)}"
    sifre = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    supabase.table("kullanicilar").insert({
        "kullanici_adi": username,
        "sifre": sifre,
        "yetki": "oyuncu",
        "id": yeni_oyuncu_id
    }).execute()
    supabase.table("basvurular").delete().eq("id", b_id).execute()
    flash(f'Onaylandı! Kullanıcı: {username}, Şifre: {sifre}', 'success')
    return redirect(url_for('admin_basvurular'))


@app.route('/oyuncu/duzenle/<int:oyuncu_id>', methods=['GET', 'POST'])
def oyuncu_duzenle(oyuncu_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if session.get('role') != 'admin' and session.get('oyuncu_id') != oyuncu_id:
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        resim_url = None
        file = request.files.get('profile_photo')
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
                resim_url = resim_url_res if isinstance(resim_url_res, str) else getattr(resim_url_res, 'public_url', str(resim_url_res))
            except Exception as e:
                flash(f"Resim yüklenemedi: {str(e)}", "danger")

        ses_url = None
        ses_file = request.files.get('ses_dosyasi')
        if ses_file and ses_file.filename != '':
            try:
                ext = os.path.splitext(ses_file.filename)[1]
                ses_filename = f"ses_{uuid.uuid4()}{ext}"
                ses_data = ses_file.read()
                supabase.storage.from_("oyuncu-sesleri").upload(
                    path=ses_filename,
                    file=ses_data,
                    file_options={"content-type": ses_file.content_type}
                )
                ses_url_res = supabase.storage.from_("oyuncu-sesleri").get_public_url(ses_filename)
                ses_url = ses_url_res if isinstance(ses_url_res, str) else getattr(ses_url_res, 'public_url', str(ses_url_res))
            except Exception as e:
                flash(f"Ses dosyası yüklenemedi: {str(e)}", "danger")

        yeni_veriler = {
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
        if resim_url:
            yeni_veriler["resim_url"] = resim_url
        if ses_url:
            yeni_veriler["ses_url"] = ses_url

        if session.get('role') != 'admin':
            supabase.table("bekleyen_degisiklikler").insert({
                "oyuncu_id": oyuncu_id,
                "yeni_veriler": yeni_veriler
            }).execute()
            flash("Değişiklik talebi gönderildi.", "info")
            return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))
        supabase.table("oyuncular").update(yeni_veriler).eq("id", oyuncu_id).execute()
        flash("Profil güncellendi!", "success")
        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    oyuncu_veri = res.data[0] if res.data else {}
    return render_template('duzenle.html', oyuncu=oyuncu_veri)


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')


@app.route('/admin/basvurular/sil/<int:b_id>', methods=['POST'])
def basvuru_sil(b_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    supabase.table("basvurular").delete().eq("id", b_id).execute()
    flash("Başvuru reddedildi.", "success")
    return redirect(url_for('admin_basvurular'))


@app.route('/admin/onaylar')
def admin_onaylar():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    bekleyenler = supabase.table("bekleyen_degisiklikler").select("*, oyuncular(isim)").execute().data
    return render_template('admin_onaylar.html', bekleyenler=bekleyenler)


@app.route('/admin/onay/islem/<int:id>/<action>')
def onay_islem(id, action):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    if action == 'onayla':
        istek = supabase.table("bekleyen_degisiklikler").select("*").eq("id", id).single().execute().data
        supabase.table("oyuncular").update(istek['yeni_veriler']).eq("id", istek['oyuncu_id']).execute()
        supabase.table("bekleyen_degisiklikler").delete().eq("id", id).execute()
        flash("Değişiklik onaylandı!", "success")
    elif action == 'reddet':
        supabase.table("bekleyen_degisiklikler").delete().eq("id", id).execute()
        flash("Değişiklik reddedildi.", "danger")
    return redirect(url_for('admin_onaylar'))


@app.route('/admin/mesajlar', methods=['GET', 'POST'])
def admin_mesajlar():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        alici_id = request.form.get('alici_id')
        mesaj = request.form.get('mesaj_metni')
        if not alici_id or not mesaj:
            flash('Lütfen alıcı ve mesaj girin.', 'warning')
            return redirect(url_for('admin_mesajlar'))
        try:
            if alici_id == 'hepsi':
                oyuncular_resp = supabase.table('oyuncular').select('id').execute()
                tum_oyuncular = oyuncular_resp.data
                if tum_oyuncular:
                    toplu_mesajlar = [{'alici_id': str(oyuncu['id']), 'mesaj_metni': mesaj} for oyuncu in tum_oyuncular]
                    supabase.table('mesajlar').insert(toplu_mesajlar).execute()
                    flash(f'Tüm oyunculara ({len(toplu_mesajlar)} kişi) iletildi.', 'success')
                else:
                    flash('Hiç oyuncu yok.', 'warning')
            else:
                supabase.table('mesajlar').insert({'alici_id': str(alici_id), 'mesaj_metni': mesaj}).execute()
                flash('Mesaj iletildi.', 'success')
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')
        return redirect(url_for('admin_mesajlar'))
    try:
        oyuncu_listesi = supabase.table('oyuncular').select('id, isim').order('isim').execute().data
    except:
        oyuncu_listesi = []
    return render_template('admin_mesaj_paneli.html', oyuncular=oyuncu_listesi)


@app.route('/ping')
def ping():
    return "Pong!", 200


@app.route('/profilim')
def profilim():
    oyuncu_id = session.get('oyuncu_id')
    if not oyuncu_id:
        return redirect(url_for('index'))
    return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))


@app.route('/oyuncu/<int:oyuncu_id>/qr')
def oyuncu_qr(oyuncu_id):
    profil_url = url_for('oyuncu_detay', oyuncu_id=oyuncu_id, _external=True)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(profil_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


@app.route('/oyuncu/<int:oyuncu_id>/kartvizit')
def kartvizit_pdf(oyuncu_id):
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    if not res.data:
        flash('Oyuncu bulunamadı.', 'danger')
        return redirect(url_for('index'))
    oyuncu = res.data[0]

    buffer = BytesIO()
    k_width = 8.5 * cm
    k_height = 5.5 * cm
    c = canvas.Canvas(buffer, pagesize=(k_width, k_height))

    c.setFillColor(white)
    c.rect(0, 0, k_width, k_height, fill=1, stroke=0)

    try:
        logo_path = os.path.join("static", "images", "logo.png")
        with open(logo_path, "rb") as f:
            logo_img = ImageReader(f)
            c.drawImage(logo_img, 0.5*cm, k_height - 2.5*cm, width=2.0*cm, height=2.0*cm, preserveAspectRatio=True, mask='auto')
    except:
        pass

    c.setFillColor(navy)
    c.setFont(FONT_BOLD, 14)
    c.drawString(2.8*cm, k_height - 2.2*cm, oyuncu.get('isim', 'İsimsiz'))

    c.setFont(FONT_NAME, 9)
    c.setFillColor(navy)
    c.drawString(2.8*cm, k_height - 2.9*cm, "NOVA CAST AJANS OYUNCUSU")

    c.setFont(FONT_NAME, 8)
    c.setFillColor(grey)
    y_pos = k_height - 3.8*cm
    if oyuncu.get('telefon'):
        c.drawString(2.8*cm, y_pos, f"Tel: {oyuncu.get('telefon')}")
        y_pos -= 0.6*cm
    if oyuncu.get('eposta'):
        c.drawString(2.8*cm, y_pos, f"E-posta: {oyuncu.get('eposta')}")
        y_pos -= 0.6*cm
    if oyuncu.get('sehir'):
        c.drawString(2.8*cm, y_pos, f"Sehir: {oyuncu.get('sehir')}")

    try:
        qr_url = url_for('oyuncu_qr', oyuncu_id=oyuncu_id, _external=True)
        qr_img_data = requests.get(qr_url, timeout=5).content
        qr_reader = ImageReader(BytesIO(qr_img_data))
        c.drawImage(qr_reader, k_width - 2.8*cm, 0.4*cm, width=2.2*cm, height=2.2*cm)
    except:
        pass

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Kartvizit_{oyuncu.get('isim', 'oyuncu')}.pdf", mimetype='application/pdf')


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    oyuncu_sayisi = supabase.table('oyuncular').select('id', count='exact').execute().count
    bekleyen_basvuru = supabase.table('basvurular').select('id', count='exact').execute().count
    bekleyen_onay = supabase.table('bekleyen_degisiklikler').select('id', count='exact').execute().count
    randevu_sayisi = supabase.table('randevular').select('id', count='exact').execute().count
    bekleyen_yorum = supabase.table('yorumlar').select('id', count='exact').eq('onaylandi', False).execute().count

    bugun = date.today().isoformat()
    bugun_randevular = supabase.table('randevular').select('*, oyuncular(isim)').eq('tarih', bugun).execute().data

    toplam_goruntulenme = supabase.table('sayfa_goruntulenme').select('id', count='exact').execute().count or 0
    son_24 = datetime.now() - timedelta(hours=24)
    son_24_str = son_24.isoformat()
    son24_goruntulenme = supabase.table('sayfa_goruntulenme').select('id', count='exact').gte('tarih', son_24_str).execute().count or 0

    benzersiz_ziyaretci = 0
    try:
        ip_res = supabase.table('sayfa_goruntulenme').select('ziyaretci_ip').gte('tarih', son_24_str).execute()
        ips = [row['ziyaretci_ip'] for row in ip_res.data if row.get('ziyaretci_ip')]
        benzersiz_ziyaretci = len(set(ips))
    except:
        benzersiz_ziyaretci = 0

    en_cok_oyuncu = None
    try:
        goruntuler = supabase.table('sayfa_goruntulenme').select('oyuncu_id').not_.is_('oyuncu_id', 'null').execute().data
        if goruntuler:
            from collections import Counter
            oyuncu_ids = [g['oyuncu_id'] for g in goruntuler]
            counter = Counter(oyuncu_ids)
            if counter:
                en_cok_id = counter.most_common(1)[0][0]
                oyuncu_res = supabase.table('oyuncular').select('isim').eq('id', en_cok_id).execute()
                if oyuncu_res.data:
                    en_cok_oyuncu = oyuncu_res.data[0]['isim']
    except:
        en_cok_oyuncu = "Veri yok"

    return render_template('admin_dashboard.html',
                           oyuncu_sayisi=oyuncu_sayisi,
                           bekleyen_basvuru=bekleyen_basvuru,
                           bekleyen_onay=bekleyen_onay,
                           randevu_sayisi=randevu_sayisi,
                           yorum_sayisi=bekleyen_yorum,
                           bugun_randevular=bugun_randevular,
                           toplam_goruntulenme=toplam_goruntulenme,
                           son24_goruntulenme=son24_goruntulenme,
                           benzersiz_ziyaretci=benzersiz_ziyaretci,
                           en_cok_oyuncu=en_cok_oyuncu)


@app.route('/admin/randevu/ekle', methods=['GET', 'POST'])
def admin_randevu_ekle():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    oyuncular = supabase.table('oyuncular').select('id, isim').order('isim').execute().data
    if request.method == 'POST':
        oyuncu_id = request.form.get('oyuncu_id')
        tarih = request.form.get('tarih')
        saat = request.form.get('saat')
        notlar = request.form.get('notlar')
        if not oyuncu_id or not tarih or not saat:
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('admin_randevu_ekle'))
        supabase.table('randevular').insert({
            'oyuncu_id': int(oyuncu_id),
            'admin_id': session.get('oyuncu_id'),
            'tarih': tarih,
            'saat': saat,
            'notlar': notlar,
            'durum': 'beklemede'
        }).execute()
        flash('Randevu oluşturuldu.', 'success')
        return redirect(url_for('admin_randevular'))
    return render_template('admin_randevu_ekle.html', oyuncular=oyuncular)


@app.route('/admin/randevular')
def admin_randevular():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    randevular = supabase.table('randevular').select('*, oyuncular(isim)').order('tarih', desc=True).execute().data
    return render_template('admin_randevular.html', randevular=randevular)


@app.route('/oyuncu/randevular')
def oyuncu_randevular():
    if not session.get('logged_in') or session.get('role') == 'admin':
        flash('Bu sayfayı görüntüleme yetkiniz yok.', 'danger')
        return redirect(url_for('index'))
    oyuncu_id = session.get('oyuncu_id')
    randevular = supabase.table('randevular').select('*').eq('oyuncu_id', oyuncu_id).order('tarih', desc=True).execute().data
    return render_template('oyuncu_randevular.html', randevular=randevular)


@app.route('/admin/duyurular')
def admin_duyurular():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    duyurular = supabase.table('duyurular').select('*').order('created_at', desc=True).execute().data
    return render_template('admin_duyurular.html', duyurular=duyurular)


@app.route('/admin/duyuru/ekle', methods=['GET', 'POST'])
def admin_duyuru_ekle():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        baslik = request.form.get('baslik')
        icerik = request.form.get('icerik')
        if not baslik or not icerik:
            flash('Başlık ve içerik zorunludur.', 'warning')
            return redirect(url_for('admin_duyuru_ekle'))
        supabase.table('duyurular').insert({
            'baslik': baslik,
            'icerik': icerik,
            'yazar': session.get('kullanici_adi', 'Admin'),
            'aktif': True
        }).execute()
        flash('Duyuru yayınlandı.', 'success')
        return redirect(url_for('admin_duyurular'))
    return render_template('admin_duyuru_ekle.html')


@app.route('/admin/duyuru/sil/<int:duyuru_id>', methods=['POST'])
def admin_duyuru_sil(duyuru_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    supabase.table('duyurular').delete().eq('id', duyuru_id).execute()
    flash('Duyuru silindi.', 'success')
    return redirect(url_for('admin_duyurular'))


@app.route('/duyurular')
def duyurular_listesi():
    meta_res = supabase.table('meta').select('*').eq('sayfa_adi', 'duyurular').execute()
    meta = meta_res.data[0] if meta_res.data else None
    duyurular = supabase.table('duyurular').select('*').eq('aktif', True).order('created_at', desc=True).execute().data
    return render_template('duyurular.html', duyurular=duyurular, meta=meta)


@app.route('/admin/meta')
def admin_meta():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    meta_list = supabase.table('meta').select('*').order('sayfa_adi').execute().data
    return render_template('admin_meta_listesi.html', meta_list=meta_list)


@app.route('/admin/meta/duzenle/<sayfa_adi>', methods=['GET', 'POST'])
def admin_meta_duzenle(sayfa_adi):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        baslik = request.form.get('baslik')
        aciklama = request.form.get('aciklama')
        anahtar_kelimeler = request.form.get('anahtar_kelimeler')
        supabase.table('meta').upsert({
            'sayfa_adi': sayfa_adi,
            'baslik': baslik,
            'aciklama': aciklama,
            'anahtar_kelimeler': anahtar_kelimeler,
            'updated_at': datetime.now().isoformat()
        }).execute()
        flash(f'{sayfa_adi} meta bilgileri güncellendi.', 'success')
        return redirect(url_for('admin_meta'))
    mevcut = supabase.table('meta').select('*').eq('sayfa_adi', sayfa_adi).execute().data
    meta = mevcut[0] if mevcut else {'sayfa_adi': sayfa_adi, 'baslik': '', 'aciklama': '', 'anahtar_kelimeler': ''}
    return render_template('admin_meta_duzenle.html', meta=meta)


@app.route('/oyuncu/<int:oyuncu_id>/pdf')
def oyuncu_pdf(oyuncu_id):
    res = supabase.table("oyuncular").select("*").eq("id", oyuncu_id).execute()
    if not res.data:
        flash('Oyuncu bulunamadı.', 'danger')
        return redirect(url_for('index'))
    oyuncu = res.data[0]

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(navy)
    c.rect(0, height-3.5*cm, width, 3.5*cm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(FONT_BOLD, 26)
    c.drawCentredString(width/2, height-1.8*cm, "NOVA CAST AJANS")
    c.setFont(FONT_NAME, 12)
    c.drawCentredString(width/2, height-2.8*cm, "PROFESYONEL OYUNCU ÖZGEÇMİŞİ")

    try:
        logo_path = os.path.join("static", "images", "logo.png")
        with open(logo_path, "rb") as f:
            logo_img = ImageReader(f)
            c.drawImage(logo_img, width - 3.5*cm, height - 3*cm, width=2.5*cm, height=2.5*cm, preserveAspectRatio=True, mask='auto')
    except:
        pass

    if oyuncu.get('resim_url'):
        try:
            img_data = requests.get(oyuncu.get('resim_url'), timeout=5).content
            img_reader = ImageReader(BytesIO(img_data))
            c.drawImage(img_reader, width-5.5*cm, height-8*cm, width=4*cm, height=4*cm, preserveAspectRatio=True, mask='auto')
        except:
            pass

    y = height - 6*cm
    c.setFillColor(navy)
    c.setFont(FONT_BOLD, 16)
    c.drawString(2*cm, y, "KİŞİSEL BİLGİLER")
    y -= 0.8*cm
    c.setStrokeColor(navy)
    c.setLineWidth(1)
    c.line(2*cm, y+0.3*cm, 11*cm, y+0.3*cm)
    y -= 0.5*cm

    c.setFont(FONT_NAME, 12)
    bilgiler = [
        ("Ad Soyad", oyuncu.get('isim', '-')),
        ("Yaş", oyuncu.get('yas', '-')),
        ("Boy", f"{oyuncu.get('boy', '-')} cm"),
        ("Kilo", f"{oyuncu.get('kilo', '-')} kg"),
        ("Cinsiyet", oyuncu.get('cinsiyet', '-')),
        ("Göz Rengi", oyuncu.get('goz_rengi', '-')),
        ("Saç Rengi", oyuncu.get('sac_rengi', '-')),
        ("Şehir", oyuncu.get('sehir', '-')),
        ("Telefon", oyuncu.get('telefon', '-')),
        ("E-posta", oyuncu.get('eposta', '-'))
    ]

    for etiket, deger in bilgiler:
        c.setFillColor(grey)
        c.drawString(2*cm, y, f"{etiket}:")
        c.setFillColor(black)
        c.drawString(5*cm, y, str(deger))
        y -= 0.7*cm

    if oyuncu.get('deneyim'):
        y -= 0.5*cm
        c.setFillColor(navy)
        c.setFont(FONT_BOLD, 14)
        c.drawString(2*cm, y, "DENEYİM / ÖZGEÇMİŞ")
        y -= 1.2*cm
        c.setFont(FONT_NAME, 11)

        metin = oyuncu.get('deneyim')
        satirlar = metin.split('\n')
        for satir in satirlar:
            if len(satir) > 80:
                for i in range(0, len(satir), 80):
                    c.drawString(2*cm, y, satir[i:i+80])
                    y -= 0.6*cm
            else:
                c.drawString(2*cm, y, satir)
                y -= 0.6*cm

    c.setFont(FONT_NAME, 9)
    c.setFillColor(grey)
    c.drawCentredString(width/2, 1*cm, f"© Nova Cast Ajans - {datetime.now().strftime('%d.%m.%Y')}")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"CV_{oyuncu.get('isim', 'oyuncu')}.pdf", mimetype='application/pdf')


@app.route('/admin/ayarlar', methods=['GET', 'POST'])
def admin_ayarlar():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        mesaj = request.form.get('hos_geldin_mesaji')
        if mesaj:
            supabase.table('ayarlar').update({'deger': mesaj}).eq('anahtar', 'hos_geldin_mesaji').execute()
            flash('Hoş geldin mesajı güncellendi.', 'success')
        else:
            flash('Mesaj boş olamaz.', 'warning')
        return redirect(url_for('admin_ayarlar'))

    hos_mesaj = supabase.table('ayarlar').select('deger').eq('anahtar', 'hos_geldin_mesaji').execute()
    hos_mesaj = hos_mesaj.data[0]['deger'] if hos_mesaj.data else "Ajansımıza hoş geldiniz!"
    return render_template('admin_ayarlar.html', hos_mesaj=hos_mesaj)


@app.route('/admin/vitrin_yonetimi')
def admin_vitrin_yonetimi():
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    oyuncular = supabase.table('oyuncular').select('id, isim, vitrin').order('isim').execute().data
    return render_template('admin_vitrin_yonetimi.html', oyuncular=oyuncular)


@app.route('/admin/vitrin/toggle/<int:oyuncu_id>')
def admin_vitrin_toggle(oyuncu_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
    res = supabase.table('oyuncular').select('vitrin').eq('id', oyuncu_id).execute()
    if not res.data:
        flash('Oyuncu bulunamadı.', 'danger')
        return redirect(url_for('admin_vitrin_yonetimi'))
    mevcut_durum = res.data[0]['vitrin']
    yeni_durum = not mevcut_durum
    supabase.table('oyuncular').update({'vitrin': yeni_durum}).eq('id', oyuncu_id).execute()
    flash(f"Vitrin durumu güncellendi!", "success")
    return redirect(url_for('admin_vitrin_yonetimi'))


def slug_olustur(baslik):
    import unicodedata
    baslik = baslik.lower()
    ceviriler = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
    for tr, en in ceviriler.items():
        baslik = baslik.replace(tr, en)
    baslik = ''.join(c if c.isalnum() else '-' for c in baslik)
    while '--' in baslik:
        baslik = baslik.replace('--', '-')
    return baslik.strip('-')


@app.route('/admin/sayfalar')
def admin_sayfalar():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Yetkiniz yok.', 'danger')
        return redirect(url_for('login'))
    res = supabase.table('ozel_sayfalar').select('*').order('sira').execute()
    sayfalar = res.data or []
    return render_template('admin_sayfalar.html', sayfalar=sayfalar)


@app.route('/admin/sayfa/ekle', methods=['GET', 'POST'])
def admin_sayfa_ekle():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Yetkiniz yok.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        baslik = request.form.get('baslik', '').strip()
        slug = request.form.get('slug', '').strip() or slug_olustur(baslik)
        icerik = request.form.get('icerik', '')
        menude_goster = request.form.get('menude_goster') == 'on'
        yayinda = request.form.get('yayinda') == 'on'
        sira = safe_int(request.form.get('sira')) or 0
        meta_baslik = request.form.get('meta_baslik', '')
        meta_aciklama = request.form.get('meta_aciklama', '')

        kapak_url = None
        kapak = request.files.get('kapak_resmi')
        if kapak and kapak.filename != '':
            try:
                ext = os.path.splitext(kapak.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    filename = f"kapak_{uuid.uuid4()}{ext}"
                    kapak_data = kapak.read()
                    supabase.storage.from_("basvuru-fotolari").upload(
                        path=filename,
                        file=kapak_data,
                        file_options={"content-type": kapak.content_type}
                    )
                    res = supabase.storage.from_("basvuru-fotolari").get_public_url(filename)
                    if isinstance(res, str):
                        kapak_url = res
                    elif isinstance(res, dict):
                        kapak_url = res.get('publicUrl') or res.get('publicURL')
            except Exception as e:
                print(f"Kapak yükleme hatası: {e}")

        try:
            supabase.table('ozel_sayfalar').insert({
                'slug': slug,
                'baslik': baslik,
                'icerik': icerik,
                'kapak_resmi': kapak_url,
                'menude_goster': menude_goster,
                'yayinda': yayinda,
                'sira': sira,
                'meta_baslik': meta_baslik,
                'meta_aciklama': meta_aciklama
            }).execute()
            flash('Sayfa başarıyla eklendi!', 'success')
            return redirect(url_for('admin_sayfalar'))
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')

    return render_template('admin_sayfa_ekle.html')


@app.route('/admin/sayfa/duzenle/<int:sayfa_id>', methods=['GET', 'POST'])
def admin_sayfa_duzenle(sayfa_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Yetkiniz yok.', 'danger')
        return redirect(url_for('login'))

    res = supabase.table('ozel_sayfalar').select('*').eq('id', sayfa_id).execute()
    if not res.data:
        flash('Sayfa bulunamadı.', 'danger')
        return redirect(url_for('admin_sayfalar'))

    sayfa = res.data[0]

    if request.method == 'POST':
        baslik = request.form.get('baslik', '').strip()
        slug = request.form.get('slug', '').strip() or slug_olustur(baslik)
        icerik = request.form.get('icerik', '')
        menude_goster = request.form.get('menude_goster') == 'on'
        yayinda = request.form.get('yayinda') == 'on'
        sira = safe_int(request.form.get('sira')) or 0
        meta_baslik = request.form.get('meta_baslik', '')
        meta_aciklama = request.form.get('meta_aciklama', '')

        guncelleme = {
            'slug': slug,
            'baslik': baslik,
            'icerik': icerik,
            'menude_goster': menude_goster,
            'yayinda': yayinda,
            'sira': sira,
            'meta_baslik': meta_baslik,
            'meta_aciklama': meta_aciklama,
            'guncelleme_tarihi': datetime.now().isoformat()
        }

        kapak = request.files.get('kapak_resmi')
        if kapak and kapak.filename != '':
            try:
                ext = os.path.splitext(kapak.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    filename = f"kapak_{uuid.uuid4()}{ext}"
                    kapak_data = kapak.read()
                    supabase.storage.from_("basvuru-fotolari").upload(
                        path=filename,
                        file=kapak_data,
                        file_options={"content-type": kapak.content_type}
                    )
                    res_u = supabase.storage.from_("basvuru-fotolari").get_public_url(filename)
                    if isinstance(res_u, str):
                        guncelleme['kapak_resmi'] = res_u
                    elif isinstance(res_u, dict):
                        guncelleme['kapak_resmi'] = res_u.get('publicUrl') or res_u.get('publicURL')
            except Exception as e:
                print(f"Kapak yükleme hatası: {e}")

        try:
            supabase.table('ozel_sayfalar').update(guncelleme).eq('id', sayfa_id).execute()
            flash('Sayfa güncellendi!', 'success')
            return redirect(url_for('admin_sayfalar'))
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')

    return render_template('admin_sayfa_duzenle.html', sayfa=sayfa)


@app.route('/admin/sayfa/sil/<int:sayfa_id>', methods=['POST'])
def admin_sayfa_sil(sayfa_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Yetkiniz yok.', 'danger')
        return redirect(url_for('login'))
    try:
        supabase.table('ozel_sayfalar').delete().eq('id', sayfa_id).execute()
        flash('Sayfa silindi.', 'success')
    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
    return redirect(url_for('admin_sayfalar'))


@app.route('/sayfa/<slug>')
def ozel_sayfa_goruntule(slug):
    res = supabase.table('ozel_sayfalar').select('*').eq('slug', slug).eq('yayinda', True).execute()
    if not res.data:
        flash('Sayfa bulunamadı.', 'warning')
        return redirect(url_for('index'))
    return render_template('ozel_sayfa.html', sayfa=res.data[0])


@app.context_processor
def menu_sayfalari_enjekte():
    try:
        res = supabase.table('ozel_sayfalar').select('slug,baslik').eq('menude_goster', True).eq('yayinda', True).order('sira').execute()
        return {'menu_sayfalari': res.data or []}
    except:
        return {'menu_sayfalari': []}


# ==================== SERTİFİKA SİSTEMİ ====================

@app.route('/admin/sertifika/ver/<int:oyuncu_id>', methods=['POST'])
def admin_sertifika_ver(oyuncu_id):
    if session.get('role') != 'admin':
        flash('Yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    oyuncu_res = supabase.table('oyuncular').select('isim').eq('id', oyuncu_id).execute()
    if not oyuncu_res.data:
        flash('Oyuncu bulunamadı.', 'danger')
        return redirect(url_for('index'))

    mevcut = supabase.table('sertifikalar').select('sertifika_kodu').eq('oyuncu_id', oyuncu_id).eq('aktif', True).execute()
    if mevcut.data:
        flash(f"Bu oyuncunun zaten aktif bir sertifikası var: {mevcut.data[0]['sertifika_kodu']}", 'warning')
        return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))

    kod = sertifika_kodu_uret()
    gecerlilik = (datetime.now() + timedelta(days=365)).date().isoformat()

    supabase.table('sertifikalar').insert({
        'oyuncu_id': oyuncu_id,
        'sertifika_kodu': kod,
        'gecerlilik_tarihi': gecerlilik,
        'veren_admin': session.get('kullanici_adi', 'Admin'),
        'aktif': True
    }).execute()

    flash(f'Sertifika verildi! Kod: {kod}', 'success')
    return redirect(url_for('oyuncu_detay', oyuncu_id=oyuncu_id))


@app.route('/sertifika/pdf/<sertifika_kodu>')
def sertifika_pdf(sertifika_kodu):
    res = supabase.table('sertifikalar').select('*, oyuncular(isim, sehir)').eq('sertifika_kodu', sertifika_kodu).execute()
    if not res.data:
        flash('Sertifika bulunamadı.', 'danger')
        return redirect(url_for('index'))

    sertifika = res.data[0]
    oyuncu_data = sertifika.get('oyuncular') or {}
    oyuncu_isim = oyuncu_data.get('isim', 'İsimsiz')

    qr_url = url_for('sertifika_dogrula', kod=sertifika_kodu, _external=True)
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_base64 = base64.b64encode(qr_buffer.read()).decode('utf-8')

    bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'sertifika_bg.png')
    bg_base64 = ""
    try:
        with open(bg_path, 'rb') as f:
            bg_data = f.read()
            bg_base64 = base64.b64encode(bg_data).decode('utf-8')
        print(f"Arka plan yuklendi: {len(bg_data)} byte")
    except Exception as e:
        print(f"Arka plan yuklenemedi: {e}")

    from datetime import datetime as dt
    verilis = sertifika.get('verilis_tarihi', '')
    try:
        tarih_str = dt.fromisoformat(verilis.replace('Z', '+00:00')).strftime('%d.%m.%Y')
    except:
        tarih_str = dt.now().strftime('%d.%m.%Y')

    html = render_template(
        'sertifika_sablon.html',
        bg_base64=bg_base64,
        oyuncu_isim=oyuncu_isim,
        tarih=tarih_str,
        sertifika_kodu=sertifika_kodu,
        qr_base64=qr_base64
    )

    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
        'disable-smart-shrinking': None,
        'print-media-type': None,
    }

    try:
        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=options)
    except Exception as e:
        flash(f'PDF oluşturma hatası: {str(e)}', 'danger')
        return redirect(url_for('oyuncu_detay', oyuncu_id=sertifika['oyuncu_id']))

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Sertifika_{oyuncu_isim}_{sertifika_kodu}.pdf",
        mimetype='application/pdf'
    )


@app.route('/sertifika/dogrula/<kod>')
def sertifika_dogrula(kod):
    res = supabase.table('sertifikalar').select('*, oyuncular(isim, resim_url, sehir)').eq('sertifika_kodu', kod).execute()
    if not res.data:
        return render_template('sertifika_dogrula.html', gecerli=False, kod=kod)

    sertifika = res.data[0]
    return render_template('sertifika_dogrula.html', gecerli=True, sertifika=sertifika, kod=kod)


# ==================== /SERTİFİKA SİSTEMİ ====================

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', debug=False, port=port)