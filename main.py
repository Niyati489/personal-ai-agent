
import ast
import json
import operator
import os
import re
from datetime import datetime, timedelta

from google import genai
from google.genai import types
from dotenv import load_dotenv


# -------------------------------
# 1. CALCULATOR TOOL
# -------------------------------

def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""

    print("[TOOL] Calculator called")

    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow
    }

    if len(expression) > 200:
        raise ValueError("Expression too long")

    tree = ast.parse(expression, mode="eval")

    if len(list(ast.walk(tree))) > 50:
        raise ValueError("Expression too complex")

    def solve(node):

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 10**12:
                raise ValueError("Number too large")
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left = solve(node.left)
            right = solve(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large")

            return operations[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = solve(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value

        raise ValueError("Unsupported mathematical expression")

    return str(solve(tree.body))


# -------------------------------
# 2. DATE AND TIME TOOLS
# -------------------------------

def get_current_datetime() -> str:
    """Get the current local date and time."""

    print("[TOOL] Date and time called")

    return datetime.now().strftime("%d-%m-%Y %I:%M %p")


def add_days(date_time: str, days: int) -> str:
    """Add days to a given date and time."""

    print("[TOOL] Add days called")

    current = datetime.strptime(
        date_time, "%d-%m-%Y %I:%M %p"
    )

    new_date = current + timedelta(days=days)

    return new_date.strftime("%d-%m-%Y %I:%M %p")


# -------------------------------
# 3. LOCAL ROUTER
# -------------------------------

def handle_locally(user_text: str):
    """Handle simple maths and date/time questions without Gemini."""

    text = user_text.lower().strip()

    # Handle future date/time questions
    match = re.search(
        r"\b(?:in|after)\s+(\d+)\s+(seconds?|minutes?|hours?|days?|weeks?)\b",
        text
    )

    if not match:
        match = re.search(
            r"\b(\d+)\s+(seconds?|minutes?|hours?|days?|weeks?)\s+"
            r"(?:from now|later|from today)\b",
            text
        )

    if match:
        amount = int(match.group(1))
        unit = match.group(2).rstrip("s") + "s"

        future = datetime.now() + timedelta(**{unit: amount})

        print("[LOCAL] Python handled date/time")

        return future.strftime("%d-%m-%Y %I:%M %p")

    # Handle current date/time questions
    if re.search(
        r"\b(current date|current time|today's date|today's time|"
        r"what time is it|what is the date|date and time right now)\b",
        text
    ):
        print("[LOCAL] Python handled date/time")

        return get_current_datetime()

    # Convert natural language maths into Python expression
    expression = text

    expression = re.sub(
        r"\b(what is|what's|calculate|compute|solve|please)\b",
        "",
        expression
    )

    replacements = {
        "multiplied by": "*",
        "multiply by": "*",
        "divided by": "/",
        "divide by": "/",
        "times": "*",
        "into": "*",
        "plus": "+",
        "minus": "-"
    }

    for word, symbol in replacements.items():
        expression = expression.replace(word, symbol)

    expression = expression.replace("×", "*").replace("÷", "/")

    expression = re.sub(
        r"(?<=\d)\s*[x]\s*(?=\d)", "*", expression
    )

    expression = expression.replace("^", "**").replace("?", "").strip()

    # Only accept expressions containing numbers and arithmetic symbols
    if (
        re.fullmatch(r"[\d\s()+\-*/.]+", expression)
        and re.search(r"\d", expression)
        and re.search(r"[+*/-]", expression)
    ):
        try:
            result = calculate(expression)

            print("[LOCAL] Python handled calculation")

            return result

        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
            return "Sorry, I couldn't calculate that expression."

    return None


# -------------------------------
# 4. LOAD API KEY
# -------------------------------

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)


# -------------------------------
# 5. LOAD LONG-TERM MEMORY
# -------------------------------

if os.path.exists("memory.json"):
    try:
        with open("memory.json", "r", encoding="utf-8") as file:
            memory = json.load(file)

        if not isinstance(memory, dict):
            memory = {}

    except (json.JSONDecodeError, OSError):
        memory = {}
else:
    memory = {}


# -------------------------------
# 6. CREATE GEMINI CHAT
# -------------------------------

chat = client.chats.create(
    model="gemini-3.5-flash"
)

tools = [
    calculate,
    get_current_datetime,
    add_days
]

print("AI Agent Started!")
print("Type 'exit' to stop.\n")


# -------------------------------
# 7. MAIN AGENT LOOP
# -------------------------------

while True:

    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        print("AI: Goodbye!")
        break

    if not user_input:
        continue

    # First check whether Python can handle the task locally
    local_answer = handle_locally(user_input)

    if local_answer is not None:
        print("AI:", local_answer)
        continue

    # Otherwise send the question to Gemini
    prompt = f"""
    You are a helpful personal AI assistant.

    Saved user memory:
    {json.dumps(memory, ensure_ascii=False)}

    User message:
    {user_input}

    Instructions:
    1. Give a natural and helpful reply.
    2. Save useful long-term personal facts and preferences.
    3. Update old facts when the user corrects them.
    4. Preserve existing memory if nothing needs updating.
    5. Do not save temporary or irrelevant details.
    6. Use available tools when they are genuinely needed.
    7. You may use multiple tools if the task requires them.

    Return valid JSON with exactly these keys:
    "reply": your response
    "memory": the complete updated memory dictionary

    Return JSON only.
    """

    try:

        response = chat.send_message(
            prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=5
                )
            )
        )

        if not response.text:
            print("AI: Empty response received.")
            continue

        result = json.loads(response.text)

        reply = result.get("reply", "I couldn't generate a reply.")

        print("AI:", reply)

        # Update memory without accidentally deleting old keys
        new_memory = result.get("memory", {})

        if isinstance(new_memory, dict):
            memory.update(new_memory)

        # Save memory
        with open("memory.json", "w", encoding="utf-8") as file:
            json.dump(memory, file, indent=4, ensure_ascii=False)

    except json.JSONDecodeError:
        print("AI: Could not process the response properly.")

    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("AI: Gemini daily quota exhausted. Try again after quota reset.")
        else:
            print(f"AI Error ({type(e).__name__}): {e}")
