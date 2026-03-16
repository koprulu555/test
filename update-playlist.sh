#!/bin/bash

# =============================================
# YOUTUBE M3U OTOMATİK GÜNCELLEYİCİ
# tecotv tarzı - GitHub Actions için optimize
# =============================================

set -e  # Hata olursa dur

echo "🚀 YouTube M3U güncelleme başladı: $(date)"

# Renkli çıktı için
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
echo -e "${YELLOW}📡 Kanallar taranıyor...${NC}"

jq -c '.[]' kanallar.json | while read -r i; do
    TOPLAM=$((TOPLAM + 1))
    
    name=$(echo "$i" | jq -r '.name')
    url=$(echo "$i" | jq -r '.url')
    category=$(echo "$i" | jq -r '.category // "diğer"')
    
    echo -e "\n${YELLOW}📺 [$TOPLAM] ${name} (${category})${NC}"
    
    # YouTube'dan manifest linkini çek
    # -i: header'ları da göster
    # -s: silent mode
    # --max-time: 30 saniye timeout
    manifest=$(curl -i -s --max-time 30 "$url" | grep -o "https://manifest.googlevideo.com[^[:space:]\"']*" | head -n 1 | tr -d '\r\n')
    
    if [ ! -z "$manifest" ] && [[ "$manifest" == http* ]]; then
        # Her kanal için ayrı m3u8 dosyası
        # Dosya adını güvenli hale getir (boşluklar vs)
        safe_name=$(echo "$name" | tr ' ' '_' | tr -d '[:punct:]')
        
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
    
    # YouTube'u yormamak için bekle (1 saniye)
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
    
    # Dosya adından kanal adını al
    filename=$(basename "$file" .m3u8)
    
    # Kanal adını JSON'dan bul (daha güzel görüntü için)
    kanal_adi=$(jq -r --arg f "$filename" '.[] | select(.name | gsub(" "; "_") | gsub("[[:punct:]]"; "") == $f) | .name' kanallar.json | head -n 1)
    
    if [ -z "$kanal_adi" ]; then
        kanal_adi="$filename"
    fi
    
    # Kategoriyi bul
    kategori=$(jq -r --arg n "$kanal_adi" '.[] | select(.name == $n) | .category // "diğer"' kanallar.json | head -n 1)
    
    # Ana listeye ekle
    echo "#EXTINF:-1 group-title=\"$kategori\" tvg-logo=\"\" ,$kanal_adi" >> playlist/playlist.m3u
    echo "https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/main/playlist/${filename}.m3u8?t=$(date +%s)" >> playlist/playlist.m3u
done

# README oluştur/güncelle
cat > README.md <<EOF
# 📺 YouTube M3U Playlist

## 📊 İstatistikler
- **Son Güncelleme:** $(date '+%d.%m.%Y %H:%M:%S')
- **Toplam Kanal:** $TOPLAM
- **Başarılı:** $BASARILI
- **Başarısız:** $BASARISIZ

## 📋 Kanallar

$(jq -r '.[] | "- **\(.name)** (\(.category // "diğer"))"' kanallar.json)

## 🔗 Playlist Bağlantısı

\`\`\`
https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/main/playlist/playlist.m3u
\`\`\`

## ⚙️ Otomatik Güncelleme
Bu playlist her **5 saatte** bir otomatik güncellenir.
EOF

# Özet
echo -e "\n${GREEN}✅ İŞLEM TAMAMLANDI${NC}"
echo "📊 Toplam: $TOPLAM, Başarılı: $BASARILI, Başarısız: $BASARISIZ"
echo "📁 Playlist: playlist/playlist.m3u"
