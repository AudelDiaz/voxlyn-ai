#!/usr/bin/env python3
import os

import numpy as np
import openai
import pyttsx3
import sounddevice as sd
import whisper

SAMPLE_RATE = 16000
DURATION = 5.0
SILENCE_THRESHOLD = 0.02
SILENCE_DURATION = 1.5
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
SYSTEM_PROMPT = "You are a helpful voice assistant. Respond concisely in 1-3 sentences."


class VoiceAssistant:
    def __init__(self, use_local_llm: bool = False):
        print("Loading Whisper model (base)...")
        self.stt_model = whisper.load_model("base")
        print("Initializing TTS engine...")
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 170)
        voices = self.tts_engine.getProperty("voices")
        if voices:
            self.tts_engine.setProperty("voice", voices[0].id)
        self.use_local_llm = use_local_llm
        if not use_local_llm and not DEEPSEEK_API_KEY:
            print("Warning: DEEPSEEK_API_KEY not set. Falling back to local LLM.")
            self.use_local_llm = True

    def record_audio(self) -> np.ndarray:
        print("\nListening... (speak now)")
        audio_chunks = []
        silent_chunks = 0
        max_silent_chunks = int(SILENCE_DURATION * SAMPLE_RATE / 1024)
        min_chunks = int(1.0 * SAMPLE_RATE / 1024)
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=1024,
            dtype="float32",
        )
        with stream:
            while True:
                chunk, _ = stream.read(1024)
                audio_chunks.append(chunk)
                if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                if len(audio_chunks) > min_chunks and silent_chunks > max_silent_chunks:
                    break
        audio = np.concatenate(audio_chunks)
        # Trim leading/trailing silence
        audio = audio[int(SAMPLE_RATE * 0.2) :]
        indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
        if len(indices) > 0:
            audio = audio[indices[0] : indices[-1] + 1]
        return audio

    def transcribe(self, audio: np.ndarray) -> str:
        result = self.stt_model.transcribe(audio, language="es", fp16=False)
        text = result["text"].strip()
        print(f"You said: {text}")
        return text

    def get_response(self, text: str) -> str:
        if self.use_local_llm:
            return self._local_response(text)
        return self._openai_response(text)

    def _openai_response(self, text: str) -> str:
        client = openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def _local_response(self, text: str) -> str:
        try:
            from transformers import pipeline
        except ImportError:
            return f"I heard: {text}. Install transformers for local LLM support."
        generator = pipeline("text-generation", model="microsoft/DialoGPT-small")
        result = generator(
            f"{SYSTEM_PROMPT}\nUser: {text}\nAssistant:",
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
        )
        return result[0]["generated_text"].split("Assistant:")[-1].strip()

    def speak(self, text: str):
        print(f"Assistant: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def run(self):
        print("\n=== Voice Assistant Ready ===")
        print("Press Ctrl+C to exit.")
        print(f"LLM mode: {'local' if self.use_local_llm else f'DeepSeek ({LLM_MODEL})'}")
        try:
            while True:
                audio = self.record_audio()
                text = self.transcribe(audio)
                if not text:
                    print("No speech detected.")
                    continue
                response = self.get_response(text)
                self.speak(response)
        except KeyboardInterrupt:
            print("\nGoodbye!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice Assistant CLI")
    parser.add_argument(
        "--local-llm",
        action="store_true",
        help="Use a local LLM (DialoGPT) instead of OpenAI API",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    args = parser.parse_args()

    assistant = VoiceAssistant(use_local_llm=args.local_llm)
    assistant.run()
