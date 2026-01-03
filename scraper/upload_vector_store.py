#!/usr/bin/env python3
"""
OpenAI Vector Store Upload Script
==================================
This script uploads Markdown documentation files to an OpenAI Vector Store.

Usage:
    export OPENAI_API_KEY='your-api-key-here'
    python upload_vector_store.py

Requirements:
    - OpenAI Python SDK (pip install openai)
    - OPENAI_API_KEY environment variable must be set
    - Markdown files must exist in the 'articles/' directory
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def validate_api_key():
    """
    Validate that the OPENAI_API_KEY environment variable is set.
    Raises a clear error if not found.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            "Error: OPENAI_API_KEY environment variable is not set.\n"
            "Please set it using: export OPENAI_API_KEY='your-api-key-here'"
        )
    return api_key


def find_markdown_files(directory='articles'):
    """
    Find all Markdown files in the specified directory.
    
    Args:
        directory: Directory path containing Markdown files
        
    Returns:
        List of Path objects for all .md files found
    """
    articles_dir = Path(directory)
    
    if not articles_dir.exists():
        raise FileNotFoundError(f"Error: Directory '{directory}' does not exist.")
    
    md_files = list(articles_dir.glob('*.md'))
    
    if not md_files:
        raise FileNotFoundError(f"Error: No Markdown files found in '{directory}' directory.")
    
    return md_files


def upload_file_to_openai(client, file_path):
    """
    Upload a single file to OpenAI using the Files API.
    
    Args:
        client: OpenAI client instance
        file_path: Path object pointing to the file to upload
        
    Returns:
        File object returned by OpenAI API
    """
    print(f"  Uploading: {file_path.name}...")
    
    with open(file_path, 'rb') as f:
        file_object = client.files.create(
            file=f,
            purpose='assistants'
        )
    
    return file_object


def create_vector_store(client, file_ids, store_name="OptiSigns Support Articles"):
    """
    Create a new Vector Store and attach uploaded files to it.
    
    Args:
        client: OpenAI client instance
        file_ids: List of file IDs to attach to the vector store
        store_name: Name for the vector store
        
    Returns:
        Vector Store object with ID and status
    """
    print(f"\nCreating Vector Store: '{store_name}'...")
    
    vector_store = client.vector_stores.create(
        name=store_name,
        file_ids=file_ids
    )
    
    return vector_store


def main():
    """
    Main execution flow:
    1. Validate API key
    2. Find Markdown files
    3. Upload files to OpenAI
    4. Create Vector Store
    5. Attach files to Vector Store
    """
    print("=" * 60)
    print("OpenAI Vector Store Upload Script")
    print("=" * 60)
    
    try:
        # Step 1: Validate API key
        print("\n[1/4] Validating API key...")
        api_key = validate_api_key()
        print("✓ API key found")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Step 2: Find Markdown files
        print("\n[2/4] Finding Markdown files...")
        md_files = find_markdown_files('articles')
        print(f"✓ Found {len(md_files)} Markdown file(s)")
        
        # Step 3: Upload files to OpenAI
        print("\n[3/4] Uploading files to OpenAI...")
        uploaded_files = []
        
        for md_file in md_files:
            try:
                file_object = upload_file_to_openai(client, md_file)
                uploaded_files.append(file_object)
                print(f"  ✓ Uploaded: {md_file.name} (ID: {file_object.id})")
            except Exception as e:
                print(f"  ✗ Failed to upload {md_file.name}: {e}")
                continue
        
        if not uploaded_files:
            raise Exception("No files were successfully uploaded.")
        
        print(f"\n✓ Successfully uploaded {len(uploaded_files)} file(s)")
        
        # Step 4: Create Vector Store and attach files
        print("\n[4/4] Creating Vector Store...")
        file_ids = [f.id for f in uploaded_files]
        vector_store = create_vector_store(client, file_ids)
        
        # Final summary
        print("\n" + "=" * 60)
        print("Upload Complete!")
        print("=" * 60)
        print(f"Markdown files found:     {len(md_files)}")
        print(f"Files uploaded:           {len(uploaded_files)}")
        print(f"Vector Store ID:          {vector_store.id}")
        print(f"Vector Store Name:        {vector_store.name}")
        print(f"Vector Store Status:      {vector_store.status}")
        print(f"Files in Vector Store:    {len(file_ids)}")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Copy the Vector Store ID above")
        print("2. Attach it to your OpenAI Assistant in the Playground")
        print("3. Enable 'File Search' tool in your Assistant settings")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
