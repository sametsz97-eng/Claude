#!/usr/bin/env bash
# AI ile üretilen sahneleri şarkıya göre kesip tek klipte birleştirir.
# Kullanım:  bash birlestir.sh
# Gerekli:   ffmpeg,  klipler/01.mp4 ... klipler/26.mp4,  ../song.m4a
#
# Ayarlar:
#   BASLIK=1      ilk 7 saniyeye "cennetten bi parça" yazısını ekler (sahne 01'de yazı yoksa)
#   ALTYAZI=1     şarkı sözlerini alt yazı olarak ekler (sozler.srt)
#   SARKI=dosya   farklı bir ses dosyası kullan
set -euo pipefail
cd "$(dirname "$0")"

BASLIK=${BASLIK:-0}
ALTYAZI=${ALTYAZI:-0}
SARKI=${SARKI:-../song.m4a}
W=1920; H=1080; FPS=30

# sahne süreleri (saniye), SAHNELER.md tablosuyla aynı sırada
SURELER=(7.6 4.9 3.9 3.5 4.0 4.3 3.7 3.9 3.5 7.3 3.7 6.1 5.6 6.8 7.4 7.7 7.0 3.1 4.0 6.0 6.0 4.0 7.0 7.0 8.5 8.0)

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
: > "$TMP/liste.txt"

for i in "${!SURELER[@]}"; do
  n=$(printf "%02d" $((i + 1))); d=${SURELER[$i]}
  f=""
  for ext in mp4 mov webm mkv; do [ -f "klipler/$n.$ext" ] && f="klipler/$n.$ext" && break; done
  if [ -z "$f" ]; then
    echo "UYARI: klipler/$n.* yok, $d sn siyah ekran konuluyor" >&2
    ffmpeg -v error -y -f lavfi -i "color=c=black:s=${W}x${H}:r=$FPS:d=$d" -c:v libx264 -pix_fmt yuv420p "$TMP/$n.mp4"
  else
    # klip kısaysa son kareyi uzatır, uzunsa keser
    ffmpeg -v error -y -i "$f" -an -vf "scale=$W:$H:force_original_aspect_ratio=increase,crop=$W:$H,fps=$FPS,setsar=1,tpad=stop_mode=clone:stop_duration=$d" \
      -t "$d" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$TMP/$n.mp4"
  fi
  echo "file '$TMP/$n.mp4'" >> "$TMP/liste.txt"
done

# kapanış: 5.5 sn siyah ekran + yazı
FONT=$(fc-match -f '%{file}' 'serif:italic' 2>/dev/null || true)
FF=""; [ -n "$FONT" ] && FF="fontfile='$FONT':"
ffmpeg -v error -y -f lavfi -i "color=c=black:s=${W}x${H}:r=$FPS:d=5.5" -vf \
"drawtext=${FF}text='SAMU':fontsize=96:fontcolor=white:x=(w-tw)/2:y=h/2-110:alpha='if(lt(t,0.4),0,if(lt(t,1.3),(t-0.4)/0.9,if(lt(t,4.6),1,max(0,(5.4-t)/0.8))))',\
drawtext=${FF}text='cennetten bi parça':fontsize=72:fontcolor=0xffe8f3:x=(w-tw)/2:y=h/2+10:alpha='if(lt(t,0.4),0,if(lt(t,1.3),(t-0.4)/0.9,if(lt(t,4.6),1,max(0,(5.4-t)/0.8))))'" \
  -c:v libx264 -pix_fmt yuv420p "$TMP/son.mp4"
echo "file '$TMP/son.mp4'" >> "$TMP/liste.txt"

ffmpeg -v error -y -f concat -safe 0 -i "$TMP/liste.txt" -c copy "$TMP/video.mp4"

VF="eq=saturation=0.9"
if [ "$BASLIK" = 1 ]; then
  VF="$VF,drawtext=${FF}text='cennetten bi parça':fontsize=120:fontcolor=white:shadowcolor=0xff9fc0@0.8:shadowx=0:shadowy=0:borderw=2:bordercolor=0x00000060:x=(w-tw)/2:y=h*0.42:alpha='if(lt(t,0.5),0,if(lt(t,1.5),t-0.5,if(lt(t,6.3),1,max(0,(7.3-t)))))'"
fi
if [ "$ALTYAZI" = 1 ]; then
  VF="$VF,subtitles=sozler.srt:force_style='FontName=Arial,Bold=1,FontSize=24,PrimaryColour=&H00E6F1F4,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=40'"
fi

mkdir -p cikti
ffmpeg -v error -y -i "$TMP/video.mp4" -i "$SARKI" -map 0:v -map 1:a -vf "$VF" \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -c:a aac -b:a 256k -af apad -t 150 -movflags +faststart \
  cikti/samu_cennetten_bi_parca_AI.mp4
echo "Hazır: $(pwd)/cikti/samu_cennetten_bi_parca_AI.mp4"
