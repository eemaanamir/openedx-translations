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


def get_supported_languages():
    """
    Determine all supported languages from upstream translations.
    Returns a list of language codes.
    """
    supported_langs = set()

    # Scan upstream for language directories
    for repo_dir in UPSTREAM_DIR.iterdir():
        if not repo_dir.is_dir():
            continue

        # Check for Django-style locale directories
        locale_dir = repo_dir / "conf" / "locale"
        if locale_dir.exists():
            for lang_dir in locale_dir.iterdir():
                if lang_dir.is_dir() and lang_dir.name != "en":
                    supported_langs.add(lang_dir.name)

        # Check for MFE-style i18n directories (src/i18n/messages/)
        i18n_dir = repo_dir / "src" / "i18n" / "messages"
        if i18n_dir.exists():
            for lang_file in i18n_dir.glob("*.json"):
                lang_code = lang_file.stem
                if lang_code != "en":
                    supported_langs.add(lang_code)

    return sorted(list(supported_langs))


def update_custom_layer(extracted_dir):
    """
    Step 3: Update translations-custom based on diff between extracted and upstream.
    Always maintains existing translations.
    Creates placeholders for all languages.
    """
    print(f"--- Updating Custom Layer from {extracted_dir} ---")
    extracted_path = Path(extracted_dir)

    # 1. Determine all supported languages from upstream
    supported_langs = get_supported_languages()
    print(f"Found {len(supported_langs)} supported languages in upstream: {', '.join(supported_langs[:10])}...")

    # 2. Iterate through extracted files (.po and .json)
    for ext in ["**/*.po", "**/*.json"]:
        for extracted_file in extracted_path.glob(ext):
            rel_path = extracted_file.relative_to(extracted_path)
            # rel_path starts with repo_name/
            repo_name = rel_path.parts[0]

            # Find corresponding upstream source file
            upstream_source = UPSTREAM_DIR / rel_path
            upstream_repo_dir = UPSTREAM_DIR / repo_name

            print(
                f"Processing: {rel_path} (Upstream repo exists: {upstream_repo_dir.exists()}, Source exists: {upstream_source.exists()})")

            # Check if this is a brand new repo not in upstream
            if not upstream_repo_dir.exists():
                print(f"New repo detected: {repo_name}. Treating all content as custom.")
                # For new repos, copy everything to custom
                custom_file_path = CUSTOM_DIR / rel_path
                ensure_directory(custom_file_path.parent)
                shutil.copy(extracted_file, custom_file_path)

                # Create placeholders for other languages
                if extracted_file.suffix == ".po":
                    create_po_placeholders(extracted_file, rel_path, supported_langs)
                elif extracted_file.suffix == ".json":
                    create_json_placeholders(extracted_file, rel_path, supported_langs)
                continue

            # Standard diff logic for existing repos
            if extracted_file.suffix == ".po":
                process_po_diff(extracted_file, upstream_source, rel_path, supported_langs)
            elif extracted_file.suffix == ".json":
                process_json_diff(extracted_file, upstream_source, rel_path, supported_langs)


def create_po_placeholders(extracted_file, rel_path, supported_langs):
    """Create empty PO files for all supported languages."""
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
                print(f"  Created placeholder: {p_path}")
        except ValueError:
            continue


def create_json_placeholders(extracted_file, rel_path, supported_langs):
    """
    Create empty JSON message files for all supported languages (MFE pattern).
    Assumes structure: <repo>/src/i18n/messages/en.json
    Creates: <repo>/src/i18n/messages/{lang}.json
    """
    with open(extracted_file, "r") as f:
        en_data = json.load(f)

    parts = list(rel_path.parts)
    try:
        # Find the language code in the path (usually the filename stem)
        if "en.json" in str(rel_path):
            # MFE pattern: src/i18n/messages/en.json
            for lang in supported_langs:
                lang_parts = parts[:-1] + [f"{lang}.json"]
                lang_path = CUSTOM_DIR / Path(*lang_parts)

                if not lang_path.exists():
                    ensure_directory(lang_path.parent)
                    # Create empty placeholder with same keys
                    placeholder_data = {key: "" for key in en_data.keys()}
                    with open(lang_path, "w") as f:
                        json.dump(placeholder_data, f, indent=2, sort_keys=True)
                    print(f"  Created JSON placeholder: {lang_path}")
    except Exception as e:
        print(f"  Warning: Could not create JSON placeholders for {rel_path}: {e}")


def process_po_diff(extracted_file, upstream_source, rel_path, supported_langs):
    """Process PO file diff and update custom layer."""
    upstream_ids = get_msgids(upstream_source)
    extracted_po = polib.pofile(extracted_file)
    custom_entries = [e for e in extracted_po if e.msgid not in upstream_ids]

    if not custom_entries:
        print(f"  No custom PO strings found for {rel_path}")
        return

    print(f"  Found {len(custom_entries)} custom strings for {rel_path}")

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

    new_count = 0
    for entry in custom_entries:
        if entry.msgid not in existing_custom_ids:
            custom_en_po.append(entry)
            new_count += 1

    if new_count > 0:
        custom_en_po.save(custom_en_path)
        print(f"  Added {new_count} new custom strings to {custom_en_path}")

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

            added = 0
            for entry in custom_entries:
                if entry.msgid not in existing_lang_map:
                    new_entry = polib.POEntry(msgid=entry.msgid, msgstr="", occurrences=entry.occurrences)
                    custom_lang_po.append(new_entry)
                    added += 1

            if added > 0:
                custom_lang_po.save(custom_lang_path)
        except ValueError:
            continue


def process_json_diff(extracted_file, upstream_source, rel_path, supported_langs):
    """
    Process JSON diff for MFE transifex_input.json files.
    Only keeps keys that don't exist in upstream.
    """
    with open(extracted_file, "r") as f:
        extracted_data = json.load(f)

    if upstream_source.exists():
        with open(upstream_source, "r") as f:
            upstream_data = json.load(f)
    else:
        upstream_data = {}

    # FIXED: Only keep keys that are NOT in upstream
    custom_data = {k: v for k, v in extracted_data.items() if k not in upstream_data}

    if not custom_data:
        print(f"  No custom JSON strings for {rel_path}")
        return

    print(f"  Found {len(custom_data)} custom JSON keys for {rel_path}")

    custom_path = CUSTOM_DIR / rel_path
    ensure_directory(custom_path.parent)

    if custom_path.exists():
        with open(custom_path, "r") as f:
            existing_custom = json.load(f)
    else:
        existing_custom = {}

    # Merge new custom keys while preserving existing ones
    new_keys = {k: v for k, v in custom_data.items() if k not in existing_custom}
    existing_custom.update(new_keys)

    with open(custom_path, "w") as f:
        json.dump(existing_custom, f, indent=2, sort_keys=True)

    print(f"  Added {len(new_keys)} new custom JSON keys to {custom_path}")

    # FIXED: Create JSON placeholders for MFE localized files
    # Pattern: transifex_input.json -> convert to src/i18n/messages/{lang}.json placeholders
    if "transifex_input.json" in str(rel_path):
        create_mfe_localized_placeholders(custom_data, rel_path, supported_langs)


def create_mfe_localized_placeholders(custom_data, rel_path, supported_langs):
    """
    Create localized JSON placeholders for MFE custom strings.
    Converts transifex_input.json custom keys -> src/i18n/messages/{lang}.json
    """
    # Determine the base path for localized files
    # transifex_input.json is usually at <repo>/src/i18n/transifex_input.json
    # localized files are at <repo>/src/i18n/messages/{lang}.json

    parts = list(rel_path.parts)
    repo_name = parts[0]

    # Construct the messages directory path
    messages_base = CUSTOM_DIR / repo_name / "src" / "i18n" / "messages"
    ensure_directory(messages_base)

    for lang in supported_langs:
        lang_file = messages_base / f"{lang}.json"

        if lang_file.exists():
            with open(lang_file, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = {}

        # Add placeholders for custom keys that don't exist
        new_keys = 0
        for key in custom_data.keys():
            if key not in existing_data:
                existing_data[key] = ""
                new_keys += 1

        if new_keys > 0:
            with open(lang_file, "w") as f:
                json.dump(existing_data, f, indent=2, sort_keys=True)
            print(f"  Created/Updated {lang_file} with {new_keys} placeholder keys")


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
                print(f"  Copied new custom file: {rel_path}")
                continue

            # Merge contents
            if custom_file.suffix == ".po":
                upstream_po = polib.pofile(final_file)
                custom_po = polib.pofile(custom_file)
                upstream_map = {e.msgid: e for e in upstream_po}
                added = 0
                updated = 0
                for entry in custom_po:
                    if entry.msgid in upstream_map:
                        if entry.msgstr:
                            upstream_map[entry.msgid].msgstr = entry.msgstr
                            updated += 1
                    else:
                        upstream_po.append(entry)
                        added += 1
                upstream_po.save(final_file)
                if added > 0 or updated > 0:
                    print(f"  Merged PO {rel_path}: +{added} entries, ~{updated} updated")

            elif custom_file.suffix == ".json":
                with open(final_file, "r") as f:
                    final_data = json.load(f)
                with open(custom_file, "r") as f:
                    custom_data = json.load(f)

                original_count = len(final_data)
                final_data.update(custom_data)
                added = len(final_data) - original_count

                with open(final_file, "w") as f:
                    json.dump(final_data, f, indent=2, sort_keys=True)

                if added > 0:
                    print(f"  Merged JSON {rel_path}: +{added} keys")

    print("--- Merge Complete ---")


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
