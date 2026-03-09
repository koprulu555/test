#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import sys
import os
import requests
import random
from datetime import datetime

# YouTube API anahtarları (yt-dlp'den alınmıştır)
YOUTUBE_API_KEYS = [
    'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',  # Web client
    'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',  # Android client
    'AIzaSyDCU8hxkR5BqB2CvNbI5sxr8bR1V75Iwhg',  # iOS client
]


def get_po_token_from_provider():
    """
    bgutil-ytdlp-pot-provider'dan PO Token al - DOĞRU ENDPOINT İLE
    """
    try:
        # Önce health check
        health_response = requests.get('http://localhost:4416/health', timeout=5)
        if health_response.status_code != 200:
            print(f"      ⚠️ PO Token provider sağlıklı değil: {health_response.status_code}")
            return None, None
        
        # Token al - /token endpoint'i çalışmıyor, /generate dene
        endpoints = ['/generate', '/token', '/pot']
        
        for endpoint in endpoints:
            try:
                print(f"      🔍 Endpoint {endpoint} deneniyor...")
                response = requests.post(
                    f'http://localhost:4416{endpoint}',
                    json={'visitor_data': generate_visitor_data()},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Farklı response formatlarını dene
                    po_token = data.get('poToken') or data.get('token') or data.get('pot')
                    visitor_data = data.get('visitorData') or data.get('visitor_data')
                    
                    if po_token:
                        print(f"      ✅ PO Token alındı (endpoint: {endpoint})")
                        return po_token, visitor_data
                        
            except Exception as e:
                print(f"      ⚠️ Endpoint {endpoint} hatası: {str(e)[:50]}")
                continue
        
        print(f"      ⚠️ Hiçbir endpoint çalışmadı")
        
    except requests.exceptions.ConnectionError:
        print(f"      ⚠️ PO Token provider bağlantı hatası (Docker çalışıyor mu?)")
    except Exception as e:
        print(f"      ⚠️ PO Token hatası: {str(e)[:50]}")
    
    return None, None


def generate_visitor_data():
    """
    Rastgele visitor data üret (YouTube'un istediği format)
    """
    import base64
    import string
    
    # 16 karakterlik rastgele ID
    random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    timestamp = int(time.time()) - random.randint(3600, 86400)
    
    # YouTube'un beklediği format (Cgt...)
    visitor_data = f"Cgt{random_id}Sj{timestamp}Dg=="
    return visitor_data


def get_hls_with_po_token(video_id):
    """
    PO Token ile YouTube canlı yayınından HLS bağlantısını al
    """
    # PO Token al
    po_token, visitor_data = get_po_token_from_provider()
    
    if not po_token:
        print(f"      ⚠️ PO Token alınamadı")
        return None
    
    # yt-dlp komutunu hazırla
    cmd = [
        'yt-dlp',
        '--no-warnings',
        '--no-cache-dir',
        '--extractor-args', f'youtubepot:po_token={po_token}:visitor_data={visitor_data}',
        '-g',  # Sadece URL'yi göster
        '-f', 'best',  # En iyi format
        f'https://www.youtube.com/watch?v={video_id}'
    ]
    
    try:
        print(f"      📤 yt-dlp çalıştırılıyor...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output and ('.m3u8' in output or 'manifest' in output):
                print(f"      ✅ HLS URL alındı")
                return output
            else:
                print(f"      ⚠️ HLS URL bulunamadı: {output[:100]}")
        else:
            error_msg = result.stderr.lower()
            if 'po token' in error_msg or 'sign in' in error_msg:
                print(f"      ⚠️ PO Token geçersiz, yenisi denenmeli")
            elif '403' in error_msg:
                print(f"      ⚠️ 403 Forbidden - IP engellenmiş olabilir")
            else:
                print(f"      ⚠️ yt-dlp hatası: {result.stderr[:100]}")
                
    except subprocess.TimeoutExpired:
        print(f"      ⚠️ Zaman aşımı")
    except Exception as e:
        print(f"      ⚠️ Beklenmeyen hata: {str(e)[:50]}")
    
    return None


def generate_m3u():
    """Ana M3U dosyasını oluştur"""
    
    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # PO Token provider'ın çalıştığını kontrol et
    try:
        health = requests.get('http://localhost:4416/health', timeout=2)
        if health.status_code == 200:
            print(f"✅ PO Token provider çalışıyor (v{health.text.strip()})")
        else:
            print(f"❌ PO Token provider sağlıklı değil!")
            return False
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
            wait_time = random.randint(15, 20)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (PO Token Provider - Düzeltilmiş) Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
