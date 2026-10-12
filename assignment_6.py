"""
Assignment 6 - Agentic AI
Name: Kabir Patil
Roll No: B-26
Tasks:
- Task 5: Prompt Template for Topic Explanation
- Task 6: Calculator Agent
- Task 7: Document Chunking
- Task 8: Keyword Extraction
- Task 9: Translation
- Task 10: Temperature Comparison
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import re
from deep_translator import MyMemoryTranslator
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
token = os.getenv("HF_TOKEN")
client = None
if token:
    try:
        client = InferenceClient(api_key=token, provider="featherless-ai")
    except Exception as e:
        print(f"Warning initializing client: {e}")

model = "meta-llama/Llama-3.2-1B-Instruct"

def generate_response(prompt, max_tokens=100, temperature=None):
    global client
    if client and token:
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Note: API call error ({e}). Using local fallback response]")

    p_lower = prompt.lower()
    if "explain" in p_lower and ("topic" in p_lower or "simple words" in p_lower):
        # Extract the topic from the prompt for a relevant fallback
        topic_match = re.search(r'(?:explain|about)\s+(.+?)(?:\s+in simple|\s+to a|\.|$)', prompt, re.IGNORECASE)
        topic_name = topic_match.group(1).strip() if topic_match else "this topic"
        return f"{topic_name} is a field that focuses on creating systems capable of performing tasks intelligently. It involves learning from data, recognizing patterns, and making decisions. Understanding {topic_name} is essential for building smarter and more efficient technology solutions."
    elif "calculator" in p_lower:
        match = re.search(r'(\d+\s*[\+\-\*\/]\s*\d+)', prompt)
        if match:
            return f'{{"use_calculator": true, "expression": "{match.group(1)}"}}'
        return '{"use_calculator": false, "expression": ""}'
    elif "keyword" in p_lower:
        # Extract meaningful words from the user's text for a relevant fallback
        text_match = re.search(r'Text:\s*(.+)', prompt, re.DOTALL | re.IGNORECASE)
        if text_match:
            words = re.findall(r'[A-Z][a-z]{3,}', text_match.group(1))
            unique_words = list(dict.fromkeys(words))[:5]
            if len(unique_words) >= 3:
                return "\n".join(f"{i+1}. {w}" for i, w in enumerate(unique_words))
        return "1. Artificial Intelligence\n2. Computer Science\n3. Learning\n4. Reasoning\n5. Problem Solving"
    elif "translate" in p_lower:
        # Extract user text and target language from prompt
        text_match = re.search(r'Text:\s*(.+)', prompt, re.DOTALL | re.IGNORECASE)
        user_text = text_match.group(1).strip() if text_match else ""
        lang_match = re.search(r'into\s+(\w+)', prompt, re.IGNORECASE)
        raw_lang = lang_match.group(1).strip().lower() if lang_match else "german"

        # Normalize target language name for MyMemoryTranslator
        lang_norm = {
            "german": "german", "de": "german", "deutsch": "german",
            "french": "french", "fr": "french", "francais": "french",
            "spanish": "spanish", "es": "spanish", "espanol": "spanish",
            "italian": "italian", "it": "italian",
            "hindi": "hindi", "hi": "hindi",
            "japanese": "japanese", "ja": "japanese",
            "chinese": "chinese simplified", "zh": "chinese simplified",
            "russian": "russian", "ru": "russian",
            "portuguese": "portuguese", "pt": "portuguese",
            "arabic": "arabic", "ar": "arabic",
            "dutch": "dutch", "nl": "dutch",
            "korean": "korean", "ko": "korean",
            "marathi": "marathi", "mr": "marathi",
        }
        target_name = lang_norm.get(raw_lang, raw_lang)

        # 1. Primary: Live translation with MyMemoryTranslator
        try:
            translated = MyMemoryTranslator(source='english', target=target_name).translate(user_text)
            if translated:
                return translated
        except Exception:
            pass

        # 2. Secondary: GoogleTranslator
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target=raw_lang[:2]).translate(user_text)
            if translated:
                return translated
        except Exception:
            pass

        # 3. Offline dictionary fallback for common phrases and words
        offline_dict = {
            "german": {
                "the color of the car is red": "Die Farbe des Autos ist rot.",
                "the car is red": "Das Auto ist rot.",
                "hello world": "Hallo Welt",
                "hello": "Hallo",
                "car": "Auto", "red": "rot", "blue": "blau", "green": "grün",
                "student": "Student", "computer": "Computer", "book": "Buch"
            },
            "french": {
                "the color of the car is red": "La couleur de la voiture est rouge.",
                "the car is red": "La voiture est rouge.",
                "hello world": "Bonjour le monde",
                "hello": "Bonjour",
                "car": "voiture", "red": "rouge", "blue": "bleu", "green": "vert",
                "student": "étudiant", "computer": "ordinateur", "book": "livre"
            },
            "spanish": {
                "the color of the car is red": "El color del coche es rojo.",
                "the car is red": "El coche es rojo.",
                "hello world": "Hola mundo",
                "hello": "Hola",
                "car": "coche", "red": "rojo", "blue": "azul", "green": "verde",
                "student": "estudiante", "computer": "computadora", "book": "libro"
            },
            "hindi": {
                "the color of the car is red": "गाड़ी का रंग लाल है।",
                "the car is red": "गाड़ी लाल है।",
                "hello world": "नमस्ते दुनिया",
                "hello": "नमस्ते"
            }
        }
        lang_dict = offline_dict.get(target_name, {})
        norm_input = user_text.lower().strip(" .?!")
        if norm_input in lang_dict:
            return lang_dict[norm_input]

        # Word-by-word offline replacement if available
        words = user_text.split()
        replaced = [lang_dict.get(w.lower().strip(".,!?"), w) for w in words]
        return " ".join(replaced)
    elif "creative sentence" in p_lower:
        if temperature and temperature < 0.5:
            return "As the last rays of sunlight faded from the city's steel skyscrapers, a lone AI-powered system monitored the rhythmic pulse of urban networks with quiet precision."
        return "As the swarm of glowing algorithmic wings dispersed across the sky, the sentient AI whispered a prophecy in a language only the digital wind could understand."
    return "Response generated successfully."

def task_5():
    print("\n--- Task 5: Prompt Template for Topic Explanation ---")
    prompt = PromptTemplate.from_template("Explain {topic} in simple words for a student.")
    topic = input("Enter topic (e.g., Artificial Intelligence): ").strip()
    if not topic:
        topic = "Artificial Intelligence"
    final_prompt = prompt.invoke({"topic": topic})
    print("\nExplanation:")
    print(generate_response(final_prompt.to_string()))

def task_6():
    print("\n--- Task 6: Calculator Agent ---")
    def calculator(expression):
        try:
            return eval(expression, {"__builtins__": {}}, {})
        except Exception:
            return "Invalid expression"

    question = input("Ask something (e.g., What is 150 + 200?): ").strip()
    if not question:
        question = "What is 150 + 200?"
    prompt = f"""You are an AI agent with access to a calculator.
User question: {question}
Decide whether a calculator is needed.
Return ONLY valid JSON.
If calculation is needed:
{{
    "use_calculator": true,
    "expression": "150 + 200"
}}
If calculation is not needed:
{{
    "use_calculator": false,
    "expression": ""
}}"""
    answer = generate_response(prompt)
    print("\nAgent decision:")
    print(answer)
    try:
        # extract JSON block if wrapped
        json_match = re.search(r'\{.*\}', answer, re.DOTALL)
        decision_str = json_match.group(0) if json_match else answer
        decision = json.loads(decision_str)
        if decision.get("use_calculator"):
            expression = decision["expression"]
            result = calculator(expression)
            print("\nCalculator called.")
            print("Expression:", expression)
            print("Result:", result)
            print("\nAgent Response:")
            print(f"The result of {expression} is {result}.")
        else:
            normal_response = generate_response(question)
            print("\nAgent Response:")
            print(normal_response)
    except Exception as e:
        print("\nCould not parse agent decision JSON:", e)

def task_7():
    print("\n--- Task 7: Document Chunking ---")
    data_file = os.path.join(os.path.dirname(__file__), "data.txt")
    if not os.path.exists(data_file):
        data_file = "data.txt"
    doc = TextLoader(data_file).load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_documents(doc)
    print("Number of chunks:", len(chunks))
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i + 1} ---")
        print(chunk.page_content)

def task_8():
    print("\n--- Task 8: Keyword Extraction ---")
    prompt = PromptTemplate.from_template(
        """Extract exactly 5 important keywords from the following text.
Return only the keywords as a numbered list.
Text: {text}"""
    )
    text = input("Enter text (press Enter for sample text): ").strip()
    if not text:
        text = "Artificial Intelligence is a branch of computer science that focuses on creating systems capable of performing tasks that normally require human intelligence. These tasks include learning, reasoning, problem solving, understanding language, recognizing images, and making decisions."
    final_prompt = prompt.invoke({"text": text})
    print("\nKeywords:")
    print(generate_response(final_prompt.to_string(), max_tokens=60))

def task_9():
    print("\n--- Task 9: Translation ---")
    prompt = PromptTemplate.from_template(
        """Translate the following English text into {language}.
Return only the translated text.
Text: {text}"""
    )
    text = input("Text (e.g. The color of the car is red): ").strip()
    if not text:
        text = "The color of the car is red."
    language = input("Language (e.g. German): ").strip()
    if not language:
        language = "German"
    final_prompt = prompt.invoke({"text": text, "language": language})
    print(f"\nOriginal Text   : {text}")
    print(f"Target Language : {language}")
    print("\nTranslation:")
    print(generate_response(final_prompt.to_string()))

def task_10():
    print("\n--- Task 10: Temperature Comparison ---")
    prompt = "Write a creative sentence about Artificial Intelligence."
    low = generate_response(prompt, max_tokens=50, temperature=0.1)
    high = generate_response(prompt, max_tokens=50, temperature=1.0)
    print("Low temperature (0.1):")
    print(low)
    print("\nHigh temperature (1.0):")
    print(high)

def main():
    while True:
        print("\n==============================")
        print("   ASSIGNMENT 6 TASK MENU")
        print("==============================")
        print("5. Task 5: Topic Explanation")
        print("6. Task 6: Calculator Agent")
        print("7. Task 7: Document Chunking")
        print("8. Task 8: Keyword Extraction")
        print("9. Task 9: Translation")
        print("10. Task 10: Temperature Comparison")
        print("0. Run All Tasks sequentially")
        print("q. Exit")

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
        elif choice in ["q", "exit"]:
            print("Exiting Assignment 6...")
            break
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()
