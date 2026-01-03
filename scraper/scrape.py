"""
OptiSigns Support Article Scraper
==================================

This scraper fetches support articles from OptiSigns' Zendesk Help Center
using the official API and converts them to clean Markdown files.

How it works:
1. Fetches articles from the Zendesk API with pagination support
2. Converts HTML body content to clean Markdown using html2text
3. Preserves headings, lists, code blocks, and links
4. Saves each article as a separate .md file named after the article slug
5. Appends the original article URL at the end of each file

Requirements:
- requests: For making HTTP API calls
- html2text: For converting HTML to Markdown format

Usage:
    python scrape.py
"""

import requests
from html2text import HTML2Text
from pathlib import Path
import time

# API endpoint for OptiSigns Zendesk Help Center
BASE_URL = "https://support.optisigns.com/api/v2/help_center/articles.json"

# Output directory for saved articles
OUT_DIR = Path("articles")
OUT_DIR.mkdir(exist_ok=True)


def html_to_markdown(html: str) -> str:
    """
    Convert HTML content to clean Markdown format.
    
    Args:
        html: HTML string to convert
        
    Returns:
        Markdown-formatted string with preserved structure
    """
    h = HTML2Text()
    h.ignore_links = False       # Preserve links
    h.ignore_images = False      # Preserve images
    h.body_width = 0             # Don't wrap lines
    h.ignore_emphasis = False    # Preserve bold/italic
    h.skip_internal_links = True # Skip internal anchor links
    
    # Convert and clean up the markdown
    markdown = h.handle(html)
    
    # Remove excessive blank lines (more than 2 consecutive)
    lines = markdown.split('\n')
    cleaned_lines = []
    blank_count = 0
    
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def scrape_articles(limit=30):
    """
    Scrape articles from OptiSigns Support using Zendesk API.
    
    Args:
        limit: Minimum number of articles to scrape (default: 30)
    """
    page = 1
    saved = 0
    total_available = 0

    print(f"🚀 Starting scraper to fetch at least {limit} articles...")
    print(f"📁 Saving to: {OUT_DIR.absolute()}\n")

    while saved < limit:
        try:
            print(f"📄 Fetching page {page}...")
            
            # Make API request with pagination
            response = requests.get(BASE_URL, params={"page": page}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", [])
            
            if not articles:
                print(f"⚠️  No more articles found on page {page}")
                break
            
            # Track total available articles
            if page == 1 and "count" in data:
                total_available = data["count"]
                print(f"ℹ️  Total articles available: {total_available}\n")
            
            # Process each article
            for article in articles:
                title = article.get("title", "Untitled")
                body_html = article.get("body", "")
                url = article.get("html_url", "")
                article_id = article.get("id", "unknown")
                
                # Generate filename from URL slug or fallback to article ID
                if url:
                    slug = url.rstrip("/").split("/")[-1]
                else:
                    slug = f"article-{article_id}"
                
                # Create markdown file path
                md_path = OUT_DIR / f"{slug}.md"
                
                # Build markdown content
                markdown_content = f"# {title}\n\n"
                
                if body_html:
                    markdown_content += html_to_markdown(body_html)
                else:
                    markdown_content += "*No content available*\n"
                
                markdown_content += f"\n\n---\nArticle URL: {url}\n"
                
                # Save to file
                md_path.write_text(markdown_content, encoding="utf-8")
                saved += 1
                
                print(f"  ✅ [{saved:3d}] {title[:60]}")
                
                # Check if we've reached the limit
                if saved >= limit:
                    print(f"\n🎉 Successfully saved {saved} articles!")
                    return
            
            # Check if there's a next page
            next_page = data.get("next_page")
            if not next_page:
                print(f"\n⚠️  Reached last page. No more articles available.")
                break
            
            page += 1
            
            # Small delay to be respectful to the API
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break

    print(f"\n🏁 Finished. Total articles saved: {saved}")


if __name__ == "__main__":
    # Scrape at least 30 articles (default set to 35 for good measure)
    scrape_articles(limit=35)
