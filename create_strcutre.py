import os

# Define the folder structure
folders = [
    "quiz-app",
    "quiz-app/static",
    "quiz-app/static/assets",
    "quiz-app/data"
]

# Define the files to create
files = {
    "quiz-app/index.html": "<!-- HTML file will go here -->",
    "quiz-app/static/style.css": "/* CSS file will go here */",
    "quiz-app/static/script.js": "// JavaScript file will go here",
    "quiz-app/static/assets/bagg.jpg": None,  # Placeholder, will not create real image
    "quiz-app/static/assets/bubbles.png": None  # Optional placeholder
}

# Create folders
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"Created folder: {folder}")

# Create files
for path, content in files.items():
    if content is not None:
        with open(path, "w") as f:
            f.write(content)
            print(f"Created file: {path}")
    else:
        # Just create an empty file as placeholder for images
        open(path, "a").close()
        print(f"Created placeholder file: {path}")
