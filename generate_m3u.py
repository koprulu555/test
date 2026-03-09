#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import sys
import os
import requests
from datetime import datetime

def get_po_token_from_provider():
    """
    bgutil-ytdlp-pot-provider'dan PO Token al
    """
    try:
        # PO Token provider'a bağlan (localhost:4416)
        response = requests.get(
            'http://localhost:4416/token',
            params={'visitor_data': generate_visitor_data()},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            po_token = data.get('poToken')
            visitor_data = data.get('visitorData')
            print(f"      ✅ PO Token alındı")
            return po_token, visitor_data
        else:
            print(f"      ⚠️ PO Token provider hatası: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"      ⚠️ PO Token provider bağlantı hatası (Docker çalışıyor mu?)")
    except Exception as e:
        print(f"      ⚠️ PO Token hatası: {str(e)}")
    
    return None, None


def generate_visitor_data():
    """
    Rastgele visitor data üret (YouTube'un istediği format)
    """
    import random
    import string
    import base64
    
    # 16 karakterlik rastgele ID
    random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    timestamp = int(time.time()) - random.randint(3600, 86400)
    
    # YouTube'un beklediği format
    visitor_data = f"Cgt{random_id}Sj{timestamp}Dg=="
    return visitor_data


def get_hls_with_po_token(video_id):
    """
    PO Token ile YouTube canlı yayınından HLS bağlantısını al
    """
    try:
        # PO Token al
        po_token, visitor_data = get_po_token_from_provider()
        
        if not po_token:
            print(f"      ⚠️ PO Token alınamadı")
            return None
        
        # yt-dlp ile HLS URL'ini al (PO Token ile)
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-cache-dir',
            '--extractor-args', f'youtubepot:po_token={po_token}:visitor_data={visitor_data}',
            '-g',  # Sadece URL'yi göster
            '-f', 'best',  # En iyi format
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output and '.m3u8' in output:
                print(f"      ✅ HLS URL alındı")
                return output
            else:
                print(f"      ⚠️ HLS URL bulunamadı")
        else:
            error_msg = result.stderr.lower()
            if 'po token' in error_msg or 'sign in' in error_msg:
                print(f"      ⚠️ Yeni PO Token gerekiyor")
            else:
                print(f"      ⚠️ yt-dlp hatası: {result.stderr[:100]}")
                
    except Exception as e:
        print(f"      ⚠️ Beklenmeyen hata: {str(e)}")
    
    return None


def generate_m3u():
    """Ana M3U dosyasını oluştur"""
    
    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # PO Token provider'ın çalıştığını kontrol et
    try:
        requests.get('http://localhost:4416/health', timeout=2)
        print(f"✅ PO Token provider çalışıyor")
    except:
        print(f"❌ PO Token provider çalışmıyor! Docker container'ı kontrol edin.")
        return False
    
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
        
        # PO Token ile HLS URL'ini al
        hls_url = get_hls_with_po_token(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        # Her kanal arasında 15 saniye bekle
        if idx < total:
            print(f"   ⏳ 15 saniye bekleniyor...")
            time.sleep(15)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (PO Token Provider) Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
