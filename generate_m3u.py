#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import re
import time
import sys
from datetime import datetime
import base64
import hashlib

# YouTube Android Uygulamasının GÜNCEL Kimlik Bilgileri
ANDROID_CLIENT = {
    'clientName': 'ANDROID',
    'clientVersion': '19.45.38',  # Güncel sürüm
    'androidSdkVersion': 34,
    'osName': 'Android',
    'osVersion': '14',
    'platform': 'MOBILE',
    'userAgent': 'com.google.android.youtube/19.45.38 (Linux; U; Android 14; TR) gzip',
    'clientId': '3'  # String olmalı
}

# YouTube API Anahtarı (Android uygulamasının kullandığı - DOĞRU OLAN)
YOUTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'


def generate_android_signature():
    """Android uygulama imzası oluştur (gerçekçi)"""
    # Gerçek bir YouTube uygulaması imzası
    return '24BB24C05A47ED07B1547F1FB2E5A14D8231FABF'


def get_hls_from_youtube(video_id):
    """
    Bir YouTube canlı yayınından HLS bağlantısını alır.
    Android uygulaması kimliğiyle - DÜZELTİLMİŞ VERSİYON
    """
    
    # Doğru API endpoint'i
    api_url = 'https://www.youtube.com/youtubei/v1/player'
    
    # Android uygulamasını taklit eden header'lar (DÜZELTİLDİ)
    headers = {
        'User-Agent': ANDROID_CLIENT['userAgent'],
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-YouTube-Client-Name': ANDROID_CLIENT['clientId'],
        'X-YouTube-Client-Version': ANDROID_CLIENT['clientVersion'],
        'X-YouTube-Utc-Offset': '180',
        'X-YouTube-Time-Zone': 'Europe/Istanbul',
        'X-YouTube-Page-Label': 'youtube.android.player_20260305_01_RC00',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    
    # Android uygulamasının göndereceği gerçekçi payload (DÜZELTİLDİ)
    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": ANDROID_CLIENT['clientName'],
                "clientVersion": ANDROID_CLIENT['clientVersion'],
                "androidSdkVersion": ANDROID_CLIENT['androidSdkVersion'],
                "osName": ANDROID_CLIENT['osName'],
                "osVersion": ANDROID_CLIENT['osVersion'],
                "platform": ANDROID_CLIENT['platform'],
                "hl": "tr",
                "gl": "TR",
                "timeZone": "Europe/Istanbul",
                "utcOffsetMinutes": 180
            },
            "thirdParty": {
                "embedUrl": "https://www.youtube.com"
            }
        },
        "racyCheckOk": True,
        "contentCheckOk": True
    }
    
    try:
        print(f"   📤 İstek gönderiliyor...")
        
        # API isteğini gönder (query string ile)
        response = requests.post(
            f'{api_url}?key={YOUTUBE_API_KEY}',
            headers=headers,
            json=payload,
            timeout=15
        )
        
        print(f"   📥 HTTP {response.status_code}")
        
        # Cevabı kontrol et
        if response.status_code != 200:
            print(f"   📄 Cevap (ilk 200): {response.text[:200]}")
            return None
            
        data = response.json()
        
        # Hata kontrolü
        if data.get('error'):
            print(f"   ⚠️ API Hatası: {data['error'].get('message', 'Bilinmiyor')}")
            return None
            
        # Canlı yayın mı?
        if not data.get('videoDetails', {}).get('isLive', False):
            print(f"   ⚠️ Canlı yayın değil")
            return None
            
        # HLS URL'ini al
        streaming_data = data.get('streamingData', {})
        hls_url = streaming_data.get('hlsManifestUrl')
        
        if not hls_url:
            # Alternatif: formats içinde ara
            formats = streaming_data.get('formats', [])
            for fmt in formats:
                if 'hls' in fmt.get('url', ''):
                    hls_url = fmt.get('url')
                    break
        
        if not hls_url:
            print(f"   ⚠️ HLS URL bulunamadı")
            return None
            
        # hls_variant -> hls_playlist dönüşümü (EN KRİTİK ADIM)
        hls_url = hls_url.replace('hls_variant', 'hls_playlist')
        hls_url = hls_url.replace('&', '/')
        
        # Gerekli parametreleri ekle
        if '/live/1' not in hls_url:
            hls_url = hls_url.replace('/source/yt_live_broadcast', '/source/yt_live_broadcast/live/1')
        if '/ratebypass/yes' not in hls_url:
            hls_url += '/ratebypass/yes'
            
        return hls_url
        
    except requests.exceptions.Timeout:
        print(f"   ⚠️ Zaman aşımı")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ Bağlantı hatası: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"   ⚠️ Geçersiz JSON: {str(e)}")
        print(f"   📄 Cevap (ilk 200): {response.text[:200]}")
        return None
    except Exception as e:
        print(f"   ⚠️ Beklenmeyen hata: {str(e)}")
        return None


def generate_m3u():
    """Ana M3U dosyasını oluşturur"""
    
    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # ids.txt'yi oku
    try:
        with open('ids.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("❌ ids.txt dosyası bulunamadı!")
        return False
    
    if not lines:
        print("❌ ids.txt dosyası boş!")
        return False
    
    m3u_content = ['#EXTM3U']
    success_count = 0
    total = len(lines)
    
    for idx, line in enumerate(lines, 1):
        parts = line.split('|')
        if len(parts) != 3:
            print(f"⚠️ Geçersiz satır ({idx}. satır): {line}")
            continue
            
        name, url, logo = parts
        video_id = url.split('=')[-1] if '=' in url else url
        
        print(f"\n📺 [{idx}/{total}] {name}")
        print(f"   ID: {video_id}")
        print(f"   Logo: {logo[:50]}...")
        
        hls_url = get_hls_from_youtube(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ HLS alındı: {hls_url[:100]}...")
            success_count += 1
        else:
            print(f"   ❌ Başarısız")
        
        # YouTube'a saygı: Her istek arasında 3-5 saniye bekle
        if idx < total:
            wait_time = 3 + (idx % 3)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    # Başarısız kanallar varsa uyarı
    if success_count < total:
        print(f"⚠️ {total - success_count} kanal alınamadı!")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
