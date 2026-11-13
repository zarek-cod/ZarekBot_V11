# Pruebas de CTX Music

## Suite automatizada

Instalación y ejecución:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q main.py music commands config moderation voice ui
```

Las suites `tests/test_music_v11.py` y `tests/test_music_premium.py` validan con
mocks:

- PLAY individual, PLAY concurrente y FIFO de varios solicitantes.
- Duplicados de una misma interacción.
- PAUSE, RESUME, STOP, volumen y reloj.
- Avance natural, LOOP y recuperación tras error de stream/FFmpeg simulado.
- SKIP con refresco y rechazo de eventos atrasados.
- Prioridad de cola manual sobre AUTOPLAY y resultados tardíos invalidados.
- Permisos de miembro, administrador y bot.
- Components V2, portada, títulos, siguiente canción y nueve controles reales.
- Panel único incluso con tres solicitudes `/player` simultáneas.
- Recuperación y conversión del panel persistente tras reinicio.
- Actualización automática por eventos y estados sin reproducción.
- Confirmaciones compactas de PLAY sin embeds repetidos.
- PLAY, SKIP y STOP mientras TTS posee el canal.
- Restauración de música reproducida o pausada y fallo de restauración TTS.
- Aislamiento de varios servidores y reconexión de voz simulada.

Los scripts históricos se ejecutan como módulos, por ejemplo:

```powershell
python -m music.auto_playback_test
python -m music.loop_playback_test
python -m commands.music.all_music_load_test
```

## Integraciones externas opcionales

```powershell
python -m music.youtube_resolver_test
python -m music.real_pipeline_test
```

Estas pruebas dependen de red, disponibilidad de YouTube, Deno/EJS y posibles
verificaciones anti-bot. No deben considerarse deterministas.

## Prueba real autorizada en Discord

En un servidor de pruebas donde el propietario haya autorizado al bot:

1. Inicia `python main.py` y confirma conexión y sincronización de slash
   commands en logs, sin imprimir el token.
2. Dos miembros distintos solicitan A, B y C; confirma A → B → C.
3. Comprueba PAUSE/RESUME y que el reloj visual se congele.
4. Comprueba SKIP, STOP, volumen, LOOP y AUTOPLAY desde comando y panel.
5. Verifica que un miembro normal no pueda usar controles administrativos.
6. Provoca una desconexión de voz controlada y vuelve a usar PLAY.
7. Activa TTS durante música y escucha que no avance accidentalmente la cola.
8. Reinicia el bot y confirma que `/player` recupera el mismo mensaje.
9. Escucha el audio: los tests automáticos no pueden confirmar calidad,
   volumen percibido, cortes o artefactos.

No ejecutar estas pruebas en comunidades ajenas ni crear servidores nuevos.

## GitHub Actions

`.github/workflows/music-tests.yml` ejecuta compilación, `pip check` y toda la
suite en Python 3.11 y 3.12 para cada actualización del PR y de la rama musical.
