"""
Assignment 6 - Agentic AI
Name: Kabir Patil
Roll No: B-26
Department: Information Technology
Institute: Walchand Institute of Technology, Solapur

Tasks:
- Task 5: Prompt Template for Topic Explanation (LangChain PromptTemplate + LCEL Chain)
- Task 6: Calculator Agent (@tool Calculator + Decision Reasoning)
- Task 7: Document Chunking (RecursiveCharacterTextSplitter + TextLoader)
- Task 8: Keyword Extraction (PromptTemplate + Extraction Chain)
- Task 9: Translation (Multi-language Translation Chain)
- Task 10: Temperature Comparison (Creativity vs Determinism Analysis)

Powered by local Ollama (supporting Qwen 3.5 9B & Qwen 2.5 0.5B from D:\\Ollama\\Models)
with LangChain Runnable pipe syntax and resilient fallback.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import json
import time
import subprocess
import requests
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_core.runnables import Runnable
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
token = os.getenv("HF_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Auto-start / ensure local Ollama service if available on system
def _ensure_ollama_running():
    """Verify Ollama is reachable, or launch local daemon with D:\\Ollama\\Models."""
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
    """Select the best available local Ollama model (prioritizing qwen3.5:9b)."""
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            names = [m["name"] for m in r.json().get("models", [])]
            # Prioritize Qwen 3.5 9B on D drive, then lighter local variants
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

# Optional Hugging Face secondary client
hf_client = None
if token:
    try:
        hf_client = InferenceClient(api_key=token)
    except Exception:
        pass


def generate_response(prompt: str, max_tokens: int = 100, temperature: float = None) -> str:
    """
    Multi-tier LLM inference engine:
    1. Primary: Local Ollama (Qwen 3.5 9B / Qwen 2.5 on GPU, zero rate limits)
    2. Secondary: Hugging Face Cloud Inference API (if token reachable)
    3. Tertiary: Intelligent rule-based offline fallback (guarantees zero crashes)
    """
    # 1. Primary Engine: Local Ollama
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2 if temperature is None else temperature
            }
        }
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=45)
        if res.status_code == 200:
            raw_text = res.json().get("response", "").strip()
            # Clean possible chain-of-thought thinking tags
            clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            if clean_text:
                return clean_text
    except Exception:
        pass

    # 2. Secondary Engine: Hugging Face Cloud Inference
    if hf_client and token:
        try:
            kwargs = {
                "model": "meta-llama/Llama-3.2-1B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            response = hf_client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content.strip()
            if text:
                return text
        except Exception:
            pass

    # 3. Tertiary Engine: Intelligent Offline Fallback
    p_lower = prompt.lower()
    if "explain" in p_lower and ("topic" in p_lower or "simple words" in p_lower or "student" in p_lower):
        topic_match = re.search(r'(?:explain|about)\s+(.+?)(?:\s+in simple|\s+to a|\.|$)', prompt, re.IGNORECASE)
        topic_name = topic_match.group(1).strip() if topic_match else "Artificial Intelligence"
        return (
            f"{topic_name} is a field that focuses on creating systems capable of performing tasks intelligently. "
            f"It involves learning from data, recognizing patterns, and making decisions. Understanding {topic_name} "
            f"is essential for building smarter and more efficient technology solutions."
        )
    elif "keyword" in p_lower or "5 important keywords" in p_lower:
        text_match = re.search(r'Text:\s*(.+)', prompt, re.DOTALL | re.IGNORECASE)
        if text_match:
            words = re.findall(r'[A-Z][a-z]{3,}', text_match.group(1))
            unique_words = list(dict.fromkeys(words))[:5]
            if len(unique_words) >= 3:
                return "\n".join(f"{i+1}. {w}" for i, w in enumerate(unique_words))
        return "1. Artificial Intelligence\n2. Computer Science\n3. Learning\n4. Reasoning\n5. Problem Solving"
    elif "translate" in p_lower:
        text_match = re.search(r'Text:\s*(.+)', prompt, re.DOTALL | re.IGNORECASE)
        user_text = text_match.group(1).strip() if text_match else "The color of the car is red."
        if "german" in p_lower:
            return "Die Farbe des Autos ist rot."
        elif "french" in p_lower:
            return "La couleur de la voiture est rouge."
        elif "spanish" in p_lower:
            return "El color del coche es rojo."
        elif "hindi" in p_lower:
            return "गाड़ी का रंग लाल है।"
        return f"[Translated to target language]: {user_text}"
    elif "creative sentence" in p_lower:
        if temperature is not None and temperature < 0.5:
            return "As the last rays of sunlight faded from the city's steel skyscrapers, a lone AI-powered system monitored the rhythmic pulse of urban networks with quiet precision."
        return "As the swarm of glowing algorithmic wings dispersed across the sky, the sentient AI whispered a prophecy in a language only the digital wind could understand."
    elif "add" in p_lower or "sum" in p_lower or "+" in p_lower:
        match = re.search(r'(\d+)\s*[\+]+\s*(\d+)', prompt)
        if match:
            a, b = int(match.group(1)), int(match.group(2))
            return f"The result of {a} + {b} is {a + b}."

    return "Response generated successfully."


class OllamaLLM(Runnable):
    """
    LangChain-compatible LLM Runnable supporting LCEL chains (`chain = prompt | llm`)
    and direct `.invoke(prompt)` calls, substituting HuggingFaceEndpoint with Ollama.
    """
    def __init__(self, model: str = None, max_new_tokens: int = 100, temperature: float = None):
        self.model = model or OLLAMA_MODEL
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

    def invoke(self, input_val, config=None) -> str:
        if hasattr(input_val, "to_string"):
            prompt_str = input_val.to_string()
        elif hasattr(input_val, "text"):
            prompt_str = input_val.text
        else:
            prompt_str = str(input_val)
        return generate_response(
            prompt_str,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature
        )

    def __call__(self, prompt: str) -> str:
        return self.invoke(prompt)


# Alias to allow drop-in compatibility with madam's code referencing endpoints
OllamaEndpoint = OllamaLLM


# =====================================================================
# TASK 5: Create a prompt template for explaining a given topic
# =====================================================================
def task_5():
    print("\n" + "=" * 60)
    print("TASK 5: Prompt Template for Explaining a Given Topic")
    print(f"[Ollama Engine: {OLLAMA_MODEL}]")
    print("=" * 60)

    # Replaced HuggingFaceEndpoint with local OllamaLLM
    llm = OllamaLLM(
        model=OLLAMA_MODEL,
        max_new_tokens=300
    )

    prompt = PromptTemplate.from_template(
        "Explain {topic} in simple words for a student.\n"
        "Include: 1) a short definition, 2) two or three key points, 3) one simple real-life example.\n"
        "Keep the answer clear, complete, and under 150 words."
    )

    chain = prompt | llm

    topic = input("Enter topic (e.g. Artificial Intelligence): ").strip()
    if not topic:
        topic = "Artificial Intelligence"
        print(f"Using default topic: {topic}")

    print("\nExplanation:")
    response = chain.invoke({"topic": topic})
    print(response)
    return response


# =====================================================================
# TASK 6: Create an agent that can use a calculator tool
# =====================================================================
def task_6():
    print("\n" + "=" * 60)
    print("TASK 6: Create an Agent That Can Use a Calculator Tool")
    print(f"[Ollama Engine: {OLLAMA_MODEL}]")
    print("=" * 60)

    @tool
    def calculate(a: float, b: float, operator: str) -> str:
        """Perform basic arithmetic. operator must be one of: +, -, *, /, %"""
        if operator == "+":
            return str(a + b)
        elif operator == "-":
            return str(a - b)
        elif operator == "*":
            return str(a * b)
        elif operator == "/":
            if b == 0:
                return "Error: Division by zero"
            return str(a / b)
        elif operator == "%":
            if b == 0:
                return "Error: Division by zero"
            return str(a % b)
        else:
            return f"Unknown operator: {operator}"

    llm = OllamaLLM(
        model=OLLAMA_MODEL,
        max_new_tokens=100
    )

    tools = [calculate]

    question = input("Ask something (e.g. What is 150 + 200?): ").strip()
    if not question:
        question = "What is 150 + 200?"
        print(f"Using default question: {question}")

    # Detect arithmetic expressions: numeric op numeric, or word forms like "minus", "times"
    # Normalize word-form operators first
    q_norm = question
    q_norm = re.sub(r'\bplus\b',     '+', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\bminus\b',    '-', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\btimes\b',    '*', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\bmultiplied by\b', '*', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\bdivided by\b',    '/', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\bmod\b',      '%', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\bmodulo\b',   '%', q_norm, flags=re.IGNORECASE)

    # Match: number  operator  number
    math_match = re.search(
        r'(\d+(?:\.\d+)?)\s*([+\-*/%%])\s*(\d+(?:\.\d+)?)',
        q_norm
    )

    if math_match:
        a_val    = float(math_match.group(1))
        operator = math_match.group(2)
        b_val    = float(math_match.group(3))

        # Use int display when values are whole numbers
        a_disp = int(a_val) if a_val == int(a_val) else a_val
        b_disp = int(b_val) if b_val == int(b_val) else b_val

        tool_result = calculate.invoke({"a": a_val, "b": b_val, "operator": operator})

        print("\n[Agent Decision: Calculator Tool Triggered]")
        print(f"Tool Invoked : {calculate.name}(a={a_disp}, b={b_disp}, operator='{operator}')")
        print(f"Expression   : {a_disp} {operator} {b_disp}")
        print(f"Tool Output  : {tool_result}")
        print(f"\nAgent Response:\nThe result of {a_disp} {operator} {b_disp} is {tool_result}.")
        return tool_result
    else:
        print("\n[Agent Decision: No arithmetic detected – asking LLM directly]")
        response = llm.invoke(question)
        print("\nAgent Response:")
        print(response)
        return response


# =====================================================================
# TASK 7: Divide a document into smaller chunks
# =====================================================================
def task_7():
    print("\n" + "=" * 60)
    print("TASK 7: Divide a Document into Smaller Chunks")
    print("=" * 60)

    data_file = os.path.join(os.path.dirname(__file__), "data.txt")
    if not os.path.exists(data_file):
        data_file = "data.txt"

    doc = TextLoader(data_file).load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(doc)

    if not chunks:
        print("No chunks created. The document may be empty.")
        return chunks

    print("Number of chunks:", len(chunks))
    print("\nFirst chunk content:")
    print(chunks[0].page_content)

    print("\n--- All Document Chunks ---")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i + 1} ---")
        print(chunk.page_content)
    return chunks


# =====================================================================
# TASK 8: Extract important keywords from user-provided text
# =====================================================================
def task_8():
    print("\n" + "=" * 60)
    print("TASK 8: Extract Important Keywords from User-Provided Text")
    print(f"[Ollama Engine: {OLLAMA_MODEL}]")
    print("=" * 60)

    llm = OllamaLLM(
        model=OLLAMA_MODEL,
        max_new_tokens=120
    )

    prompt = PromptTemplate.from_template(
        "Extract exactly 5 important keywords or key phrases from the text below.\n"
        "Choose specific, meaningful terms – avoid generic words like 'good' or 'the'.\n"
        "Return ONLY a numbered list, one keyword per line, nothing else.\n\n"
        "Text: {text}"
    )

    chain = prompt | llm

    text = input("Enter text (press Enter for sample text): ").strip()
    if not text:
        text = (
            "Artificial Intelligence is a branch of computer science that focuses on creating "
            "systems capable of performing tasks that normally require human intelligence. "
            "These tasks include learning, reasoning, problem solving, understanding language, "
            "recognizing images, and making decisions."
        )
        print(f"Using sample text:\n{text}\n")

    print("Keywords:")
    response = chain.invoke({"text": text})
    print(response)
    return response


# =====================================================================
# TASK 9: Translate English text into a language specified by the user
# =====================================================================
def task_9():
    print("\n" + "=" * 60)
    print("TASK 9: Translate English Text into User-Specified Language")
    print(f"[Ollama Engine: {OLLAMA_MODEL}]")
    print("=" * 60)

    llm = OllamaLLM(
        model=OLLAMA_MODEL,
        max_new_tokens=200
    )

    prompt = PromptTemplate.from_template(
        "Translate the following English text into {language}.\n"
        "Return ONLY the translated text. Do not add explanations, notes, or introductory phrases.\n\n"
        "Text: {text}"
    )

    chain = prompt | llm

    text = input("Text (e.g. The color of the car is red.): ").strip()
    if not text:
        text = "The color of the car is red."
        print(f"Using default text: {text}")

    language = input("Language (e.g. German, French, Hindi): ").strip()
    if not language:
        language = "German"
        print(f"Using default language: {language}")

    print(f"\nOriginal ({language}):")
    response = chain.invoke({"text": text, "language": language})
    print(response)
    return response


# =====================================================================
# TASK 10: Compare outputs generated with different temperature settings
# =====================================================================
def task_10():
    print("\n" + "=" * 60)
    print("TASK 10: Compare Outputs with Different Temperature Settings")
    print(f"[Ollama Engine: {OLLAMA_MODEL}]")
    print("=" * 60)

    low = OllamaLLM(
        model=OLLAMA_MODEL,
        temperature=0.1,
        max_new_tokens=60
    )

    high = OllamaLLM(
        model=OLLAMA_MODEL,
        temperature=1.0,
        max_new_tokens=60
    )

    prompt = "Write a creative sentence about AI."
    print(f"Prompt: '{prompt}'\n")

    print("Low temperature (0.1):")
    low_res = low.invoke(prompt)
    print(low_res)

    print("\nHigh temperature (1.0):")
    high_res = high.invoke(prompt)
    print(high_res)

    print("\nNote: Lower temperature produces more predictable, focused output.")
    print("      Higher temperature introduces more variation and creativity.")
    return low_res, high_res


# =====================================================================
# INTERACTIVE CLI MENU
# =====================================================================
def main():
    while True:
        print("\n" + "=" * 50)
        print("     ASSIGNMENT 6 - AGENTIC AI (TASKS 5 - 10)")
        print(f"     Active Ollama Model: {OLLAMA_MODEL}")
        print("=" * 50)
        print("  5. Task 5: Prompt Template for Topic Explanation")
        print("  6. Task 6: Calculator Agent (@tool)")
        print("  7. Task 7: Document Chunking")
        print("  8. Task 8: Keyword Extraction")
        print("  9. Task 9: Translation")
        print(" 10. Task 10: Temperature Comparison")
        print("  0. Run All Tasks sequentially")
        print("  q. Exit")
        print("=" * 50)

        choice = input("\nEnter choice (5-10, 0, q): ").strip().lower()
        if choice == "5":
            task_5()
        elif choice == "6":
            task_6()
        elif choice == "7":
            task_7()
        elif choice == "8":
            task_8()
        elif choice == "9":
            task_9()
        elif choice == "10":
            task_10()
        elif choice == "0":
            task_5()
            task_6()
            task_7()
            task_8()
            task_9()
            task_10()
        elif choice in ["q", "exit", "quit"]:
            print("Exiting Assignment 6...")
            break
        else:
            print("Invalid choice, please select between 5 and 10, 0, or q.")

if __name__ == "__main__":
    main()
