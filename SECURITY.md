# Seguridad

## Reporte privado

No publiques tokens, claves, cookies o URLs firmadas en un issue. Revoca primero
la credencial comprometida y contacta al propietario del repositorio por un
canal privado.

## Secretos y datos locales

El repositorio no debe incluir:

- `.env`, tokens Discord ni claves Gemini.
- Cookies, perfiles de navegador o archivos `cookies.txt`.
- Binarios FFmpeg locales, entornos virtuales o cachés.
- WAV/PCM/MP3 temporales, logs o URLs internas de streams.
- `data/music_panels.json`, porque contiene IDs operativos del servidor.

Usa `.env.example` únicamente como plantilla sin valores. Si un secreto llegó a
un commit, ignorarlo después no basta: hay que rotarlo y limpiar el historial
antes de hacer público el repositorio.

## YouTube

CTX utiliza capacidades documentadas de yt-dlp. No intenta resolver CAPTCHA,
evitar controles de acceso ni automatizar verificaciones anti-bot. Las cookies
de navegador son opcionales y solo deben usarse con una sesión propia y
autorizada.
