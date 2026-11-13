# CTX Music V11

## Arquitectura

Cada `guild_id` obtiene una sesión, cola, estado, backend, reloj y lock propios.
No existen colas por usuario.

```text
Comando / botón
      ↓
Controlador + lock del servidor
      ↓
Resolver / cola / backend Discord+FFmpeg
      ↓
PlaybackEvent (FINISHED, STOPPED, ERROR)
      ↓
AutoAdvance → AutoPlayback → StateEvent → reloj/panel
```

Los callbacks de Discord Voice pueden llegar desde un hilo de audio. El bus de
playback los devuelve al event loop principal antes de mutar sesiones. Cada
evento conserva el objeto `Track` exacto para rechazar callbacks atrasados.

## Orden de reproducción

1. LOOP repite la canción terminada sin consumir la cola.
2. Sin LOOP, la siguiente solicitud manual sale en FIFO.
3. Solo con cola vacía y AUTOPLAY activo se busca una recomendación.
4. Sin cola ni AUTOPLAY, la sesión queda en espera.

Una búsqueda manual invalida inmediatamente recomendaciones pendientes. Antes
de aplicar un resultado de YouTube se revalida, bajo el lock del servidor, que
autoplay siga activo y que no haya aparecido música manual.

## Panel principal

`/player` crea como máximo un mensaje principal por servidor. Las referencias
se guardan en `data/music_panels.json` (archivo local ignorado por Git). En el
siguiente arranque se valida que canal y mensaje sigan existiendo y se vuelve a
registrar la View persistente.

Los cambios se agrupan con debounce. Mientras una canción avanza, el panel se
edita cada 15 segundos; no se edita cada segundo para evitar rate limits.

## Permisos

- Miembro humano: PLAY, QUEUE, PLAYER y MUSICHELP.
- Nivel `CREADOR` o `CREADOR_DEL_SERVIDOR`: todos los controles.
- Bot: sin acceso a solicitudes ni controles.

Las mismas funciones de `music.permissions` se usan en comandos de prefijo,
slash commands y Views.

## Reloj

El reloj empieza únicamente después de que el backend acepta PLAY. PAUSE lo
congela, RESUME continúa, y FINISHED/ERROR/SKIP/STOP reinician o limpian el
estado según corresponda. Duraciones desconocidas muestran `--:--`.

## Music + CTX Voice

Discord solo admite una fuente por `VoiceClient`. Antes de TTS:

1. Edge TTS genera el archivo; si falla, la música nunca se toca.
2. El backend marca la generación como interrupción externa.
3. Se libera la fuente musical sin emitir FINISHED/STOPPED.
4. TTS usa el canal.
5. En `finally`, se refresca el stream y se reinicia aproximadamente en la
   posición congelada. Si la canción ya estaba pausada, vuelve a quedar pausada.

Las órdenes diagnósticas de tono no pueden ejecutarse mientras CTX Music tiene
una canción activa.

## YouTube y errores externos

- Las llamadas bloqueantes de yt-dlp se ejecutan con `asyncio.to_thread`.
- Los streams de YouTube se refrescan antes de sonar desde cola.
- Un bloqueo anti-bot activa cooldown de cinco minutos.
- No se resuelven CAPTCHA ni se eluden verificaciones.
- Las cookies de navegador son opcionales y nunca se exportan al repositorio.
- Un error de reproducción avanza a la siguiente canción manual; no repite en
  loop para evitar fallos infinitos.
