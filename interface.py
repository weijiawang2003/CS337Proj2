"""
interface.py

Terminal-based conversational interface for the recipe parser.
Extra credit:
- Optional speech-to-text input using the microphone (speech_recognition).
- More flexible language understanding (how much / how many / etc.).

Run:
    python interface.py
"""

from __future__ import annotations

from typing import Optional
import string
import re

from recipe_api import parse_recipe_from_url, Recipe, Step

# Optional STT imports
try:
    import speech_recognition as sr
except ImportError:
    sr = None


class RecipeBot:
    def __init__(self, use_speech: bool = False):
        self.recipe: Optional[Recipe] = None
        self.current_step_idx: int = 0  # index in recipe.steps
        self.use_speech = use_speech and (sr is not None)

        if use_speech and sr is None:
            print("Bot: speech_recognition is not installed; falling back to text input.")
            self.use_speech = False

    # -------------------------
    # Utility: normalization
    # -------------------------

    @staticmethod
    def normalize(text: str) -> str:
        """
        Lowercase, remove basic punctuation, collapse whitespace.
        Helps match patterns like 'how many' / 'how much' / etc.
        """
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        text = " ".join(text.split())
        return text

    # -------------------------
    # Main loop
    # -------------------------

    def run(self) -> None:
        print("Bot: Hi! I can walk you through a recipe from AllRecipes.com.")
        if self.use_speech:
            print("Bot: Speech input is ENABLED. Say 'quit' to exit.")
        else:
            print("Bot: Speech input is DISABLED. Type 'quit' to exit.")

        print("Bot: Please paste or say a recipe URL to get started.")

        while True:
            user = self.get_user_input()
            if user is None:
                # speech recognition failed; just keep looping
                continue

            norm = self.normalize(user)
            if norm in ["quit", "exit", "q"]:
                print("Bot: Goodbye!")
                break

            response = self.handle_input(user)
            print(f"Bot: {response}")

    def get_user_input(self) -> Optional[str]:
        """
        Get user input either from microphone (STT) or keyboard.
        Returns recognized text or None on STT failure.
        """
        if not self.use_speech:
            return input("User: ").strip()

        # Speech mode
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("User (speak): ", end="", flush=True)
            audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print(text)  # echo recognized text
            return text.strip()
        except sr.UnknownValueError:
            print("\nBot: Sorry, I didn't catch that. Please repeat.")
            return None
        except sr.RequestError as e:
            print(f"\nBot: STT service error ({e}). Falling back to keyboard input.")
            self.use_speech = False
            return input("User: ").strip()

    # -------------------------
    # Input handling
    # -------------------------

    def handle_input(self, user: str) -> str:
        raw = user.strip()
        norm = self.normalize(raw)

        # 1. Load recipe if a URL is given
        if raw.startswith("http"):
            return self.load_recipe(raw)

        # If we don't have a recipe yet, force the user to provide URL
        if self.recipe is None:
            if "allrecipes" in norm:
                # If they said "allrecipes dot com slash ..." etc. this is harder,
                # but for now we assume they either paste or dictate a proper URL.
                url = raw
                if not url.startswith("http"):
                    url = "https://" + url
                return self.load_recipe(url)
            return "Please paste or say an AllRecipes.com URL first."

        # At this point, we have a recipe loaded.

        # 2. High-level choices after loading
        if norm in ["1", "ingredients", "ingredient list", "show me the ingredients list",
                    "show ingredients", "go over ingredients"]:
            return self.show_ingredients()

        if norm in ["2", "steps", "go over steps", "start steps", "show steps"]:
            self.current_step_idx = 0
            return self.show_current_step()

        # 3. Navigation commands (more flexible)
        if self.is_next_command(norm):
            return self.next_step()

        if self.is_back_command(norm):
            return self.prev_step()

        if self.is_repeat_command(norm):
            return self.show_current_step()

        if "first step" in norm or "go to step one" in norm or "go to the first step" in norm:
            self.current_step_idx = 0
            return self.show_current_step()

        # 4. Time / temperature / quantity questions (more flexible)
        if self.is_time_question(norm):
            return self.answer_time_question()

        if self.is_temp_question(norm):
            return self.answer_temp_question()

        if self.is_quantity_question(norm):
            return self.answer_quantity_question(raw)

        # 5. Clarification: "what is X" (simple external search)
        if norm.startswith("what is "):
            query = norm[len("what is "):].strip().replace(" ", "+")
            return f"https://www.google.com/search?q=what+is+{query}"

        # 6. Procedure: "how do I X" / "how to X"
        if norm.startswith("how do i "):
            query = norm[len("how do i "):].strip().replace(" ", "+")
            return f"https://www.youtube.com/results?search_query=how+to+{query}"

        if norm.startswith("how to "):
            query = norm[len("how to "):].strip().replace(" ", "+")
            return f"https://www.youtube.com/results?search_query=how+to+{query}"

        # Vague "How do I do that?"
        if "how do i do that" in norm or "how do i do this" in norm or "how do i do it" in norm:
            return self.answer_vague_how_to()

        # Fallback
        return ("I didn't quite catch that.\n"
                "You can try commands like:\n"
                "- '1' or 'show me the ingredients list'\n"
                "- '2' or 'go over steps'\n"
                "- 'next step', 'go to the next step', 'continue'\n"
                "- 'go back one step', 'previous step'\n"
                "- 'repeat that', 'say that again'\n"
                "- 'How long do I bake it for?'\n"
                "- 'What temperature should the oven be?'\n"
                "- 'How many eggs do I need?', 'How much salt do I need?'\n"
                "- 'What is a whisk?'\n"
                "- 'How do I knead the dough?'")

    # -------------------------
    # Small intent helpers
    # -------------------------

    @staticmethod
    def is_next_command(norm: str) -> bool:
        patterns = [
            "next step", "go to the next step", "go to next step",
            "next", "continue", "what's next", "whats next", "what is next"
        ]
        return any(p in norm for p in patterns)

    @staticmethod
    def is_back_command(norm: str) -> bool:
        patterns = [
            "go back one step", "go back a step", "go back",
            "previous step", "previous", "back"
        ]
        return any(p in norm for p in patterns)

    @staticmethod
    def is_repeat_command(norm: str) -> bool:
        patterns = [
            "repeat please", "repeat that", "say that again", "again", "repeat"
        ]
        return any(p in norm for p in patterns)

    @staticmethod
    def is_time_question(norm: str) -> bool:
        # Handle variations like:
        # - "how long do I bake it for"
        # - "for how long should it cook"
        # - "what is the cooking time"
        if "how long" in norm or "for how long" in norm:
            return True
        if "cooking time" in norm or "baking time" in norm:
            return True
        if "time" in norm and ("cook" in norm or "bake" in norm or "simmer" in norm):
            return True
        return False

    @staticmethod
    def is_temp_question(norm: str) -> bool:
        # Variations:
        # - "what temperature should the oven be"
        # - "what temp do I bake at"
        # - "how hot should the oven be"
        if "temperature" in norm or "temp" in norm:
            if "oven" in norm or "bake" in norm:
                return True
        if "how hot" in norm and "oven" in norm:
            return True
        if "bake at" in norm or "baked at" in norm:
            return True
        return False

    @staticmethod
    def is_quantity_question(norm: str) -> bool:
        # Now handles both "how much" and "how many", plus some variants
        if "how much" in norm or "how many" in norm:
            return True
        if "amount of" in norm or "quantity of" in norm:
            return True
        return False

    # -------------------------
    # Recipe loading & display
    # -------------------------

    def load_recipe(self, url: str) -> str:
        try:
            self.recipe = parse_recipe_from_url(url)
            self.current_step_idx = 0
            return (f"Alright. So let's start working with \"{self.recipe.title}\".\n"
                    "What do you want to do?\n"
                    "[1] Go over ingredients list\n"
                    "[2] Go over recipe steps.")
        except Exception as e:
            return f"Something went wrong loading that recipe: {e}"

    def show_ingredients(self) -> str:
        assert self.recipe is not None
        lines = [f'Here are the ingredients for "{self.recipe.title}":']
        for ing in self.recipe.ingredients:
            q = f"{ing.quantity:g} " if ing.quantity is not None else ""
            unit = f"{ing.unit} " if ing.unit else ""
            desc = f"{ing.descriptor} " if ing.descriptor else ""
            prep = f", {ing.preparation}" if ing.preparation else ""
            lines.append(f"- {q}{unit}{desc}{ing.name}{prep}")
        return "\n".join(lines)

    # -------------------------
    # Step navigation
    # -------------------------

    def get_current_step(self) -> Step:
        assert self.recipe is not None
        return self.recipe.steps[self.current_step_idx]

    def show_current_step(self) -> str:
        step = self.get_current_step()
        ordinal = self.ordinal(step.step_number)
        return f"The {ordinal} step is: {step.description}"

    def next_step(self) -> str:
        assert self.recipe is not None
        if self.current_step_idx + 1 >= len(self.recipe.steps):
            return "You are at the last step."
        self.current_step_idx += 1
        return self.show_current_step()

    def prev_step(self) -> str:
        if self.current_step_idx == 0:
            return "You are at the first step."
            # Already at beginning
        self.current_step_idx -= 1
        return self.show_current_step()

    @staticmethod
    def ordinal(n: int) -> str:
        """Return ordinal string for a positive integer (1 -> '1st')."""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    # -------------------------
    # Parameter questions
    # -------------------------

    def answer_time_question(self) -> str:
        step = self.get_current_step()

        # 1. Check current step
        if step.time.get("duration"):
            return f"In this step, the time is {step.time['duration']}."

        # 2. Check any step that mentions time + a similar action
        assert self.recipe is not None
        verbs = set(step.methods)
        for s in self.recipe.steps:
            if s.time.get("duration"):
                if verbs & set(s.methods):
                    return (f"For {', '.join(verbs)} earlier, "
                            f"the recipe says: {s.time['duration']}.")
        # 3. Generic fallback
        for s in self.recipe.steps:
            if s.time.get("duration"):
                return f"Earlier, the recipe says: {s.time['duration']}."
        return "The recipe does not specify a clear time here."

    def answer_temp_question(self) -> str:
        step = self.get_current_step()

        # 1. Current step
        if "oven" in step.temperature:
            return f"In this step, the oven should be at {step.temperature['oven']}."

        # 2. Context from previous preheat
        if "oven_temperature" in step.context:
            return f"The oven should be at {step.context['oven_temperature']}."

        # 3. Any step with oven temperature
        assert self.recipe is not None
        for s in self.recipe.steps:
            if "oven" in s.temperature:
                return f"The recipe uses an oven temperature of {s.temperature['oven']}."
        return "I couldn't find an oven temperature in the recipe."

    def answer_quantity_question(self, user: str) -> str:
        assert self.recipe is not None
        norm = self.normalize(user)

        # Try to identify all ingredient names mentioned in the question
        mentioned = []
        for ing in self.recipe.ingredients:
            name = ing.name.lower()
            if not name:
                continue
            # allow partial matches but word-boundary-based
            if re.search(r"\b" + re.escape(name) + r"\b", norm):
                mentioned.append(ing)

        # If they mention specific ingredient(s)
        if mentioned:
            lines = []
            for ing in mentioned:
                q = f"{ing.quantity:g} " if ing.quantity is not None else ""
                unit = f"{ing.unit} " if ing.unit else ""
                lines.append(f"- {q}{unit}{ing.name}")
            if len(lines) == 1:
                return f"You need {lines[0][2:]}."
            else:
                return "Here are the quantities:\n" + "\n".join(lines)

        # Vague "How much/how many of that/it/this?"
        step = self.get_current_step()
        if step.ingredients:
            # Try all ingredients in this step
            lines = []
            for name in step.ingredients:
                for ing in self.recipe.ingredients:
                    if ing.name.lower() == name:
                        q = f"{ing.quantity:g} " if ing.quantity is not None else ""
                        unit = f"{ing.unit} " if ing.unit else ""
                        lines.append(f"- {q}{unit}{ing.name}")
            if lines:
                if len(lines) == 1:
                    return f"For that, you need {lines[0][2:]}."
                else:
                    return "For this step, the relevant quantities are:\n" + "\n".join(lines)

        return "I'm not sure which ingredient you mean."

    # -------------------------
    # Vague procedure questions
    # -------------------------

    def answer_vague_how_to(self) -> str:
        step = self.get_current_step()
        if step.action:
            query = f"how to {step.action}".replace(" ", "+")
            return f"https://www.youtube.com/results?search_query={query}"
        # fallback: use any method in this step
        if step.methods:
            query = f"how to {step.methods[0]}".replace(" ", "+")
            return f"https://www.youtube.com/results?search_query={query}"
        return "I'm not sure what 'that' refers to in this step."


if __name__ == "__main__":
    # Ask user whether to enable speech input for this run
    use_speech_choice = input("Enable speech input? (y/n): ").strip().lower()
    use_speech = use_speech_choice.startswith("y")
    bot = RecipeBot(use_speech=use_speech)
    bot.run()
