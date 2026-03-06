#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys
import random
from datetime import datetime

# YouTube Android Uygulamasının GERÇEK Kimlik Bilgileri
class YouTubeAndroidClient:
    def __init__(self):
        self.client_name = 'ANDROID'
        self.client_version = '19.45.38'
        self.android_sdk_version = 34
        self.os_name = 'Android'
        self.os_version = '14'
        self.platform = 'MOBILE'
        self.device_model = 'SM-A127F'
        
        # Rastgele device ID üret
        self.device_id = self._generate_device_id()
        
    def _generate_device_id(self):
        """Android cihaz ID'si formatında rastgele ID üret"""
        import uuid
        return str(uuid.uuid4()).replace('-', '')[:16]
    
    def get_headers(self):
        """Android uygulamasının gönderdiği header'lar"""
        return {
            'User-Agent': f'com.google.android.youtube/{self.client_version} (Linux; U; Android {self.os_version}; {self.device_model})',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'X-YouTube-Client-Name': '3',  # ANDROID = 3
            'X-YouTube-Client-Version': self.client_version,
            'X-YouTube-Utc-Offset': '180',
            'X-YouTube-Time-Zone': 'Europe/Istanbul',
            'Connection': 'Keep-Alive'
        }
    
    def get_payload(self, video_id):
        """Android uygulamasının gönderdiği payload - DÜZELTİLDİ"""
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
                    "gl": "TR",
                    "timeZone": "Europe/Istanbul",
                    "utcOffsetMinutes": 180,
                    "deviceModel": self.device_model
                },
                "user": {
                    "lockedSafetyMode": False
                },
                "request": {
                    "useSsl": True
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True
        }


# YouTube API Anahtarı
YOUTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'


def get_hls_from_youtube(video_id, client):
    """
    YouTube canlı yayınından HLS bağlantısını al
    """
    
    api_url = 'https://www.youtube.com/youtubei/v1/player'
    headers = client.get_headers()
    payload = client.get_payload(video_id)
    
    try:
        print(f"   📤 İstek gönderiliyor...")
        print(f"   📱 Cihaz: {client.device_model} (Android {client.os_version})")
        
        # İsteği gönder
        response = requests.post(
            f'{api_url}?key={YOUTUBE_API_KEY}',
            headers=headers,
            json=payload,
            timeout=15
        )
        
        print(f"   📥 HTTP {response.status_code}")
        
        if response.status_code != 200:
            print(f"   📄 Hata detayı: {response.text[:300]}")
            return None
        
        data = response.json()
        
        # Video detaylarını kontrol et
        video_details = data.get('videoDetails', {})
        if not video_details.get('isLive', False):
            print(f"   ⚠️ Video canlı değil: {video_details.get('title', 'Bilinmiyor')[:50]}")
            return None
        
        # Streaming data'yı al
        streaming_data = data.get('streamingData', {})
        hls_url = streaming_data.get('hlsManifestUrl')
        
        if not hls_url:
            print(f"   ⚠️ HLS URL bulunamadı")
            return None
        
        # hls_variant -> hls_playlist dönüşümü
        hls_url = hls_url.replace('hls_variant', 'hls_playlist')
        hls_url = hls_url.replace('&', '/')
        
        # Gerekli parametreleri ekle
        if '/live/1' not in hls_url:
            hls_url = hls_url.replace('/source/yt_live_broadcast', '/source/yt_live_broadcast/live/1')
        if '/ratebypass/yes' not in hls_url:
            hls_url += '/ratebypass/yes'
        
        return hls_url
        
    except Exception as e:
        print(f"   ⚠️ Hata: {str(e)}")
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
        
        # Her kanal için yeni client
        client = YouTubeAndroidClient()
        hls_url = get_hls_from_youtube(video_id, client)
        
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
