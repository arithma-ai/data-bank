import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urlparse, parse_qs


# Function to clean text (remove unwanted titles and extra spaces)
def clean_text(text):
    # Remove unwanted titles and keep the rest of the content intact
    text = re.sub(r"^(Enoncé|Indication|Corrigé)", "", text, flags=re.IGNORECASE)
    return text.strip()  # Remove leading/trailing spaces after the title removal

def create_directories(base_directory, category, subcategory):
    """
    Creates directories for the given category and subcategory if they don't exist.
    """
    category_dir = os.path.join(base_directory, category)
    subcategory_dir = os.path.join(category_dir, subcategory)
    os.makedirs(subcategory_dir, exist_ok=True)
    return subcategory_dir

def scrape_exercises(url, category, subcategory, base_directory, return_exercises=False):
    """
    Scrapes exercises from the given URL and returns the list of exercises, categories, and subcategories.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all exercises on the page
    exercises = soup.find_all('div', class_='exo')

    # Create directories for category and subcategory
    subcategory_dir = create_directories(base_directory, category, subcategory)

    exercises_list = []
    categories_set = set()  # Set to store unique categories
    subcategories_set = set()  # Set to store unique subcategories

    for i, exercise in enumerate(exercises, start=1):
        # Extract script, hint, and solution
        script = exercise.find('div', class_='enonce').get_text(strip=True).replace('Enoncé', '').strip()
        hint = exercise.find('div', class_='indication').get_text(strip=True).replace('Indication', '').strip()
        solution = exercise.find('div', class_='corrige').get_text(strip=True).replace('Corrigé', '').strip()

        # Clean up the extracted content
        script = clean_text(script)
        hint = clean_text(hint)
        solution = clean_text(solution)

        exercise_data = {
            "script": script,
            "hint": hint,
            "solution": solution,
            "lang": "french"
        }

        exercises_list.append(exercise_data)

        # Add the category and subcategory to the sets
        categories_set.add(category)
        subcategories_set.add(subcategory)

        # Save each exercise to a JSON file (optional)
        filename = f'exercise_{i}.json'
        filepath = os.path.join(subcategory_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(exercise_data, f, ensure_ascii=False, indent=4)

    # Return the list of exercises and the unique categories/subcategories
    if return_exercises:
        return {
            "exercises": exercises_list,
            "categories": list(categories_set),
            "subcategories": list(subcategories_set)
        }




def extract_subcategory_from_url(url):
    """
    Extracts subcategory from the URL's query parameters. Assumes that the 'quoi' parameter
    contains the subcategory path.
    Example: from 'https://www.bibmath.net/ressources/index.php?action=affiche&quoi=bde/algebre/anneaux',
    'anneaux' will be extracted as the subcategory.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Check if 'quoi' parameter is in the URL and extract its last part as subcategory
    if 'quoi' in query_params:
        subcategory_path = query_params['quoi'][0]
        subcategory = subcategory_path.strip("/").split('/')[-1]  # Get the last part of 'quoi'
        return subcategory
    return "unknown_subcategory"  # Fallback if no valid subcategory is found
