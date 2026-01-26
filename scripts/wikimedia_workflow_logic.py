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
    """Get all msgids from a PO file, handling edge cases."""
    if not os.path.exists(po_file_path):
        return set()
    try:
        po = polib.pofile(po_file_path)
        # Filter out empty msgids and metadata entries
        return {entry.msgid for entry in po if entry.msgid and not entry.obsolete}
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

        # Check for Django-style locale directories (including nested structures)
        for locale_dir in repo_dir.rglob("locale"):
            if locale_dir.is_dir():
                for lang_dir in locale_dir.iterdir():
                    if lang_dir.is_dir() and lang_dir.name != "en":
                        supported_langs.add(lang_dir.name)

        # Check for MFE-style i18n directories (src/i18n/messages/)
        for i18n_dir in repo_dir.rglob("i18n"):
            messages_dir = i18n_dir / "messages"
            if messages_dir.exists():
                for lang_file in messages_dir.glob("*.json"):
                    lang_code = lang_file.stem
                    if lang_code != "en":
                        supported_langs.add(lang_code)

    return sorted(list(supported_langs))


def update_custom_layer(extracted_dir):
    """
    Step 3: Update translations-custom based on diff between extracted and upstream.
    Always maintains existing translations.
    Creates placeholders for all languages.
    Handles BOTH django.po and djangojs.po files.
    """
    print(f"--- Updating Custom Layer from {extracted_dir} ---")
    extracted_path = Path(extracted_dir)

    # 1. Determine all supported languages from upstream
    supported_langs = get_supported_languages()
    print(f"Found {len(supported_langs)} supported languages in upstream: {', '.join(supported_langs[:10])}...")

    # 2. Iterate through extracted files (.po and .json)
    # IMPORTANT: Process both django.po and djangojs.po
    for ext in ["**/*.po", "**/*.json"]:
        for extracted_file in extracted_path.glob(ext):
            rel_path = extracted_file.relative_to(extracted_path)
            # rel_path starts with repo_name/
            repo_name = rel_path.parts[0]

            # Find corresponding upstream source file
            upstream_source = UPSTREAM_DIR / rel_path
            upstream_repo_dir = UPSTREAM_DIR / repo_name

            # Identify file type for logging
            file_type = "unknown"
            if "djangojs.po" in str(rel_path):
                file_type = "djangojs.po (JavaScript)"
            elif "django.po" in str(rel_path):
                file_type = "django.po (Templates/Python)"
            elif "transifex_input.json" in str(rel_path):
                file_type = "transifex_input.json (MFE source)"
            elif ".json" in str(rel_path):
                file_type = "JSON (MFE)"

            print(
                f"Processing: {rel_path} [{file_type}] (Upstream repo exists: {upstream_repo_dir.exists()}, Source exists: {upstream_source.exists()})")

            # Check if this is a brand new repo not in upstream
            if not upstream_repo_dir.exists():
                print(f"New repo detected: {repo_name}. Treating all content as custom.")

                # Copy English source to custom
                custom_file_path = CUSTOM_DIR / rel_path
                ensure_directory(custom_file_path.parent)
                shutil.copy(extracted_file, custom_file_path)
                print(f"  → Copied to custom: {custom_file_path}")

                # Create/update placeholders for other languages
                if extracted_file.suffix == ".po":
                    create_or_update_po_placeholders(extracted_file, rel_path, supported_langs)
                elif extracted_file.suffix == ".json":
                    create_or_update_json_placeholders(extracted_file, rel_path, supported_langs)
                continue

            # Standard diff logic for existing repos
            if extracted_file.suffix == ".po":
                process_po_diff(extracted_file, upstream_source, rel_path, supported_langs)
            elif extracted_file.suffix == ".json":
                process_json_diff(extracted_file, upstream_source, rel_path, supported_langs)


def create_or_update_po_placeholders(extracted_file, rel_path, supported_langs):
    """
    Create NEW PO files OR update EXISTING ones with new strings for all supported languages.
    Handles both django.po and djangojs.po files.
    Supports nested repo structures.
    """
    print(f"  Creating/updating PO placeholders for {len(supported_langs)} languages...")

    try:
        po = polib.pofile(extracted_file)
        en_entries = {e.msgid: e for e in po if e.msgid and not e.obsolete}
    except Exception as e:
        print(f"  WARNING: Cannot read extracted file for placeholders: {e}")
        return

    created = 0
    updated = 0
    skipped = 0

    for lang in supported_langs:
        parts = list(rel_path.parts)

        try:
            # Find 'en' in the path - it should be in locale/en pattern
            en_index = parts.index("en")

            # Verify this is a locale/en pattern
            if en_index > 0 and parts[en_index - 1] == "locale":
                parts[en_index] = lang
                p_path = CUSTOM_DIR / Path(*parts)

                if p_path.exists():
                    # File exists - update it with new strings
                    try:
                        existing_po = polib.pofile(p_path)
                        existing_msgids = {e.msgid for e in existing_po}

                        added = 0
                        for msgid, entry in en_entries.items():
                            if msgid not in existing_msgids:
                                existing_po.append(polib.POEntry(
                                    msgid=msgid,
                                    msgstr="",
                                    occurrences=entry.occurrences
                                ))
                                added += 1

                        if added > 0:
                            existing_po.save(p_path)
                            updated += 1
                            print(f"    ✅ Updated {lang}: +{added} strings")
                        else:
                            skipped += 1
                    except Exception as e:
                        print(f"    ❌ ERROR updating {lang}: {e}")
                else:
                    # File doesn't exist - create it
                    ensure_directory(p_path.parent)
                    new_po = polib.POFile()
                    new_po.metadata = po.metadata.copy()

                    # Preserve Domain metadata for djangojs.po files
                    if "djangojs" in str(rel_path):
                        new_po.metadata['Domain'] = 'djangojs'

                    for entry in po:
                        if entry.msgid:
                            new_po.append(polib.POEntry(
                                msgid=entry.msgid,
                                msgstr="",
                                occurrences=entry.occurrences
                            ))
                    new_po.save(p_path)
                    created += 1
                    print(f"    ✅ Created {lang}: {len(en_entries)} strings")
        except ValueError:
            print(f"  WARNING: Could not find 'en' in path for {rel_path}, skipping placeholder creation")
            continue

    print(f"  Summary: Created {created}, Updated {updated}, Already synced {skipped}")


def create_or_update_json_placeholders(extracted_file, rel_path, supported_langs):
    """
    Create NEW JSON files OR update EXISTING ones for all supported languages (MFE pattern).
    Handles both transifex_input.json and direct message files.
    """
    print(f"  Creating/updating JSON placeholders for {len(supported_langs)} languages...")

    try:
        with open(extracted_file, "r", encoding="utf-8") as f:
            en_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Malformed JSON in {extracted_file}: {e}")
        return
    except Exception as e:
        print(f"  ERROR reading {extracted_file}: {e}")
        return

    # Determine messages directory based on extracted file location
    repo_name = rel_path.parts[0]
    messages_dir = CUSTOM_DIR / repo_name / "src" / "i18n" / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    updated = 0
    skipped = 0

    # Create/update placeholder for each language
    for lang in supported_langs:
        lang_path = messages_dir / f"{lang}.json"

        if lang_path.exists():
            # File exists - update with new keys
            try:
                with open(lang_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except:
                existing_data = {}

            new_keys = {k: "" for k in en_data.keys() if k not in existing_data}

            if new_keys:
                existing_data.update(new_keys)
                with open(lang_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=2, sort_keys=True, ensure_ascii=False)
                updated += 1
                print(f"    ✅ Updated {lang}: +{len(new_keys)} keys")
            else:
                skipped += 1
        else:
            # File doesn't exist - create it
            placeholder_data = {key: "" for key in en_data.keys()}
            with open(lang_path, "w", encoding="utf-8") as f:
                json.dump(placeholder_data, f, indent=2, sort_keys=True, ensure_ascii=False)
            created += 1
            print(f"    ✅ Created {lang}: {len(en_data)} keys")

    print(f"  Summary: Created {created}, Updated {updated}, Already synced {skipped}")


def process_po_diff(extracted_file, upstream_source, rel_path, supported_langs):
    """
    Process PO file diff and update custom layer.
    Updates existing placeholder files with new custom strings.
    """
    upstream_ids = get_msgids(upstream_source)

    try:
        extracted_po = polib.pofile(extracted_file)
    except Exception as e:
        print(f"  ERROR: Cannot read extracted PO file {rel_path}: {e}")
        return

    # Filter out empty msgids and metadata
    custom_entries = [e for e in extracted_po if e.msgid and not e.obsolete and e.msgid not in upstream_ids]

    if not custom_entries:
        print(f"  No custom PO strings found for {rel_path}")
        return

    print(f"  Found {len(custom_entries)} custom strings for {rel_path}")

    # Update English Custom File
    custom_en_path = CUSTOM_DIR / rel_path
    ensure_directory(custom_en_path.parent)

    if custom_en_path.exists():
        try:
            custom_en_po = polib.pofile(custom_en_path)
            existing_custom_ids = {e.msgid for e in custom_en_po}
        except Exception as e:
            print(f"  WARNING: Cannot read existing custom file, creating new: {e}")
            custom_en_po = polib.POFile()
            custom_en_po.metadata = extracted_po.metadata.copy()
            existing_custom_ids = set()
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
            # Find 'en' in the path - it should be in locale/en pattern
            en_index = parts.index("en")

            # Verify this is actually a locale directory
            if en_index > 0 and parts[en_index - 1] == "locale":
                parts[en_index] = lang
                custom_lang_path = CUSTOM_DIR / Path(*parts)
                ensure_directory(custom_lang_path.parent)

                if custom_lang_path.exists():
                    try:
                        custom_lang_po = polib.pofile(custom_lang_path)
                        existing_lang_map = {e.msgid: e for e in custom_lang_po}
                    except Exception as e:
                        print(f"  WARNING: Cannot read existing placeholder for {lang}, creating new: {e}")
                        custom_lang_po = polib.POFile()
                        custom_lang_po.metadata = extracted_po.metadata.copy()
                        existing_lang_map = {}
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
                    updated_count += 1
        except ValueError:
            print(f"  WARNING: Could not find 'en' in path for {rel_path}, skipping language {lang}")
            continue

    if updated_count > 0:
        print(f"  Updated {updated_count} language placeholder files")


def process_json_diff(extracted_file, upstream_source, rel_path, supported_langs):
    """
    Process JSON diff for MFE transifex_input.json files.
    Only keeps keys that don't exist in upstream.
    Updates existing placeholder files with new keys.
    """
    try:
        with open(extracted_file, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ERROR: Malformed extracted JSON {rel_path}: {e}")
        return
    except Exception as e:
        print(f"  ERROR reading extracted JSON {rel_path}: {e}")
        return

    if upstream_source.exists():
        try:
            with open(upstream_source, "r", encoding="utf-8") as f:
                upstream_data = json.load(f)
        except:
            upstream_data = {}
    else:
        upstream_data = {}

    # Only keep keys that are NOT in upstream
    custom_data = {k: v for k, v in extracted_data.items() if k not in upstream_data}

    if not custom_data:
        print(f"  No custom JSON strings for {rel_path}")
        return

    print(f"  Found {len(custom_data)} custom JSON keys for {rel_path}")

    custom_path = CUSTOM_DIR / rel_path
    ensure_directory(custom_path.parent)

    if custom_path.exists():
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                existing_custom = json.load(f)
        except:
            existing_custom = {}
    else:
        existing_custom = {}

    # Merge new custom keys while preserving existing ones
    new_keys = {k: v for k, v in custom_data.items() if k not in existing_custom}
    existing_custom.update(new_keys)

    try:
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(existing_custom, f, indent=2, sort_keys=True, ensure_ascii=False)

        print(f"  Added {len(new_keys)} new custom JSON keys to {custom_path}")
    except Exception as e:
        print(f"  ERROR writing custom JSON {custom_path}: {e}")
        return

    # Update MFE localized placeholders
    if "transifex_input.json" in str(rel_path):
        update_mfe_localized_placeholders(custom_data, rel_path, supported_langs)


def update_mfe_localized_placeholders(custom_data, rel_path, supported_langs):
    """
    Create/update localized JSON placeholders for MFE custom strings.
    Converts transifex_input.json custom keys -> src/i18n/messages/{lang}.json
    """
    parts = list(rel_path.parts)
    repo_name = parts[0]
    messages_base = CUSTOM_DIR / repo_name / "src" / "i18n" / "messages"
    ensure_directory(messages_base)

    print(f"  Updating MFE localized files for {len(supported_langs)} languages...")

    updated_count = 0
    for lang in supported_langs:
        lang_file = messages_base / f"{lang}.json"

        try:
            if lang_file.exists():
                with open(lang_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            else:
                existing_data = {}
        except:
            existing_data = {}

        # Add placeholders for custom keys that don't exist
        new_keys = 0
        for key in custom_data.keys():
            if key not in existing_data:
                existing_data[key] = ""
                new_keys += 1

        if new_keys > 0:
            try:
                with open(lang_file, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=2, sort_keys=True, ensure_ascii=False)
                updated_count += 1
            except Exception as e:
                print(f"    ❌ ERROR writing {lang}: {e}")

    if updated_count > 0:
        print(f"    Updated {updated_count} MFE language files")


def merge_final():
    """
    Step 4: Combine Upstream and Custom Layer.
    Handles languages that exist in custom but not in upstream.
    Excludes dummy/test locales (qqq) from custom overlay only.
    """
    print("--- Merging Final Layer (Step 4) ---")

    # Languages to exclude from custom overlay (keep in upstream as-is)
    exclude_langs = {'qqq'}

    if FINAL_DIR.exists():
        shutil.rmtree(FINAL_DIR)

    # Start with upstream (includes qqq from upstream)
    shutil.copytree(UPSTREAM_DIR, FINAL_DIR)

    # Overlay custom - skip excluded languages
    for ext in ["**/*.po", "**/*.json"]:
        for custom_file in CUSTOM_DIR.glob(ext):
            rel_path = custom_file.relative_to(CUSTOM_DIR)

            # Skip excluded languages from custom
            skip = False
            for lang in exclude_langs:
                if f"/{lang}/" in str(rel_path) or f"/{lang}.json" in str(rel_path):
                    skip = True
                    break

            if skip:
                continue

            final_file = FINAL_DIR / rel_path

            if not final_file.exists():
                # New file (could be new repo, new language, or both)
                ensure_directory(final_file.parent)
                shutil.copy(custom_file, final_file)
                print(f"  Copied new custom file: {rel_path}")
                continue

            # Merge contents for existing files
            if custom_file.suffix == ".po":
                try:
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
                except Exception as e:
                    print(f"  ERROR merging PO {rel_path}: {e}")
                    print(f"  Skipping malformed file and using custom version")
                    shutil.copy(custom_file, final_file)

            elif custom_file.suffix == ".json":
                try:
                    with open(final_file, "r", encoding="utf-8") as f:
                        final_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"  WARNING: Malformed upstream JSON {rel_path}: {e}")
                    print(f"  Using custom file as base instead")
                    shutil.copy(custom_file, final_file)
                    continue
                except Exception as e:
                    print(f"  ERROR reading upstream JSON {rel_path}: {e}")
                    shutil.copy(custom_file, final_file)
                    continue

                try:
                    with open(custom_file, "r", encoding="utf-8") as f:
                        custom_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"  WARNING: Malformed custom JSON {rel_path}: {e}")
                    print(f"  Skipping custom overlay for this file")
                    continue
                except Exception as e:
                    print(f"  ERROR reading custom JSON {rel_path}: {e}")
                    continue

                try:
                    original_count = len(final_data)
                    final_data.update(custom_data)
                    added = len(final_data) - original_count

                    with open(final_file, "w", encoding="utf-8") as f:
                        json.dump(final_data, f, indent=2, sort_keys=True, ensure_ascii=False)

                    if added > 0:
                        print(f"  Merged JSON {rel_path}: +{added} keys")
                except Exception as e:
                    print(f"  ERROR writing merged JSON {rel_path}: {e}")

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
