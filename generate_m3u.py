#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import re
import time
import sys
from datetime import datetime

# YouTube Android Uygulamasının Gerçek Kimlik Bilgileri
ANDROID_CLIENT = {
    'clientName': 'ANDROID',
    'clientVersion': '19.09.37',  # Güncel bir sürüm
    'androidSdkVersion': 33,
    'osName': 'Android',
    'osVersion': '13',
    'platform': 'MOBILE',
    'userAgent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 13; TR) gzip',
    'clientId': 3
}

# Google Play Store İmzası (YouTube uygulaması için)
ANDROID_CERT = '24BB24C05A47ED07B1547F1FB2E5A14D8231FABF'
PACKAGE_NAME = 'com.google.android.youtube'

# YouTube API Anahtarı (Android uygulamasının kullandığı)
YOUTUBE_API_KEY = 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w'


def get_hls_from_youtube(video_id):
    """
    Bir YouTube canlı yayınından HLS bağlantısını alır.
    Bu fonksiyon, YouTube Android uygulamasının kimliğine bürünerek en istikrarlı sonucu verir.
    """
    
    # Android uygulamasını taklit eden header'lar
    headers = {
        'User-Agent': ANDROID_CLIENT['userAgent'],
        'Content-Type': 'application/json',
        'X-Android-Package': PACKAGE_NAME,
        'X-Android-Cert': ANDROID_CERT,
        'X-YouTube-Client-Name': str(ANDROID_CLIENT['clientId']),
        'X-YouTube-Client-Version': ANDROID_CLIENT['clientVersion'],
        'Accept': 'application/json',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    
    # Android uygulamasının göndereceği gerçekçi payload
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
                "utcOffsetMinutes": 180,
                "deviceModel": "SM-A127F"  # Gerçek bir cihaz modeli
            },
            "thirdParty": {
                "embedUrl": "https://www.youtube.com"
            }
        },
        "playbackContext": {
            "contentPlaybackContext": {
                "currentUrl": f"/watch?v={video_id}",
                "html5Preference": "HTML5_PREF_WANTS"
            }
        },
        "racyCheckOk": True,
        "contentCheckOk": True
    }
    
    try:
        # API isteğini gönder
        response = requests.post(
            f'https://www.youtube.com/youtubei/v1/player?key={YOUTUBE_API_KEY}',
            headers=headers,
            json=payload,
            timeout=15
        )
        
        # Cevabı kontrol et
        if response.status_code != 200:
            print(f"  ⚠️ HTTP Hatası {response.status_code}")
            return None
            
        data = response.json()
        
        # Hata kontrolü
        if data.get('error'):
            print(f"  ⚠️ API Hatası: {data['error'].get('message', 'Bilinmiyor')}")
            return None
            
        # Canlı yayın mı?
        if not data.get('videoDetails', {}).get('isLive', False):
            print(f"  ⚠️ Canlı yayın değil")
            return None
            
        # HLS URL'ini al
        hls_url = data.get('streamingData', {}).get('hlsManifestUrl')
        if not hls_url:
            print(f"  ⚠️ HLS URL bulunamadı")
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
        print(f"  ⚠️ Zaman aşımı")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ Bağlantı hatası: {str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"  ⚠️ Geçersiz JSON cevabı")
        return None
    except Exception as e:
        print(f"  ⚠️ Beklenmeyen hata: {str(e)}")
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
        
        hls_url = get_hls_from_youtube(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ HLS alındı")
            success_count += 1
        else:
            print(f"   ❌ Başarısız")
        
        # YouTube'a saygı: Her istek arasında 2-3 saniye bekle (ÇOK ÖNEMLİ!)
        if idx < total:  # Son istekten sonra bekleme
            wait_time = 2 + (idx % 2)  # 2 veya 3 saniye
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # M3U dosyasını yaz
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    print(f"📁 Çıktı: youtube.m3u")
    
    return success_count > 0


if __name__ == '__main__':
    success = generate_m3u()
    sys.exit(0 if success else 1)
