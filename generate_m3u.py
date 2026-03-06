#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import re
import time
import sys
import random
from datetime import datetime
import base64

class YouTubeDynamicClient:
    """
    YouTube'un InnerTube API'sinden canlı olarak client bilgilerini çeker
    """
    
    def __init__(self):
        self.base_js_url = "https://www.youtube.com/s/player/"
        self.client_name = "ANDROID"
        self.client_version = None
        self.api_key = None
        self.device_model = "SM-A127F"
        
    def fetch_latest_config(self):
        """
        YouTube'un en son player config'inden API key ve client version'ı çeker
        """
        try:
            # Önce ana sayfadan player JS path'ini bul
            homepage = requests.get(
                "https://www.youtube.com",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=10
            )
            
            # player js dosyasının yolunu bul
            player_js_pattern = r'src="(/s/player/[^"]+base\.js)"'
            player_js_match = re.search(player_js_pattern, homepage.text)
            
            if not player_js_match:
                print("   ⚠️ Player JS bulunamadı")
                return False
                
            player_js_url = f"https://www.youtube.com{player_js_match.group(1)}"
            
            # Player JS dosyasını çek
            player_js = requests.get(player_js_url, timeout=10)
            
            # API key'i bul (youtubei.googleapis.com key'i)
            api_key_pattern = r'key="([^"]+)"'
            api_keys = re.findall(api_key_pattern, player_js.text)
            
            if api_keys:
                # En uzun key'i al (genelde doğru olan)
                self.api_key = max(set(api_keys), key=len)
                print(f"   🔑 API Key bulundu: {self.api_key[:10]}...")
            else:
                print("   ⚠️ API Key bulunamadı")
                return False
            
            # Client version'ı bul
            version_pattern = r'INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"'
            version_match = re.search(version_pattern, player_js.text)
            
            if version_match:
                self.client_version = version_match.group(1)
                print(f"   📱 Client Version: {self.client_version}")
            else:
                # Fallback version
                self.client_version = "19.45.38"
                print(f"   ⚠️ Fallback version: {self.client_version}")
            
            return True
            
        except Exception as e:
            print(f"   ⚠️ Config çekme hatası: {str(e)}")
            return False
    
    def get_headers(self):
        """Android uygulaması header'ları"""
        return {
            'User-Agent': f'com.google.android.youtube/{self.client_version} (Linux; U; Android 14; {self.device_model})',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-YouTube-Client-Name': '3',
            'X-YouTube-Client-Version': self.client_version,
            'X-YouTube-Utc-Offset': '180',
            'X-YouTube-Time-Zone': 'Europe/Istanbul',
            'Connection': 'Keep-Alive'
        }
    
    def get_payload(self, video_id):
        """Minimal ama çalışan payload"""
        return {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": self.client_name,
                    "clientVersion": self.client_version,
                    "androidSdkVersion": 34,
                    "osName": "Android",
                    "osVersion": "14",
                    "platform": "MOBILE",
                    "hl": "tr",
                    "gl": "TR"
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True
        }


def get_hls_from_youtube(video_id):
    """
    YouTube canlı yayınından HLS bağlantısını al - Dinamik API key ile
    """
    
    # Her kanal için yeni client oluştur
    client = YouTubeDynamicClient()
    
    print(f"   🔍 YouTube config çekiliyor...")
    if not client.fetch_latest_config():
        print("   ❌ Config alınamadı")
        return None
    
    if not client.api_key:
        print("   ❌ API key alınamadı")
        return None
    
    print(f"   📤 İstek gönderiliyor...")
    print(f"   📱 Client: {client.client_name} v{client.client_version}")
    
    try:
        response = requests.post(
            f'https://www.youtube.com/youtubei/v1/player?key={client.api_key}',
            headers=client.get_headers(),
            json=client.get_payload(video_id),
            timeout=15
        )
        
        print(f"   📥 HTTP {response.status_code}")
        
        if response.status_code != 200:
            print(f"   📄 Hata: {response.text[:200]}")
            return None
        
        data = response.json()
        
        # Video canlı mı?
        if not data.get('videoDetails', {}).get('isLive', False):
            print(f"   ⚠️ Video canlı değil")
            return None
        
        # HLS URL'ini al
        hls_url = data.get('streamingData', {}).get('hlsManifestUrl')
        
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
        
        hls_url = get_hls_from_youtube(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        # Her kanal arasında 8-12 saniye bekle (YouTube'u yormamak için)
        if idx < total:
            wait_time = random.randint(8, 12)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (Dinamik API Key) Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
