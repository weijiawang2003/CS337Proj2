# CS337Proj2 - Recipe Parser & Conversational Interface

A terminal-based recipe parsing and conversational system that can parse recipes from AllRecipes.com and guide users through recipe steps via a conversational interface.

## Features

- 📝 **Recipe Parsing**: Automatically parse recipe information from AllRecipes.com URLs
- 💬 **Conversational Interface**: Browse recipe steps through natural language interaction
- 🎤 **Speech Input** (Optional): Support for speech-to-text input
- 🔍 **Smart Q&A**: Answer questions about time, temperature, quantities, etc.
- 📋 **Structured Data**: Parse ingredients, steps, tools, methods, and other information

## Requirements

- Python 3.7+
- Conda (recommended) or pip

## Installation

### 1. Create Conda Environment

```bash
# Create a new conda environment (Python 3.9)
conda create -n cs337proj2 python=3.9

# Activate the environment
conda activate cs337proj2
```

### 2. Install Dependencies

```bash
# Install dependencies using pip (recommended)
pip install -r requirements.txt

# Or use conda-forge (some packages may not be available)
conda install --file requirements.txt -c conda-forge
```

### 3. Verify Installation

```bash
# Check Python version
python --version

# Check installed packages
pip list
```

## Usage

### Basic Usage

```bash
# Run the conversational interface
python interface.py
```

### Startup Flow

1. After starting the program, the system will ask if you want to enable speech input
   - Enter `y` to enable speech input (requires microphone permissions)
   - Enter `n` to use text input

2. Paste or enter an AllRecipes.com recipe URL

3. Choose an action:
   - Enter `1` or `ingredients` to view the ingredients list
   - Enter `2` or `steps` to start browsing steps

### Common Commands

#### Navigation Commands
- `next step` / `next` / `continue` - Go to next step
- `previous step` / `back` - Go to previous step
- `repeat` / `again` - Repeat current step
- `first step` - Go back to the first step

#### Q&A Commands
- `How long do I bake it for?` - Ask about cooking time
- `What temperature should the oven be?` - Ask about oven temperature
- `How many eggs do I need?` - Ask about ingredient quantity
- `How much salt do I need?` - Ask about ingredient quantity
- `What is a whisk?` - Query tools/terms
- `How do I knead the dough?` - Query cooking methods

#### Exit
- `quit` / `exit` / `q` - Exit the program

### Direct Recipe Parsing Test

```bash
# Run API test directly
python recipe_api.py
```

## Project Structure

```
CS337Proj2/
├── recipe_api.py      # Recipe parsing API (data classes and parsing functions)
├── interface.py       # Conversational user interface
├── requirements.txt   # Python dependency list
└── README.md         # Project documentation
```

## Dependencies

Main dependencies:

- **requests** (>=2.28.0) - HTTP request library for fetching web content
- **beautifulsoup4** (>=4.11.0) - HTML parsing library for parsing recipe pages
- **speechrecognition** (>=3.10.0) - Speech recognition library (optional, for speech input functionality)

> **Note**: `speechrecognition` is an optional dependency. If you don't need speech input functionality, you can comment out this line in `requirements.txt`.

## Example

```
Bot: Hi! I can walk you through a recipe from AllRecipes.com.
Bot: Speech input is DISABLED. Type 'quit' to exit.
Bot: Please paste or say a recipe URL to get started.
User: https://www.allrecipes.com/recipe/...
Bot: Alright. So let's start working with "Chocolate Chip Cookies".
     What do you want to do?
     [1] Go over ingredients list
     [2] Go over recipe steps.
User: 1
Bot: Here are the ingredients for "Chocolate Chip Cookies":
     - 2 cups all-purpose flour
     - 1 cup butter
     ...
User: 2
Bot: The 1st step is: Preheat oven to 375 degrees F.
User: next step
Bot: The 2nd step is: Mix butter and sugar until creamy.
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure the conda environment is activated
   conda activate cs337proj2
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Speech Recognition Not Working**
   - Check microphone permissions
   - Ensure network connection is working (uses Google speech recognition service)
   - If you don't need speech functionality, select `n` at startup

3. **Unable to Parse Recipe**
   - Ensure the URL is from AllRecipes.com
   - Check network connection
   - Some page formats may not be supported

## Development Notes

### Code Modules

- **recipe_api.py**: Provides `parse_recipe_from_url()` function and data structures (`Recipe`, `Ingredient`, `Step`)
- **interface.py**: Implements `RecipeBot` class, handles user interaction and natural language understanding

### Extended Features

The project supports the following extended features (already implemented in code):
- Speech-to-text input
- Flexible language understanding (supports various question formats)
- Context-aware Q&A (e.g., temperature, time, etc.)

## License

This project is a course assignment project.

## Author

CS337 Project 2
