import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PAGES_DIR = "./pages"
OUTPUT_FILE = "index.html"
# Paste your deployed Google Apps Script Web App URL here:
TEACHER_API_URL = "https://script.google.com/macros/s/AKfycbxFBtu9WUcgEeOaGEJQjmDhIrcM-rMwNDvA_oTztDLUCXGNTDmQ_NnAQ4gTMCw4T4n3/exec"
# ==============================================================================

page_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".html")]
page_files.sort()

cards_html = ""
for filename in page_files:
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split("_")
    
    if parts[0].isdigit():
        year = parts[0]
        title = " ".join(parts[1:])
        display_name = f"{year} {title}"
    else:
        display_name = base_name.replace("_", " ")

    cards_html += f'''
        <div class="card" data-id="{base_name}" data-search="{display_name.lower()}">
            <div class="card-content">
                <h2>{display_name}</h2>
                <p>1:100 Scale AR Model</p>
            </div>
            <a href="pages/{filename}" class="ar-link">Explore Model</a>
        </div>
    '''

INDEX_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1:100 Scale AR Aircraft Library</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f4f4f9;
            color: #1c1c1e;
            margin: 0;
            padding: 2rem 1rem;
        }}
        .header {{ text-align: center; max-width: 800px; margin: 0 auto 2rem auto; }}
        h1 {{ font-size: 2.2rem; margin-bottom: 0.5rem; }}
        p {{ color: #636366; font-size: 1.1rem; margin-top: 0; }}
        .search-container {{ max-width: 500px; margin: 0 auto 2rem auto; }}
        #search-input {{
            width: 100%; padding: 0.8rem 1.2rem; font-size: 1rem;
            border: 1px solid #d1d1d6; border-radius: 12px; outline: none;
        }}
        .grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 1.25rem; max-width: 1100px; margin: 0 auto;
        }}
        .card {{
            background: #ffffff; border-radius: 14px; padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); display: flex;
            flex-direction: column; justify-content: space-between;
        }}
        .card h2 {{ font-size: 1.2rem; margin: 0 0 0.4rem 0; }}
        .card p {{ font-size: 0.9rem; color: #8e8e93; margin-bottom: 1.25rem; }}
        .ar-link {{
            display: block; text-align: center; background-color: #0071e3;
            color: #ffffff; text-decoration: none; font-weight: 600;
            padding: 0.75rem 1rem; border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>1:100 Scale AR Aircraft Library</h1>
        <p>Interactive Aviation Timeline</p>
    </div>

    <div class="search-container">
        <input type="text" id="search-input" placeholder="Search by name or year..." onkeyup="filterModels()">
    </div>

    <div class="grid" id="catalog-grid">
        {cards_html}
    </div>

    <script>
        const API_URL = "{TEACHER_API_URL}";

        // Fetch live checkbox configuration from Google Sheet
        async function syncTeacherVisibility() {{
            if (!API_URL || API_URL.includes("YOUR_SCRIPT_ID_HERE")) return;

            try {{
                const response = await fetch(API_URL);
                const config = await response.json();
                
                const cards = document.querySelectorAll('.card');
                cards.forEach(card => {{
                    const modelId = card.getAttribute('data-id');
                    
                    // Hide card if explicitly unchecked in Google Sheet
                    if (config.hasOwnProperty(modelId) && config[modelId] === false) {{
                        card.style.display = 'none';
                        card.setAttribute('data-disabled', 'true');
                    }} else {{
                        card.removeAttribute('data-disabled');
                    }}
                }});
            }} catch (err) {{
                console.warn("Using default layout (could not reach control API):", err);
            }}
        }}

        function filterModels() {{
            const query = document.getElementById('search-input').value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            
            cards.forEach(card => {{
                // Skip cards disabled by teacher
                if (card.getAttribute('data-disabled') === 'true') return;

                const title = card.getAttribute('data-search');
                card.style.display = title.includes(query) ? 'flex' : 'none';
            }});
        }}

        // Run visibility sync when student opens page
        syncTeacherVisibility();
    </script>
</body>
</html>
"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(INDEX_TEMPLATE)

print(f"Generated '{OUTPUT_FILE}' with remote-control API integration.")