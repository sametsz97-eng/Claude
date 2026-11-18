# Samu – Cennetten Bi Parça · AI video sahne paketi

Bu paket, klibi bir AI video aracında (Kling, Google Veo, Runway, Hailuo, Sora vb.) üretmek için hazırlandı.
Her sahne şarkının zamanlamasına göre kesildi. Klipleri ürettikten sonra `birlestir.sh` hepsini şarkıyla birleştirir.

## Nasıl kullanılır

1. Her sahne için **STİL BLOĞU + KARAKTERLER + sahne promptu**nu birlikte yapıştır (İngilizce, araçlar en iyi İngilizceyi anlıyor).
2. Ses / müzik / konuşma üretimini kapat. Klipte seslendirme yok.
3. En-boy oranı **16:9**. Her sahneyi tablodaki süreden **en az 1 saniye uzun** üret (betik fazlasını keser).
4. Karakterlerin her sahnede aynı kalması için önce Samu'nun ve kızın birer referans görselini üret. Sonra her sahnede bu görselleri "reference image / character reference" olarak ver.
5. Üretilen dosyaları `ai_klip/klipler/` klasörüne `01.mp4`, `02.mp4` … diye kaydet ve `bash birlestir.sh` çalıştır.

---

## STİL BLOĞU (her sahnenin başına ekle)

```
Authentic in-game cutscene footage from a classic 2004–2007 PlayStation 2 open-world action-adventure game, nostalgic San Andreas-era look. Real-time early-2000s game engine rendering, slightly low-poly character models, low-resolution textures with visible detail, soft ambient lighting, subtle environmental shadows, slightly muted and faded colors, light haze and distance fog. Slightly stiff but natural character animation, believable body movement and facial expressions. Cinematic third-person game camera. Rainy foggy Sunday evening, light drizzle, wet asphalt reflecting orange sodium streetlights. Dreamy cloud-rap mood. NOT photorealistic, NOT Unreal Engine 5, NOT anime, NOT cartoon, NOT polished modern CGI. No on-screen HUD, no subtitles, no text unless specified.
```

## KARAKTERLER (her sahnede tekrar et)

```
SAMU: man in his late 20s, short dark hair, full short dark beard, olive-green jacket over a dark shirt, dark jeans, thoughtful calm expression.
THE GIRL: young woman, petite and slim (164 cm, about 50 kg), long straight hair between black and dark brunette, cream trench coat, dark pants, white sneakers, holding a clear transparent umbrella.
THE CAR: early-2000s grey four-door sedan, a little worn, rain-beaded windows.
```

---

## Sahneler

| # | Süre | Zaman | Şarkı sözü |
|---|------|-------|-----------|
| 01 | 7.6 sn | 0:00.0 – 0:07.6 | (intro) Gelen olmadı, giden oldu hep |
| 02 | 4.9 sn | 0:07.6 – 0:12.5 | Kaldım kendime sebep kalmadı |
| 03 | 3.9 sn | 0:12.5 – 0:16.4 | Kalbime serinlik desen olmadı |
| 04 | 3.5 sn | 0:16.4 – 0:19.9 | Bugün zorladım, ara gazladım |
| 05 | 4.0 sn | 0:19.9 – 0:23.9 | Arabayı çok kötü yerde bıraktım ama |
| 06 | 4.3 sn | 0:23.9 – 0:28.2 | Karşımda bir kadın var |
| 07 | 3.7 sn | 0:28.2 – 0:31.9 | Tarif edemem ama |
| 08 | 3.9 sn | 0:31.9 – 0:35.8 | Cennetten bir parça |
| 09 | 3.5 sn | 0:35.8 – 0:39.3 | Aşık oluyorum ona, ona galiba |
| 10 | 7.3 sn | 0:39.3 – 0:46.6 | Karşımda bir kadın var / Tarif edemem ama |
| 11 | 3.7 sn | 0:46.6 – 0:50.3 | Cennetten bir parça |
| 12 | 6.1 sn | 0:50.3 – 0:56.4 | Aşık oluyorum ona, ona galiba |
| 13 | 5.6 sn | 0:56.4 – 1:02.0 | Ona galiba |
| 14 | 6.8 sn | 1:02.0 – 1:08.8 | Ona galiba |
| 15 | 7.4 sn | 1:08.8 – 1:16.2 | Karşımda bir kadın var / Tarif edemem ama |
| 16 | 7.7 sn | 1:16.2 – 1:23.9 | Cennetten bir parça / Aşık oluyorum ona |
| 17 | 7.0 sn | 1:23.9 – 1:30.9 | Karşımda bir kadın var / Tarif edemem ama |
| 18 | 3.1 sn | 1:30.9 – 1:34.0 | Cennetten bir parça |
| 19 | 4.0 sn | 1:34.0 – 1:38.0 | Aşık oluyorum ona, evet, ona galiba |
| 20 | 6.0 sn | 1:38.0 – 1:44.0 | (müzik) |
| 21 | 6.0 sn | 1:44.0 – 1:50.0 | (müzik) |
| 22 | 4.0 sn | 1:50.0 – 1:54.0 | (müzik, sessizleşme) |
| 23 | 7.0 sn | 1:54.0 – 2:01.0 | (müzik) |
| 24 | 7.0 sn | 2:01.0 – 2:08.0 | (müzik) |
| 25 | 8.5 sn | 2:08.0 – 2:16.5 | (müzik) |
| 26 | 8.0 sn | 2:16.5 – 2:24.5 | Ve arabaya bir şey oldu / Kalbime değil |
| — | 5.5 sn | 2:24.5 – 2:30.0 | Kapanış yazısı (betik otomatik ekler) |

### 01 · Açılış: yazı arabanın arkasında (7.6 sn)
```
Low rear third-person game camera behind the grey sedan on a wet, foggy two-lane city street at dusk, light rain, red taillights glowing in the mist, orange streetlights fading into fog. Large elegant italic white glowing title text "cennetten bi parça" floats in the air at the height of the car's trunk: the lower half of the letters is hidden behind the car's trunk, the upper half is in front of the car. The car slowly pulls away down the road into the fog while the title text stays fixed in place, hovering over the wet asphalt. Static camera, slight handheld drift.
```
> Not: AI araçları yazıyı her zaman doğru çizemiyor. Yazı bozuk çıkarsa promptu yazısız üret. `birlestir.sh` içinde `BASLIK=1` yaparsan betik yazıyı ilk 7 saniyeye kendisi ekler. Bu durumda yazı arabanın önünde durur, arkasına geçme efekti olmaz.

### 02 · Samu sürüyor, profil (4.9 sn)
```
Interior side shot from the passenger seat: SAMU driving at night, one hand on the steering wheel, elbow resting on the door, staring ahead with a pensive, tired expression. Rain streaks on the side window, streetlights sliding past and washing his face with orange light. Dashboard glow.
```

### 03 · Silecekler, ön cam POV (3.9 sn)
```
First-person view through the car windshield from the driver's seat: wipers sweeping slowly, raindrops on the glass, blurry orange streetlights and fog on an empty wet city road ahead, buildings with a few lit windows.
```

### 04 · Gaza basıyor (3.5 sn)
```
Low side tracking shot at wheel level: the grey sedan accelerates hard along the wet street, tires spraying water, rain streaks stretched by speed, slight camera shake. Quick cut-in on SAMU's foot pressing the gas pedal.
```

### 05 · Kötü park (4.0 sn)
```
High wide shot from above a streetlight: the grey sedan brakes and stops crookedly half on the curb next to a no-parking sign, hazard lights blinking orange. The driver door opens and SAMU steps out into the rain, looking ahead.
```

### 06 · Onu görüyor (4.3 sn)
```
Over-the-shoulder shot from behind SAMU standing in the rain: across the empty wet street, under a single warm streetlight in the fog, THE GIRL stands holding a clear umbrella. She is small in frame. Rain falls slower, a soft dreamy glow around the streetlight. Slow push-in.
```

### 07 · Samu yakın çekim (3.7 sn)
```
Close-up of SAMU's face in the rain, wet hair, drops on his beard, warm streetlight from the side. He freezes, his expression softens, and a small surprised smile appears. Shallow game-style depth of field.
```

### 08 · Kız yakın çekim (3.9 sn)
```
Close-up of THE GIRL under the clear umbrella, raindrops sliding down the umbrella, her long dark-brunette hair, warm light on her face. She slowly turns her head toward the camera and smiles softly. Tiny floating light particles, raindrops almost frozen in the air.
```

### 09 · Geniş iki kişilik plan (3.5 sn)
```
Wide side shot across the street: SAMU on one side next to his crookedly parked car with blinking hazards, THE GIRL on the other side under the streetlight with her umbrella, both looking at each other. Fog, light rain, empty street, slow lateral camera move.
```

### 10 · Birbirlerine yürüyorlar (7.3 sn)
```
Low side tracking shot: SAMU and THE GIRL walk slowly toward each other across the wet empty street, reflections under their feet. As they get closer, the buildings and street around them gradually dissolve into soft clouds and pastel fog, dreamy atmosphere. Slightly stiff game-style walk cycle.
```

### 11 · Yüz yüze (3.7 sn)
```
Medium close two-shot, SAMU and THE GIRL face to face under her clear umbrella, raindrops frozen mid-air around them, glowing softly. Slow orbiting camera. They smile at each other.
```

### 12 · Kamera yukarı (6.1 sn)
```
Crane shot rising up from the couple under the umbrella on a road that floats in a sea of soft clouds and fog, streetlights glowing along the road, muted pastel evening sky. Dreamy and calm.
```

### 13 · "Ona galiba" montajı A (5.6 sn)
```
Slow-motion profile close-up of SAMU looking at her and smiling, then a close-up of THE GIRL laughing and tucking her hair behind her ear, rain glittering in the streetlight. Soft light flashes.
```

### 14 · "Ona galiba" montajı B (6.8 sn)
```
Close-up of their hands as SAMU takes the umbrella handle from THE GIRL and their fingers touch, then a low-angle shot of both under the umbrella against the glowing streetlight and falling rain. Ends with a soft white flash.
```

### 15 · Tek şemsiye altında yürüyüş (7.4 sn)
```
Following shot from behind: SAMU and THE GIRL walk side by side under one clear umbrella down the middle of a misty wet road lined with streetlights, she leans her head toward his shoulder. Clouds and fog on both sides of the road.
```

### 16 · Arabada beraber (7.7 sn)
```
Interior shot from the dashboard facing the front seats: SAMU driving and THE GIRL in the passenger seat, she laughs and turns toward him, he glances at her and smiles. Rain on the windshield, streetlights sliding over them.
```

### 17 · Araba dışı, drone (7.0 sn)
```
Slow orbiting high shot of the grey sedan driving along a foggy road that runs through soft clouds at night, headlights cutting through the mist, rows of streetlights. Classic PS2 open-world driving camera.
```

### 18 · Ön camdan ikisi (3.1 sn)
```
Shot from outside the car through the rain-covered windshield: SAMU driving and THE GIRL beside him, both smiling, wipers sweeping.
```

### 19 · Eller (4.0 sn)
```
Close-up inside the car: THE GIRL places her hand on SAMU's hand resting on the gear stick, soft dashboard light, rain sounds implied by drops on the window.
```

### 20 · Yağmurda dans 1 (6.0 sn)
```
Wide orbit shot: SAMU and THE GIRL slow-dancing in the rain in the middle of the empty street next to the parked car with blinking orange hazards, streetlight above, fog all around.
```

### 21 · Yağmurda dans 2 (6.0 sn)
```
Low-angle spinning shot looking up at SAMU twirling THE GIRL under the streetlight, rain drops falling toward the camera and glowing, her coat and hair swinging.
```

### 22 · Alın alına (4.0 sn)
```
Extreme close-up in profile, SAMU and THE GIRL with foreheads touching, eyes closed, rain on their faces, slow camera push-in, fade to black at the end.
```

### 23 · Hızlı sürüş (7.0 sn)
```
Low front-side chase camera: the grey sedan speeds down the misty road, THE GIRL leans out of the passenger window with her arm stretched out into the rain, laughing; SAMU drives smiling. Water spray, light streaks.
```

### 24 · Kaputta oturuyorlar (7.0 sn)
```
SAMU and THE GIRL sitting on the hood of the parked sedan, leaning back on the windshield, looking at the foggy city lights below, she points at something, he laughs. Slow crane up.
```

### 25 · Araba bozuluyor (8.5 sn)
```
The grey sedan is stopped at the roadside with the hood open and white steam pouring out into the rain, hazard lights blinking. SAMU looks at the engine, scratches his head, then turns to THE GIRL and they both burst out laughing. Medium shot.
```

### 26 · Final: "Ve arabaya bir şey oldu / Kalbime değil" (8.0 sn)
```
Wide shot behind them: SAMU and THE GIRL walk away together under one clear umbrella down the foggy wet street, leaving the steaming broken-down car behind with its hazards still blinking. The camera slowly cranes up into the rain and fog as the scene fades out.
```
