#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys
import random
import re
import execjs  # JavaScript motoru
from datetime import datetime

# yt-dlp'nin kullandığı güncel API key'leri
YOUTUBE_API_KEYS = [
    'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',  # Web client
    'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',  # Android client
    'AIzaSyDCU8hxkR5BqB2CvNbI5sxr8bR1V75Iwhg',  # iOS client
]

class YouTubeClient:
    def __init__(self):
        self.device_model = 'SM-A127F'
        self.os_version = '14'
        self.po_token = None
        self.js_context = None
        
    def get_po_token(self, video_id):
        """
        YouTube'un PO Token'ını çöz - JavaScript challenge
        """
        try:
            # Önce normal sayfayı çek
            response = requests.get(
                f'https://www.youtube.com/watch?v={video_id}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=10
            )
            
            html = response.text
            
            # Player JS dosyasını bul
            player_js_match = re.search(r'src="(/s/player/[^"]+base\.js)"', html)
            if not player_js_match:
                return None
                
            player_js_url = f'https://www.youtube.com{player_js_match.group(1)}'
            
            # Player JS'yi çek
            player_js = requests.get(player_js_url, timeout=10)
            
            # JS içindeki challenge kodunu bul
            challenge_pattern = r'function\([^\)]*\){[^}]*decodeURIComponent[^}]*}'
            challenge_code = re.search(challenge_pattern, player_js.text)
            
            if challenge_code:
                # JavaScript motoru ile challenge'ı çöz
                ctx = execjs.compile(challenge_code.group())
                self.po_token = ctx.call('solve')
                print(f"   🔑 PO Token alındı")
                return self.po_token
                
        except Exception as e:
            print(f"   ⚠️ PO Token hatası: {str(e)}")
            
        return None
    
    def get_headers(self):
        """Android uygulaması header'ları"""
        headers = {
            'User-Agent': f'com.google.android.youtube/19.48.41 (Linux; U; Android {self.os_version}; {self.device_model})',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9',
            'X-YouTube-Client-Name': '3',
            'X-YouTube-Client-Version': '19.48.41',
            'Connection': 'Keep-Alive'
        }
        
        # PO Token varsa ekle
        if self.po_token:
            headers['X-YouTube-PO-Token'] = self.po_token
            headers['X-YouTube-PO-Token-Provider'] = 'web'
            
        return headers
    
    def get_payload(self, video_id):
        """Minimal payload"""
        return {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.48.41",
                    "androidSdkVersion": 34,
                    "osName": "Android",
                    "osVersion": self.os_version,
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
    YouTube canlı yayınından HLS bağlantısını al - PO Token ile
    """
    client = YouTubeClient()
    
    print(f"   🔍 PO Token alınıyor...")
    po_token = client.get_po_token(video_id)
    
    if not po_token:
        print(f"   ⚠️ PO Token alınamadı, devam ediliyor...")
    
    # Tüm API key'lerini dene
    for idx, api_key in enumerate(YOUTUBE_API_KEYS, 1):
        print(f"   🔑 API Key {idx} deneniyor...")
        
        try:
            response = requests.post(
                f'https://www.youtube.com/youtubei/v1/player?key={api_key}',
                headers=client.get_headers(),
                json=client.get_payload(video_id),
                timeout=15
            )
            
            print(f"      HTTP {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('videoDetails', {}).get('isLive'):
                    hls_url = data.get('streamingData', {}).get('hlsManifestUrl')
                    if hls_url:
                        print(f"      ✅ BAŞARILI!")
                        
                        # hls_variant -> hls_playlist dönüşümü
                        hls_url = hls_url.replace('hls_variant', 'hls_playlist')
                        hls_url = hls_url.replace('&', '/')
                        
                        if '/live/1' not in hls_url:
                            hls_url = hls_url.replace('/source/yt_live_broadcast', '/source/yt_live_broadcast/live/1')
                        if '/ratebypass/yes' not in hls_url:
                            hls_url += '/ratebypass/yes'
                        
                        return hls_url
                        
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', '')
                print(f"      ⚠️ {error_msg[:50]}")
                
        except Exception as e:
            print(f"      ⚠️ Hata: {str(e)[:50]}")
            
        time.sleep(2)
    
    return None


def generate_m3u():
    """Ana M3U dosyasını oluştur"""
    
    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
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
        
        if idx < total:
            wait_time = random.randint(15, 20)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (PO Token Çözümlü) Başlatılıyor...")
    success = generate_m3u()
    
    if success:
        print("\n✅ İşlem tamamlandı!")
        sys.exit(0)
    else:
        print("\n❌ İşlem başarısız!")
        sys.exit(1)
