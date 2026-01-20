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

    # 2. Iterate through extracted files (.po and .json)
    for ext in ["**/*.po", "**/*.json"]:
        for extracted_file in extracted_path.glob(ext):
            rel_path = extracted_file.relative_to(extracted_path)
            # rel_path starts with repo_name/
            repo_name = rel_path.parts[0]
            
            # 2.1 Resolve Upstream Source Path (Handle MFE specialized naming)
            upstream_source = resolve_upstream_path(rel_path)
            upstream_repo_dir = UPSTREAM_DIR / repo_name
            
            print(f"Processing: {rel_path} (Mapped Upstream: {upstream_source.relative_to(REPO_ROOT) if upstream_source.exists() else 'N/A'})")

            # 2.2 Check if this is a brand new repo not in upstream
            if not upstream_repo_dir.exists():
                print(f"New repo detected: {repo_name}. Skipping diff, treating all as custom.")
                # We save it to custom
                custom_file_path = CUSTOM_DIR / rel_path
                ensure_directory(custom_file_path.parent)
                shutil.copy(extracted_file, custom_file_path)
                
                # Setup placeholders for all languages to ensure full coverage
                if extracted_file.suffix == ".po":
                    create_po_placeholders(extracted_file, rel_path, supported_langs)
                elif extracted_file.suffix == ".json":
                    create_json_placeholders(extracted_file, rel_path, supported_langs)
                continue

            # 2.3 Existing repo: Standard diff logic
            if extracted_file.suffix == ".po":
                process_po_diff(extracted_file, upstream_source, rel_path, supported_langs)
            elif extracted_file.suffix == ".json":
                process_json_diff(extracted_file, upstream_source, rel_path, supported_langs)

def resolve_upstream_path(rel_path):
    """
    Maps an extracted file path to its corresponding upstream path.
    Example: frontend-app-learning/src/i18n/transifex_input.json 
             -> translations-upstream/frontend-app-learning/src/i18n/messages/en.json
    """
    # Default
    upstream_path = UPSTREAM_DIR / rel_path
    
    # MFE Logic: transifex_input.json -> src/i18n/messages/en.json
    if rel_path.name == "transifex_input.json":
        # Check standard MFE messages location
        mfe_upstream = UPSTREAM_DIR / rel_path.parent / "messages" / "en.json"
        if mfe_upstream.exists():
            return mfe_upstream
        # Fallback: maybe it's directly in i18n/en.json?
        mfe_fallback = UPSTREAM_DIR / rel_path.parent / "en.json"
        if mfe_fallback.exists():
            return mfe_fallback
            
    return upstream_path

def create_po_placeholders(extracted_file, rel_path, supported_langs):
    po = polib.pofile(extracted_file)
    for lang in supported_langs:
        parts = list(rel_path.parts)
        try:
            en_index = parts.index("en")
            parts[en_index] = lang
            p_path = CUSTOM_DIR / Path(*parts)
            if not p_path.exists():
                ensure_directory(p_path.parent)
                new_po = polib.POFile()
                new_po.metadata = po.metadata.copy()
                for entry in po:
                    new_po.append(polib.POEntry(msgid=entry.msgid, msgstr="", occurrences=entry.occurrences))
                new_po.save(p_path)
        except ValueError:
            continue

def create_json_placeholders(extracted_file, rel_path, supported_langs):
    """
    For JSON repos, we create <lang>.json entries in the custom layer.
    """
    with open(extracted_file, "r") as f:
        extracted_data = json.load(f)
    
    # For JSON, often the file itself is 'en.json' or 'transifex_input.json'
    # We want to create counterparts for other languages.
    for lang in supported_langs:
        parts = list(rel_path.parts)
        # If the file is 'transifex_input.json' (MFE), we map to messages/<lang>.json
        if rel_path.name == "transifex_input.json":
            # For custom layer, we follow the structured path: /src/i18n/messages/<lang>.json
            p_path = CUSTOM_DIR / rel_path.parent / "messages" / f"{lang}.json"
        else:
            # Generic case: swap 'en' in path or just sibling file
            try:
                en_index = parts.index("en")
                parts[en_index] = lang
                p_path = CUSTOM_DIR / Path(*parts)
            except ValueError:
                # Just sibling with lang name if it's a specific filename
                p_path = CUSTOM_DIR / rel_path.parent / f"{lang}.json"

        if not p_path.exists():
            ensure_directory(p_path.parent)
            # Empty translations
            placeholder_data = {k: "" for k in extracted_data.keys()}
            with open(p_path, "w") as f:
                json.dump(placeholder_data, f, indent=2, sort_keys=True)

def process_po_diff(extracted_file, upstream_source, rel_path, supported_langs):
    upstream_ids = get_msgids(upstream_source)
    extracted_po = polib.pofile(extracted_file)
    custom_entries = [e for e in extracted_po if e.msgid not in upstream_ids]
    
    if not custom_entries:
        print(f"No custom PO strings found for {rel_path}")
        return

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
        parts = list(rel_path.parts)
        try:
            en_index = parts.index("en")
            parts[en_index] = lang
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
                    new_entry = polib.POEntry(msgid=entry.msgid, msgstr="", occurrences=entry.occurrences)
                    custom_lang_po.append(new_entry)
            custom_lang_po.save(custom_lang_path)
        except ValueError:
            continue

def process_json_diff(extracted_file, upstream_source, rel_path, supported_langs):
    # Javascript transifex_input.json is a simple { "msgid": "En String" } map
    with open(extracted_file, "r") as f:
        extracted_data = json.load(f)
    
    if upstream_source.exists():
        with open(upstream_source, "r") as f:
            upstream_data = json.load(f)
    else:
        upstream_data = {}

    custom_keys = [k for k in extracted_data.keys() if k not in upstream_data]
    
    if not custom_keys:
        print(f"No custom JSON strings for {rel_path}")
        return

    print(f"Found {len(custom_keys)} custom JSON strings for {rel_path}")

    # 1. Update English Custom Source
    custom_path = CUSTOM_DIR / rel_path
    ensure_directory(custom_path.parent)
    
    if custom_path.exists():
        with open(custom_path, "r") as f:
            existing_custom = json.load(f)
    else:
        existing_custom = {}

    for k in custom_keys:
        if k not in existing_custom:
            existing_custom[k] = extracted_data[k]
            
    with open(custom_path, "w") as f:
        json.dump(existing_custom, f, indent=2, sort_keys=True)

    # 2. Update Placeholders for all languages
    for lang in supported_langs:
        # Resolve target lang path (MFE style vs Generic style)
        if rel_path.name == "transifex_input.json":
            lang_path = CUSTOM_DIR / rel_path.parent / "messages" / f"{lang}.json"
        else:
            parts = list(rel_path.parts)
            try:
                en_index = parts.index("en")
                parts[en_index] = lang
                lang_path = CUSTOM_DIR / Path(*parts)
            except ValueError:
                lang_path = CUSTOM_DIR / rel_path.parent / f"{lang}.json"

        ensure_directory(lang_path.parent)
        if lang_path.exists():
            with open(lang_path, "r") as f:
                lang_data = json.load(f)
        else:
            lang_data = {}

        for k in custom_keys:
            if k not in lang_data:
                lang_data[k] = "" # New placeholder
        
        with open(lang_path, "w") as f:
            json.dump(lang_data, f, indent=2, sort_keys=True)

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
    for ext in ["**/*.po", "**/*.json"]:
        for custom_file in CUSTOM_DIR.glob(ext):
            rel_path = custom_file.relative_to(CUSTOM_DIR)
            final_file = FINAL_DIR / rel_path
            
            if not final_file.exists():
                # Brand new custom file (e.g. from a new custom repo)
                ensure_directory(final_file.parent)
                shutil.copy(custom_file, final_file)
                continue
                
            # Merge contents
            if custom_file.suffix == ".po":
                upstream_po = polib.pofile(final_file)
                custom_po = polib.pofile(custom_file)
                upstream_map = {e.msgid: e for e in upstream_po}
                for entry in custom_po:
                    if entry.msgid in upstream_map:
                        if entry.msgstr:
                            upstream_map[entry.msgid].msgstr = entry.msgstr
                    else:
                        upstream_po.append(entry)
                upstream_po.save(final_file)
            elif custom_file.suffix == ".json":
                with open(final_file, "r") as f:
                    final_data = json.load(f)
                with open(custom_file, "r") as f:
                    custom_data = json.load(f)
                final_data.update(custom_data)
                with open(final_file, "w") as f:
                    json.dump(final_data, f, indent=2, sort_keys=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    p_update = subparsers.add_parser("update_custom")
    p_update.add_argument("--extracted-dir", required=True)

    p_merge = subparsers.add_parser("merge_final")

    args = parser.parse_args()

    if args.command == "update_custom":
        print(f"Base Directory: {REPO_ROOT}")
        print(f"Upstream Directory: {UPSTREAM_DIR}")
        print(f"Custom Directory: {CUSTOM_DIR}")
        update_custom_layer(args.extracted_dir)
    elif args.command == "merge_final":
        merge_final()
