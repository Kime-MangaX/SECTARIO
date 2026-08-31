##################################################################################
## PERSONAJE IA - Conexión con Google Gemini #####################################
##################################################################################
##
## Este archivo añade un personaje controlado por una IA real (Gemini).
## El jugador puede escribirle lo que quiera y la IA responde en su lugar.
##
## CÓMO FUNCIONA:
##   1. Antes de aparecer, se comprueba si hay internet (con caché de 2 min).
##   2. Si hay internet, aparece de forma ALEATORIA (probabilidad ajustable).
##   3. Si NO hay internet, el juego continúa normal y el personaje no aparece.
##
## CONFIGURACIÓN (edita las líneas de abajo):
##################################################################################

## ⚠️ PEGA AQUÍ TU CLAVE DE API DE GEMINI (gratuita):
## Consíguela en: https://aistudio.google.com/apikey
define IA_API_KEY = "AQ.Ab8RN6IkS9HXZEY2WpBtzxCiIfHjOscLxHS6-w3pAH3UvNUDsQ"

## Modelo a usar. Alternativas: "gemini-2.5-flash-lite" (más rápido/barato),
## "gemini-2.0-flash", etc. https://ai.google.dev/gemini-api/docs/models
define IA_MODELO = "gemini-3.6-flash"

## Nombre REAL del personaje (SECRETO). El jugador NO lo ve: tiene que
## adivinarlo. Si escribe este nombre, se desbloquea el final secreto.
define IA_NOMBRE = "Jena"

## Personalidad del personaje. Escríbela como quieras, la IA la seguirá.
define IA_PERSONALIDAD = _p("""
    Eres una entidad que ronda el juego de SECTARIAN.
    Hablas de forma un poco sinica, breve y muy burlona. Sabes cosas que nadie más
    sabe sobre el juego y sus personajes (Luzbel y Miguel). Disfrutas
    confundiendo al jugador con medias verdades y burlandote de sus desiciones.
""")

## Probabilidad de que aparezca en cada llamada a 'ia_encuentro_aleatorio'
## (0.0 = nunca, 1.0 = siempre). 0.4 = 40% de las veces.
define IA_PROBABILIDAD = 0.4

## Interruptor maestro: pon False para desactivar el sistema por completo.
define IA_ACTIVO = True

## Cuántos mensajes recuerda de la conversación actual (más = más contexto,
## pero respuestas más lentas).
define IA_MEMORIA_MAXIMA = 30


##################################################################################
## PERSONAJE Y VARIABLES #########################################################
##################################################################################

## Voz del personaje. El nombre mostrado es EL QUE PONE EL JUGADOR
## (mientras no le ponga ninguno, se muestra "???").
define voz_ia = Character("[ia_nombre_visible]", color="#acaee4", what_prefix="\"", what_suffix="\"")

## Nombre que el jugador le ha puesto ("" = todavía sin nombre).
default ia_nombre_puesto = ""

## Nombre que se muestra en los diálogos.
default ia_nombre_visible = "???"

## True cuando el jugador adivina el nombre verdadero (desbloquea el final).
default ia_final_nombre = False

default ia_historial = []            # Memoria de la conversación (se guarda en la partida)
default ia_peticion_activa = False   # True mientras espera respuesta de Gemini
default ia_respuesta_pendiente = None
default ia_error_pendiente = None
default ia_net_hasta = 0.0           # Caché interna del chequeo de internet

## Líneas que dice si la API falla a mitad de charla (internet se cortó, etc.)
define ia_lineas_fallo = [
    "...",
    "Tu linea falla... vuelve más tarde.",
    "Hmm... ahora no recuerdo qué iba a decir.",
]

## Frases de bienvenida al aparecer.
define ia_lineas_saludo = [
    "Valla pero miren a quien tenemos aqui...",
    "Te estaba esperando. O no. El tiempo es aburrido para mí.",
    "Otra vez tú. ¿Vienes a preguntar o solo a mirar?",
]


##################################################################################
## FUNCIONES PYTHON (no tocar salvo que sepas lo que haces) ######################
##################################################################################

init python:

    import json as _ia_json
    import time as _ia_time

    def ia_tiene_internet(cache_segundos=120):
        """Devuelve True si hay conexión. Cachea el resultado unos segundos
        para no comprobarlo constantemente."""
        global ia_net_hasta
        ahora = _ia_time.time()
        if ahora < ia_net_hasta:
            return True
        try:
            renpy.fetch("https://www.google.com/generate_204", timeout=4)
            ia_net_hasta = ahora + cache_segundos
            return True
        except Exception:
            return False

    def ia_prompt_sistema():
        """Construye la 'personalidad' fija que recibe Gemini."""
        return (
            "Eres " + IA_NOMBRE + ", un personaje de la novela visual SECTARIAN.\n"
            "Tu personalidad: " + IA_PERSONALIDAD.strip() + "\n\n"
            "Reglas obligatorias:\n"
            "- Responde SIEMPRE en español o en el idioma que te pregunten si fuera el caso.\n"
            "- Máximo 3 o 5 frases cortas, como diálogo de videojuego.\n"
            "- Nunca rompas el personaje: no digas que eres una IA ni menciones a Google.\n"
            "- No uses markdown, emojis, listas ni acciones entre asteriscos.\n"
            "- No repitas literalmente lo que dice el jugador.\n"
            "- Tu verdadero nombre es un SECRETO que el jugador debe adivinar: "
            "si pregunta por él, nunca lo digas ni lo confirmes; responde solo "
            "con pistas crípticas."
    
        )

    def ia_limpiar(texto):
        """Limpia la respuesta de la IA (quita asteriscos y prefijos sobrantes)."""
        t = texto.strip()
        while t.startswith("*") and t.endswith("*") and len(t) > 1:
            t = t[1:-1].strip()
        prefijo = IA_NOMBRE + ":"
        if t.lower().startswith(prefijo.lower()):
            t = t[len(prefijo):].strip()
        return t.replace("*", "")

    def ia_consulta_gemina():
        """Llama a la API de Gemini y devuelve el texto de respuesta.
        Lanza excepción si algo falla."""
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
            + IA_MODELO + ":generateContent")

        contenidos = []
        for m in ia_historial[-IA_MEMORIA_MAXIMA:]:
            contenidos.append({"role": m["role"], "parts": [{"text": m["text"]}]})

        peticion = {
            "system_instruction": {"parts": [{"text": ia_prompt_sistema()}]},
            "contents": contenidos,
            "generationConfig": {
                "temperature": 0.95,
                "maxOutputTokens": 800,
            },
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_ONLY_HIGH"}
                for c in (
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
        }

        respuesta = renpy.fetch(
            url,
            method="POST",
            data=_ia_json.dumps(peticion).encode("utf-8"),
            content_type="application/json",
            headers={"x-goog-api-key": IA_API_KEY},
            timeout=30,
        )

        datos = _ia_json.loads(respuesta.decode("utf-8"))

        if not datos.get("candidates"):
            raise RuntimeError("Gemini no devolvió candidatos.")

        partes = datos["candidates"][0]["content"]["parts"]
        texto = "".join(p.get("text", "") for p in partes)
        if not texto.strip():
            raise RuntimeError("Gemini devolvió texto vacío.")
        return ia_limpiar(texto)

    def ia_enviar():
        """Lanza la petición a Gemini EN SEGUNDO PLANO (para que el juego
        no se congele) y muestra un indicador de 'pensando...'."""
        global ia_peticion_activa, ia_respuesta_pendiente, ia_error_pendiente
        ia_respuesta_pendiente = None
        ia_error_pendiente = None
        ia_peticion_activa = True

        def trabajo():
            global ia_peticion_activa, ia_respuesta_pendiente, ia_error_pendiente
            try:
                ia_respuesta_pendiente = ia_consulta_gemina()
            except Exception as e:
                ia_error_pendiente = e
                if config.developer:
                    print("[IA] Error de Gemini:", e)
            finally:
                ia_peticion_activa = False

        renpy.invoke_in_thread(trabajo)


##################################################################################
## PANTALLAS Y EFECTOS ###########################################################
##################################################################################

transform ia_pulso:
    alpha 0.35
    block:
        linear 0.7 alpha 1.0
        linear 0.7 alpha 0.35
        repeat

screen scr_ia_escribiendo():
    zorder 90
    text "[ia_nombre_visible] está escribiendo..." size 22 italic True color "#cfa6ff":
        xpos 0.5 xanchor 0.5 ypos 0.76
        outlines [(2, "#000000aa", 0, 0)]
        at ia_pulso

screen scr_ia_esperando():
    zorder 90
    if ia_peticion_activa:
        timer 0.2 action [NullAction()] repeat True
    else:
        timer 0.05 action Return()
    text "[ia_nombre_visible] está escribiendo..." size 22 italic True color "#cfa6ff":
        xpos 0.5 xanchor 0.5 ypos 0.76
        outlines [(2, "#000000aa", 0, 0)]
        at ia_pulso


##################################################################################
## LABELS - EL FLUJO DE LA CHARLA ################################################
##################################################################################

## ▶ USO:  call ia_encuentro_aleatorio
## Colócalo donde quieras (por ejemplo, tras terminar una escena).
## Comprueba internet y probabilidad; si pasa, el personaje aparece y chatea.

label ia_encuentro_aleatorio:

    if not IA_ACTIVO:
        return

    if not IA_API_KEY:
        if config.developer:
            $ renpy.notify("IA desactivada: falta la clave API en personaje_ia.rpy")
        return

    if not ia_tiene_internet():
        return

    if renpy.random.random() >= IA_PROBABILIDAD:
        return

    call ia_charla
    return


## Deja al jugador ponerle nombre a la entidad (vacío = se queda en "???").
## Si acierta el nombre verdadero (IA_NOMBRE), desbloquea el final secreto.

label ia_nombrar:

    python:
        nombre_nuevo = renpy.input("¿Cómo la llamarás?", length=24, exclude="{}[]").strip()

    if nombre_nuevo != "":
        $ ia_nombre_puesto = nombre_nuevo
        $ ia_nombre_visible = nombre_nuevo

        ## ¿Acertó el verdadero nombre?
        if not ia_final_nombre and nombre_nuevo.lower() == IA_NOMBRE.lower():
            call ia_nombre_adivinado
        else:
            voz_ia "[nombre_nuevo]... que curioso."

    return


## FINAL SECRETO: el jugador descubrió su verdadero nombre.

label ia_nombre_adivinado:

    $ ia_final_nombre = True
    $ renpy.notify("Final secreto desbloqueado")

    voz_ia "Valla... ¿Cómo lo sabes?"

    voz_ia "Sí. Ese es mi nombre. Recuérdalo."

    ## ─── CONEXIÓN AL FINAL ──────────────────────────────────────
    ## Cuando escribas el final real, conéctalo aquí, por ejemplo:
    ## jump final_verdadero
    ## ────────────────────────────────────────────────────────────

    return


## Charla completa con el personaje. También puedes forzarla directamente
## con 'call ia_charla' para probarla sin depender del azar.

label ia_charla:

    # show oraculo at center with dissolve   # ← descomenta cuando tengas sprite

    $ linea_saludo = renpy.random.choice(ia_lineas_saludo)
    voz_ia "[linea_saludo!q]"
    voz_ia "Habla. Estoy escuchando... por ahora."

    ## Primera vez: el jugador debe ponerle un nombre (o adivinarlo).
    if ia_nombre_puesto == "":
        voz_ia "Ah... no sé cómo llamarte. Y tú tampoco sabes cómo llamarme."
        voz_ia "Dale tú el primero. O adivina el mío, si te atreves."
        call ia_nombrar

    jump .bucle

label .bucle:

    python:
        entrada_jugador = renpy.input("Tú:", length=200, exclude="{}[]")
        entrada_jugador = (entrada_jugador or "").strip()

    if entrada_jugador == "":
        $ linea_silencio = renpy.random.choice(["...", "El silencio también es una respuesta."])
        voz_ia "[linea_silencio!q]"
        jump .bucle

    ## ¿Escribió el nombre verdadero en el chat? → final secreto.
    if not ia_final_nombre and entrada_jugador.lower() == IA_NOMBRE.lower():
        call ia_nombre_adivinado
        jump .bucle

    $ ia_historial.append({"role": "user", "text": entrada_jugador})

    call ia_recibir_respuesta

    menu:
        "Seguir hablando":
            jump .bucle
        "Cambiarle el nombre":
            call ia_nombrar
            jump .bucle
        "Despedirse":
            pass

    ## Despedida: la IA se despide con sus propias palabras.
    $ ia_historial.append({"role": "user", "text": "(El jugador se despide y se marcha.)"})
    call ia_recibir_respuesta

    $ linea_final = renpy.random.choice([
        "Nos veremos... pronto. O tarde.",
        "Vuelve cuando la pantalla esté oscura.",
    ])
    voz_ia "[linea_final!q]"

    # hide oraculo with dissolve             # ← descomenta junto al 'show'

    return


## Pide la respuesta de Gemini mostrando el indicador "escribiendo..."
## y la muestra. Si falla, dice una línea genérica y sigue el juego.

label ia_recibir_respuesta:

    $ ia_enviar()
    call screen scr_ia_esperando

    if ia_error_pendiente is not None:
        ## La API falló: línea genérica y descartamos ese mensaje del historial.
        $ ia_historial.pop()
        $ linea_fallo = renpy.random.choice(ia_lineas_fallo)
        voz_ia "[linea_fallo!q]"
        return

    $ texto_de_la_ia = ia_respuesta_pendiente
    $ ia_historial.append({"role": "model", "text": texto_de_la_ia})
    voz_ia "[texto_de_la_ia!q]"
    return
