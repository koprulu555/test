#!/bin/bash

# =============================================
# YOUTUBE M3U OTOMATİK GÜNCELLEYİCİ
# tecotv tarzı - HEADER'ları da kontrol eder
# =============================================

set -e

echo "🚀 YouTube M3U güncelleme başladı: $(date)"

# Renkli çıktı için
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Kanal listesini oku
if [ ! -f "kanallar.json" ]; then
    echo -e "${RED}❌ kanallar.json bulunamadı!${NC}"
    exit 1
fi

# Playlist klasörünü temizle
mkdir -p playlist
rm -f playlist/*.m3u8

# İstatistikler
TOPLAM=0
BASARILI=0
BASARISIZ=0

# JSON'daki her kanal için
jq -c '.[]' kanallar.json | while read -r i; do
    TOPLAM=$((TOPLAM + 1))
    
    name=$(echo "$i" | jq -r '.name')
    url=$(echo "$i" | jq -r '.url')
    category=$(echo "$i" | jq -r '.category // "diğer"')
    
    echo -e "\n${YELLOW}📺 [$TOPLAM] ${name} (${category})${NC}"
    
    # ===== CRITICAL FIX: -i flag'i EKLENDİ! =====
    # YouTube manifest linkini HEADER'lardan bul
    manifest=$(curl -i -s --max-time 30 "$url" | grep -o "https://manifest.googlevideo.com[^[:space:]\"']*" | head -n 1 | tr -d '\r\n')
    
    if [ ! -z "$manifest" ] && [[ "$manifest" == http* ]]; then
        # Dosya adını güvenli hale getir
        safe_name=$(echo "$name" | sed 's/[^a-zA-Z0-9_-]/_/g')
        
        # M3U8 dosyasını oluştur (tecotv formatında)
        cat <<EOF > "playlist/${safe_name}.m3u8"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720
$manifest
EOF
        echo -e "${GREEN}   ✅ BAŞARILI: $name${NC}"
        BASARILI=$((BASARILI + 1))
    else
        echo -e "${RED}   ❌ BAŞARISIZ: $name - Manifest bulunamadı${NC}"
        BASARISIZ=$((BASARISIZ + 1))
    fi
    
    sleep 1
done

# Ana playlist oluştur
echo -e "\n${YELLOW}📝 Ana playlist oluşturuluyor...${NC}"

{
    echo "#EXTM3U"
    echo "# Ana M3U Playlist - $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
} > playlist/playlist.m3u

# Her kanalın m3u8'ini ana listeye ekle
for file in playlist/*.m3u8; do
    [ "$file" = "playlist/playlist.m3u" ] && continue
    [ -s "$file" ] || continue
    
    filename=$(basename "$file" .m3u8)
    
    # Kanal adını JSON'dan bul
    kanal_adi=$(jq -r --arg f "$filename" '.[] | select(.name | sed "s/[^a-zA-Z0-9_-]/_/g" == $f) | .name' kanallar.json | head -n 1)
    
    if [ -z "$kanal_adi" ]; then
        kanal_adi="$filename"
    fi
    
    kategori=$(jq -r --arg n "$kanal_adi" '.[] | select(.name == $n) | .category // "diğer"' kanallar.json | head -n 1)
    
    # Ana listeye ekle (tecotv formatında)
    echo "#EXTINF:-1,$kanal_adi" >> playlist/playlist.m3u
    echo "https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/main/playlist/${filename}.m3u8?t=$(date +%s)" >> playlist/playlist.m3u
done

# README oluştur
cat > README.md <<EOF
# 📺 YouTube M3U Playlist

## 📊 İstatistikler
- **Son Güncelleme:** $(date '+%d.%m.%Y %H:%M:%S')
- **Toplam Kanal:** $TOPLAM
- **Başarılı:** $BASARILI
- **Başarısız:** $BASARISIZ

## 🔗 Playlist Bağlantısı

\`\`\`
https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/main/playlist/playlist.m3u
\`\`\`

## ⚙️ Otomatik Güncelleme
Her 5 saatte bir otomatik güncellenir.
EOF

# Özet
echo -e "\n${GREEN}✅ İŞLEM TAMAMLANDI${NC}"
echo "📊 Toplam: $TOPLAM, Başarılı: $BASARILI, Başarısız: $BASARISIZ"
echo "📁 Playlist: playlist/playlist.m3u"

# Başarısız kanalları listele
if [ $BASARISIZ -gt 0 ]; then
    echo -e "\n${YELLOW}⚠️ Başarısız kanallar:${NC}"
    jq -r '.[] | .name' kanallar.json | while read -r name; do
        safe_name=$(echo "$name" | sed 's/[^a-zA-Z0-9_-]/_/g')
        if [ ! -f "playlist/${safe_name}.m3u8" ]; then
            echo "   ❌ $name"
        fi
    done
fi
