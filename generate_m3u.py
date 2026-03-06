#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys
import uuid
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
        self.device_brand = 'samsung'
        self.device_manufacturer = 'samsung'
        
        # Rastgele ama gerçekçi değerler üret
        self.device_id = self._generate_device_id()
        self.adapter_info = self._generate_adapter_info()
        self.adapter_info_hash = self._hash_string(self.adapter_info)
        
    def _generate_device_id(self):
        """Android cihaz ID'si formatında rastgele ID üret"""
        return ''.join(random.choices('0123456789abcdef', k=16))
    
    def _generate_adapter_info(self):
        """Gerçekçi adapter info üret"""
        adapters = ['WIFI', 'MOBILE', 'ETHERNET']
        return random.choice(adapters)
    
    def _hash_string(self, s):
        """String hash'le"""
        import hashlib
        return hashlib.md5(s.encode()).hexdigest()
    
    def get_headers(self):
        """Android uygulamasının gönderdiği TÜM header'lar"""
        return {
            'User-Agent': f'com.google.android.youtube/{self.client_version} (Linux; U; Android {self.os_version}; {self.device_model})',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'X-YouTube-Client-Name': '3',  # ANDROID = 3
            'X-YouTube-Client-Version': self.client_version,
            'X-YouTube-Device': f'DEVICE_TYPE_PHONE',
            'X-YouTube-Device-Model': self.device_model,
            'X-YouTube-Device-Brand': self.device_brand,
            'X-YouTube-Device-Manufacturer': self.device_manufacturer,
            'X-YouTube-Utc-Offset': '180',
            'X-YouTube-Time-Zone': 'Europe/Istanbul',
            'X-YouTube-Ad-Signals': self._generate_ad_signals(),
            'X-YouTube-Adapter-Info': self.adapter_info,
            'X-YouTube-Adapter-Info-Hash': self.adapter_info_hash,
            'X-YouTube-Device-ID': self.device_id,
            'X-YouTube-Device-ID-Hash': self._hash_string(self.device_id),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    
    def _generate_ad_signals(self):
        """Reklam sinyalleri üret"""
        import base64
        signals = {
            'session_id': str(uuid.uuid4()),
            'timestamp': int(time.time()),
            'random': random.randint(1000, 9999)
        }
        return base64.b64encode(json.dumps(signals).encode()).decode()
    
    def get_payload(self, video_id):
        """Android uygulamasının gönderdiği TÜM payload"""
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
                    "deviceModel": self.device_model,
                    "deviceBrand": self.device_brand,
                    "deviceManufacturer": self.device_manufacturer
                },
                "user": {
                    "lockedSafetyMode": False
                },
                "request": {
                    "useSsl": True
                },
                "thirdParty": {
                    "embedUrl": "https://www.youtube.com"
                },
                "adSignalsInfo": {
                    "params": [
                        {
                            "key": "mt_op",
                            "value": "1"
                        },
                        {
                            "key": "mt_op",
                            "value": "1"
                        }
                    ]
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True,
            "playbackContext": {
                "contentPlaybackContext": {
                    "currentUrl": f"/watch?v={video_id}",
                    "html5Preference": "HTML5_PREF_WANTS",
                    "lactMilliseconds": str(random.randint(10000, 60000)),
                    "autoplay": True,
                    "autonavState": "AUTONAV_STATE_OFF"
                }
            },
            "cpn": self._generate_cpn()
        }
    
    def _generate_cpn(self):
        """Rastgele CPN (Client Playback Nonce) üret"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))


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
    
    # Her kanal için yeni bir client oluştur (farklı device ID ile)
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
        
        # Her kanal için yeni client oluştur (farklı device ID)
        client = YouTubeAndroidClient()
        hls_url = get_hls_from_youtube(video_id, client)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        # Her kanal arasında 5-8 saniye bekle
        if idx < total:
            wait_time = random.randint(5, 8)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
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
