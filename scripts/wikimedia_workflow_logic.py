#!/usr/bin/env python3
"""
Logic for Wikimedia Unified Translation Workflow:
1. diff_and_update_custom: Compares extracted sources against upstream and updates translations-custom/.
2. merge_final: Overlays translations-custom/ onto translations-upstream/ to produce translations/.
"""
import os
import sys
import json
import shutil
import argparse
from pathlib import Path
import polib

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = REPO_ROOT / "translations-upstream"
CUSTOM_DIR = REPO_ROOT / "translations-custom"
FINAL_DIR = REPO_ROOT / "translations"

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def get_msgids(po_file_path):
    if not os.path.exists(po_file_path):
        return set()
    try:
        po = polib.pofile(po_file_path)
        return {entry.msgid for entry in po}
    except Exception as e:
        print(f"Error reading {po_file_path}: {e}")
        return set()

def update_custom_layer(extracted_dir):
    """
    Step 3: Update translations-custom based on diff between extracted and upstream.
    Always maintains existing translations.
    Creates placeholders for all languages.
    """
    print(f"--- Updating Custom Layer from {extracted_dir} ---")
    extracted_path = Path(extracted_dir)
    
    # 1. Determine all supported languages from upstream
    supported_langs = []
    # Upstream structure: translations-upstream/<repo>/conf/locale/<lang>/...
    # We'll scan a known large repo like edx-platform or just aggregate all langs found.
    for repo_dir in UPSTREAM_DIR.iterdir():
        if not repo_dir.is_dir(): continue
        locale_dir = repo_dir / "conf" / "locale"
        if locale_dir.exists():
            for lang_dir in locale_dir.iterdir():
                if lang_dir.is_dir() and lang_dir.name != "en" and lang_dir.name not in supported_langs:
                    supported_langs.append(lang_dir.name)
    
    print(f"Found {len(supported_langs)} supported languages in upstream: {', '.join(supported_langs)}")

    # 2. Iterate through extracted files
    for extracted_file in extracted_path.glob("**/LC_MESSAGES/*.po"):
        rel_path = extracted_file.relative_to(extracted_path)
        # rel_path looks like: edx-platform/conf/locale/en/LC_MESSAGES/django.po
        
        # Find corresponding upstream source file
        upstream_source = UPSTREAM_DIR / rel_path
        
        # If upstream doesn't exist, the entire repo is custom
        upstream_ids = get_msgids(upstream_source)
        extracted_po = polib.pofile(extracted_file)
        
        custom_entries = [e for e in extracted_po if e.msgid not in upstream_ids]
        
        if not custom_entries:
            print(f"No custom strings found for {rel_path}")
            continue

        print(f"Found {len(custom_entries)} custom strings for {rel_path}")
        
        # Update English Custom File
        custom_en_path = CUSTOM_DIR / rel_path
        ensure_directory(custom_en_path.parent)
        
        if custom_en_path.exists():
            custom_en_po = polib.pofile(custom_en_path)
            existing_custom_ids = {e.msgid for e in custom_en_po}
        else:
            custom_en_po = polib.POFile()
            custom_en_po.metadata = extracted_po.metadata.copy()
            existing_custom_ids = set()

        for entry in custom_entries:
            if entry.msgid not in existing_custom_ids:
                custom_en_po.append(entry)
        custom_en_po.save(custom_en_path)

        # Update Placeholders for ALL other languages
        for lang in supported_langs:
            # We need to construct the localized path for custom
            # rel_path: edx-platform/conf/locale/en/LC_MESSAGES/django.po
            # parts: ('edx-platform', 'conf', 'locale', 'en', 'LC_MESSAGES', 'django.po')
            parts = list(rel_path.parts)
            try:
                en_index = parts.index("en")
                parts[en_index] = lang
            except ValueError:
                # If 'en' is not in path, we assume it's some other structure?
                # Usually it should be there.
                continue
                
            custom_lang_path = CUSTOM_DIR / Path(*parts)
            ensure_directory(custom_lang_path.parent)
            
            if custom_lang_path.exists():
                custom_lang_po = polib.pofile(custom_lang_path)
                existing_lang_map = {e.msgid: e for e in custom_lang_po}
            else:
                custom_lang_po = polib.POFile()
                custom_lang_po.metadata = extracted_po.metadata.copy()
                existing_lang_map = {}

            for entry in custom_entries:
                if entry.msgid not in existing_lang_map:
                    # New placeholder
                    new_entry = polib.POEntry(
                        msgid=entry.msgid,
                        msgstr="", # Empty translation
                        occurrences=entry.occurrences
                    )
                    custom_lang_po.append(new_entry)
                else:
                    # Maintain existing translation
                    pass
            custom_lang_po.save(custom_lang_path)

def merge_final():
    """
    Step 4: Combine Upstream and Custom Layer.
    """
    print("--- Merging Final Layer (Step 4) ---")
    if FINAL_DIR.exists():
        shutil.rmtree(FINAL_DIR)
    
    # Start with upstream
    shutil.copytree(UPSTREAM_DIR, FINAL_DIR)
    
    # Overlay custom
    for custom_file in CUSTOM_DIR.glob("**/*.po"):
        rel_path = custom_file.relative_to(CUSTOM_DIR)
        final_file = FINAL_DIR / rel_path
        
        if not final_file.exists():
            # Brand new custom file (e.g. from a new custom repo)
            ensure_directory(final_file.parent)
            shutil.copy(custom_file, final_file)
            continue
            
        # Merge contents
        upstream_po = polib.pofile(final_file)
        custom_po = polib.pofile(custom_file)
        
        upstream_map = {e.msgid: e for e in upstream_po}
        
        for entry in custom_po:
            if entry.msgid in upstream_map:
                # Override
                if entry.msgstr: # Only override if custom has a translation? 
                                 # Or override anyway to keep it empty if that's what's in custom?
                                 # Usually custom wins.
                    upstream_map[entry.msgid].msgstr = entry.msgstr
            else:
                # Append
                upstream_po.append(entry)
        
        upstream_po.save(final_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    p_update = subparsers.add_parser("update_custom")
    p_update.add_argument("--extracted-dir", required=True)
    
    p_merge = subparsers.add_parser("merge_final")
    
    args = parser.parse_args()
    
    if args.command == "update_custom":
        update_custom_layer(args.extracted_dir)
    elif args.command == "merge_final":
        merge_final()
