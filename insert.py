import sqlite3
import json
import os
from Scraping import scrapping as scrape

# Load your JSON data
with open("datasources.json", "r") as f:
    data = json.load(f)

# Base directory to store exercises
base_directory = "exercises"

# database file path for SQLite
databasefilepath = "./Database/arithma-databank.db"


def process_json_data(data, base_directory):
    """
    Iterates through each entry in the JSON data, creates directories for categories and subcategories
    and returns a dictionary of categories and their subcategories.
    """
    # Initialize a dictionary to store categories and their respective subcategories
    categories_subcategories = {}

    for key, content in data.items():
        category = content["Category"]  # Main category (e.g., Algebra)
        urls = content["urls"]  # List of URLs

        # Create the main category folder
        category_dir = scrape.create_directories(base_directory, category, "")

        # Initialize a set to keep track of unique subcategories for the current category
        subcategories_set = set()

        # Iterate through each URL and getting the categories/subcategories set
        for i, url_entry in enumerate(urls):
            url = url_entry["url"]  # URL to scrape
            subcategory = scrape.extract_subcategory_from_url(url)

            # Add subcategory to the set for this category
            subcategories_set.add(subcategory)

        # Convert the set to a list and store it in the dictionary under the category key
        categories_subcategories[category] = list(subcategories_set)

    # Return the final dictionary with categories and subcategories
    print("Finished ! The categories have been scraped and parsed from the sources")
    return categories_subcategories


# Helper function to insert or get category id
def insert_or_get_category(cursor,category_name):
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        print("Done ! The number of categories inserted is => "+ str(cursor.lastrowid))
        return cursor.lastrowid
    else:
        print("Data already exists in this table for the categories")
        return result[0]

# Helper function to insert or get subcategory id
def insert_or_get_subcategory(cursor,subcategory_name, category_id):
    cursor.execute("SELECT id FROM subcategories WHERE name = ? AND category_id = ?", (subcategory_name, category_id))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (subcategory_name, category_id))
        print("Done ! The number of subcategories inserted is => "+ str(cursor.lastrowid))
        return cursor.lastrowid
    else:
        print("Data already exists in this table for the subcategories")
        return result[0]

def prepare_database(databasefilename, categories_subcategories):
    """
    Prepares the database, creates tables if they do not exist, and inserts categories
    and subcategories based on the input data.
    
    Args:
        databasefilename: Path to the SQLite database file.
        categories_subcategories: A dictionary with categories as keys and a list of subcategories as values.
    """
    # Connect to SQLite database
    with sqlite3.connect(databasefilename) as conn:
        cursor = conn.cursor()
        # Create tables if they do not exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        );
    """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            script TEXT,
            hint TEXT,
            solution TEXT,
            lang TEXT,
            category_id INTEGER,
            subcategory_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
        );
    """)
        conn.commit()
        # Insert Categories and Subcategories if they do not exist
        for category, subcategories in categories_subcategories.items():
            category_id = insert_or_get_category(cursor, category)
            # Loop through subcategories and insert them with the parent category ID
            for subcategory in subcategories:
                insert_or_get_subcategory(cursor, subcategory, category_id)
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("All Done, your Data has been parsed and loaded into your SQLite Database")


def load_json_data_to_db(databasefilename, data, base_directory):
    """
    Loads the JSON data into the SQLite database by inserting exercises,
    and linking them to categories and subcategories.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(databasefilename)
    cursor = conn.cursor()

    for key, content in data.items():
        category = content["Category"]  # Main category (e.g., Algebra)
        urls = content["urls"]  # List of URLs

        # Get or insert category into the database
        category_id = insert_or_get_category(cursor, category)

        for url_entry in urls:
            url = url_entry["url"]  # URL to scrape
            subcategory = scrape.extract_subcategory_from_url(url)  # Extract subcategory from the URL

            # Get or insert subcategory into the database, linked to the category
            subcategory_id = insert_or_get_subcategory(cursor, subcategory, category_id)

            # Scrape exercises from the URL and get exercises, categories, subcategories
            result = scrape.scrape_exercises(url, category, subcategory, base_directory, return_exercises=True)

            # Insert each exercise into the 'exercises' table
            for exercise in result["exercises"]:
                cursor.execute(
                    """
                    INSERT INTO exercises (script, hint, solution, category_id, subcategory_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (exercise["script"], exercise["hint"], exercise["solution"], category_id, subcategory_id)
                )

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

def load_en_json_files_to_db(databasefilename, base_folder):
    """
    Load English JSON files from subdirectories and insert them into the database.
    
    Args:
        databasefilename: Path to the SQLite database file.
        base_folder: Path to the base folder containing category subfolders.
    """
    # Connect to SQLite database
    conn = sqlite3.connect(databasefilename)
    cursor = conn.cursor()

    # Iterate through the base folder and its subfolders
    for category_folder in os.listdir(base_folder):
        category_path = os.path.join(base_folder, category_folder)

        if os.path.isdir(category_path):  # Ensure it's a directory
            category_id = insert_or_get_category(cursor, category_folder)

            for filename in os.listdir(category_path):
                if filename.endswith('.json'):
                    json_file_path = os.path.join(category_path, filename)

                    with open(json_file_path, 'r', encoding='utf-8') as file:
                        exercise = json.load(file)
                        cursor.execute("""
                                    INSERT INTO exercises (script, solution, category_id, lang,level) 
                                    VALUES (?, ?, ?, ?, ?)
                                """, (exercise["problem"],exercise["solution"], category_id, 'en',exercise["level"]))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("All JSON data has been inserted into the database.")


#cat_sub_list=process_json_data(data,base_directory)
#prepare_database(databasefilepath,cat_sub_list)
#load_json_data_to_db(databasefilepath, data, base_directory)
base_folder='./train'
load_en_json_files_to_db(databasefilepath, base_folder)
