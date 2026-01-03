#!/usr/bin/env python3
"""
OptiSigns OptiBot Daily Job
============================

This script serves as the main entrypoint for the daily scraping and upload job.

Workflow:
1. Re-scrape all support articles from OptiSigns Zendesk API
2. Detect new or updated articles using SHA-256 content hash
3. Upload ONLY the delta (new or updated files) to OpenAI Vector Store
4. Persist state in state.json for tracking between runs
5. Log statistics: articles added, updated, and skipped

Usage:
    export OPENAI_API_KEY='your-api-key-here'
    python main.py

Exit codes:
    0 - Success
    1 - Error occurred
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Tuple, List
from openai import OpenAI
from dotenv import load_dotenv

# Import functions from existing modules
from scrape import scrape_articles, html_to_markdown
from upload_vector_store import validate_api_key, upload_file_to_openai

# Load environment variables
load_dotenv()

# Constants
STATE_FILE = Path("state.json")
ARTICLES_DIR = Path("articles")
VECTOR_STORE_ID_FILE = Path("vector_store_id.txt")


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of file content for change detection.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_state() -> Dict[str, str]:
    """
    Load previous state from state.json.
    
    Returns:
        Dictionary mapping filename to content hash
    """
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load state file: {e}")
            return {}
    return {}


def save_state(state: Dict[str, str]) -> None:
    """
    Save current state to state.json.
    
    Args:
        state: Dictionary mapping filename to content hash
    """
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"💾 State saved to {STATE_FILE}")
    except Exception as e:
        print(f"❌ Error saving state: {e}")


def detect_changes(articles_dir: Path, previous_state: Dict[str, str]) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Detect new, updated, and unchanged articles by comparing content hashes.
    
    Args:
        articles_dir: Directory containing article Markdown files
        previous_state: Dictionary mapping filename to previous content hash
        
    Returns:
        Tuple of (new_files, updated_files, unchanged_files)
    """
    new_files = []
    updated_files = []
    unchanged_files = []
    
    # Get all current markdown files
    current_files = list(articles_dir.glob('*.md'))
    
    for file_path in current_files:
        filename = file_path.name
        current_hash = calculate_file_hash(file_path)
        
        if filename not in previous_state:
            # New file
            new_files.append(file_path)
        elif previous_state[filename] != current_hash:
            # File was updated
            updated_files.append(file_path)
        else:
            # File unchanged
            unchanged_files.append(file_path)
    
    return new_files, updated_files, unchanged_files


def upload_delta_to_vector_store(client: OpenAI, files_to_upload: List[Path], vector_store_id: str = None) -> str:
    """
    Upload only new or updated files to the OpenAI Vector Store.
    
    Args:
        client: OpenAI client instance
        files_to_upload: List of file paths to upload
        vector_store_id: Existing vector store ID (if any)
        
    Returns:
        Vector store ID
    """
    if not files_to_upload:
        print("ℹ️  No files to upload")
        return vector_store_id
    
    print(f"\n📤 Uploading {len(files_to_upload)} file(s) to OpenAI...")
    
    uploaded_file_ids = []
    for file_path in files_to_upload:
        try:
            file_object = upload_file_to_openai(client, file_path)
            uploaded_file_ids.append(file_object.id)
            print(f"  ✓ {file_path.name} (ID: {file_object.id})")
        except Exception as e:
            print(f"  ✗ Failed to upload {file_path.name}: {e}")
    
    # Create or update vector store
    if vector_store_id:
        # Add files to existing vector store
        try:
            print(f"\n🔗 Adding files to existing Vector Store: {vector_store_id}")
            for file_id in uploaded_file_ids:
                client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id
                )
            print(f"✓ Added {len(uploaded_file_ids)} file(s) to Vector Store")
        except Exception as e:
            print(f"❌ Error adding files to vector store: {e}")
    else:
        # Create new vector store
        try:
            print("\n🆕 Creating new Vector Store...")
            vector_store = client.vector_stores.create(
                name="OptiSigns Support Articles",
                file_ids=uploaded_file_ids
            )
            vector_store_id = vector_store.id
            print(f"✓ Created Vector Store: {vector_store_id}")
            
            # Save vector store ID for future runs
            with open(VECTOR_STORE_ID_FILE, 'w') as f:
                f.write(vector_store_id)
        except Exception as e:
            print(f"❌ Error creating vector store: {e}")
            raise
    
    return vector_store_id


def load_vector_store_id() -> str:
    """
    Load the vector store ID from file if it exists.
    
    Returns:
        Vector store ID or None
    """
    if VECTOR_STORE_ID_FILE.exists():
        try:
            return VECTOR_STORE_ID_FILE.read_text().strip()
        except Exception as e:
            print(f"⚠️  Warning: Could not read vector store ID: {e}")
    return None


def main():
    """
    Main execution flow for the daily job.
    
    Exit codes:
        0 - Success
        1 - Error
    """
    print("=" * 70)
    print("OptiSigns OptiBot - Daily Scraping Job")
    print("=" * 70)
    
    try:
        # Step 1: Validate OpenAI API key
        print("\n[1/5] Validating OpenAI API key...")
        api_key = validate_api_key()
        client = OpenAI(api_key=api_key)
        print("✓ API key validated")
        
        # Step 2: Load previous state
        print("\n[2/5] Loading previous state...")
        previous_state = load_state()
        print(f"✓ Loaded state for {len(previous_state)} previous article(s)")
        
        # Step 3: Scrape articles
        print("\n[3/5] Scraping support articles...")
        scrape_articles(limit=35)  # Re-scrape all articles
        print("✓ Scraping completed")
        
        # Step 4: Detect changes
        print("\n[4/5] Detecting changes...")
        new_files, updated_files, unchanged_files = detect_changes(ARTICLES_DIR, previous_state)
        
        print(f"  📊 Change Summary:")
        print(f"     • New articles:       {len(new_files)}")
        print(f"     • Updated articles:   {len(updated_files)}")
        print(f"     • Unchanged articles: {len(unchanged_files)}")
        
        # Step 5: Upload delta to Vector Store
        print("\n[5/5] Processing delta upload...")
        files_to_upload = new_files + updated_files
        
        if files_to_upload:
            # Load existing vector store ID
            vector_store_id = load_vector_store_id()
            if vector_store_id:
                print(f"ℹ️  Using existing Vector Store: {vector_store_id}")
            
            # Upload delta
            vector_store_id = upload_delta_to_vector_store(client, files_to_upload, vector_store_id)
            
            # Update state for uploaded files
            new_state = previous_state.copy()
            for file_path in files_to_upload:
                new_state[file_path.name] = calculate_file_hash(file_path)
            
            # Also update state for unchanged files (in case hash algorithm changes)
            for file_path in unchanged_files:
                new_state[file_path.name] = calculate_file_hash(file_path)
            
            save_state(new_state)
        else:
            print("ℹ️  No changes detected. Skipping upload.")
            print("💾 State remains unchanged")
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 Job Completion Summary")
        print("=" * 70)
        print(f"Articles added:     {len(new_files)}")
        print(f"Articles updated:   {len(updated_files)}")
        print(f"Articles skipped:   {len(unchanged_files)}")
        print("=" * 70)
        print("✅ Job completed successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Job interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Job failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
