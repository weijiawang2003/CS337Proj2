from __future__ import annotations

from typing import Optional, Any
import string
import re
from urllib.parse import quote

from recipe_api import parse_recipe_from_url, Recipe, Step


try:
    import speech_recognition as sr
except ImportError:
    sr = None

EXIT_COMMANDS = ["quit", "exit", "q"]
QUIT_MESSAGE = "Bot: Goodbye!"




class RecipeBot:
    def __init__(self, use_speech: bool = False):
        self.recipe: Optional[Recipe] = None
        self.current_step_idx: int = 0  
        self.use_speech = use_speech and (sr is not None)
        self.recognizer: Optional[Any] = None 
        if use_speech and sr is None:
            print("Bot: speech_recognition is not installed; falling back to text input.")
            self.use_speech = False
        elif use_speech:
            # Initialize recognizer once for reuse
            self.recognizer = sr.Recognizer()




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
                continue
            


            if not user:  
                
                continue

            norm = self.normalize(user)
            if norm in EXIT_COMMANDS:
                print(QUIT_MESSAGE)
                break

            response = self.handle_input(user)
            print(f"Bot: {response}")

    def get_user_input(self) -> Optional[str]:
        """
        Get user input either from microphone (STT) or keyboard.
        Returns recognized text or None on STT failure.
        """
        if not self.use_speech:
            try:
                return input("User: ").strip()
            except KeyboardInterrupt:
                print(f"\n{QUIT_MESSAGE}")
                return "quit"

        # Speech mode
        if self.recognizer is None:
            self.recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                print("User (speak): ", end="", flush=True)
                audio = self.recognizer.listen(source)

            try:
                text = self.recognizer.recognize_google(audio)
                print(text)  # echo recognized text
                return text.strip()
            except sr.UnknownValueError:
                print("\nBot: Sorry, I didn't catch that. Please repeat.")
                return None
            except sr.RequestError as e:
                print(f"\nBot: STT service error ({e}). Falling back to keyboard input.")
                self.use_speech = False
                self.recognizer = None
                return input("User: ").strip()
        except KeyboardInterrupt:
            print(f"\n{QUIT_MESSAGE}")
            return "quit"




    def handle_input(self, user: str) -> str:
        raw = user.strip()
        norm = self.normalize(raw)


        if raw.startswith("http"):
            return self.load_recipe(raw)

        if self.recipe is None:
            if "allrecipes" in norm:

                url = raw
                if not url.startswith("http"):
                    url = "https://" + url
                return self.load_recipe(url)
            return "Please paste or say an AllRecipes.com URL first."



        if norm in ["1", "ingredients", "ingredient list", "show me the ingredients list",
                    "show ingredients", "go over ingredients","Go over ingredients list"]:
            return self.show_ingredients()

        if norm in ["2", "steps", "go over steps", "start steps", "show steps","Go over recipe steps"]:
            self.current_step_idx = 0
            return self.show_current_step()


        if self.is_next_command(norm):
            return self.next_step()

        if self.is_back_command(norm):
            return self.prev_step()

        if self.is_repeat_command(norm):
            return self.show_current_step()


        if "first step" in norm or "go to step one" in norm or "go to the first step" in norm:
            self.current_step_idx = 0
            return self.show_current_step()



        if self.is_time_question(norm):
            return self.answer_time_question()

        if self.is_temp_question(norm):
            return self.answer_temp_question()

        if self.is_quantity_question(norm):
            return self.answer_quantity_question(raw)

        if norm.startswith("what is "):
            query = norm[len("what is "):].strip()
            return f"https://www.google.com/search?q=what+is+{quote(query)}"
        

        if norm.startswith("how do i "):
            query = norm[len("how do i "):].strip()
            return f"https://www.youtube.com/results?search_query=how+to+{quote(query)}"

        if norm.startswith("how to "):
            query = norm[len("how to "):].strip()
            return f"https://www.youtube.com/results?search_query=how+to+{quote(query)}"


        if "how do i do that" in norm or "how do i do this" in norm or "how do i do it" in norm:
            return self.answer_vague_how_to()



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
        if "how long" in norm or "for how long" in norm:
            return True
        if "cooking time" in norm or "baking time" in norm:
            return True
        if "time" in norm and ("cook" in norm or "bake" in norm or "simmer" in norm):
            return True
        return False



    @staticmethod
    def is_temp_question(norm: str) -> bool:
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



    @staticmethod
    def format_ingredient(ing: Ingredient) -> str:
        """Format an ingredient for display."""
        q = f"{ing.quantity:g} " if ing.quantity is not None else ""
        unit = f"{ing.unit} " if ing.unit else ""
        desc = f"{ing.descriptor} " if ing.descriptor else ""
        prep = f", {ing.preparation}" if ing.preparation else ""
        return f"{q}{unit}{desc}{ing.name}{prep}"

    def load_recipe(self, url: str) -> str:
        """Load a recipe from the given URL."""
        if not url or not url.strip():
            return "Please provide a valid URL."
        
        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            return "Please provide a valid URL starting with http:// or https://"
        
        try:
            self.recipe = parse_recipe_from_url(url)
            self.current_step_idx = 0
            return (f"Alright. So let's start working with \"{self.recipe.title}\".\n"
                    "What do you want to do?\n"
                    "[1] Go over ingredients list\n"
                    "[2] Go over recipe steps.")
        except ValueError as e:
            return f"Could not parse the recipe from that URL: {e}"
        except Exception as e:
            return f"Something went wrong loading that recipe: {e}"

    def show_ingredients(self) -> str:
        """Display all ingredients for the current recipe."""
        if self.recipe is None:
            return "No recipe loaded. Please load a recipe first."
        lines = [f'Here are the ingredients for "{self.recipe.title}":']
        for ing in self.recipe.ingredients:
            lines.append(f"- {self.format_ingredient(ing)}")
        return "\n".join(lines)




    def get_current_step(self) -> Step:
        """Get the current step, raising an error if no recipe is loaded."""
        if self.recipe is None:
            raise ValueError("No recipe loaded. Please load a recipe first.")
        if not self.recipe.steps:
            raise ValueError("Recipe has no steps.")
        if self.current_step_idx >= len(self.recipe.steps):
            raise ValueError(f"Step index {self.current_step_idx} out of range.")
        return self.recipe.steps[self.current_step_idx]

    def show_current_step(self) -> str:
        """Display the current step."""
        try:
            step = self.get_current_step()
            ordinal = self.ordinal(step.step_number)
            return f"The {ordinal} step is: {step.description}"
        except ValueError as e:
            return str(e)

    def next_step(self) -> str:
        """Move to the next step."""
        if self.recipe is None:
            return "No recipe loaded. Please load a recipe first."
        if self.current_step_idx + 1 >= len(self.recipe.steps):
            return "You are at the last step."
        self.current_step_idx += 1
        return self.show_current_step()

    def prev_step(self) -> str:
        """Go to the previous step."""
        if self.current_step_idx == 0:
            return "You are at the first step."
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



    def answer_time_question(self) -> str:
        """Answer questions about cooking time."""
        if self.recipe is None:
            return "No recipe loaded. Please load a recipe first."
        try:
            step = self.get_current_step()
        except ValueError as e:
            return str(e)


        if step.time.get("duration"):
            return f"In this step, the time is {step.time['duration']}."



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
        """Answer questions about oven temperature."""
        if self.recipe is None:
            return "No recipe loaded. Please load a recipe first."
        try:
            step = self.get_current_step()
        except ValueError as e:
            return str(e)

        if "oven" in step.temperature:
            return f"In this step, the oven should be at {step.temperature['oven']}."

        if "oven_temperature" in step.context:
            return f"The oven should be at {step.context['oven_temperature']}."

        for s in self.recipe.steps:
            if "oven" in s.temperature:
                return f"The recipe uses an oven temperature of {s.temperature['oven']}."
        return "I couldn't find an oven temperature in the recipe."

    def answer_quantity_question(self, user: str) -> str:
        """Answer questions about ingredient quantities."""
        if self.recipe is None:
            return "No recipe loaded. Please load a recipe first."
        norm = self.normalize(user)
        mentioned = []
        for ing in self.recipe.ingredients:
            name = ing.name.lower()

            if not name:
                continue
            if re.search(r"\b" + re.escape(name) + r"\b", norm):
                mentioned.append(ing)

        if mentioned:
            lines = [f"- {self.format_ingredient(ing)}" for ing in mentioned]
            if len(lines) == 1:
                return f"You need {lines[0][2:]}."
            else:
                return "Here are the quantities:\n" + "\n".join(lines)
            
        step = self.get_current_step()
        if step.ingredients:
            lines = []
            for name in step.ingredients:
                for ing in self.recipe.ingredients:
                    if ing.name.lower() == name:
                        lines.append(f"- {self.format_ingredient(ing)}")
            if lines:
                if len(lines) == 1:
                    return f"For that, you need {lines[0][2:]}."
                else:
                    return "For this step, the relevant quantities are:\n" + "\n".join(lines)

        return "I'm not sure which ingredient you mean."

    def answer_vague_how_to(self) -> str:
        """Answer vague 'how do I do that' questions."""
        step = self.get_current_step()
        if step.action:
            query = f"how to {step.action}"
            return f"https://www.youtube.com/results?search_query={quote(query)}"
        # fallback: use any method in this step
        if step.methods:
            query = f"how to {step.methods[0]}"
            return f"https://www.youtube.com/results?search_query={quote(query)}"
        return "I'm not sure what 'that' refers to in this step."


if __name__ == "__main__":
    use_speech_choice = input("Enable speech input? (y/n): ").strip().lower()
    use_speech = use_speech_choice.startswith("y")
    bot = RecipeBot(use_speech=use_speech)
    bot.run()
