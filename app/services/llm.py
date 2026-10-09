import os
import groq

def query_groq(prompt: str) -> str:
    # Active production models on Groq
    FALLBACK_MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return f"[PayPulse AI] Received query: '{prompt}'. (Set GROQ_API_KEY environment variable to enable real-time response)."

    client = groq.Groq(api_key=api_key)

    for model in FALLBACK_MODELS:
        try:
            print(f"[PayPulse AI] Requesting model: {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[PayPulse AI Error] {model} failed: {e}")

    return "All configured Groq models failed. Please verify API key permissions."
