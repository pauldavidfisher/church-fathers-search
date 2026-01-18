# System Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Church Fathers Search System                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          DATA COLLECTION                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐         ┌─────────────────────────────────┐     │
│   │              │         │                                   │     │
│   │  New Advent  │────────▶│      Web Scraper (scraper.py)    │     │
│   │   Website    │  HTTP   │                                   │     │
│   │              │  GET    │  - Parse HTML with BeautifulSoup  │     │
│   └──────────────┘         │  - Extract authors & works        │     │
│                            │  - Download full texts             │     │
│                            │  - Respectful delays (1s)          │     │
│                            └───────────────┬───────────────────┘     │
│                                            │                          │
└────────────────────────────────────────────┼──────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                     ┌───────────────────────┐                        │
│                     │   SQLite Database     │                        │
│                     │  (church_fathers.db)  │                        │
│                     └───────┬───────────────┘                        │
│                             │                                         │
│        ┌────────────────────┼────────────────────┐                  │
│        │                    │                    │                  │
│        ▼                    ▼                    ▼                  │
│  ┌──────────┐      ┌──────────────┐     ┌──────────────┐           │
│  │ Authors  │      │    Works      │     │   Chapters   │           │
│  │          │      │               │     │              │           │
│  │ • Names  │◀─────│ • Titles      │◀────│ • Content    │           │
│  │ • Saints │      │ • URLs        │     │ • Metadata   │           │
│  │ • Doctors│      │ • Types       │     │              │           │
│  └──────────┘      └───────────────┘     └──────┬───────┘           │
│                                                  │                   │
│                    ┌─────────────────────────────┤                  │
│                    │                             │                   │
│                    ▼                             ▼                   │
│         ┌────────────────────┐       ┌────────────────────┐         │
│         │  Phrase Index      │       │  Trigram Index     │         │
│         │  (N-grams)         │       │  (Characters)      │         │
│         │                    │       │                    │         │
│         │ • 2-10 word        │       │ • 3-char strings   │         │
│         │   phrases          │       │ • Fuzzy matching   │         │
│         │ • Position data    │       │ • Typo tolerance   │         │
│         │ • B-tree indexed   │       │                    │         │
│         └────────────────────┘       └────────────────────┘         │
│                                                                       │
│                    ┌─────────────────────┐                           │
│                    │    FTS5 Index       │                           │
│                    │  (Full-Text)        │                           │
│                    │                     │                           │
│                    │ • Boolean queries   │                           │
│                    │ • Word proximity    │                           │
│                    │ • Advanced syntax   │                           │
│                    └─────────────────────┘                           │
│                                                                       │
└───────────────────────────────────────────────────────────────────── │
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SEARCH ENGINE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                  ┌──────────────────────────────┐                   │
│                  │  PhraseSearchEngine Class    │                   │
│                  │  (search_engine.py)          │                   │
│                  └───────────┬──────────────────┘                   │
│                              │                                        │
│     ┌────────────────────────┼────────────────────────┐             │
│     │            │            │            │           │             │
│     ▼            ▼            ▼            ▼           ▼             │
│ ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐    │
│ │ Exact  │ │Proximity │ │ Fuzzy  │ │ Boolean  │ │ Combined   │    │
│ │ Phrase │ │  Search  │ │ Phrase │ │  Search  │ │   Search   │    │
│ │        │ │          │ │        │ │          │ │            │    │
│ │O(logN) │ │O(N*M)    │ │O(N)    │ │O(logN)   │ │All methods │    │
│ │<10ms   │ │50-200ms  │ │100ms   │ │<50ms     │ │200-800ms   │    │
│ └────────┘ └──────────┘ └────────┘ └──────────┘ └────────────┘    │
│                                                                       │
└───────────────────────────────────────────────────────────────────── │
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐      ┌──────────────┐      ┌─────────────┐      │
│   │  Web UI      │      │  REST API    │      │  CLI        │      │
│   │  (Flask)     │      │  (Flask)     │      │  (Python)   │      │
│   │              │      │              │      │             │      │
│   │ • HTML/CSS   │      │ • JSON       │      │ • Interactive│     │
│   │ • JavaScript │      │ • Endpoints  │      │ • Scripting │      │
│   │ • Responsive │      │ • Auth ready │      │ • Batch     │      │
│   └──────────────┘      └──────────────┘      └─────────────┘      │
│                                                                       │
└───────────────────────────────────────────────────────────────────── │


## Data Flow: Search Query Processing

┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  1. User Query: "love of God"                                        │
│                     │                                                 │
│                     ▼                                                 │
│  2. Normalize: "love of god"                                         │
│                     │                                                 │
│                     ▼                                                 │
│  3. Route to Search Method(s)                                        │
│                     │                                                 │
│         ┌───────────┼───────────┐                                    │
│         ▼           ▼           ▼                                    │
│     [Exact]    [Proximity]  [Fuzzy]                                  │
│         │           │           │                                    │
│         ▼           ▼           ▼                                    │
│   Index      FTS5 +      Similarity                                  │
│   Lookup     Distance    Matching                                    │
│         │      Calc         │                                        │
│         └───────┬───────────┘                                        │
│                 ▼                                                     │
│  4. Collect & Merge Results                                          │
│                 │                                                     │
│                 ▼                                                     │
│  5. Extract Context (~20 words around match)                         │
│                 │                                                     │
│                 ▼                                                     │
│  6. Format Results                                                    │
│     • Author name                                                     │
│     • Work title                                                      │
│     • Chapter                                                         │
│     • Context snippet                                                 │
│     • Source URL                                                      │
│                 │                                                     │
│                 ▼                                                     │
│  7. Return to User (JSON/HTML/CLI)                                   │
│                                                                       │
└───────────────────────────────────────────────────────────────────── │


## Indexing Pipeline

┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  Input: Raw text from chapter                                        │
│  Example: "Great is Your power and Your wisdom infinite"             │
│                     │                                                 │
│                     ▼                                                 │
│  1. Tokenize into words                                              │
│     ["Great", "is", "Your", "power", ...]                            │
│                     │                                                 │
│                     ▼                                                 │
│  2. Generate N-grams (2-10 words)                                    │
│     • "great is"                                                      │
│     • "great is your"                                                 │
│     • "great is your power"                                          │
│     • "is your power and"                                            │
│     • etc...                                                          │
│                     │                                                 │
│                     ▼                                                 │
│  3. Normalize (lowercase, clean)                                     │
│     "great is your power"                                            │
│                     │                                                 │
│                     ▼                                                 │
│  4. Store in phrases table with:                                     │
│     • Phrase text                                                     │
│     • Chapter ID                                                      │
│     • Position in text                                                │
│     • Length (word count)                                             │
│                     │                                                 │
│                     ▼                                                 │
│  5. Create index entries                                             │
│     phrase_index["great is your power"] = [                          │
│       {chapter_id: 42, position: 5, length: 4},                      │
│       ...                                                             │
│     ]                                                                 │
│                     │                                                 │
│                     ▼                                                 │
│  6. Generate character trigrams                                      │
│     "gre", "rea", "eat", "at ", "t i", ...                          │
│                     │                                                 │
│                     ▼                                                 │
│  7. Store in trigrams table                                          │
│                     │                                                 │
│                     ▼                                                 │
│  8. Index in FTS5 for full-text                                      │
│                     │                                                 │
│                     ▼                                                 │
│  Complete! Chapter fully indexed.                                    │
│                                                                       │
└───────────────────────────────────────────────────────────────────── │


## Performance Characteristics

┌────────────────────┬──────────────┬─────────────┬──────────────┐
│  Search Type       │ Time         │ Use Case    │ Index Used   │
├────────────────────┼──────────────┼─────────────┼──────────────┤
│  Exact Phrase      │  < 10ms      │  Quotations │  Phrases     │
│  Proximity         │  50-200ms    │  Concepts   │  FTS5        │
│  Fuzzy             │  100-500ms   │  Variations │  Trigrams    │
│  Boolean           │  < 50ms      │  Complex    │  FTS5        │
│  Combined          │  200-800ms   │  Thorough   │  All         │
└────────────────────┴──────────────┴─────────────┴──────────────┘

┌────────────────────┬──────────────┬──────────────────────────────┐
│  Database Size     │  Volume      │  Contents                    │
├────────────────────┼──────────────┼──────────────────────────────┤
│  Authors Table     │  ~ 100 rows  │  Church Fathers              │
│  Works Table       │  ~ 500 rows  │  Books/Epistles              │
│  Chapters Table    │  ~ 5K rows   │  Sections                    │
│  Phrases Index     │  ~ 10M rows  │  N-gram phrases              │
│  Trigrams Index    │  ~ 50M rows  │  Character trigrams          │
│  FTS5 Index        │  Virtual     │  Full-text data              │
│  TOTAL SIZE        │  500MB-2GB   │  Complete system             │
└────────────────────┴──────────────┴──────────────────────────────┘
