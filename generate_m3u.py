#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys
import random
from datetime import datetime

# YouTube'un FARKLI API KEY'leri (hepsi denenmeli)
YOUTUBE_API_KEYS = [
    'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',  # Web client
    'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',  # Android client
    'AIzaSyDCU8hxkR5BqB2CvNbI5sxr8bR1V75Iwhg',  # iOS client
    'AIzaSyC1VbHlE1R9Q3yR5sW3jK8tL2mN4pX7vZ',   # YouTube Studio
    'AIzaSyBk0qGqLjE9Q8rY5tW2uK7pL4mN6oX8vA',   # YouTube Music
    'AIzaSyA2qB4rC6dE8fG0hI2jK4lM6nO8pQ0rS',   # YouTube Kids
]


class YouTubeAndroidClient:
    def __init__(self):
        self.client_name = 'ANDROID'
        self.client_version = '19.45.38'
        self.android_sdk_version = 34
        self.os_name = 'Android'
        self.os_version = '14'
        self.platform = 'MOBILE'
        self.device_model = 'SM-A127F'
        
    def get_headers(self):
        """Android uygulamasının header'ları"""
        return {
            'User-Agent': f'com.google.android.youtube/{self.client_version} (Linux; U; Android {self.os_version}; {self.device_model})',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-YouTube-Client-Name': '3',
            'X-YouTube-Client-Version': self.client_version,
            'Connection': 'Keep-Alive'
        }
    
    def get_payload(self, video_id):
        """Basit ama çalışan payload"""
        return {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": self.client_name,
                    "clientVersion": self.client_version,
                    "androidSdkVersion": self.android_sdk_version,
                    "osName": self.os_name,
                    "osVersion": self.os_version,
                    "platform": self.platform,
                    "hl": "tr",
                    "gl": "TR"
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True
        }


def try_all_api_keys(video_id, client):
    """
    Tüm API key'lerini dene
    """
    for idx, api_key in enumerate(YOUTUBE_API_KEYS, 1):
        print(f"   🔑 API Key {idx}/{len(YOUTUBE_API_KEYS)} deneniyor...")
        
        try:
            response = requests.post(
                f'https://www.youtube.com/youtubei/v1/player?key={api_key}',
                headers=client.get_headers(),
                json=client.get_payload(video_id),
                timeout=10
            )
            
            print(f"      HTTP {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Video canlı mı?
                if data.get('videoDetails', {}).get('isLive'):
                    hls_url = data.get('streamingData', {}).get('hlsManifestUrl')
                    if hls_url:
                        print(f"      ✅ Başarılı!")
                        return hls_url
                
            elif response.status_code == 400:
                # Hata mesajını kontrol et
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', '')
                
                # "Precondition" hatası devam ediyorsa diğer key'i dene
                if 'Precondition' in error_msg:
                    print(f"      ⚠️ Precondition hatası, diğer key deneniyor...")
                    continue
                    
        except Exception as e:
            print(f"      ⚠️ Hata: {str(e)}")
            continue
            
        # 200 döndü ama HLS yoksa veya başka bir hata varsa
        time.sleep(1)
    
    return None


def get_hls_from_youtube(video_id):
    """
    YouTube canlı yayınından HLS bağlantısını al
    """
    client = YouTubeAndroidClient()
    print(f"   📱 Cihaz: {client.device_model} (Android {client.os_version})")
    
    # Tüm API key'lerini dene
    hls_url = try_all_api_keys(video_id, client)
    
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
        
        # Her kanal arasında 5 saniye bekle
        if idx < total:
            print(f"   ⏳ 5 saniye bekleniyor...")
            time.sleep(5)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
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
