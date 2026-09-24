import os

PAGES_DIR = "./pages"
OUTPUT_FILE = "index.html"

# Scan and sort generated HTML pages
if os.path.exists(PAGES_DIR):
    page_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".html")]
    page_files.sort()  # Automatically orders chronologically if filenames start with year (e.g., 1903_)
else:
    page_files = []

# Build individual aircraft card elements
cards_html = ""
for filename in page_files:
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split("_")
    
    # Extract year and title
    if parts[0].isdigit():
        year = parts[0]
        title = " ".join(parts[1:])
        display_name = f"{year} {title}"
    else:
        display_name = base_name.replace("_", " ")

    cards_html += f'''
        <div class="card" data-search="{display_name.lower()}">
            <div class="card-content">
                <h2>{display_name}</h2>
                <p>1:100 Scale AR Model</p>
            </div>
            <a href="pages/{filename}" class="ar-link">Explore Model</a>
        </div>
    '''

# Complete responsive index page template with built-in client-side search
INDEX_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1:100 Scale AR Aircraft Library</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f4f9;
            color: #1c1c1e;
            margin: 0;
            padding: 2rem 1rem;
        }}
        .header {{
            text-align: center;
            max-width: 800px;
            margin: 0 auto 2rem auto;
        }}
        h1 {{ font-size: 2.2rem; margin-bottom: 0.5rem; }}
        p {{ color: #636366; font-size: 1.1rem; margin-top: 0; }}
        
        /* Search Bar */
        .search-container {{
            max-width: 500px;
            margin: 0 auto 2rem auto;
        }}
        #search-input {{
            width: 100%;
            padding: 0.8rem 1.2rem;
            font-size: 1rem;
            border: 1px solid #d1d1d6;
            border-radius: 12px;
            outline: none;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        #search-input:focus {{
            border-color: #0071e3;
            box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.2);
        }}

        /* Grid Layout */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 1.25rem;
            max-width: 1100px;
            margin: 0 auto;
        }}
        .card {{
            background: #ffffff;
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }}
        .card h2 {{
            font-size: 1.2rem;
            margin: 0 0 0.4rem 0;
            color: #000000;
        }}
        .card p {{
            font-size: 0.9rem;
            color: #8e8e93;
            margin-bottom: 1.25rem;
        }}
        .ar-link {{
            display: block;
            text-align: center;
            background-color: #0071e3;
            color: #ffffff;
            text-decoration: none;
            font-weight: 600;
            padding: 0.75rem 1rem;
            border-radius: 10px;
            font-size: 0.95rem;
        }}
        .ar-link:active {{ background-color: #005bb5; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>1:100 Scale AR Aircraft Library</h1>
        <p>Interactive Aviation Timeline for Classroom iPads</p>
    </div>

    <div class="search-container">
        <input type="text" id="search-input" placeholder="Search by name or year (e.g., 1917 or Sopwith)..." onkeyup="filterModels()">
    </div>

    <div class="grid" id="catalog-grid">
        {cards_html}
    </div>

    <script>
        function filterModels() {{
            const query = document.getElementById('search-input').value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            
            cards.forEach(card => {{
                const title = card.getAttribute('data-search');
                if (title.includes(query)) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(INDEX_TEMPLATE)

print(f"Successfully created '{OUTPUT_FILE}' with {len(page_files)} aircraft listings.")