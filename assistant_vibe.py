#!/usr/bin/env python3
"""
Voice assistant designed to work with Vibe Typer.

Workflow:
  1. Press Vibe Typer hotkey → speak → text appears in terminal
  2. Script reads the text, sends to DeepSeek LLM
  3. Response is spoken aloud via TTS

Usage:
  export DEEPSEEK_API_KEY="sk-..."
  python assistant_vibe.py
  # Then press Vibe Typer hotkey (e.g. Alt+Space) and speak into the terminal
"""
import os
import sys

import openai
import pyttsx3

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
SYSTEM_PROMPT = "You are a helpful voice assistant. Respond concisely in 1-3 sentences."


def get_llm_response(text: str) -> str:
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
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


def speak(text: str):
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    print(f"\nAssistant: {text}")
    engine.say(text)
    engine.runAndWait()


def main():
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY environment variable not set.")
        print("Get a free key at https://platform.deepseek.com")
        sys.exit(1)

    print("=== Voice Assistant (Vibe Typer mode) ===")
    print("1. Press your Vibe Typer hotkey (default: Alt+Space)")
    print("2. Speak your question/command")
    print("3. Text will appear here → sent to DeepSeek → response spoken aloud")
    print("4. Type 'quit' or 'exit' to stop")
    print("-" * 50)

    try:
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break
            response = get_llm_response(user_input)
            speak(response)
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
