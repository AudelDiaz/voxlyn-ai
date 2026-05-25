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

Incorpora en `process_pipeline()` en `daemon.py`, después de `speak()`.

```python
while not _cancel_playback.is_set():
    with _busy_lock:
        _busy = True
    notify("Voxlyn", "Te escucho…")
    time.sleep(0.3)  # pausa post-TTS
    audio = quick_listen(timeout=FOLLOWUP_TIMEOUT)
    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        break  # timeout → IDLE
    text = transcribe(whisper, audio)
    if not text:
        log.info("Follow-up: no speech detected, retrying")
        _retries += 1
        if _retries >= FOLLOWUP_MAX_RETRIES:
            break
        continue
    if text.lower() in FOLLOWUP_NEGATIVE:
        log.info("Follow-up: negative, returning to IDLE")
        break
    if text.lower() in FOLLOWUP_SILENT_AFFIRMATIVE:
        _affirm_retries += 1
        if _affirm_retries >= FOLLOWUP_MAX_RETRIES:
            break
        speak("¿Alguna otra pregunta?")
        _cancel_playback.clear()
        continue
    # Tiene una pregunta real
    ai_response = get_response(text, server, session)
    _retries = 0
    _affirm_retries = 0
    if ai_response in ("__LOGS__", "__EXIT__"):
        speak(ai_response, cancel_event=_cancel_playback)
        break  # comandos especiales → IDLE
    speak(ai_response)
    if not ai_response.endswith("?"):
        break  # respuesta sin pregunta → IDLE
    _cancel_playback.clear()
```

### Notas de implementación

| Aspecto | Detalle |
|---------|---------|
| `_busy` | Se pone `True` al entrar a AWAITING, se pone `False` al salir a IDLE (finally block de `process_pipeline`). Esto evita que trigger inicie nueva grabación en vez de cancelar. |
| Retry counters | `_retries` y `_affirm_retries` locales, resetean al obtener pregunta real. |
| `_cancel_playback.clear()` | se llama al inicio de cada iteración para que la siguiente iteración no se salte por una cancelación previa. |
| `speak()` commands | `__LOGS__` y `__EXIT__` necesitan `cancel_event` y rompen el loop (no tienen follow-up). |
| "¿Algo más?" | `speak("¿Alguna otra pregunta?")` es TTS local (Kokoro) — cero costo de LLM. No necesita OpenCode. |

## 5. quick_listen()

Función **bloqueante** nueva en `daemon.py` (no reusa `_capture_worker` que es async):

```python
def _quick_listen(timeout: float) -> np.ndarray | None:
    """Record audio for follow-up: shorter silence, shorter timeout.

    Returns audio array if speech detected, None on timeout/cancel.
    Checks ``_cancel_playback`` and ``_capture_stop`` during recording.
    """
    chunks: list[np.ndarray] = []
    silent_chunks = 0
    max_silent = int(FOLLOWUP_SILENCE_DURATION * SAMPLE_RATE / 1024)
    max_chunks = int(timeout * SAMPLE_RATE / 1024)

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    ) as stream:
        while len(chunks) < max_chunks:
            if _cancel_playback.is_set() or _capture_stop.is_set():
                return None
            chunk, _ = stream.read(1024)
            chunks.append(chunk)
            if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
            if silent_chunks > max_silent:
                break
    audio = np.concatenate(chunks).flatten()
    indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
    if len(indices) == 0:
        return None
    return audio[indices[0] : indices[-1] + 1]
```

| Parámetro       | Follow-up     | Normal (record_audio) |
|-----------------|---------------|----------------------|
| SILENCE_DURATION| 0.5s          | 2.0s                 |
| MAX_RECORD_SEC  | 3.0s          | 60s                  |
| Tono de inicio  | No            | Sí                   |
| Cancel support  | `_cancel_playback` + `_capture_stop` | No     |
| Threading       | Bloqueante (en pipeline thread) | Bloqueante (en pipeline thread) |

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
FOLLOWUP_MAX_RETRIES: int = 3
```

`FOLLOWUP_MAX_RETRIES` limita las repeticiones por ruido o afirmación vacía.

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
| `daemon.py`                       | Función `_quick_listen()` + loop post-speak en `process_pipeline()` + mover `_busy = False` al final del finally block |
| `voice_assistant/config.py`       | `FOLLOWUP_TIMEOUT`, `FOLLOWUP_SILENCE_DURATION`, `FOLLOWUP_NEGATIVE`, `FOLLOWUP_SILENT_AFFIRMATIVE`, `FOLLOWUP_MAX_RETRIES` |
| — | Sin cambios en transcription, audio, llm, router |

## 10. Lo que NO cambia

- Mempalace guarda cada turno vía `get_response()` (igual que ahora) — los follow-ups son turnos adicionales con su propio `save_turn()`
- Session de OpenCode mantiene contexto natural entre turnos
- Cancel con trigger funciona igual (setea `_cancel_playback` + `_capture_stop`)
- Sin gasto extra de LLM cuando la respuesta no termina en `?`
- Sin gasto extra de LLM en negativas (`FOLLOWUP_NEGATIVE`) ni afirmaciones vacías (`FOLLOWUP_SILENT_AFFIRMATIVE`)
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
