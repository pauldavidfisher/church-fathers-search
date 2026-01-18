# Quick Start Guide

## Church Fathers Search Engine - Get Started in 5 Minutes

### Option 1: Try the Demo (Fastest)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo with sample data
python demo.py

# This creates a small database and shows example searches
```

The demo will:
- Create a sample database with 3 authors and 5 chapters
- Index ~3,000 unique phrases
- Run example searches showing different search types
- Complete in under 1 minute

### Option 2: Scrape Limited Data (20 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape first 10 works (about 2-5 minutes)
python scraper.py --limit 10

# Test the search
python search_engine.py --stats
python search_engine.py --query "love of God" --type exact
```

### Option 3: Full Database (Several Hours)

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape ALL Church Fathers content (takes several hours)
# Creates ~500MB-2GB database
python scraper.py

# The scraper will:
# - Fetch 70+ authors
# - Download 300+ works
# - Index 5,000+ chapters
# - Build millions of phrase n-grams
```

**Note:** The full scrape makes thousands of HTTP requests. Please be respectful:
- The scraper includes 1-second delays between requests
- Consider running overnight
- Can be stopped and restarted (uses INSERT OR IGNORE)

## Using the Search Engine

### Command Line

```bash
# Interactive mode
python search_engine.py

# Single query - exact phrase
python search_engine.py --query "holy spirit" --type exact --limit 20

# Proximity search - words near each other  
python search_engine.py --query "faith hope" --type proximity --limit 15

# Fuzzy search - similar phrases
python search_engine.py --query "love of god" --type fuzzy

# Combined search - all methods
python search_engine.py --query "eternal life" --type combined

# Show database statistics
python search_engine.py --stats
```

### Web Interface

```bash
# Start the Flask server
python app.py

# Open browser to http://localhost:5000
```

The web interface provides:
- Simple search box
- Multiple search method selection (exact, proximity, fuzzy, boolean, combined)
- Author filtering
- Result context with highlighting
- Links to source texts

### Python API

```python
from search_engine import PhraseSearchEngine

# Initialize
engine = PhraseSearchEngine('church_fathers.db')

# Exact phrase search
results = engine.exact_phrase_search("love of God", limit=20)

# Proximity search (words within N words of each other)
results = engine.proximity_search(["faith", "hope"], max_distance=5)

# Fuzzy search (similar phrases)
results = engine.fuzzy_phrase_search("eternal life", threshold=0.8)

# Combined search (all methods)
all_results = engine.combined_search("holy trinity")

# Filter by author
augustine_results = engine.search_by_author("Augustine", "grace")

# Get statistics
stats = engine.get_stats()
print(f"Total phrases indexed: {stats['unique_phrases']}")

engine.close()
```

## Search Examples

### Theological Concepts
- "holy trinity"
- "body of Christ"
- "grace of God"
- "eternal life"
- "kingdom of heaven"

### Virtues and Vices
- "faith hope charity"
- "patience and endurance"
- "pride and humility"
- "love and sacrifice"

### Sacraments and Practices
- "baptism of water"
- "breaking of bread"
- "prayer and fasting"
- "laying on of hands"

### Christology
- "incarnation of the word"
- "resurrection of the dead"
- "passion of christ"
- "divinity of jesus"

### Church and Ministry
- "apostolic succession"
- "bishops and deacons"
- "unity of the church"
- "schism and heresy"

## Understanding Search Types

### Exact Phrase
- Finds **exact matches** of your phrase
- Fastest search method
- Use for: specific quotes, well-known phrases
- Example: "our father who art in heaven"

### Proximity Search
- Finds words that appear **near each other**
- Adjustable distance (default: within 5 words)
- Use for: related concepts that may not form exact phrases
- Example: searching "love God" finds "love of God", "God's love", "loving God"

### Fuzzy Search
- Finds **similar phrases** using similarity scoring
- Handles variations in wording
- Use for: when you're not sure of exact wording
- Example: "kingdom of heaven" also finds "heavenly kingdom"

### Boolean Search
- Combines terms with **AND, OR, NOT**
- Most flexible for complex queries
- Use for: combining multiple concepts
- Example: "faith AND hope NOT despair"

### Combined Search
- Runs **all search methods** simultaneously
- Shows best results from each method
- Use for: comprehensive search when you're not sure which method works best

## Tips for Best Results

1. **Start with exact phrase** - if you know the exact wording
2. **Use 2-5 words** - optimal phrase length
3. **Try different methods** - if one doesn't work, try another
4. **Filter by author** - if you know who wrote it
5. **Check proximity** - for related concepts
6. **Use fuzzy search** - when unsure of exact words

## Troubleshooting

**Q: No results found?**
- Try a different search method
- Use fewer or more general words
- Check spelling
- Try proximity or fuzzy search

**Q: Too many results?**
- Use more specific phrases (3-5 words instead of 1-2)
- Filter by specific author
- Use exact phrase search instead of proximity

**Q: Search is slow?**
- Exact phrase search should be <10ms
- Proximity/fuzzy may take 100-500ms
- Reduce result limit if needed
- Ensure database indexes are built

**Q: Want to search specific author?**
```bash
python search_engine.py --query "grace" --type exact
# Then manually filter results, or use Python API:
```
```python
engine.search_by_author("Augustine", "grace")
```

## Next Steps

1. ✅ Try the demo
2. ✅ Run some searches
3. ✅ Start the web interface
4. Read the full README.md for advanced features
5. Explore the code to customize searches
6. Run full scrape for complete database

## Need Help?

- Check README.md for detailed documentation
- Examine demo.py for code examples
- Review search_engine.py for all available methods
- Open an issue on GitHub

Happy searching! 📚⛪
