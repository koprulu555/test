#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import random
import shutil
from datetime import datetime

def get_hls_with_ytdlp_ytse(video_id):
    """
    yt-dlp-ytse ile YouTube canlı yayınından HLS bağlantısını al
    """
    # yt-dlp'nin tam yolunu bul
    yt_dlp_path = shutil.which('yt-dlp')
    
    if not yt_dlp_path:
        # Alternatif yolları dene
        possible_paths = [
            '/usr/local/bin/yt-dlp',
            '/usr/bin/yt-dlp',
            f'{sys.prefix}/bin/yt-dlp'
        ]
        for path in possible_paths:
            if shutil.which(path) or True:  # Basit kontrol
                yt_dlp_path = path
                break
    
    if not yt_dlp_path:
        # Son çare: pip show ile bulmaya çalış
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', 'yt-dlp-ytse'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Genelde ~/.local/bin/yt-dlp olur
                yt_dlp_path = f'{sys.prefix}/bin/yt-dlp'
        except:
            pass
    
    cmd = [
        yt_dlp_path or 'yt-dlp',  # Fallback
        '--no-warnings',
        '--no-cache-dir',
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
                return output
            else:
                print(f"      ⚠️ HLS URL bulunamadı")
        else:
            error_msg = result.stderr.lower()
            if '403' in error_msg:
                print(f"      ⚠️ 403 Forbidden - IP engellenmiş olabilir")
            elif 'sign in' in error_msg:
                print(f"      ⚠️ YouTube oturum gerektiriyor")
            else:
                print(f"      ⚠️ yt-dlp hatası: {result.stderr[:100]}")
                
    except subprocess.TimeoutExpired:
        print(f"      ⚠️ Zaman aşımı")
    except Exception as e:
        print(f"      ⚠️ Hata: {str(e)[:50]}")
    
    return None


def generate_m3u():
    print(f"\n🎬 YouTube M3U Jeneratör - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        with open('ids.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("❌ ids.txt bulunamadı!")
        return False
    
    m3u_content = ['#EXTM3U']
    success_count = 0
    total = len(lines)
    
    for idx, line in enumerate(lines, 1):
        parts = line.split('|')
        if len(parts) != 3:
            continue
        
        name, url, logo = parts
        video_id = url.split('=')[-1]
        
        print(f"\n📺 [{idx}/{total}] {name}")
        
        hls_url = get_hls_with_ytdlp_ytse(video_id)
        
        if hls_url:
            m3u_content.append(f'\n#EXTINF:-1 tvg-id="{video_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="Canlı TV",{name}')
            m3u_content.append(hls_url)
            print(f"   ✅ BAŞARILI!")
            success_count += 1
        else:
            print(f"   ❌ BAŞARISIZ")
        
        if idx < total:
            wait_time = random.randint(10, 15)
            print(f"   ⏳ {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
    
    with open('youtube.m3u', 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_content))
    
    print(f"\n📊 ÖZET: {success_count}/{total} kanal başarılı")
    return success_count > 0


if __name__ == '__main__':
    print("🚀 YouTube M3U Generator (yt-dlp-ytse) Başlatılıyor...")
    success = generate_m3u()
    sys.exit(0 if success else 1)
