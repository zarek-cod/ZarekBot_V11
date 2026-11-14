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

`/player` crea como máximo un mensaje principal por servidor. Un lock cubre la
búsqueda, creación y persistencia para que varias interacciones simultáneas no
dupliquen el mensaje. Las referencias se guardan en `data/music_panels.json`
(archivo local ignorado por Git). En el siguiente arranque se valida que canal
y mensaje sigan existiendo y se vuelve a registrar la View persistente.

El mensaje principal utiliza Discord Components V2 mediante `LayoutView`:

- `Container` con acento carmesí y fondo nativo del cliente.
- `MediaGallery` para que la portada original sea el elemento dominante.
- `TextDisplay` y `Separator` para jerarquía compacta en móvil y escritorio.
- Tres `ActionRow` con nueve botones reales y estados dinámicos.

Components V2 no permite mezclar el mensaje con embeds o contenido tradicional.
Al recuperar un panel antiguo, CTX lo convierte una sola vez eliminando su embed
y conservando el mismo mensaje. El negro depende del tema oscuro del cliente;
Discord no permite fijar un color de fondo arbitrario.

Los cambios se agrupan con debounce y se coalescen por servidor. Todas las
actualizaciones automáticas y de botones comparten un intervalo mínimo entre
ediciones. Mientras una canción avanza, el panel solicita una actualización cada
15 segundos; no se edita cada segundo para evitar rate limits. Los intervalos
pueden ajustarse con `CTX_MUSIC_PANEL_DEBOUNCE_SECONDS`,
`CTX_MUSIC_PANEL_MIN_EDIT_INTERVAL_SECONDS` y
`CTX_MUSIC_PANEL_REFRESH_SECONDS`, dentro de límites seguros.

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
2. La sesión TTS obtiene el mismo lock de operaciones musicales del servidor.
3. El backend marca la generación como interrupción externa.
4. Se libera la fuente musical sin emitir FINISHED/STOPPED.
5. TTS conserva la propiedad exclusiva del `VoiceClient` hasta terminar.
6. Antes de liberar el lock se refresca el stream y se reinicia aproximadamente en la
   posición congelada. Si la canción ya estaba pausada, vuelve a quedar pausada.

PLAY, SKIP y STOP solicitados durante TTS esperan el fin de esa sesión y luego
se ejecutan en orden. Los locks son por servidor, por lo que dos servidores no
se bloquean entre sí. Si la restauración falla, se elimina la pista actual
inconsistente y el panel informa el error.

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
