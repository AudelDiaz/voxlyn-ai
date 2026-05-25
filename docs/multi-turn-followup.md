# Multi-turn Follow-up (Confirmación Contextual)

Feature branch: `feat/multi-turn-followup`

## 1. Objetivo

Evitar que el usuario tenga que presionar la tecla de nuevo cuando el LLM
hace una pregunta o necesita confirmación. El daemon detecta que la respuesta
termina en `?` y se queda escuchando una respuesta corta.

## 2. Máquina de estados

```
IDLE ──(trigger)──► LISTENING ──(audio)──► PROCESSING ──(speak)──► AWAITING
                         ▲                                                    │
                         │                                          ┌─────────┼──────────┐
                         │                                          │         │          │
                         │                                      dice "no"  dice algo   timeout
                         │                                          │         │          │
                         │                                          ▼         ▼          ▼
                         │                                        IDLE   PROCESSING    IDLE
                         └────────────────(trigger=cancel)──────────────────────────────┘
```

## 3. Detonante (entrada a AWAITING)

Después de `speak(ai_response)` en `process_pipeline`:
- Si `ai_response` **termina con `?`** → loop de follow-up
- Si **no** → vuelve a `IDLE`

## 4. Loop de follow-up

```python
while not _cancel_playback.is_set():
    notify("Voxlyn", "Te escucho…")
    audio = quick_listen(timeout=FOLLOWUP_TIMEOUT)
    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        break  # timeout → IDLE
    text = transcribe(whisper, audio)
    if not text:
        continue  # ruido, escucha de nuevo
    if text.lower() in FOLLOWUP_NEGATIVE:
        break  # "no"/"nada"/"gracias" → IDLE
    if text.lower() in FOLLOWUP_SILENT_AFFIRMATIVE:
        speak("¿Alguna otra pregunta?")
        continue  # "sí" sin contenido → re-pregunta
    # Tiene una pregunta real
    ai_response = get_response(text, server, session)
    speak(ai_response)
    if not ai_response.endswith("?"):
        break  # respuesta sin pregunta → fin
```

## 5. quick_listen()

Reusa `_capture_worker` pero con parámetros específicos:

| Parámetro       | Follow-up     | Normal    |
|-----------------|---------------|-----------|
| SILENCE_DURATION| 0.5s          | 2.0s      |
| MAX_RECORD_SEC  | FOLLOWUP_TIMEOUT (3s) | 60s |
| Tono de inicio  | No            | Sí        |
| `_capture_stop` | Mismo event   | Idem      |

## 6. Variables en `voice_assistant/config.py`

```python
FOLLOWUP_TIMEOUT: float = float(os.getenv("FOLLOWUP_TIMEOUT", "3.0"))
FOLLOWUP_SILENCE_DURATION: float = float(
    os.getenv("FOLLOWUP_SILENCE_DURATION", "0.5")
)
FOLLOWUP_NEGATIVE: frozenset = frozenset({
    "no", "nada", "gracias", "eso es todo",
    "no gracias", "no más", "no quiero", "no tengo",
    "no, gracias", "no, eso es todo", "listo", "terminado",
})
FOLLOWUP_SILENT_AFFIRMATIVE: frozenset = frozenset({
    "sí", "síp", "ajá", "si", "yes", "yeah", "dale", "ok", "okay",
})
```

## 7. Notificación

| Momento        | Acción                            |
|----------------|-----------------------------------|
| Entra AWAITING | `notify("Voxlyn", "Te escucho…")` |
| Timeout        | Notificación desaparece           |
| Negativa       | Notificación desaparece           |
| Procesando     | Reusa existing notify             |

Sin tono de listen — el asistente acaba de hablar.

## 8. Cancelación

El trigger `cancel` setea `_cancel_playback` y `_capture_stop`:
- Rompe `speak()` en curso
- Rompe `quick_listen()` en curso
- Sale del loop → IDLE

## 9. Archivos a modificar

| Archivo                           | Cambio                              |
|-----------------------------------|-------------------------------------|
| `daemon.py`                       | Loop post-speak + `quick_listen()`  |
| `voice_assistant/config.py`       | Constantes de follow-up             |
| — | Sin cambios en transcription, audio, llm |

## 10. Lo que NO cambia

- Mempalace guarda el turno normal (el follow-up es continuidad en la misma sesión)
- Session de OpenCode mantiene contexto natural
- Cancel con trigger funciona igual
- Sin gasto extra de LLM cuando no hay `?`
- Sin cambios en TTS, grabación ni transcripción

## 11. Ejemplos

```
Usuario: recursos del sistema
Asistente: Memoria: 30 GB, disco: 92%…      ← fin → IDLE ✓

Usuario: quiero apagar algo
Asistente: ¿El equipo local o el servidor?   ← ?
              [3s, sin tono]
Usuario: el servidor
Asistente: No puedo apagar el servidor…      ← fin → IDLE ✓

Usuario: necesito ayuda con un error
Asistente: ¿Qué error estás viendo?          ← ?
              [3s, sin tono]
Usuario: no, ya lo resolví                    ← negative → IDLE ✓

Usuario: explícame qué es una VPN
Asistente: ¿Quieres teoría, comando          ← ?
           para configurar una, o ambas?
              [3s, sin tono]
Usuario: el comando
Asistente: Wireguard: sudo pacman -S…        ← fin → IDLE ✓
```
