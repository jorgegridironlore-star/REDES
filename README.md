# Redes — 4 cuentas de TikTok de curiosidades deportivas (Jorge)

Gridiron Lore (NFL, @nflgridironlore) · Hoops Lore (NBA, @hoopslore0) · Prem Lore (Premier) · Fútbol Oculto (LaLiga)

## Estructura
```
fuentes/                      Anton, Bebas Neue, Graduate
<CUENTA>/<cuenta>_logo.png
<CUENTA>/AAAA-MM-DD/          una carpeta por día
  <cuenta>_NN_tiktok.mp4      versión para subir (<10 MB, 950 kbps en dos pasadas)
  <cuenta>_NN_portada.jpg     portada sin subtítulos
  <cuenta>_NN_voz.mp3         voz de ElevenLabs
  <cuenta>_NN_guion.txt, times.json, scripts de render
```

## Reglas
- Solo se guarda la versión de TikTok (no los másteres).
- Si se cambia un vídeo, se sobrescribe con el mismo nombre en su carpeta del día (nada de v2 ni _final).
- Para un vídeo nuevo se copian los scripts del último vídeo de esa cuenta a la carpeta del día nuevo.
- El estado de cada cuenta y los guiones están en el proyecto "Redes" de Claude (cuentas/*.md, guiones/*.md).
