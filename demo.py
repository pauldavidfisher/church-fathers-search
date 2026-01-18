#!/usr/bin/env python3
"""
Demo script - creates a small sample database to demonstrate the search system
without requiring a full scrape of the New Advent website.
"""

import sqlite3
import sys
from scraper import ChurchFathersScraper
from search_engine import PhraseSearchEngine


# Sample data for demonstration
DEMO_DATA = {
    'Clement of Rome': {
        'is_saint': True,
        'is_doctor': False,
        'works': [
            {
                'title': 'First Epistle to the Corinthians',
                'url': 'https://www.newadvent.org/fathers/1010.htm',
                'chapters': [
                    {
                        'number': 1,
                        'title': 'The Salutation',
                        'content': '''The church of God which sojourns at Rome, to the church of God sojourning at Corinth, 
                        to them that are called and sanctified by the will of God, through our Lord Jesus Christ: 
                        Grace unto you, and peace, from Almighty God through Jesus Christ, be multiplied.'''
                    },
                    {
                        'number': 5,
                        'title': 'The Martyrdom of Peter and Paul',
                        'content': '''Let us take the noble examples furnished in our own generation. Through envy and 
                        jealousy the greatest and most righteous pillars of the church have been persecuted and put to death. 
                        Let us set before our eyes the illustrious apostles. Peter, through unrighteous envy, endured not one 
                        or two, but numerous labours; and when he had at length suffered martyrdom, departed to the place of 
                        glory due to him. Owing to envy, Paul also obtained the reward of patient endurance, after being seven 
                        times thrown into captivity, compelled to flee, and stoned.'''
                    }
                ]
            }
        ]
    },
    'Augustine of Hippo': {
        'is_saint': True,
        'is_doctor': True,
        'works': [
            {
                'title': 'Confessions',
                'url': 'https://www.newadvent.org/fathers/1101.htm',
                'chapters': [
                    {
                        'number': 1,
                        'title': 'Book I - Childhood',
                        'content': '''Great are You, O Lord, and greatly to be praised; great is Your power, and Your wisdom 
                        is infinite. And You would man praise; man, but a particle of Your creation; man, that bears about him 
                        his mortality, the witness of his sin, the witness that You resist the proud: yet would man praise You; 
                        he, but a particle of Your creation. You awaken us to delight in Your praise; for You made us for 
                        Yourself, and our heart is restless until it rests in You.'''
                    },
                    {
                        'number': 10,
                        'title': 'Book X - Memory and Time',
                        'content': '''Late have I loved You, O Beauty ever ancient, ever new, late have I loved You! You were 
                        within me, but I was outside, and it was there that I searched for You. In my unloveliness I plunged 
                        into the lovely things which You created. You were with me, but I was not with You. Created things kept 
                        me from You; yet if they had not been in You they would not have been at all.'''
                    }
                ]
            }
        ]
    },
    'Athanasius': {
        'is_saint': True,
        'is_doctor': True,
        'works': [
            {
                'title': 'On the Incarnation of the Word',
                'url': 'https://www.newadvent.org/fathers/2802.htm',
                'chapters': [
                    {
                        'number': 1,
                        'title': 'Creation and the Fall',
                        'content': '''For God has not only made us out of nothing; but He gave us freely, by the grace of 
                        the Word, a life in correspondence with God. But men, having rejected things eternal, and, by counsel 
                        of the devil, turned to the things of corruption, became the cause of their own corruption in death, 
                        being, as I said before, by nature corruptible, but destined, by the grace following from partaking of 
                        the Word, to have escaped their natural state, had they remained good.'''
                    }
                ]
            }
        ]
    }
}


def create_demo_database(db_path='demo_church_fathers.db'):
    """Create a demo database with sample content"""
    print("Creating demo database...")
    
    # Initialize scraper (this creates the schema)
    scraper = ChurchFathersScraper(db_path=db_path)
    
    # Add demo data
    for author_name, author_info in DEMO_DATA.items():
        print(f"\nAdding {author_name}...")
        
        # Store author
        author_id = scraper.store_author({
            'name': author_name,
            'is_saint': author_info['is_saint'],
            'is_doctor': author_info['is_doctor']
        })
        
        # Store works and chapters
        for work in author_info['works']:
            print(f"  - {work['title']}")
            work_id = scraper.store_work(author_id, work)
            
            for chapter in work['chapters']:
                scraper.store_chapter(work_id, chapter)
                print(f"    ✓ Chapter {chapter['number']}: {chapter['title']}")
    
    scraper.close()
    print(f"\n✅ Demo database created: {db_path}")
    return db_path


def run_demo_searches(db_path):
    """Run example searches on the demo database"""
    print("\n" + "="*70)
    print("DEMO: Church Fathers Search Engine")
    print("="*70)
    
    engine = PhraseSearchEngine(db_path=db_path)
    
    # Show stats
    stats = engine.get_stats()
    print("\n📊 Database Statistics:")
    print(f"   Authors: {stats['total_authors']}")
    print(f"   Works: {stats['total_works']}")
    print(f"   Chapters: {stats['total_chapters']}")
    print(f"   Unique Phrases: {stats['unique_phrases']:,}")
    print(f"   Total Phrase Occurrences: {stats['total_phrase_occurrences']:,}")
    
    # Demo searches
    demo_queries = [
        ("love You", "exact"),
        ("grace of God", "exact"),
        ("through envy", "exact"),
        ("Jesus Christ", "proximity"),
    ]
    
    print("\n" + "="*70)
    print("DEMO SEARCHES")
    print("="*70)
    
    for query, search_type in demo_queries:
        print(f"\n🔍 Searching for: '{query}' (Type: {search_type})")
        print("-" * 70)
        
        if search_type == 'exact':
            results = engine.exact_phrase_search(query, limit=5)
        elif search_type == 'proximity':
            words = query.split()
            results = engine.proximity_search(words, limit=5)
        
        if results:
            print(f"Found {len(results)} result(s):\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['author']}: {result['work']}")
                print(f"   Chapter: {result['chapter']}")
                context = result['context']
                if len(context) > 200:
                    context = context[:200] + '...'
                print(f"   Context: {context}")
                print()
        else:
            print("No results found.\n")
    
    # Demonstrate combined search
    print("\n" + "="*70)
    print("COMBINED SEARCH DEMO")
    print("="*70)
    print("\n🔍 Searching for: 'love' using ALL methods")
    print("-" * 70)
    
    combined_results = engine.combined_search("love", limit=3)
    
    for search_type, results in combined_results.items():
        if results:
            print(f"\n{search_type.upper()}: {len(results)} result(s)")
            for result in results[:2]:  # Show first 2 of each type
                print(f"  • {result['author']}: {result['work']}")
    
    engine.close()
    
    print("\n" + "="*70)
    print("Demo complete! To explore more:")
    print(f"  python search_engine.py --db {db_path}")
    print(f"  python app.py  # (set DB_PATH={db_path})")
    print("="*70 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Create and test demo database')
    parser.add_argument('--db', default='demo_church_fathers.db', 
                       help='Demo database path')
    parser.add_argument('--skip-create', action='store_true',
                       help='Skip database creation, just run searches')
    args = parser.parse_args()
    
    if not args.skip_create:
        create_demo_database(args.db)
    
    run_demo_searches(args.db)


if __name__ == '__main__':
    main()
