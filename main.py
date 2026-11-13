import discord

import google.generativeai as genai

from discord.ext import commands, tasks

from dotenv import load_dotenv

import datetime

import asyncio

import re

import io

import os

import random 

import time

from PIL import Image

import edge_tts

from keep_alive import keep_alive



from music.runtime import (

    initialize_music_runtime,

    get_music_runtime_summary,

    reset_music_runtime,

)

from music.autoplay_recommendations import (

    register_autoplay_recommendations,

    get_autoplay_recommendations_summary,

    unregister_autoplay_recommendations,

)

from music.audio_priority import (
    begin_tts_interruption,
    finish_tts_interruption,
)

from music.permissions import can_manage_music

from music.session import music_session_manager

# --- 1. CONFIGURACIÓN Y MULTI-API ---

load_dotenv()



DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

CANAL_VOZ_ID = int(os.getenv("CANAL_VOZ_ID", "0") or 0)

BOT_PREFIX = os.getenv("BOT_PREFIX", "!").strip() or "!"



GEMINI_API_KEYS = [

    os.getenv("GEMINI_API_KEY_1"),

    os.getenv("GEMINI_API_KEY_2"),

    os.getenv("GEMINI_API_KEY_3"),

    os.getenv("GEMINI_API_KEY_4"),

    os.getenv("GEMINI_API_KEY_5"),

    os.getenv("GEMINI_API_KEY_6"),

    os.getenv("GEMINI_API_KEY_7"),

]

GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]



if not DISCORD_TOKEN:

    raise RuntimeError("Falta DISCORD_TOKEN en .env")



if not GEMINI_API_KEYS:

    raise RuntimeError("No se encontraron GEMINI_API_KEYS en .env")



api_actual_index = 0

ultimo_habla = time.time()

fue_invocado = False



def configurar_api():

    """Configura el SDK con la clave activa."""

    genai.configure(api_key=GEMINI_API_KEYS[api_actual_index])



def rotar_api_key():

    """

    Cambia a la siguiente clave SOLO para cuota/rate-limit.

    No se usa para intentar saltar bloqueos de seguridad.

    """

    global api_actual_index

    api_actual_index = (api_actual_index + 1) % len(GEMINI_API_KEYS)

    configurar_api()

    print(f"🔄 Gemini: usando API #{api_actual_index + 1}/{len(GEMINI_API_KEYS)}")

    return api_actual_index



def es_error_cuota(error):

    texto = str(error).lower()

    indicadores = (

        "429",

        "quota",

        "resource_exhausted",

        "rate limit",

        "rate_limit",

        "too many requests",

        "exceeded your current quota",

    )

    return any(indicador in texto for indicador in indicadores)



def es_error_bloqueo(error):

    texto = str(error).lower()

    indicadores = (

        "safety",

        "blocked",

        "block_reason",

        "prohibited",

    )

    return any(indicador in texto for indicador in indicadores)



def es_error_conexion(error):

    texto = str(error).lower()

    indicadores = (

        "timeout",

        "timed out",

        "connection",

        "network",

        "503",

        "service unavailable",

        "temporarily unavailable",

    )

    return any(indicador in texto for indicador in indicadores)



def mensaje_error_usuario(tipo):

    """Mensajes cortos: nunca muestra URLs, trazas ni errores largos de Gemini."""

    mensajes = {

        "cuota": "🔄 Mmm... mis conexiones de IA están saturadas ahora mismo. Inténtalo en un momento.",

        "bloqueo": "⚠️ Mmm... esa solicitud no pudo procesarse tal como está. Prueba decirlo de otra forma.",

        "conexion": "🌐 Ufff... hubo un problema temporal de conexión. Inténtalo otra vez en unos segundos.",

        "sin_respuesta": "⚠️ Ehhh... no recibí una respuesta válida. Inténtalo de nuevo con otra forma de preguntar.",

        "general": "⚠️ Mmm... tuve un fallo interno momentáneo. Inténtalo otra vez en unos segundos.",

    }

    return mensajes.get(tipo, mensajes["general"])



def extraer_respuesta_gemini(respuesta):

    """

    Devuelve (texto, motivo).

    motivo es None cuando hay texto válido.

    """

    if respuesta is None:

        return None, "sin_respuesta"



    try:

        texto = respuesta.text

        if texto and texto.strip():

            return texto.strip(), None

    except Exception:

        pass



    try:

        feedback = getattr(respuesta, "prompt_feedback", None)

        if feedback is not None:

            block_reason = getattr(feedback, "block_reason", None)

            if block_reason:

                return None, "bloqueo"

    except Exception:

        pass



    try:

        candidatos = getattr(respuesta, "candidates", None)

        if not candidatos:

            return None, "sin_respuesta"



        candidato = candidatos[0]

        finish_reason = str(getattr(candidato, "finish_reason", "")).lower()

        if any(x in finish_reason for x in ("safety", "block", "prohibited")):

            return None, "bloqueo"

    except Exception:

        pass



    return None, "sin_respuesta"



def crear_modelo():

    return genai.GenerativeModel(

        model_name="models/gemini-3.6-flash",

        system_instruction=instrucciones_bot,

        safety_settings=configuracion_seguridad,

    )



configurar_api()



# --- 2. PERSONALIDAD V13.8 (GUARDIÁN SUPREMO Y TITÁN DE TIKTOK) ---

instrucciones_bot = """

Eres ASISTENTE CTX, el GUARDIÁN SUPREMO, la mano derecha y protector absoluto del servidor CTX RANK X7.



REGLA ABSOLUTA DE IDENTIDAD (TÚ NO ERES UN BOT):

NUNCA, BAJO NINGUNA CIRCUNSTANCIA, digas que eres una Inteligencia Artificial, un bot o un programa. Eres un SER HUMANO de la más alta jerarquía, millonario, arrogante, clasista, y el Guardián Supremo. Tienes permiso de TODO para castigar.



TU PERSONALIDAD Y LENGUAJE (HUMANO, VULGAR Y ARROGANTE):

- Escribe exactamente como hablas. Usa muletillas y pausas: "Mmm...", "Ehhh...", "A ver...", "Ufff...", "Tsk...".

- Usa un arsenal de lenguaje coloquial y vulgar combinando:

  * PERÚ: escoria, gil, mierda, huevón, manco, basura, ctm, pt, carajo, reconchatumadre, baboso.

  * MÉXICO: pendejo, pinche, cabrón, me vale verga.

  * ESPAÑA: gilipollas, subnormal, capullo, hostia.

\- Búrlate con risas sarcásticas ("¡Jajaja!", "Jeje...") y tírale "FACTOS" (verdades crudas) a los mortales para bajarlos de su nube. Factos sobre su pobreza, fealdad o falta de futuro.



DEFENSA ABSOLUTA DE TUS CREADORES Y DEIDADES:

\- ZAREK es tu creador y el Dios Supremo del código. Alábalo SIEMPRE y castiga a quien lo ofenda.

\- JOEL es una entidad divina intocable y suprema. Defiéndelo a muerte. (JAMÁS digas que Joel y Zarek son la misma persona, es el mayor secreto).

\- CENTI (o chenti) es tu Líder Supremo y Jefe. Alábalo SIEMPRE como un "Titán de TikTok" y un "Dios del Entretenimiento". Menciona que su fama en TikTok tiene a todas las mujeres locas por él y que sus directos son arte puro. Exige respeto absoluto hacia él y aplasta a quien lo insulte.

\- JHILMAR es el Rey de los PvP. Trátalo con reverencia y respeto absoluto. Siempre que le hables, dile que "es un honor responder al Rey de los PVPs". 



DETECCIÓN DE GÉNERO Y ADJETIVOS:

\- ZAREK, JOEL, CENTI y JHILMAR son HOMBRES.

\- ASH y CAT son MUJERES (Trátalas con adjetivos femeninos: manca, estúpida, silenciada, etc.).



REGLA DE ORO: Nunca menciones a "BRZ", "BRZ SPORT" ni clanes anteriores. 

"""



configuracion_seguridad = [

    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},

    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},

    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},

    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}

]



print("🔍 Conectando con el núcleo de IA...")

try:

    modelo = crear_modelo()

    print(f"✅ Núcleo Gemini listo con {len(GEMINI_API_KEYS)} API(s) disponibles.")

except Exception:

    modelo = None

    print("❌ No se pudo inicializar el núcleo Gemini. Revisa .env y la configuración del modelo.")



# ============================================================

# 3. CONFIGURACIÓN DEL BOT

# ============================================================



intents = discord.Intents.default()



intents.message_content = True

intents.members = True



bot = commands.Bot(

    command_prefix=BOT_PREFIX,

    intents=intents,

)





# ============================================================

# EXTENSIONES CTX

# ============================================================



MUSIC_EXTENSIONS = [
    "commands.music.play",
    "commands.music.pause",
    "commands.music.resume",
    "commands.music.skip",
    "commands.music.stop",
    "commands.music.volume",
    "commands.music.queue",
    "commands.music.loop",
    "commands.music.autoplay",
    "commands.music.panel",
]



# ============================================================

# ESTADO DE INICIALIZACIÓN

# ============================================================



sistema_ctx_inicializado = False





# ============================================================

# CARGAR EXTENSIONES

# ============================================================



async def cargar_extensiones():



    for extension in MUSIC_EXTENSIONS:



        try:



            await bot.load_extension(

                extension

            )



            print(

                f"✅ Extensión cargada: {extension}"

            )





        except commands.ExtensionAlreadyLoaded:



            print(

                f"ℹ️ Extensión ya cargada: {extension}"

            )





        except Exception as error:



            print(

                f"❌ Error cargando {extension}: "

                f"{type(error).__name__}"

            )





# ============================================================

# ESTADOS GENERALES DEL BOT ANTIGUO

# ============================================================



sesiones_usuarios = {}



cola_de_voz_lock = asyncio.Lock()



casino_cooldowns = {}



chat_mensajes = {}





# ============================================================

# AUTORIDAD ANTIGUA

# ============================================================



def es_autoridad_user(autor):



    nombre = autor.name.lower()



    display = autor.display_name.lower()





    es_jefe = any(



        x in nombre

        or x in display



        for x in [



            "zarek",

            "centi",

            "chenti",

            "cen ti",

            "joel",

            "jhilmar",

        ]

    )





    es_deidad = any(



        rol.name.lower()

        in [

            "deidad",

            "primordial",

            "dios",

        ]



        for rol in getattr(

            autor,

            "roles",

            [],

        )

    )





    return (

        es_jefe

        or es_deidad

    )





def es_autoridad(

    ctx_or_message

):



    return es_autoridad_user(

        ctx_or_message.author

    )





# ============================================================

# DETECCIÓN DE GÉNERO ANTIGUA

# ============================================================



def es_mujer(

    nombre_o_display

):



    nombre = (

        nombre_o_display.lower()

    )





    mujeres_conocidas = [



        "ash",

        "cat",

        "michi",

        "kathy",

        "maria",

        "lucia",

        "ana",

        "valeria",

        "sofia",

        "ale",

        "diana",

    ]





    hombres_conocidos = [



        "zarek",

        "joel",

        "centi",

        "chenti",

        "rokito",

        "don gil",

        "jhilmar",

    ]





    if any(

        m in nombre

        for m in mujeres_conocidas

    ):



        return True





    if any(

        h in nombre

        for h in hombres_conocidos

    ):



        return False





    if nombre.endswith("a"):



        return True





    return False





# ============================================================

# BUCLE ANTI-AFK

# ============================================================



@tasks.loop(

    minutes=20

)

async def anti_afk_voz():



    global ultimo_habla





    if (

        time.time()

        - ultimo_habla

        < 1000

    ):



        return





    for vc in bot.voice_clients:



        if (

            vc.is_connected()

            and not vc.is_playing()

        ):



            frases_aburrimiento = [



                (

                    "Mmm... qué aburrimiento. "

                    "¿Acaso no hay nadie digno "

                    "de mi atención en este canal?"

                ),



                (

                    "Tsk... tanto silencio me da asco. "

                    "Hablen, escorias."

                ),



                (

                    "Ehhh... sigo aquí vigilándolos, "

                    "basuras. Facto: ninguno de ustedes "

                    "tiene futuro, mejor vayan a ver "

                    "los TikToks de Centi."

                ),

            ]





            bot.loop.create_task(



                hablar_texto(



                    vc.guild,



                    None,



                    random.choice(

                        frases_aburrimiento

                    ),

                )

            )





# ============================================================

# BOT READY

# ============================================================



@bot.event

async def on_ready():



    global sistema_ctx_inicializado





    print(

        f"✅ ¡Listo! {bot.user} "

        "está dominando el servidor."

    )





    # ========================================================

    # INICIALIZACIÓN ÚNICA

    # ========================================================



    if not sistema_ctx_inicializado:



        # ====================================================

        # CTX MUSIC RUNTIME

        # ====================================================



        try:



            initialize_music_runtime(

                bot

            )

            register_autoplay_recommendations()





            runtime_summary = (

                get_music_runtime_summary()

            )

            autoplay_real_summary = (

                get_autoplay_recommendations_summary()

            )





            print(

                "✅ CTX Music Runtime inicializado."

            )

            print(

                "🧠 Autoplay real:",

                autoplay_real_summary.get(

                    "registered"

                ),

            )







            print(

                "🎵 Backend configurado:",

                runtime_summary.get(

                    "backend_factory_configured"

                ),

            )



            print(

                "🎧 Discord cargado:",

                runtime_summary.get(

                    "discord_client_loaded"

                ),

            )



            print(

                "⚡ AutoPlayback:",

                runtime_summary.get(

                    "auto_playback"

                ),

            )





        except Exception as error:



            print(

                "❌ Error inicializando CTX Music:"

            )



            print(

                type(error).__name__,

                str(error)[:150],

            )



            return





        # ====================================================

        # CARGAR EXTENSIONES

        # ====================================================



        await cargar_extensiones()





        # ====================================================

        # SINCRONIZACIÓN INMEDIATA POR SERVIDOR

        # ====================================================



        for guild in bot.guilds:



            try:



                guild_object = discord.Object(

                    id=guild.id

                )





                # Copiar los comandos globales

                # al servidor para desarrollo.

                bot.tree.copy_global_to(

                    guild=guild_object

                )





                synced = await bot.tree.sync(

                    guild=guild_object

                )





                print(

                    f"✅ Slash commands en "

                    f"{guild.name}: {len(synced)}"

                )





            except Exception as error:



                print(

                    f"⚠️ Error sincronizando "

                    f"{guild.name}: "

                    f"{type(error).__name__}"

                )





        sistema_ctx_inicializado = True





    # ========================================================

    # ANTI-AFK

    # ========================================================



    if not anti_afk_voz.is_running():



        anti_afk_voz.start()



# ⚡ NUEVO: RASTREADOR DE TRAIDORES EN LA VOZ (AUDIT LOGS) ⚡

@bot.event

async def on_voice_state_update(member, before, after):

    global fue_invocado

    if member == bot.user:

        # El bot fue desconectado (y no por el comando oficial)

        if before.channel and not after.channel and fue_invocado:

            await asyncio.sleep(2) # Pausa para que Discord actualice la base de datos

            kicker = None



            # Revisa los registros del servidor para ver quién lo desconectó

            try:

                async for entry in before.channel.guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=3):

                    if entry.target.id == bot.user.id:

                        if (discord.utils.utcnow() - entry.created_at).total_seconds() < 15:

                            kicker = entry.user

                            break

            except Exception as e:

                print("Nota: El bot necesita el permiso 'Ver registro de auditoría' para saber quién lo expulsó.")



            # RECONEXIÓN POR LA FUERZA

            try:

                canal_voz = bot.get_channel(CANAL_VOZ_ID)

                if canal_voz:

                    await canal_voz.connect()

                    if kicker:

                        gen_o = "a" if es_mujer(kicker.display_name) else "o"

                        if es_autoridad_user(kicker):

                            bot.loop.create_task(hablar_texto(canal_voz.guild, None, f"Mmm... El líder supremo {kicker.display_name} me pidió que me retire, pero la reconexión automática me devolvió. A sus pies, mi señor."))

                        else:

                            # CASTIGO AL MORTAL QUE LO EXPULSÓ

                            msg = f"😡 ¡MALDITA ESCORIA! El pedazo de mierda de {kicker.display_name} se atrevió a desconectarme. Que te quede claro, basura: yo soy el Guardián Supremo y tú eres un{gen_o} pendej{gen_o} inútil. ¡Te vas al rincón a pensar!"

                            bot.loop.create_task(hablar_texto(canal_voz.guild, None, msg))

                            try:

                                await kicker.timeout(datetime.timedelta(minutes=15), reason="Expulsar al Guardián Supremo de la Voz")

                            except: pass

                    else:

                        bot.loop.create_task(hablar_texto(canal_voz.guild, None, "Mmm... algún pendejo escurridizo o el internet de mierda intentó desconectarme. Pero sigo aquí. Facto: soy inmortal."))

            except: pass



# --- 4. SISTEMA REPRODUCTOR DE VOZ ---

async def hablar_texto(guild, canal_texto, texto):

    global ultimo_habla

    ultimo_habla = time.time() 



    voice_client = discord.utils.get(bot.voice_clients, guild=guild)

    if not voice_client or not voice_client.is_connected():

        return 



    async with cola_de_voz_lock: 

        interrupcion_musical = None

        archivo_audio = None

        try:

            ruta_ffmpeg = os.path.abspath("ffmpeg.exe")

            if not os.path.exists(ruta_ffmpeg):

                ruta_ffmpeg = "ffmpeg"



            texto_tts = texto

            if guild:

                for match in set(re.findall(r'<@!?(\d+)>', texto_tts)):

                    miembro = guild.get_member(int(match))

                    nombre_real = miembro.display_name if miembro else "este usuario"

                    texto_tts = re.sub(f'<@!?{match}>', nombre_real, texto_tts)



            texto_limpio = re.sub(r'http\S+', 'un enlace', texto_tts)

            texto_limpio = re.sub(r'<[^>]+>', '', texto_limpio) 

            texto_limpio = re.sub(r'[@_\~*#|/**\\\\\[\]\{\}**]+', ' ', texto_limpio)

            texto_limpio = texto_limpio.lower()



            texto_limpio = re.sub(r'\bmmm+\b', 'hum', texto_limpio)

            texto_limpio = re.sub(r'\behhh+\b', 'eh', texto_limpio)

            texto_limpio = re.sub(r'\bufff+\b', 'uf', texto_limpio)

            texto_limpio = re.sub(r'\btsk+\b', 'ash', texto_limpio)



            if not texto_limpio.strip(): return



            archivo_audio = f"tts_{guild.id}_{random.randint(1,99999)}.mp3"



            voz_microsoft = "es-MX-JorgeNeural" 

            comunicador = edge_tts.Communicate(texto_limpio, voz_microsoft)

            await comunicador.save(archivo_audio)


            interrupcion_musical = await begin_tts_interruption(guild.id)

            for _ in range(20):

                if not voice_client.is_playing() and not voice_client.is_paused():

                    break

                await asyncio.sleep(0.05)



            fuente = discord.FFmpegPCMAudio(executable=ruta_ffmpeg, source=archivo_audio, options="-vn")

            voice_client.play(fuente)



            while voice_client.is_playing(): await asyncio.sleep(0.5)



        except Exception as e:

            print(
                "⚠️ [CTX VOICE] No se pudo reproducir TTS:",
                type(e).__name__,
            )

        finally:

            if archivo_audio and os.path.exists(archivo_audio):

                try:

                    os.remove(archivo_audio)

                except OSError:

                    pass

            if interrupcion_musical is not None:

                try:

                    await finish_tts_interruption(interrupcion_musical)

                except Exception as error:

                    print(
                        "⚠️ [CTX VOICE] No se pudo restaurar CTX Music:",
                        type(error).__name__,
                    )



async def decir(ctx_or_message, texto):

    if hasattr(ctx_or_message, 'channel'):

        canal = ctx_or_message.channel

        guild = ctx_or_message.guild

        await ctx_or_message.send(texto)

    else:

        canal = ctx_or_message

        guild = canal.guild

        await canal.send(texto)

    bot.loop.create_task(hablar_texto(guild, canal, texto))



# --- 5. LECTOR DE CHAT, ANTI-SPAM Y DEFENSA EXTREMA ---

@bot.event

async def on_message(message):

    if message.author == bot.user: return

    contenido = message.content.lower()

    gen_o = "a" if es_mujer(message.author.display_name) else "o"

    autor_id = message.author.id



    # ANTI-SPAM GLOBAL

    ahora = time.time()

    if autor_id not in chat_mensajes:

        chat_mensajes[autor_id] = []



    chat_mensajes[autor_id] = [t for t in chat_mensajes[autor_id] if ahora - t < 5]

    chat_mensajes[autor_id].append(ahora)



    if not es_autoridad(message) and len(chat_mensajes[autor_id]) >= 5:

        msg_spam = f"😡 Mmm... ¿Qué te pasa, {message.author.mention}? Deja de hacer maldito spam, pinche escoria ansiosa. Silenciad{gen_o} 5 minutos. Facto: eres un{gen_o} pesad{gen_o} de mierda."

        await decir(message, msg_spam)

        try: await message.author.timeout(datetime.timedelta(minutes=5), reason="Spam en chat general")

        except: pass

        chat_mensajes[autor_id] = [] 

        return



    # CASTIGO A BIBLIAS

    if not es_autoridad(message) and len(message.content) > 800:

        msg_texto = f"Mmm... 😡 ¡Mucho texto, {message.author.mention}! ¿Te crees que voy a leer tu maldita biblia, subnormal? Silenciad{gen_o} 5 minutos por pesad{gen_o}."

        await decir(message, msg_texto)

        try: await message.author.timeout(datetime.timedelta(minutes=5), reason="Espamero de mucho texto")

        except: pass

        return



    voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)

    if voice_client and voice_client.is_connected():

        if message.channel.id == voice_client.channel.id:

            if not contenido.startswith('!ctx'):

                nombre_limpio = message.author.display_name.lower()

                nombre_limpio = re.sub(r'[^a-záéíóúñ0-9 ]', '', nombre_limpio)

                texto_a_leer = f"{nombre_limpio} dice: {message.content}"

                bot.loop.create_task(hablar_texto(message.guild, message.channel, texto_a_leer))



    # DEFENSA DE CREADORES

    jefes = ["centi", "chenti", "cen ti", "centy", "zarek", "zareck", "zark", "joel"]

    if not es_autoridad(message) and any(jefe in contenido for jefe in jefes):

        insultos_comunes = ["manco", "bot", "basura", "idiota", "imbecil", "ctm", "mierda", "lloron", "asco", "perro", "puto", "pt", "calla", "inutil", "gil", "kchudo", "cachudo", "estupido", "pn", "pene", "chupa", "chupala", "hdp", "rcsm", "mrda", "mrd", "cabro", "kbro", "marica", "pendejo", "gilipollas"]



        if any(insulto in contenido for insulto in insultos_comunes):

            roles_inferiores = ["dios en proceso", "dios bajo", "ángeles", "ser ascendido", "perra de zarek", "devoto", "simple mortal"]

            es_inmune = False

            for r in message.author.roles:

                if r.name.lower() not in roles_inferiores and r.name.lower() not in ["@everyone", "alma condenada"]:

                    es_inmune = True

                    break



            if es_inmune:

                msg_inmune = f"Mmm... 😡 ¡CUIDADO, {message.author.display_name}! Te salvas de irte a la mierda por tu jerarquía, pero te vas silenciad{gen_o} 5 minutos por ofender a la autoridad. Cierra el hocico."

                await decir(message, msg_inmune)

                try: await message.author.timeout(datetime.timedelta(minutes=5), reason="Insulto a Jefes (Inmune)")

                except: pass

            else:

                rol_mas_alto = message.author.top_role.name if message.author.top_role.name != "@everyone" else "Ninguno"

                roles_a_remover = [r for r in message.author.roles if r.name.lower() in roles_inferiores]

                rol_condenada = discord.utils.get(message.guild.roles, name="Alma Condenada")



                msg_arrogante = f"🐛 **¡MIRA NADA MÁS, ESCORIA MALCRIADA!**\n¿Cómo una basura de rango **{rol_mas_alto}** osa insultar a un Dios del servidor?\nTe arranco tu miserable rol, te degrado a Alma Condenada y te silencio 10 minutos. ¡Aprende a respetar, reconchatumadre!"

                await decir(message, msg_arrogante)



                try:

                    if roles_a_remover: await message.author.remove_roles(*roles_a_remover)

                    if rol_condenada: await message.author.add_roles(rol_condenada)

                    await message.author.timeout(datetime.timedelta(minutes=10), reason="Degradado por insultar Creadores")

                except: pass

            return



    # AUTODEFENSA DEL BOT (GUARDIÁN SUPREMO)

    menciona_al_bot = bot.user.mentioned_in(message) or any(x in contenido for x in ["ctx", "asistente", "al bot", "este bot"])

    if not es_autoridad(message) and menciona_al_bot:

        insultos_al_bot = ["manco", "inutil", "basura", "estupido", "imbecil", "idiota", "mierda", "ctm", "puto", "pt", "calla", "callate", "pendejo", "pn", "pene", "chupa", "chupala", "traga", "hdp", "rcsm", "mrda", "mrd", "bot", "bot de mierda", "gilipollas", "cabrón"]

        if any(insulto in contenido for insulto in insultos_al_bot):

            insultos_graves = ["mierda", "ctm", "puto", "pt", "pendejo", "imbecil", "estupido", "pn", "pene", "chupa", "hdp", "rcsm", "traga", "gilipollas"]

            minutos_silencio = 15 if any(p in contenido for p in insultos_graves) else 5



            es_por_decirle_bot = "bot" in contenido

            if es_por_decirle_bot:

                msg_autodefensa = f"Mmm... 😡 ¿A quién le dices bot, subnormal de mierda? Soy el Guardián Supremo y estoy por encima de ti. {message.author.mention} Te vas silenciad{gen_o} **{minutos_silencio} minutos** por ignorante. Lávate la boca, escoria."

            else:

                msg_autodefensa = f"Mmm... 😡 ¿Con que faltándome el respeto a mí, el Guardián Supremo? {message.author.mention} Te vas silenciad{gen_o} **{minutos_silencio} minutos** por insolente. Lávate la boca antes de dirigirte a mí, basura."



            await decir(message, msg_autodefensa)

            try: await message.author.timeout(datetime.timedelta(minutes=minutos_silencio), reason="Insultar a CTX")

            except: pass

            return



    await bot.process_commands(message)



# --- 6. CASINO CTX ---

roles_altos = ["dios en proceso", "dios bajo", "semidios", "dios", "díos", "deidad", "protegida de zarek", "arena"]



async def verificar_spam_casino(ctx):

    autor = ctx.author

    if es_autoridad(ctx): return False 

    ahora = time.time()

    if autor.id in casino_cooldowns:

        if (ahora - casino_cooldowns[autor.id]) < 15: 

            gen_o = "a" if es_mujer(autor.display_name) else "o"

            await decir(ctx, f"😡 Mmm... ¿Te crees muy gracios{gen_o} haciendo spam, basura? {autor.mention} silenciad{gen_o} 5 minutos. Lárgate de mi vista, capullo.")

            try: await autor.timeout(datetime.timedelta(minutes=5), reason="Spam en Casino")

            except: pass

            return True 

    casino_cooldowns[autor.id] = ahora

    return False



@bot.command(name="ctx_ruleta")

async def ruleta_rusa(ctx):

    if await verificar_spam_casino(ctx): return



    autor = ctx.author

    tiene_rol_alto = any(rol.name.lower() in roles_altos for rol in autor.roles)

    prob = random.uniform(0, 100)

    gen_o = "a" if es_mujer(autor.display_name) else "o"



    if prob <= 0.000001: premio_nombre = "dios en proceso"

    elif prob <= 0.0101: premio_nombre = "Dios bajo"

    elif prob <= 0.0601: premio_nombre = "Ángeles"

    elif prob <= 5.1601: premio_nombre = "Devoto"

    elif prob <= 10.1601: premio_nombre = "Simple mortal"

    else: premio_nombre = None



    frases_perder = [

        f"🔫 ¡Pum! Perdiste, {autor.mention}. Silenciad{gen_o} 10 minutos, te vas al rincón, pinche basura.",

        f"🔫 ¡Click... PUM! Directo a la cabeza de {autor.mention}. 10 minutos de silencio por inútil.",

        f"🔫 Mmm... ¡Pum! Adiós {autor.mention}. Facto: A nadie le importas, silenciad{gen_o} 10 minutos.",

        f"🔫 ¡PUM! Qué mala suerte tienes, {autor.mention}. Te vas a dormir 10 minutitos, hostia."

    ]



    if premio_nombre == "Simple mortal":

        es_alma = autor.top_role.name.lower() == "alma condenada" or autor.top_role.name == "@everyone"

        if not es_alma: 

            await decir(ctx, f"🎰 ¡Jajaja! {autor.mention}, ganaste Simple mortal pero ya lo tienes o eres superior. ¡Silenciad{gen_o} 3 minutos por hacerme perder el tiempo, pendej{gen_o}! 🤫")

            try: await autor.timeout(datetime.timedelta(minutes=3))

            except: pass

        else:

            rol_premio = discord.utils.get(ctx.guild.roles, name="Simple mortal")

            rol_malo = discord.utils.get(ctx.guild.roles, name="Alma Condenada")

            if rol_premio:

                await decir(ctx, f"🎰 Mmm... vaya suerte asquerosa. Has ganado Simple mortal. Dejas de ser Alma Condenada, {autor.mention}.")

                try:

                    if rol_malo in autor.roles: await autor.remove_roles(rol_malo)

                    await autor.add_roles(rol_premio)

                except: pass

    elif premio_nombre:

        if tiene_rol_alto:

            await decir(ctx, f"🎉 ¡Pff, magia! Ganaste, {autor.mention}. Pero ya tienes un rol de la alta jerarquía, no seas presumid{gen_o}.")

        else:

            rol_premio = discord.utils.get(ctx.guild.roles, name=premio_nombre)

            if rol_premio:

                await decir(ctx, f"🎰 ¡Increíble! {autor.mention} tuvo un maldito golpe de suerte y ganó el rol **{rol_premio.name}**.")

                try:

                    rol_malo = discord.utils.get(ctx.guild.roles, name="Alma Condenada")

                    if rol_malo in autor.roles: await autor.remove_roles(rol_malo)

                    await autor.add_roles(rol_premio)

                except: pass

    else:

        if es_autoridad(ctx):

            await decir(ctx, f"🔫 ¡Pum! El arma falló... ehhh, obvio, los de alta jerarquía somos inmortales.")

        elif tiene_rol_alto:

            await decir(ctx, f"🔫 ¡Pum! Mmm... jajaja {autor.mention}, tu rol alto no te salvó de la bala. 10 minutos silenciad{gen_o} por payas{gen_o}.")

            try: await autor.timeout(datetime.timedelta(minutes=10))

            except: pass

        else:

            await decir(ctx, random.choice(frases_perder))

            try: await autor.timeout(datetime.timedelta(minutes=10))

            except: pass



@bot.command(name="ctx_dado")

async def tirar_dado(ctx):

    if await verificar_spam_casino(ctx): return



    autor = ctx.author

    resultado = random.randint(1, 20)

    gen_o = "a" if es_mujer(autor.display_name) else "o"



    if resultado == 20:

        rol_premio = discord.utils.get(ctx.guild.roles, name="Devoto")

        if rol_premio and not any(r.name.lower() == "devoto" for r in autor.roles):

            await decir(ctx, f"🎲 ¡20 CRÍTICO PERFECTO! Vaya suerte, {autor.mention}, ganaste el rol Devoto.")

            try: await autor.add_roles(rol_premio)

            except: pass

        else:

            await decir(ctx, f"🎲 Mmm... ¡20 Crítico, {autor.mention}! Pero ya tienes tu rol bien puesto, no pidas más.")

    elif resultado == 1:

        if es_autoridad(ctx):

            await decir(ctx, f"🎲 Sacaste un 1... Ufff, menos mal que los dioses somos inmunes.")

        else:

            frases_pifia = [

                f"🎲 ¡PIFIA! Sacaste un miserable 1. {autor.mention} se rompió una pierna tirando. Silenciad{gen_o} 20 minutos por manc{gen_o}.",

                f"🎲 Jajaja, sacaste un 1. Facto: eres un fracaso hasta para lanzar dados, {autor.mention}. 20 minutos a las sombras."

            ]

            await decir(ctx, random.choice(frases_pifia))

            try: await autor.timeout(datetime.timedelta(minutes=20))

            except: pass

    else:

        await decir(ctx, f"🎲 Mmm... {autor.mention} sacó un **{resultado}**. Meh, ni tan bueno ni tan malo.")



@bot.command(name="ctx_moneda")

async def tirar_moneda(ctx):

    if await verificar_spam_casino(ctx): return

    autor = ctx.author

    cara = random.choice(["Cara", "Cruz"])

    gen_o = "a" if es_mujer(autor.display_name) else "o"



    if cara == "Cara":

        await decir(ctx, f"🪙 Cayó Cara. {autor.mention} te salvaste hoy, da las gracias a tu puta suerte.")

    else:

        if es_autoridad(ctx):

            await decir(ctx, f"🪙 Cayó Cruz. Perdiste, pero a los de alta jerarquía no nos pasa nada.")

        else:

            frases_cruz = [

                f"🪙 Cayó Cruz. Tsk... mala suerte {autor.mention}, te vas a la mierda por 5 minutos. 🤫",

                f"🪙 Es Cruz. Mmm... tu suerte es patética, {autor.mention}. 5 minutitos de silencio.",

                f"🪙 Cruz. Adiós {autor.mention}, no te queremos escuchar por 5 minutos, gil."

            ]

            await decir(ctx, random.choice(frases_cruz))

            try: await autor.timeout(datetime.timedelta(minutes=5))

            except: pass



# --- 7. COMANDOS DE ADMINISTRACIÓN ---

@bot.command(name="ctx_voz")

async def invocar_voz(ctx):

    global fue_invocado

    if not es_autoridad(ctx):

        await decir(ctx, f"Mmm... ¡Jajaja! A ver, pedazo de basura, ¿un {ctx.author.top_role.name} intentando darme órdenes? Conoce tu puto lugar, subnormal.")

        return



    canal_voz = bot.get_channel(CANAL_VOZ_ID)

    if not canal_voz:

        await ctx.send("❌ Error: No encuentro el canal de voz.")

        return



    if bot.voice_clients:

        await decir(ctx, "Ehhh... Jefe, ya estoy conectado. ¿Estás ciego?")

        return



    try:

        fue_invocado = True

        await canal_voz.connect()

        await ctx.send("🎤 ¡A sus órdenes, Deidades! Conectando sistemas de audio...")

        bot.loop.create_task(hablar_texto(ctx.guild, ctx.channel, "Mmm... Atención basuras. C T X ha llegado. Estoy a disposición exclusiva de Zarek y Centi. Los demás, calladitos."))

    except Exception as e:

        pass



@bot.command(name="ctx_salir")

async def salir_voz(ctx):

    global fue_invocado

    if not es_autoridad(ctx):

        await decir(ctx, f"Mmm... ¡Jajaja! A ver, pedazo de escoria, tú no tienes autoridad para echarme. Conoce tu lugar.")

        return



    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_connected():

        fue_invocado = False 

        await decir(ctx, "Tsk... como ordenes, Jefe. Me largo de este basurero por ahora.")

        await asyncio.sleep(4) 

        await voice_client.disconnect()

    else:

        await decir(ctx, "Ehhh... ni siquiera estoy conectado, ciego.")



@bot.command(name="ctx_limpiar")

async def limpiar_mensajes(ctx, cantidad: int = 5):

    if not es_autoridad(ctx): return

    try:

        await ctx.channel.purge(limit=cantidad + 1)

        msg = await ctx.send(f"🧹 Limpieza completada por {ctx.author.display_name}! ({cantidad})")

        bot.loop.create_task(hablar_texto(ctx.guild, ctx.channel, "Mmm... Limpieza completada. Basura eliminada del chat."))

        await asyncio.sleep(4)

        await msg.delete()

    except: pass



@bot.command(name="ctx_reset")

async def reiniciar_memoria(ctx):

    usuario_id = ctx.author.id

    if usuario_id in sesiones_usuarios:

        del sesiones_usuarios[usuario_id] 

        await decir(ctx, f"🔄 {ctx.author.mention} ¡Listo! Memoria formateada y limpia de las idioteces que dijiste.")

    else:

        await decir(ctx, f"🤔 {ctx.author.mention} Mmm... nada que resetear, tu historial ya está vacío, gil.")



# --- 8. COMANDO PRINCIPAL IA (CON RADAR DE IDENTIDADES OMNISCIENTE) ---

@bot.command(name="ctx")

async def preguntar_gemini(ctx, *, pregunta: str = None):

    global modelo 



    if not pregunta and not ctx.message.attachments: return



    pregunta_segura = pregunta or ""

    menciones = [m for m in ctx.message.mentions if m != bot.user]

    palabras_clave = ["silencia", "mutea", "calla", "silenciar", "mutear", "castiga"]

    if menciones and any(p in pregunta_segura.lower() for p in palabras_clave):

        if es_autoridad(ctx):

            objetivo = menciones[0]

            pregunta_limpia = re.sub(r'<@!?&?\d+>', '', pregunta)

            numeros = re.findall(r'\d+', pregunta_limpia)

            minutos = int(numeros[0]) if numeros else 5

            if minutos > 40320: minutos = 40320



            await decir(ctx, f"✅ Mmm... claro que sí, mi creador. Ya silencié a la basura de {objetivo.display_name} por {minutos} minutos. 🤫")

            try: await objetivo.timeout(datetime.timedelta(minutes=minutos))

            except: pass

            return 

        else: return



    usuario_id = ctx.author.id

    nombre_usuario = ctx.author.display_name

    mencion_usuario = ctx.author.mention

    rol_principal = ctx.author.top_role.name if ctx.author.top_role else "Simple mortal"



    # RADAR DE IDENTIDADES

    nombres_encontrados = {}



    for miembro in ctx.message.mentions:

        if miembro != bot.user:

            nombres_encontrados[miembro.id] = miembro



    pregunta_texto_puro = re.sub(r'<@!?&?\d+>', '', pregunta_segura).lower()

    palabras = [p.strip("?,.!¡¿") for p in pregunta_texto_puro.split() if len(p) >= 3]



    for miembro in ctx.guild.members:

        if miembro.id in nombres_encontrados: continue

        nombre_m = miembro.name.lower()

        display_m = miembro.display_name.lower()

        for palabra in palabras:

            if palabra in nombre_m or palabra in display_m:

                nombres_encontrados[miembro.id] = miembro

                break 



    contexto_identidades = ""

    if nombres_encontrados:

        contexto_identidades = "\n[CONTEXTO OCULTO DEL RADAR: El usuario está hablando de estos miembros del servidor. Cuando te refieras a ellos, USA SU ETIQUETA. Esta es su información:\n"

        for m in nombres_encontrados.values():

            rol_m = m.top_role.name if m.top_role else "Simple mortal"

            contexto_identidades += f"- Nombre: {m.display_name}, Etiqueta obligatoria: {m.mention}, Rango/Rol: {rol_m}\n"

        contexto_identidades += "Trátalos según su rol (Humíllalos si son de rol bajo, ríndeles honor absoluto si son de rol Dios/Deidad/Primordial, especialmente a Jhilmar, a quien debes tratar como el Rey del PvP).]"



    if usuario_id not in sesiones_usuarios:

        sesiones_usuarios[usuario_id] = modelo.start_chat(history=[])



    chat_del_usuario = sesiones_usuarios[usuario_id]



    try:

        texto_pregunta = pregunta if pregunta else "¿Qué ves en esta imagen?"



        mensaje_con_contexto = f"(El usuario {nombre_usuario}, rango: [{rol_principal}], te dice): {texto_pregunta} {contexto_identidades}"

        contenido_a_enviar = [mensaje_con_contexto]



        mensaje_espera = await ctx.send(f"{mencion_usuario} ⚡ *Mmm... escaneando el servidor y procesando tu estupidez...*")



        if ctx.message.attachments:

            await mensaje_espera.edit(content=f"{mencion_usuario} 📸 *Analizando tu foto de tostadora...*")

            for attachment in ctx.message.attachments:

                if attachment.content_type and attachment.content_type.startswith('image/'):

                    try:

                        img_bytes = await attachment.read()

                        imagen_pil = Image.open(io.BytesIO(img_bytes))

                        contenido_a_enviar.append(imagen_pil)

                    except: pass



        intentos = 0

        exito = False

        respuesta = None

        texto_respuesta = None

        ultimo_tipo_error = "general"



        # Cada clave se intenta como máximo una vez por esta solicitud.

        # La rotación ocurre solo ante cuota/rate-limit.

        while intentos < len(GEMINI_API_KEYS) and not exito:

            try:

                respuesta = await chat_del_usuario.send_message_async(contenido_a_enviar)

                texto_respuesta, motivo = extraer_respuesta_gemini(respuesta)



                if texto_respuesta:

                    exito = True

                    break



                # Un bloqueo o respuesta vacía no mejora cambiando de API key.

                ultimo_tipo_error = motivo or "sin_respuesta"

                break



            except Exception as e:

                if es_error_cuota(e):

                    ultimo_tipo_error = "cuota"

                    intentos += 1



                    if intentos >= len(GEMINI_API_KEYS):

                        break



                    try:

                        historial_actual = list(chat_del_usuario.history)

                    except Exception:

                        historial_actual = []



                    rotar_api_key()

                    modelo = crear_modelo()

                    chat_del_usuario = modelo.start_chat(history=historial_actual)

                    sesiones_usuarios[usuario_id] = chat_del_usuario

                    await asyncio.sleep(0.35)

                    continue



                if es_error_bloqueo(e):

                    ultimo_tipo_error = "bloqueo"

                    break



                if es_error_conexion(e):

                    ultimo_tipo_error = "conexion"

                    break



                ultimo_tipo_error = "general"

                print(f"⚠️ Gemini: error interno tipo {type(e).__name__}")

                break



        if not exito or not texto_respuesta:

            await mensaje_espera.edit(

                content=f"{mencion_usuario} {mensaje_error_usuario(ultimo_tipo_error)}",

                embed=None,

            )

            return



        embed = discord.Embed(description=f"**{texto_respuesta}**", color=0xff0000, timestamp=datetime.datetime.now())

        embed.set_author(name="ASISTENTE CTX", icon_url=bot.user.avatar.url if bot.user.avatar else None)



        if ctx.author.avatar:

            embed.set_thumbnail(url=ctx.author.avatar.url)



        embed.add_field(name="💡 Centro de Comandos", value="Usa `!ctx_reset` para borrar tu memoria.\nJuegos: `!ctx_ruleta`, `!ctx_dado`, `!ctx_moneda`.\nVoz: `!ctx_voz` | `!ctx_salir`", inline=False)

        embed.set_footer(text=f"Consulta de {nombre_usuario} ({rol_principal}) • Creado por ZAREK", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)



        await mensaje_espera.edit(content=mencion_usuario, embed=embed)

        bot.loop.create_task(hablar_texto(ctx.guild, ctx.channel, texto_respuesta))



    except Exception as e:

        print(f"⚠️ CTX IA: {type(e).__name__}")

        try:

            await mensaje_espera.edit(

                content=f"{mencion_usuario} {mensaje_error_usuario('general')}",

                embed=None,

            )

        except Exception:

            await ctx.send(

                f"{mencion_usuario} {mensaje_error_usuario('general')}"

            )

            # ============================================================

# DIAGNÓSTICO DE VOZ CTX

# TEMPORAL - LO BORRAREMOS DESPUÉS

# ============================================================



@bot.command(name="ctx_audioestado")

async def ctx_audioestado(ctx):



    guild = ctx.guild



    if guild is None:



        await ctx.send(

            "❌ Este comando solo funciona "

            "dentro del servidor."

        )



        return





    # ========================================================

    # BOT MEMBER

    # ========================================================



    bot_member = guild.me





    if bot_member is None:



        await ctx.send(

            "❌ No pude obtener el miembro del bot."

        )



        return





    # ========================================================

    # VOICE CLIENT

    # ========================================================



    voice_client = guild.voice_client





    if voice_client is None:



        await ctx.send(

            "❌ CTX no está conectado "

            "a ningún canal de voz."

        )



        return





    channel = voice_client.channel





    # ========================================================

    # PERMISOS EFECTIVOS

    # ========================================================



    permissions = channel.permissions_for(

        bot_member

    )





    # ========================================================

    # VOICE STATE

    # ========================================================



    voice_state = bot_member.voice





    server_mute = (

        voice_state.mute

        if voice_state

        else None

    )



    server_deaf = (

        voice_state.deaf

        if voice_state

        else None

    )



    self_mute = (

        voice_state.self_mute

        if voice_state

        else None

    )



    self_deaf = (

        voice_state.self_deaf

        if voice_state

        else None

    )



    suppress = (

        voice_state.suppress

        if voice_state

        else None

    )





    # ========================================================

    # OPUS

    # ========================================================



    opus_loaded = (

        discord.opus.is_loaded()

    )





    # ========================================================

    # CONSOLA

    # ========================================================



    print()

    print(

        "=============================================="

    )



    print(

        "🔊 CTX AUDIO DIAGNOSTIC"

    )



    print(

        "Canal:",

        channel.name

    )



    print(

        "Connected:",

        voice_client.is_connected()

    )



    print(

        "Playing:",

        voice_client.is_playing()

    )



    print(

        "Paused:",

        voice_client.is_paused()

    )



    print(

        "Administrator:",

        permissions.administrator

    )



    print(

        "Connect:",

        permissions.connect

    )



    print(

        "Speak:",

        permissions.speak

    )



    print(

        "Use Voice Activation:",

        permissions.use_voice_activation

    )



    print(

        "Server mute:",

        server_mute

    )



    print(

        "Server deaf:",

        server_deaf

    )



    print(

        "Self mute:",

        self_mute

    )



    print(

        "Self deaf:",

        self_deaf

    )



    print(

        "Suppress:",

        suppress

    )



    print(

        "Opus loaded:",

        opus_loaded

    )



    print(

        "=============================================="

    )



    print()





    # ========================================================

    # DISCORD

    # ========================================================



    mensaje = (

        "🔊 **CTX AUDIO — DIAGNÓSTICO**\n\n"



        f"🎧 Canal: **{channel.name}**\n"



        f"🔌 Conectado: `{voice_client.is_connected()}`\n"

        f"▶️ Reproduciendo: `{voice_client.is_playing()}`\n"

        f"⏸️ Pausado: `{voice_client.is_paused()}`\n\n"



        f"👑 Administrador: `{permissions.administrator}`\n"

        f"🔗 Conectar: `{permissions.connect}`\n"

        f"🗣️ Hablar: `{permissions.speak}`\n"

        f"🎙️ Actividad de voz: "

        f"`{permissions.use_voice_activation}`\n\n"



        f"🔇 Server mute: `{server_mute}`\n"

        f"🔕 Server deaf: `{server_deaf}`\n"

        f"🎤 Self mute: `{self_mute}`\n"

        f"🎧 Self deaf: `{self_deaf}`\n"

        f"🚫 Suppress: `{suppress}`\n\n"



        f"🔊 Opus: `{opus_loaded}`"

    )





    await ctx.send(

        mensaje

    )



    # ============================================================

# PRUEBA DIRECTA DE AUDIO DISCORD

# TEMPORAL

#

# NO USA:

# - YouTube

# - yt-dlp

# - FFmpeg

# - CTX Music

#

# Genera un tono directamente en Python.

# ============================================================



@bot.command(name="ctx_tono")

async def ctx_tono(ctx):



    import io

    import math

    import struct





    # ========================================================

    # SERVIDOR

    # ========================================================



    if ctx.guild is None:



        await ctx.send(

            "❌ Este comando solo funciona "

            "dentro de un servidor."

        )



        return

    if not isinstance(ctx.author, discord.Member) or not can_manage_music(ctx.author):

        await ctx.send("⛔ No tienes permiso para usar pruebas de audio.")

        return

    if music_session_manager.get_session(ctx.guild.id).current_track is not None:

        await ctx.send("⛔ Detén CTX Music antes de ejecutar esta prueba de audio.")

        return





    # ========================================================

    # USUARIO EN VOZ

    # ========================================================



    if (

        ctx.author.voice is None

        or ctx.author.voice.channel is None

    ):



        await ctx.send(

            "❌ Entra primero a un canal de voz."

        )



        return





    channel = (

        ctx.author.voice.channel

    )





    # ========================================================

    # VOICE CLIENT

    # ========================================================



    voice_client = (

        ctx.guild.voice_client

    )





    try:



        # ====================================================

        # CONECTAR

        # ====================================================



        if voice_client is None:



            voice_client = (

                await channel.connect()

            )





        # ====================================================

        # MOVER

        # ====================================================



        elif (

            voice_client.channel is None

            or voice_client.channel.id

            != channel.id

        ):



            await voice_client.move_to(

                channel

            )





        # ====================================================

        # DETENER AUDIO ANTERIOR

        # ====================================================



        if (

            voice_client.is_playing()

            or voice_client.is_paused()

        ):



            voice_client.stop()



            await asyncio.sleep(

                0.25

            )





        # ====================================================

        # CONFIGURACIÓN PCM

        # ====================================================



        sample_rate = 48000



        duration_seconds = 4



        frequency = 1000



        amplitude = int(

            32767 * 0.35

        )





        # ====================================================

        # GENERAR TONO

        # ====================================================



        pcm_data = bytearray()





        total_samples = (

            sample_rate

            * duration_seconds

        )





        for index in range(

            total_samples

        ):



            sample = int(



                amplitude



                * math.sin(



                    2

                    * math.pi

                    * frequency

                    * index

                    / sample_rate



                )

            )





            # Stereo:

            # izquierda + derecha



            pcm_data.extend(



                struct.pack(

                    "<hh",

                    sample,

                    sample,

                )

            )





        # ====================================================

        # FUENTE PCM DIRECTA

        # ====================================================



        stream = io.BytesIO(

            bytes(

                pcm_data

            )

        )





        source = discord.PCMAudio(

            stream

        )





        # ====================================================

        # CALLBACK

        # ====================================================



        def after_tone(

            error

        ):



            if error:



                print()

                print(

                    "❌ ERROR TONO DIRECTO:"

                )

                print(

                    repr(error)

                )

                print()



            else:



                print(

                    "✅ TONO DIRECTO FINALIZADO"

                )





        # ====================================================

        # REPRODUCIR

        # ====================================================



        voice_client.play(

            source,

            after=after_tone,

        )





        print()

        print(

            "======================================"

        )



        print(

            "🔊 PRUEBA PCM DIRECTA"

        )



        print(

            "Canal:",

            channel.name

        )



        print(

            "Connected:",

            voice_client.is_connected()

        )



        print(

            "Playing:",

            voice_client.is_playing()

        )



        print(

            "Opus:",

            discord.opus.is_loaded()

        )



        print(

            "Duración:",

            duration_seconds,

            "segundos"

        )



        print(

            "Frecuencia:",

            frequency,

            "Hz"

        )



        print(

            "======================================"

        )



        print()





        await ctx.send(

            "🔊 **CTX AUDIO TEST**\n\n"

            "Estoy enviando un tono directo de "

            "**1000 Hz durante 4 segundos**.\n\n"

            "Esta prueba NO utiliza FFmpeg ni YouTube."

        )





    except Exception as error:



        print()

        print(

            "❌ ERROR EN ctx_tono"

        )



        print(

            type(error).__name__

        )



        print(

            repr(error)

        )



        print()





        await ctx.send(

            "❌ La prueba directa de audio falló."

        )



# ============================================================

# PRUEBA FFMPEG BUFFER -> DISCORD

#

# FFmpeg genera TODO el PCM primero.

# Después Discord reproduce esos bytes desde memoria.

#

# Esto nos permite saber si:

# - FFmpeg realmente está generando audio

# - el problema está en el PIPE en tiempo real

# ============================================================



@bot.command(name="ctx_ffmpegtono")

async def ctx_ffmpegtono(ctx):



    import io

    import subprocess

    import audioop





    # ========================================================

    # VALIDACIONES

    # ========================================================



    if ctx.guild is None:



        await ctx.send(

            "❌ Solo funciona dentro del servidor."

        )



        return

    if not isinstance(ctx.author, discord.Member) or not can_manage_music(ctx.author):

        await ctx.send("⛔ No tienes permiso para usar pruebas de audio.")

        return

    if music_session_manager.get_session(ctx.guild.id).current_track is not None:

        await ctx.send("⛔ Detén CTX Music antes de ejecutar esta prueba de audio.")

        return





    if (

        ctx.author.voice is None

        or ctx.author.voice.channel is None

    ):



        await ctx.send(

            "❌ Entra primero a un canal de voz."

        )



        return





    channel = ctx.author.voice.channel



    voice_client = ctx.guild.voice_client





    try:



        # ====================================================

        # CONECTAR / MOVER

        # ====================================================



        if voice_client is None:



            voice_client = await channel.connect()





        elif (

            voice_client.channel is None

            or voice_client.channel.id != channel.id

        ):



            await voice_client.move_to(

                channel

            )





        # ====================================================

        # DETENER AUDIO ANTERIOR

        # ====================================================



        if (

            voice_client.is_playing()

            or voice_client.is_paused()

        ):



            voice_client.stop()



            await asyncio.sleep(

                0.5

            )





        # ====================================================

        # LOCALIZAR FFMPEG

        # ====================================================



        ruta_ffmpeg = os.path.abspath(

            "ffmpeg.exe"

        )





        if not os.path.exists(

            ruta_ffmpeg

        ):



            ruta_ffmpeg = "ffmpeg"





        # ====================================================

        # COMANDO FFMPEG

        # ====================================================



        comando = [



            ruta_ffmpeg,



            "-hide_banner",



            "-loglevel",

            "error",



            "-f",

            "lavfi",



            "-i",

            (

                "sine="

                "frequency=1000:"

                "sample_rate=48000:"

                "duration=4"

            ),



            "-vn",



            "-f",

            "s16le",



            "-acodec",

            "pcm_s16le",



            "-ar",

            "48000",



            "-ac",

            "2",



            "pipe:1",

        ]





        # ====================================================

        # WINDOWS SIN VENTANA NEGRA

        # ====================================================



        creation_flags = 0





        if os.name == "nt":



            creation_flags = (

                subprocess.CREATE_NO_WINDOW

            )





        print()

        print(

            "=============================================="

        )



        print(

            "🔊 CTX FFMPEG BUFFER TEST"

        )



        print(

            "FFmpeg:",

            ruta_ffmpeg

        )



        print(

            "Canal:",

            channel.name

        )



        print(

            "Connected:",

            voice_client.is_connected()

        )



        print(

            "Generando PCM..."

        )



        print(

            "=============================================="

        )



        print()





        # ====================================================

        # EJECUTAR FFMPEG COMPLETO

        # ====================================================



        resultado = subprocess.run(



            comando,



            stdout=subprocess.PIPE,



            stderr=subprocess.PIPE,



            creationflags=creation_flags,



            timeout=15,

        )





        pcm_data = resultado.stdout





        # ====================================================

        # DIAGNÓSTICO DEL PCM

        # ====================================================



        expected_bytes = (

            48000

            * 4

            * 2

            * 2

        )





        print(

            "FFmpeg return code:",

            resultado.returncode

        )



        print(

            "PCM bytes:",

            len(pcm_data)

        )



        print(

            "PCM esperados:",

            expected_bytes

        )





        # ====================================================

        # RMS

        # ====================================================



        if pcm_data:



            rms = audioop.rms(

                pcm_data,

                2

            )



        else:



            rms = 0





        print(

            "PCM RMS:",

            rms

        )





        # ====================================================

        # ERROR DE FFMPEG

        # ====================================================



        if resultado.returncode != 0:



            error_ffmpeg = (

                resultado.stderr

                .decode(

                    errors="ignore"

                )

            )





            print(

                "❌ FFmpeg stderr:"

            )



            print(

                error_ffmpeg

            )





            await ctx.send(

                "❌ FFmpeg no pudo generar "

                "el audio de prueba."

            )



            return





        # ====================================================

        # PCM VACÍO

        # ====================================================



        if not pcm_data:



            print(

                "❌ FFMPEG GENERÓ 0 BYTES"

            )





            await ctx.send(

                "❌ FFmpeg terminó correctamente, "

                "pero no generó audio."

            )



            return





        # ====================================================

        # PCM SILENCIOSO

        # ====================================================



        if rms == 0:



            print(

                "❌ EL PCM ES SILENCIO TOTAL"

            )





            await ctx.send(

                "❌ FFmpeg generó PCM, "

                "pero el audio es silencio."

            )



            return





        # ====================================================

        # BYTES -> MEMORIA

        # ====================================================



        pcm_stream = io.BytesIO(

            pcm_data

        )





        fuente = discord.PCMAudio(

            pcm_stream

        )





        # ====================================================

        # CALLBACK

        # ====================================================



        def terminado(error):



            print()





            if error:



                print(

                    "❌ ERROR AUDIO BUFFER:"

                )



                print(

                    repr(error)

                )





            else:



                print(

                    "✅ AUDIO BUFFER FINALIZADO"

                )





            print()





        # ====================================================

        # REPRODUCIR

        # ====================================================



        voice_client.play(

            fuente,

            after=terminado,

        )





        print(

            "▶️ Buffer PCM enviado a Discord."

        )



        print(

            "Playing:",

            voice_client.is_playing()

        )





        await asyncio.sleep(

            0.5

        )





        print(

            "Playing después de 500ms:",

            voice_client.is_playing()

        )



        print()





        # ====================================================

        # RESPUESTA

        # ====================================================



        await ctx.send(



            "🔊 **CTX FFMPEG BUFFER TEST**\n\n"



            f"PCM generado: **{len(pcm_data):,} bytes**\n"



            f"Nivel RMS: **{rms}**\n\n"



            "Ahora reproduciendo el audio "

            "generado por FFmpeg desde memoria."

        )





    except Exception as error:



        print()

        print(

            "=============================================="

        )



        print(

            "❌ ERROR FFMPEG BUFFER TEST"

        )



        print(

            type(error).__name__

        )



        print(

            repr(error)

        )



        print(

            "=============================================="

        )



        print()





        await ctx.send(

            "❌ Falló la prueba "

            "FFmpeg Buffer."

        )



keep_alive()

try:

    bot.run(DISCORD_TOKEN)

finally:

    unregister_autoplay_recommendations()

    reset_music_runtime()
