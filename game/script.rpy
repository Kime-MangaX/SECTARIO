# Coloca el código de tu juego en este archivo.

# Declara los personajes usados en el juego como en el ejemplo:

define e = Character("Eileen")



# El juego comienza aquí.

label start:

    # Muestra una imagen de fondo: Aquí se usa un marcador de posición por
    # defecto. Es posible añadir un archivo en el directorio 'images' con el
    # nombre "bg room.png" or "bg room.jpg" para que se muestre aquí.

    scene bg room

    # Muestra un personaje: Se usa un marcador de posición. Es posible
    # reemplazarlo añadiendo un archivo llamado "eileen happy.png" al directorio
    # 'images'.

    show eileen happy

    # Presenta las líneas del diálogo.

    e "Hola XD."

    e "Toca crear la historia, osea no la historia en si si no el guion."

    e "Pero F ajdlksahfkh"

    yusu "O no, q mal XD"

    daisu "Eres cruel..."

    "Narrador narrando waaaaaaaa"

    ## ─── PERSONAJE IA ──────────────────────────────────────────────
    ## PRUEBA: aparece siempre al ejecutar. Comenta la de abajo y
    ## descomenta ia_encuentro_aleatorio para volver al modo 40% azar.
    call ia_charla
    # call ia_encuentro_aleatorio
    ## ────────────────────────────────────────────────────────────────

    # Finaliza el juego:

    return
