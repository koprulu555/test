#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import sys
import os
import glob
import shutil
import sqlite3
from datetime import datetime

# YouTube API anahtarları (yt-dlp'den alınmıştır)
YOUTUBE_API_KEYS = [
    'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',  # Web client
    'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',  # Android client
    'AIzaSyDCU8hxkR5BqB2CvNbI5sxr8bR1V75Iwhg',  # iOS client
]


def extract_firefox_cookies():
    """
    Firefox tarayıcısından YouTube cookie'lerini çıkar
    Chrome artık çalışmıyor! (app-bound encryption)
    """
    try:
        # Firefox profil dizinini bul
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', '')
            profiles_dir = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
        elif sys.platform == 'darwin':  # macOS
            home = os.environ.get('HOME', '')
            profiles_dir = os.path.join(home, 'Library', 'Application Support', 'Firefox', 'Profiles')
        else:  # Linux
            home = os.environ.get('HOME', '')
            profiles_dir = os.path.join(home, '.mozilla', 'firefox')

        if not os.path.exists(profiles_dir):
            print("   ⚠️ Firefox profil dizini bulunamadı")
            return None

        # En son kullanılan profili bul
        profile_dirs = glob.glob(os.path.join(profiles_dir, '*.default*'))
        if not profile_dirs:
            print("   ⚠️ Firefox profili bulunamadı")
            return None

        profile_dir = max(profile_dirs, key=os.path.getmtime)
        cookies_db = os.path.join(profile_dir, 'cookies.sqlite')

        if not os.path.exists(cookies_db):
            print("   ⚠️ cookies.sqlite bulunamadı")
            return None

        # Veritabanını kopyala (Firefox kilitli olabilir)
        temp_db = '/tmp/firefox_cookies.sqlite'
        shutil.copy2(cookies_db, temp_db)

        # SQLite'dan cookie'leri oku
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # YouTube ve Google cookie'lerini al
        cursor.execute("""
            SELECT host, name, value, path, expiry, isSecure 
            FROM moz_cookies 
            WHERE host LIKE '%youtube%' OR host LIKE '%google%'
        """)

        cookies = cursor.fetchall()
        conn.close()
        os.remove(temp_db)

        if not cookies:
            print("   ⚠️ YouTube cookie'si bulunamadı")
            return None

        # Netscape formatında cookie dosyası oluştur
        cookiefile = '/tmp/youtube_cookies.txt'
        with open(cookiefile, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for host, name, value, path, expiry, isSecure in cookies:
                secure = 'TRUE' if isSecure else 'FALSE'
                f.write(f"{host}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")

        print(f"   ✅ {len(cookies)} cookie alındı")
        return cookiefile

    except Exception as e:
        print(f"   ⚠️ Cookie çıkarma hatası: {str(e)}")
        return None


def get_hls_with_ytdlp(video_id, cookiefile):
    """
    yt-dlp ile YouTube canlı yayınından HLS bağlantısını al
    """
    try:
        # PO Token plugin'ini aktif et
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-cache-dir',
            '--extractor-args', 'youtubepot:provider=bgutil',
            '--cookies', cookiefile,  # Firefox cookie'leri
            '-g',  # Sadece URL'yi göster
            '-f', 'best',  # En iyi format
            f'https://www.youtube.com/watch?v={video_id}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Çıktıyı kontrol et
        output = result.stdout.strip()
        if output and '.m3u8' in output:
            print(f"      ✅ HLS URL alındı")
            return output
        else:
            print(f"      ⚠️ HLS URL bulunamadı: {output[:100]}")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.lower() if e.stderr else ''
        if 'sign in' in error_msg:
            print(f"      ⚠️ YouTube oturum açmanızı istiyor. Firefox'a giriş yapın.")
        elif 'pot token' in error_msg:
            print(f"      ⚠️ PO Token hatası: {e.stderr[:100]}")
        else:
            print(f"      ⚠️ yt-dlp hatası: {e.stderr[:100]}")
    except Exception as e:
        print(f"      ⚠️ Beklenmeyen hata: {str(e)}")

    return None


def generate_m3u():
    """Ana M3U dosyasını oluştur"""

    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ids.txt'yi oku
    try:
        with open('ids.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("❌ ids.txt bulunamadı!")
        return False

    if not lines:
        print("❌ ids.txt boş!")
        return False

    # Firefox cookie'lerini çıkar
    print("\n🔑 Firefox cookie'leri alınıyor...")
    cookiefile = extract_firefox_cookies()
    if not cookiefile:
        print("❌ Cookie alınamadı! Firefox'a YouTube'da giriş yapın.")
        return False

    m3u_content = ['#EXTM3U']
    success_count = 0
    total = len(lines)

    for idx, line in enumerate(lines, 1):
        parts = line.split('|')
        if len(parts) != 3:
            print(f"⚠️ Geçersiz satır: {line}")
            continue

        name, url, logo = parts
        video_id = url.split('=')[-1] if '=' in url else url

        print(f"\n📺 [{idx}/{total}] {name}")
        print(f"   ID: {video_id}")

        # yt-dlp ile HLS URL'ini al
        hls_url = get_hls_with_ytdlp(video_id, cookiefile)

        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")

        # Her kanal arasında 10 saniye bekle
        if idx < total:
            print(f"   ⏳ 10 saniye bekleniyor...")
            time.sleep(10)

    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))

    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")

    # Geçici cookie dosyasını temizle
    if os.path.exists('/tmp/youtube_cookies.txt'):
        os.remove('/tmp/youtube_cookies.txt')

    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (Cookie + PO Token) Başlatılıyor...")
    success = generate_m3u()

    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
