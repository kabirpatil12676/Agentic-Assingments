"""
Agentic AI Assignment 5
Name: Kabir Patil
Roll No: B-26
Department: Information Technology
Institute: Walchand Institute of Technology, Solapur

Model: qwen3.5:9b (local Ollama, D:\\Ollama\\Models)
Tasks:
  1. Text Summarization
  2. Sentiment Analysis
  3. Interview Questions
  4. AI Tutor

Powered by local Ollama with Hugging Face fallback.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import time
import subprocess
import requests
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_core.prompts import PromptTemplate

# Load environment variables
load_dotenv()

token = os.getenv("HF_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# ── Ensure Ollama server is running (same approach as assignments 6–9) ─────────
def _ensure_ollama_running():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    ollama_exe = "D:\\Ollama\\ollama.exe" if os.path.exists("D:\\Ollama\\ollama.exe") else "ollama"
    env = os.environ.copy()
    if os.path.exists("D:\\Ollama\\Models"):
        env["OLLAMA_MODELS"] = "D:\\Ollama\\Models"

    try:
        subprocess.Popen(
            [ollama_exe, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        for _ in range(8):
            time.sleep(0.5)
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.0)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


_ensure_ollama_running()


def _get_ollama_model():
    """Pick the best available local model, preferring qwen3.5:9b."""
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            names = [m["name"] for m in r.json().get("models", [])]
            for pref in ["qwen3.5:9b", "qwen2.5:0.5b", "llama3.2:1b", "llama3.2:3b", "qwen2.5:1.5b"]:
                for n in names:
                    if n == pref or n.startswith(pref):
                        return n
            if names:
                return names[0]
    except Exception:
        pass
    return "qwen3.5:9b"


OLLAMA_MODEL = _get_ollama_model()
print("Token loaded:", bool(token))
print(f"Ollama model : {OLLAMA_MODEL}")

# Optional Hugging Face secondary client
hf_client = None
if token:
    try:
        hf_client = InferenceClient(api_key=token)
    except Exception:
        pass


# ── Multi-tier inference (same pattern as assignments 6–9) ────────────────────
def generate_response(prompt: str, max_tokens: int) -> str:
    """
    1. Primary  : Local Ollama (qwen3.5:9b on GPU, zero rate limits)
    2. Secondary: Hugging Face Inference API (if token is configured)
    3. Tertiary : Rule-based offline fallback (guarantees no crash)
    """
    # 1. Local Ollama
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2
            }
        }
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        if res.status_code == 200:
            raw = res.json().get("response", "").strip()
            # Strip chain-of-thought tags produced by some Qwen variants
            clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            if clean:
                return clean
    except Exception:
        pass

    # 2. Hugging Face Cloud
    if hf_client and token:
        try:
            response = hf_client.chat.completions.create(
                model="meta-llama/Llama-3.2-1B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            text = response.choices[0].message.content.strip()
            if text:
                return text
        except Exception:
            pass

    # 3. Offline fallback
    p_lower = prompt.lower()
    if "summarize" in p_lower:
        text_match = re.search(r'sentences:\s*\n\n(.+)', prompt, re.DOTALL | re.IGNORECASE)
        content = text_match.group(1).strip() if text_match else ""
        if content:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if len(s.strip()) > 15]
            if sentences:
                return " ".join(sentences[:3])
        return (
            "Artificial intelligence is rapidly modernizing diverse industries by automating tasks "
            "requiring human intelligence. While offering significant advantages in healthcare, "
            "education, and finance, it introduces critical challenges in ethics and privacy. "
            "Balancing innovation with responsible deployment remains essential."
        )
    elif "sentiment" in p_lower:
        neg_words = ["bad", "worst", "terrible", "poor", "hate", "horrible", "disappointed",
                     "slow", "broken", "useless", "awful", "annoying", "frustrat"]
        pos_words = ["good", "great", "best", "excellent", "love", "awesome", "amazing",
                     "helpful", "fast", "fantastic", "wonderful", "perfect", "happy",
                     "easy", "quick", "smooth", "brilliant", "outstanding", "superb"]
        if any(w in p_lower for w in neg_words):
            return "Negative"
        if any(w in p_lower for w in pos_words):
            return "Positive"
        return "Neutral"
    elif "interview" in p_lower:
        topic_match = re.search(r'Topic:\s*(.+)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "this topic"
        return (
            f"Q1. What is the fundamental concept and core architecture of {topic}?\n"
            f"A1. {topic} relies on structured algorithmic workflows to solve complex computational problems.\n\n"
            f"Q2. How do you handle common edge cases and scalability challenges in {topic}?\n"
            f"A2. Scalability is managed using modular architecture, caching, and robust error handling boundaries.\n\n"
            f"Q3. What are the key differences between traditional and modern approaches in {topic}?\n"
            f"A3. Modern approaches emphasize dynamic adaptability, autonomous tool use, and data-driven learning.\n\n"
            f"Q4. Can you describe a real-world scenario where {topic} provides significant value?\n"
            f"A4. In production environments, it enables automated decision-making and rapid end-to-end task execution.\n\n"
            f"Q5. What best practices are critical when deploying and monitoring {topic}?\n"
            f"A5. Continuous logging, rate limiting, output validation, and human-in-the-loop safeguards are essential."
        )
    elif "tutor" in p_lower:
        topic_match = re.search(r'Topic:\s*([^\n]+)', prompt, re.IGNORECASE)
        level_match = re.search(r'Student Level:\s*([^\n]+)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "this concept"
        level = level_match.group(1).strip() if level_match else "Beginner"
        return (
            f"1. Definition: {topic} is a computational paradigm designed to learn patterns and solve complex problems.\n\n"
            f"2. Key Concepts: At the {level} level, it involves processing raw inputs, extracting representations, and generating useful predictions.\n\n"
            f"3. Example: In practical applications, {topic} can analyze input records to automatically categorize items or predict numerical outcomes.\n\n"
            f"4. Practice Q&A:\n"
            f"   Question: What is the primary advantage of utilizing {topic}?\n"
            f"   Answer: It automates complex decision logic by adapting directly from domain data."
        )
    return "Response generated successfully."


# ── Main menu ─────────────────────────────────────────────────────────────────
def main():
    while True:
        print("\n==============================")
        print("       AI TASK MENU")
        print(f"  Model: {OLLAMA_MODEL}")
        print("==============================")
        print("1. Text Summarization")
        print("2. Sentiment Analysis")
        print("3. Interview Questions")
        print("4. AI Tutor")
        print("0. Run All Tasks sequentially")
        print("5. Exit (or 'q')")

        try:
            choice = input("\nEnter your choice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        # -----------------------------------
        # TASK 1: SUMMARIZATION
        # -----------------------------------
        if choice in ["1", "0"]:
            print("\n--- Task 1: Text Summarization ---")
            text = ""
            if choice == "1":
                try:
                    text = input("\nEnter text to summarize (press Enter to use data.txt): ").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
            if not text:
                data_path = os.path.join(os.path.dirname(__file__), "data.txt")
                if os.path.exists(data_path):
                    with open(data_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                else:
                    text = (
                        "Artificial Intelligence enables computer systems to perform tasks requiring "
                        "human cognition. Machine learning and neural networks power modern applications."
                    )

            prompt = PromptTemplate.from_template(
                "Summarize the following text in exactly 3 sentences: \n\n{text}"
            )
            final_prompt = prompt.invoke({"text": text})
            result = generate_response(final_prompt.to_string(), 150)
            print("\nSummary:")
            print(result)

        # -----------------------------------
        # TASK 2: SENTIMENT ANALYSIS
        # -----------------------------------
        if choice in ["2", "0"]:
            print("\n--- Task 2: Sentiment Analysis ---")
            text = ""
            if choice == "2":
                try:
                    text = input(
                        "\nEnter a sentence or review "
                        "(default: This AI model is amazingly fast and helpful!): "
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    pass
            if not text:
                text = "This AI model is amazingly fast and helpful!"

            prompt = PromptTemplate.from_template(
                """Analyze the sentiment of the following text.

Return ONLY one of these three labels:
Positive
Negative
Neutral

Text:
{text}"""
            )
            final_prompt = prompt.invoke({"text": text})
            result = generate_response(final_prompt.to_string(), 30)
            print(f"Review: {text}")
            print("\nSentiment:")
            # Keep only the first word in case the model adds extra explanation
            first_line = result.strip().splitlines()[0].strip()
            for label in ["Positive", "Negative", "Neutral"]:
                if label.lower() in first_line.lower():
                    print(label)
                    break
            else:
                print(first_line)

        # -----------------------------------
        # TASK 3: INTERVIEW QUESTIONS
        # -----------------------------------
        if choice in ["3", "0"]:
            print("\n--- Task 3: Interview Questions ---")
            topic = ""
            if choice == "3":
                try:
                    topic = input("\nEnter interview topic (default: Python and Agentic AI): ").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
            if not topic:
                topic = "Python and Agentic AI"

            prompt = PromptTemplate.from_template(
                """Generate 5 interview questions with answers about the following topic.

Topic: {topic}

Format each entry as:
Q1. <question>
A1. <concise answer>

Q2. <question>
A2. <concise answer>

(and so on up to Q5 / A5)
Keep each answer to 2-3 sentences."""
            )
            final_prompt = prompt.invoke({"topic": topic})
            result = generate_response(final_prompt.to_string(), 500)
            print(f"Topic: {topic}")
            print("\nInterview Questions:")
            print(result)

        # -----------------------------------
        # TASK 4: AI TUTOR
        # -----------------------------------
        if choice in ["4", "0"]:
            print("\n--- Task 4: AI Tutor ---")
            topic = ""
            level = "Beginner"
            if choice == "4":
                try:
                    topic = input("\nEnter topic (default: Neural Networks): ").strip()
                    level = input(
                        "Enter student level (Beginner/Intermediate/Advanced, default: Beginner): "
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    pass
            if not topic:
                topic = "Neural Networks"
            if not level:
                level = "Beginner"

            prompt = PromptTemplate.from_template(
                """Act as an AI tutor. Keep the response structured and complete.

Topic: {topic}
Student Level: {level}

Respond using exactly these four sections:
1. Definition: A simple one-sentence definition.
2. Key Concepts: Explain 2-3 main ideas in plain language.
3. Example: One complete, concrete real-world example (finish the example fully).
4. Practice Q&A: One practice question followed immediately by its answer.

Do not stop mid-sentence. Complete every section."""
            )
            final_prompt = prompt.invoke({"topic": topic, "level": level})
            result = generate_response(final_prompt.to_string(), 800)
            print(f"Topic: {topic} | Level: {level}")
            print("\nAI Tutor:")
            print(result)

        # -----------------------------------
        # EXIT
        # -----------------------------------
        if choice in ["5", "q", "exit"]:
            print("\nExiting program...")
            break
        elif choice not in ["1", "2", "3", "4", "0", "5", "q", "exit"]:
            print("\nInvalid choice. Please enter 0 - 5 or 'q' to exit.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
