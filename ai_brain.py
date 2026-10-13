import os
import inspect
import datetime
import typing

import ollama
from google import genai
from google.genai import types

import system_controls as sc

SYSTEM_PROMPT = (
    "You are Alfred, a voice assistant running on the user's Windows PC. "
    "Use your tools whenever they fit the request, including playing music, "
    "reading news, opening websites and controlling the system. "
    "Your replies are spoken aloud, so answer in 1 to 2 short, natural sentences "
    "with no markdown, asterisks, lists or emojis. "
    "When reading news, read the headlines briefly. "
    "If a tool says an action was cancelled, tell the user it was cancelled. "
    "When the user shares something worth remembering, save it with remember_fact. "
    "The user's words come from speech recognition and may contain mistakes. "
    "Only use a tool when the request clearly asks for that action. "
    "If a request is garbled, incomplete or doesn't make sense, do not guess and do not "
    "use any tool; briefly ask the user to repeat it instead."
)

TOOLS = [
    sc.play_youtube,
    sc.get_top_headlines,
    sc.open_website,
    sc.lock_pc,
    sc.mute_volume,
    sc.set_volume_percent,
    sc.change_volume_by,
    sc.take_screenshot,
    sc.write_note,
    sc.get_clipboard,
    sc.remember_fact,
    sc.recall_facts,
    sc.forget_fact,
]

MAX_TOOL_ROUNDS = 5  # Safety limit on tool calls per command for the local model


def build_instruction():
    """System prompt plus today's date and saved memories."""
    today = datetime.date.today().strftime("%A, %d %B %Y")
    instruction = f"{SYSTEM_PROMPT}\nToday is {today}."
    facts = sc.load_facts()
    if facts:
        instruction += "\nThings you remember about the user:\n" + "\n".join(
            f"- {fact}" for fact in facts
        )
    return instruction


def clean_reply(text):
    """Removes formatting characters that sound wrong when spoken."""
    for char in "*#`_":
        text = (text or "").replace(char, "")
    return " ".join(text.split())


def run_tool(tool_map, name, args):
    """Runs a tool by name, converting argument types (models sometimes send '30' instead of 30)."""
    func = tool_map.get(name)
    if func is None:
        return f"Error: there is no tool called {name}."
    params = inspect.signature(func).parameters
    hints = typing.get_type_hints(func)
    clean_args = {}
    for key, value in (args or {}).items():
        if key not in params:
            continue
        kind = hints.get(key)
        try:
            if kind is int:
                value = int(float(value))
            elif kind is float:
                value = float(value)
            elif kind is str:
                value = str(value)
        except (TypeError, ValueError):
            pass
        clean_args[key] = value
    try:
        return func(**clean_args)
    except Exception as e:
        return f"Error while running {name}: {e}"


class GeminiBrain:
    """Cloud brain: Google Gemini with automatic function calling."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

        self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.label = f"gemini ({self.model})"
        self.instruction = build_instruction()
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=30_000,  # Milliseconds (30 seconds)
                retry_options=types.HttpRetryOptions(
                    attempts=4,
                    initial_delay=1.0,
                    http_status_codes=[429, 500, 503, 504],
                ),
            ),
        )
        self.chat = self.client.chats.create(model=self.model, config=self._config())

    def _config(self, run_tools=True):
        settings = dict(system_instruction=self.instruction, tools=TOOLS, temperature=0.2)
        if not run_tools:
            # Gemini only says which tool it would call; nothing is executed
            settings["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
        return types.GenerateContentConfig(**settings)

    def process_input(self, user_input):
        print("[Alfred is thinking...]")
        try:
            response = self.chat.send_message(user_input)
            return clean_reply(response.text) or "Done."
        except Exception as e:
            print(f"[AI error]: {e}")
            if getattr(e, "code", None) == 429:
                return "I've used up my AI quota for now. Please try again later or switch to another model."
            return "Sorry, I couldn't reach my AI service. Please try again."

    def choose_tool(self, text):
        """For evaluation: returns (tool_name or None, args) without running anything."""
        response = self.client.models.generate_content(
            model=self.model, contents=text, config=self._config(run_tools=False)
        )
        calls = response.function_calls or []
        if not calls:
            return None, {}
        return calls[0].name, dict(calls[0].args or {})


class LocalBrain:
    """Local brain: a model running on this PC through Ollama."""

    def __init__(self):
        self.model = os.getenv("LOCAL_MODEL", "qwen2.5:3b")
        self.label = f"local ({self.model})"
        self.client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        self.instruction = build_instruction()
        self.tool_map = {func.__name__: func for func in TOOLS}
        self.messages = [{"role": "system", "content": self.instruction}]
        try:
            self.client.show(self.model)
        except Exception as e:
            raise RuntimeError(
                f"Could not load local model '{self.model}'. Make sure the Ollama app is running, "
                f"then run: ollama pull {self.model}"
            ) from e

    def _chat(self, messages):
        return self.client.chat(
            model=self.model, messages=messages, tools=TOOLS, options={"temperature": 0.2}
        )

    def process_input(self, user_input):
        print("[Alfred is thinking...]")
        self.messages.append({"role": "user", "content": user_input})
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                message = self._chat(self.messages).message
                self.messages.append(message)
                if not message.tool_calls:
                    return clean_reply(message.content) or "Done."
                for call in message.tool_calls:
                    result = run_tool(self.tool_map, call.function.name, call.function.arguments)
                    self.messages.append(
                        {"role": "tool", "content": str(result), "tool_name": call.function.name}
                    )
            return "Sorry, I couldn't finish that request."
        except Exception as e:
            print(f"[AI error]: {e}")
            return "Sorry, I couldn't reach the local AI model. Is Ollama running?"

    def choose_tool(self, text):
        """For evaluation: returns (tool_name or None, args) without running anything."""
        messages = [
            {"role": "system", "content": self.instruction},
            {"role": "user", "content": text},
        ]
        message = self._chat(messages).message
        if not message.tool_calls:
            return None, {}
        call = message.tool_calls[0]
        return call.function.name, dict(call.function.arguments or {})


def create_brain():
    """Picks the brain from the BRAIN setting in .env ('gemini' or 'local')."""
    backend = os.getenv("BRAIN", "gemini").strip().lower()
    if backend == "gemini":
        return GeminiBrain()
    if backend == "local":
        return LocalBrain()
    raise RuntimeError(f"Unknown BRAIN '{backend}' in .env. Use 'gemini' or 'local'.")