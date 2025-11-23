"""
recipe_api.py

Provides:
- Data classes: Ingredient, Step, Recipe
- Main function: parse_recipe_from_url(url) -> Recipe

Requires:
    pip install requests beautifulsoup4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import json
import re

import requests
from bs4 import BeautifulSoup


# -------------------------
# Data Classes
# -------------------------

@dataclass
class Ingredient:
    raw: str                    # original text line
    name: str
    quantity: Optional[float]   # parsed numeric quantity (if possible)
    unit: Optional[str]         # cup, tsp, etc.
    descriptor: Optional[str]   # fresh, large, lean, etc.
    preparation: Optional[str]  # finely chopped, shredded, etc.


@dataclass
class Step:
    step_number: int
    description: str            # atomic step text
    ingredients: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    time: Dict[str, str] = field(default_factory=dict)
    temperature: Dict[str, str] = field(default_factory=dict)
    action: Optional[str] = None        # main verb / method
    objects: List[str] = field(default_factory=list)  # ingredients acted on
    modifiers: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, str] = field(default_factory=dict)  # carried info (e.g. oven temp)


@dataclass
class Recipe:
    title: str
    url: str
    ingredients: List[Ingredient]
    tools: List[str]
    methods: List[str]
    steps: List[Step]


# -------------------------
# Lexicons
# -------------------------

UNITS = [
    "teaspoon", "teaspoons", "tsp", "tablespoon", "tablespoons", "tbsp",
    "cup", "cups", "pint", "pints", "quart", "quarts",
    "pound", "pounds", "lb", "lbs",
    "ounce", "ounces", "oz",
    "clove", "cloves",
    "pinch", "dash",
    "slice", "slices",
    "can", "cans",
    "package", "packages"
]

DESCRIPTORS = [
    "fresh", "dried", "lean", "boneless", "skinless", "extra-virgin",
    "large", "small", "medium",
    "minced", "chopped", "shredded", "grated"
]

TOOLS = [
    "oven", "pan", "skillet", "baking sheet", "baking dish", "dish",
    "pot", "saucepan", "whisk", "bowl", "knife", "spatula", "grater",
    "colander", "mixing bowl", "foil", "grill"
]

PRIMARY_METHODS = [
    "bake", "boil", "simmer", "saute", "sauté", "fry", "grill",
    "broil", "roast", "steam", "poach"
]

OTHER_METHODS = [
    "chop", "slice", "mince", "stir", "mix", "whisk", "beat",
    "grate", "sprinkle", "drain", "pour", "spread", "layer",
    "preheat", "grease", "cover", "uncover"
]


# -------------------------
# HTML Fetching & Base Parsing
# -------------------------

def fetch_html(url: str) -> str:
    """Fetch page HTML from a URL."""
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text


def parse_allrecipes_basic(html: str) -> Dict[str, object]:
    """
    Extract title, raw ingredients, and raw steps from an AllRecipes page
    using JSON-LD embedded in the HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    json_ld = soup.find("script", type="application/ld+json")
    if json_ld is None or not json_ld.string:
        raise ValueError("Could not find recipe JSON-LD on page.")

    data = json.loads(json_ld.string)

    # Sometimes it's a list, sometimes a single dict
    if isinstance(data, list):
        recipe_obj = None
        for item in data:
            # item["@type"] can be "Recipe" or ["Thing","Recipe"] etc.
            t = item.get("@type")
            if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
                recipe_obj = item
                break
        if recipe_obj is None:
            raise ValueError("JSON-LD does not contain a Recipe object.")
        data = recipe_obj

    title = data.get("name", "Unknown recipe")
    raw_ingredients = data.get("recipeIngredient", [])
    instructions = data.get("recipeInstructions", [])

    steps_raw: List[str] = []
    for inst in instructions:
        if isinstance(inst, dict):
            text = inst.get("text", "")
            if text:
                steps_raw.append(text.strip())
        elif isinstance(inst, str):
            if inst.strip():
                steps_raw.append(inst.strip())

    return {
        "title": title,
        "ingredients_raw": raw_ingredients,
        "steps_raw": steps_raw,
    }


# -------------------------
# Ingredient Parsing
# -------------------------

def parse_quantity(token: str) -> Optional[float]:
    """
    Parse token as quantity. Handles:
    - "1"
    - "1/2"
    - "1-1/2"
    Returns float or None if not parseable.
    """
    token = token.strip()
    # direct float
    try:
        return float(token)
    except ValueError:
        pass

    # fraction like "1/2"
    if "/" in token and "-" not in token:
        parts = token.split("/")
        if len(parts) == 2:
            num, den = parts
            try:
                return float(num) / float(den)
            except ValueError:
                return None

    # mixed fraction like "1-1/2"
    if "-" in token:
        parts = token.split("-")
        if len(parts) == 2:
            base_str, frac_str = parts
            try:
                base = float(base_str)
            except ValueError:
                base = 0.0
            frac = parse_quantity(frac_str)
            if frac is not None:
                return base + frac

    return None


def parse_ingredient_line(line: str) -> Ingredient:
    """
    Rules-based parsing of ingredient string into structured fields.
    This is intentionally approximate / "good enough".
    """
    raw = line.strip()
    tokens = raw.split()
    quantity: Optional[float] = None
    unit: Optional[str] = None
    descriptor_tokens: List[str] = []
    name_tokens: List[str] = []
    preparation: Optional[str] = None

    # quantity: first token
    if tokens:
        q = parse_quantity(tokens[0])
        if q is not None:
            quantity = q
            tokens = tokens[1:]

    # unit: next token if in UNITS
    if tokens and tokens[0].lower() in UNITS:
        unit = tokens[0].lower()
        tokens = tokens[1:]

    # split by comma to separate preparation
    before_comma, *after_comma = " ".join(tokens).split(",", 1)
    if after_comma:
        prep_str = after_comma[0].strip()
        if prep_str:
            preparation = prep_str

    # descriptors vs name
    for tok in before_comma.split():
        if tok.lower() in DESCRIPTORS:
            descriptor_tokens.append(tok.lower())
        else:
            name_tokens.append(tok)

    descriptor = " ".join(descriptor_tokens) if descriptor_tokens else None
    name = " ".join(name_tokens).strip()

    return Ingredient(
        raw=raw,
        name=name,
        quantity=quantity,
        unit=unit,
        descriptor=descriptor,
        preparation=preparation,
    )


def parse_ingredients(raw_ingredients: List[str]) -> List[Ingredient]:
    return [parse_ingredient_line(line) for line in raw_ingredients]


# -------------------------
# Step Parsing & Annotation
# -------------------------

def split_into_atomic_steps(step_text: str) -> List[str]:
    """
    Split a raw instruction into smaller atomic clauses.
    Here we use a simple heuristic: split on '.' and ';'.
    You can refine this if you want extra credit.
    """
    parts = re.split(r"[.;]", step_text)
    return [p.strip() for p in parts if p.strip()]


def find_items_in_text(text: str, vocab: List[str]) -> List[str]:
    """
    Return all words/phrases from vocab that appear in text as separate words.
    """
    text_lower = text.lower()
    found: List[str] = []
    for word in vocab:
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            found.append(word)
    return found


def extract_time(text: str) -> Dict[str, str]:
    """
    Extract a simple 'duration' from text, e.g.
    "bake for 30 minutes" -> {"duration": "30 minutes"}
    """
    match = re.search(r"(\d+)\s*(minutes?|mins?|hours?|hrs?)", text, flags=re.I)
    if match:
        return {"duration": match.group(0)}
    return {}


def extract_temperature(text: str) -> Dict[str, str]:
    """
    Extract a simple oven temperature from text, e.g.
    "350 degrees F" or "350 F".
    """
    match = re.search(r"(\d+)\s*(degrees\s*)?(F|C)", text, flags=re.I)
    if match:
        return {"oven": match.group(0)}
    return {}


def build_steps(steps_raw: List[str], ingredients: List[Ingredient]) -> List[Step]:
    """
    Convert raw instruction strings into annotated Step objects.
    Also carries forward oven temperature as 'context'.
    """
    steps: List[Step] = []
    ingredient_names = [ing.name.lower() for ing in ingredients]

    current_oven_temp: Optional[str] = None
    step_counter = 1

    for raw_step in steps_raw:
        atomic_texts = split_into_atomic_steps(raw_step)

        for text in atomic_texts:
            tools = find_items_in_text(text, TOOLS)
            methods_primary = find_items_in_text(text, PRIMARY_METHODS)
            methods_other = find_items_in_text(text, OTHER_METHODS)
            methods = list(dict.fromkeys(methods_primary + methods_other))  # deduplicate

            time_info = extract_time(text)
            temp_info = extract_temperature(text)
            if "oven" in temp_info:
                current_oven_temp = temp_info["oven"]

            # find ingredient mentions
            used_ingredients: List[str] = []
            text_lower = text.lower()
            for name in ingredient_names:
                if name and re.search(r"\b" + re.escape(name) + r"\b", text_lower):
                    used_ingredients.append(name)

            action = methods[0] if methods else None

            context: Dict[str, str] = {}
            if current_oven_temp:
                context["oven_temperature"] = current_oven_temp

            step = Step(
                step_number=step_counter,
                description=text,
                ingredients=used_ingredients,
                tools=tools,
                methods=methods,
                time=time_info,
                temperature=temp_info,
                action=action,
                objects=used_ingredients,
                modifiers={"tools": ", ".join(tools)} if tools else {},
                context=context,
            )
            steps.append(step)
            step_counter += 1

    return steps


def collect_recipe_tools_and_methods(steps: List[Step]) -> Tuple[List[str], List[str]]:
    tools_set = set()
    methods_set = set()
    for s in steps:
        tools_set.update(s.tools)
        methods_set.update(s.methods)
    return sorted(tools_set), sorted(methods_set)


# -------------------------
# Public API
# -------------------------

def parse_recipe_from_url(url: str) -> Recipe:
    """
    Main entry point for the rest of the project.
    Given a URL (AllRecipes.com), returns a fully parsed Recipe object.
    """
    html = fetch_html(url)
    base = parse_allrecipes_basic(html)

    ingredients = parse_ingredients(base["ingredients_raw"])
    steps = build_steps(base["steps_raw"], ingredients)
    tools, methods = collect_recipe_tools_and_methods(steps)

    return Recipe(
        title=base["title"],
        url=url,
        ingredients=ingredients,
        tools=tools,
        methods=methods,
        steps=steps,
    )


# Simple manual test (run this file directly)
if __name__ == "__main__":
    test_url = input("Enter an AllRecipes URL: ").strip()
    recipe = parse_recipe_from_url(test_url)
    print("Title:", recipe.title)
    print("Number of ingredients:", len(recipe.ingredients))
    print("Number of steps:", len(recipe.steps))
