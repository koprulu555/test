#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import sys
import re
from datetime import datetime

def get_hls_with_ytdlp(video_id):
    """
    yt-dlp ve PO Token plugin ile YouTube canlı yayınından HLS bağlantısını al
    """
    try:
        # yt-dlp ile direkt HLS URL'ini çek
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-cache-dir',
            '--extractor-args', 'youtubepot:provider=bgutil',
            '-g',  # Sadece URL'yi göster
            '-f', 'best',  # En iyi format
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        # Çıktıyı kontrol et
        output = result.stdout.strip()
        if output and '.m3u8' in output:
            print(f"      ✅ HLS URL alındı")
            return output
            
    except subprocess.CalledProcessError as e:
        print(f"      ⚠️ yt-dlp hatası: {e.stderr[:100]}")
    except Exception as e:
        print(f"      ⚠️ Beklenmeyen hata: {str(e)}")
    
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
        
        # yt-dlp ile HLS URL'ini al
        hls_url = get_hls_with_ytdlp(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        # Her kanal arasında 10 saniye bekle
        if idx < total:
            print(f"   ⏳ 10 saniye bekleniyor...")
            time.sleep(10)
    
    # M3U dosyasını yaz
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
