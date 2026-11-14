# ZarekBot V11 / ASISTENTE CTX

Bot multipropósito de Discord en Python. Esta rama concentra la finalización de
**CTX Music V11**: reproducción por servidor, cola colaborativa, autoplay,
loop, controles jerárquicos, panel persistente y convivencia segura con TTS.

## Estado de CTX Music

- Búsqueda por texto y enlaces de YouTube mediante `yt-dlp`.
- Streams de audio reproducidos con Discord Voice + FFmpeg.
- Cola FIFO compartida por servidor; cualquier miembro real puede solicitar.
- PLAY, PAUSE, RESUME, SKIP, STOP, VOLUME, QUEUE, LOOP y AUTOPLAY.
- Avance automático, refresco de streams y recuperación hacia la siguiente
  canción manual cuando falla una reproducción.
- Historial y pool limitado de recomendaciones, cooldown anti-bot y
  cancelación por generación para resultados atrasados.
- Panel premium único por servidor con Discord Components V2: Container
  carmesí, portada grande mediante Media Gallery, jerarquía compacta y nueve
  controles persistentes que reflejan el estado real.
- Locks independientes por servidor y protección de interacciones duplicadas.
- Propiedad exclusiva del `VoiceClient` durante toda la intervención TTS;
  PLAY, SKIP y STOP se serializan por servidor sin bloquear otros servidores.

La barra de progreso usa un reloj monotónico local. Se congela durante pausa y
TTS, pero es **aproximada**: Discord/FFmpeg no exponen una posición de
reproducción de precisión de muestra.

## Requisitos

- Windows 10/11 o Linux.
- Python 3.11 o superior (recomendado y usado por la imagen Docker).
- FFmpeg disponible en `PATH` (o `FFMPEG_PATH`).
- Deno 2.3+ en `PATH` para el solver EJS de YouTube.
- Una aplicación/bot de Discord con acceso al servidor autorizado.

## Instalación rápida en Windows

```powershell
winget install Gyan.FFmpeg
winget install DenoLand.Deno

py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Verifica las herramientas:

```powershell
ffmpeg -version
deno --version
python -c "import discord, yt_dlp; print(discord.__version__, yt_dlp.version.__version__)"
```

`yt-dlp[default]` instala una versión compatible de `yt-dlp-ejs`. Deno es el
runtime recomendado y está habilitado por defecto por yt-dlp. No se incluyen
cookies y no son obligatorias; `YTDLP_BROWSER` es opcional para un navegador
local autorizado.

## Configuración de Discord

1. Crea o selecciona tu aplicación en Discord Developer Portal.
2. En **Bot**, crea el bot y activa los intents privilegiados **Message
   Content** y **Server Members**.
3. Invítalo únicamente al servidor autorizado con permisos para ver/enviar
   mensajes, usar comandos de aplicación, conectar y hablar en voz.
4. Copia `.env.example` como `.env` y completa `DISCORD_TOKEN` y la jerarquía.
5. Nunca publiques `.env`, tokens, cookies, audio temporal ni URLs de stream.

El sistema musical reutiliza la jerarquía existente en `config/hierarchy.py`.
No autentica por nombre visible.

## Ejecutar

```powershell
python main.py
```

Al iniciar, CTX carga las extensiones musicales y sincroniza los slash commands
en los servidores donde ya está instalado. No crea servidores ni se conecta a
comunidades nuevas por su cuenta.

## Comandos principales

| Slash | Prefijo | Acceso |
|---|---|---|
| `/play` | `!ctx_play` | Miembros reales |
| `/queue` | `!ctx_queue` | Miembros reales |
| `/player` | `!ctx_player` | Miembros reales; controles protegidos |
| `/musichelp` | `!ctx_musichelp` | Miembros reales |
| `/pause`, `/resume` | `!ctx_pause`, `!ctx_resume` | Admin. de música |
| `/skip`, `/stop` | `!ctx_skip`, `!ctx_stop` | Admin. de música |
| `/volume` | `!ctx_volume` | Admin. de música |
| `/loop`, `/autoplay` | `!ctx_loop`, `!ctx_autoplay` | Admin. de música |

ZAREK/CENTI se resuelven mediante los niveles `CREADOR` y
`CREADOR_DEL_SERVIDOR`. Los bots no pueden solicitar ni controlar música.

## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m music.youtube_resolver_test   # integración externa, opcional
```

La suite local usa backends y objetos simulados; no entra a Discord y no
reproduce sonido. Consulta [docs/TESTING.md](docs/TESTING.md) para la matriz de
pruebas y lo que requiere validación humana.

## Documentación

- [Arquitectura y operación de CTX Music](docs/CTX_MUSIC.md)
- [Pruebas y validación manual](docs/TESTING.md)
- [Política de seguridad](SECURITY.md)

## Privacidad y publicación

`.gitignore` excluye `.env`, entornos, binarios, backups, audio temporal, logs y
el registro persistente de paneles. Antes de publicar se debe ejecutar además
un escaneo del árbol Git completo y revisar que ningún commit contenga secretos.

El resto de sistemas del bot (moderación, IA y economía) queda fuera del alcance
de esta etapa.
