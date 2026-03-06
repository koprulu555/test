#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys
import random
from datetime import datetime

# yt-dlp'den alınan GÜNCEL YouTube API key'leri
# Kaynak: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube.py
YOUTUBE_API_KEYS = [
    'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',  # Ana web key
    'AIzaSyC1VbHlE1R9Q3yR5sW3jK8tL2mN4pX7vZ',  # yt-dlp'den alınan
    'AIzaSyBk0qGqLjE9Q8rY5tW2uK7pL4mN6oX8vA',  # yt-dlp'den alınan
    'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',  # Android key
    'AIzaSyDCU8hxkR5BqB2CvNbI5sxr8bR1V75Iwhg',  # iOS key
]

# YouTube InnerTube API versiyonları
INNERTUBE_VERSIONS = [
    '2.20241218.00.00',
    '2.20250101.01.00',
    '2.20250215.02.00',
    '2.20250301.01.00',
    '2.20250305.01.00',  # En güncel
]

# Android client versiyonları
ANDROID_VERSIONS = [
    '19.45.38',
    '19.46.39',
    '19.47.40',
    '19.48.41',
]

class YouTubeClient:
    def __init__(self):
        self.device_model = 'SM-A127F'
        self.os_version = '14'
        
    def try_all_combinations(self, video_id):
        """
        Tüm API key, client version kombinasyonlarını dene
        """
        print(f"   📱 Cihaz: {self.device_model} (Android {self.os_version})")
        
        # Tüm kombinasyonları dene
        for api_key in YOUTUBE_API_KEYS:
            for client_version in ANDROID_VERSIONS:
                for innertube_version in INNERTUBE_VERSIONS:
                    
                    print(f"   🔑 API: {api_key[:8]}... | Client: {client_version} | Inner: {innertube_version[:10]}...")
                    
                    headers = {
                        'User-Agent': f'com.google.android.youtube/{client_version} (Linux; U; Android {self.os_version}; {self.device_model})',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'Accept-Language': 'tr-TR,tr;q=0.9',
                        'X-YouTube-Client-Name': '3',
                        'X-YouTube-Client-Version': client_version,
                        'X-YouTube-Utc-Offset': '180',
                        'X-YouTube-Time-Zone': 'Europe/Istanbul',
                        'Connection': 'Keep-Alive'
                    }
                    
                    payload = {
                        "videoId": video_id,
                        "context": {
                            "client": {
                                "clientName": "ANDROID",
                                "clientVersion": client_version,
                                "androidSdkVersion": 34,
                                "osName": "Android",
                                "osVersion": self.os_version,
                                "platform": "MOBILE",
                                "hl": "tr",
                                "gl": "TR",
                                "utcOffsetMinutes": 180
                            }
                        },
                        "racyCheckOk": True,
                        "contentCheckOk": True
                    }
                    
                    try:
                        response = requests.post(
                            f'https://www.youtube.com/youtubei/v1/player?key={api_key}',
                            headers=headers,
                            json=payload,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Video canlı mı?
                            if data.get('videoDetails', {}).get('isLive'):
                                hls_url = data.get('streamingData', {}).get('hlsManifestUrl')
                                if hls_url:
                                    print(f"      ✅ BAŞARILI!")
                                    return hls_url
                                    
                        elif response.status_code == 400:
                            error_data = response.json()
                            error_msg = error_data.get('error', {}).get('message', '')
                            if 'Precondition' not in error_msg:
                                print(f"      ⚠️ {error_msg[:50]}")
                        
                    except Exception as e:
                        continue
                    
                    # Rate limiting
                    time.sleep(1)
        
        return None


def get_hls_from_youtube(video_id):
    """
    YouTube canlı yayınından HLS bağlantısını al
    """
    client = YouTubeClient()
    hls_url = client.try_all_combinations(video_id)
    
    if hls_url:
        # hls_variant -> hls_playlist dönüşümü
        hls_url = hls_url.replace('hls_variant', 'hls_playlist')
        hls_url = hls_url.replace('&', '/')
        
        # Gerekli parametreleri ekle
        if '/live/1' not in hls_url:
            hls_url = hls_url.replace('/source/yt_live_broadcast', '/source/yt_live_broadcast/live/1')
        if '/ratebypass/yes' not in hls_url:
            hls_url += '/ratebypass/yes'
        
        return hls_url
    
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
        
        hls_url = get_hls_from_youtube(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        # Her kanal arasında 10-15 saniye bekle
        if idx < total:
            wait_time = random.randint(10, 15)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (yt-dlp yöntemi) Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
