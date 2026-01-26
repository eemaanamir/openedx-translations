#!/usr/bin/env python3
"""
cleanup_lang_codes.py

Cleans up non-standard language codes in ALL custom repos (Python + MFE).
Maps pt-br -> pt_BR and zh-hans -> zh_CN in both .po and .json files.

Usage:
    python cleanup_lang_codes.py
    (Run from openedx-translations root directory)
"""

import json
import os
from pathlib import Path
import shutil

# Mappings of non-standard to standard codes
MAPPINGS = {
    'pt-br': 'pt_BR',
    'pt_BR': 'pt_BR',  # Also handle pt_BR -> pt_BR (consolidate)
    'zh-hans': 'zh_CN',
}

CUSTOM_DIR = Path('translations-custom')


def merge_json_files(old_file, new_file):
    """Merge old_file into new_file (or create new_file), then delete old_file."""

    with open(old_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    if new_file.exists():
        with open(new_file, 'r', encoding='utf-8') as f:
            new_data = json.load(f)

        merged_count = 0
        for key, value in old_data.items():
            if key not in new_data or not new_data[key]:
                new_data[key] = value
                merged_count += 1

        print(f"    Merged {merged_count} keys into {new_file.name}")
    else:
        new_data = old_data
        print(f"    Created {new_file.name} with {len(old_data)} keys")

    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, sort_keys=True, ensure_ascii=False)

    old_file.unlink()
    print(f"    ✓ Removed {old_file.name}")


def merge_po_files(old_dir, new_dir):
    """Merge .po files from old language directory into new one, then delete old."""

    try:
        import polib
    except ImportError:
        print("    ERROR: polib not installed. Run: pip install polib")
        return

    # Get all .po files in old directory
    old_po_files = list(old_dir.glob("LC_MESSAGES/*.po"))

    if not old_po_files:
        print(f"    No .po files found in {old_dir}")
        return

    # Ensure new directory exists
    new_lc_dir = new_dir / "LC_MESSAGES"
    new_lc_dir.mkdir(parents=True, exist_ok=True)

    for old_po_file in old_po_files:
        new_po_file = new_lc_dir / old_po_file.name

        old_po = polib.pofile(str(old_po_file))

        if new_po_file.exists():
            # Merge into existing
            new_po = polib.pofile(str(new_po_file))
            existing_msgids = {e.msgid for e in new_po}

            merged_count = 0
            for entry in old_po:
                if entry.msgid and entry.msgid not in existing_msgids:
                    new_po.append(entry)
                    merged_count += 1
                elif entry.msgid in existing_msgids and entry.msgstr:
                    # Update translation if old has it and new doesn't
                    for new_entry in new_po:
                        if new_entry.msgid == entry.msgid and not new_entry.msgstr:
                            new_entry.msgstr = entry.msgstr
                            merged_count += 1
                            break

            new_po.save()
            print(f"    Merged {merged_count} entries into {new_po_file.name}")
        else:
            # Copy entire file
            old_po.save(str(new_po_file))
            print(f"    Created {new_po_file.name} with {len(old_po)} entries")

    # Remove old directory
    shutil.rmtree(old_dir)
    print(f"    ✓ Removed {old_dir.name}/ directory")


def cleanup_mfe_repo(repo_dir):
    """Clean up language codes in MFE repos (.json files)."""

    messages_dir = repo_dir / 'src' / 'i18n' / 'messages'

    if not messages_dir.exists():
        return False

    found_any = False
    for old_name, new_name in MAPPINGS.items():
        if old_name == new_name:  # Skip pt_BR -> pt_BR
            continue

        old_file = messages_dir / f'{old_name}.json'
        new_file = messages_dir / f'{new_name}.json'

        if old_file.exists():
            found_any = True
            print(f"  [MFE] {old_name}.json -> {new_name}.json")
            merge_json_files(old_file, new_file)

    return found_any


def cleanup_python_repo(repo_dir):
    """Clean up language codes in Python repos (.po files)."""

    locale_dir = repo_dir / 'conf' / 'locale'

    # Also check for nested structure
    if not locale_dir.exists():
        nested_locale = repo_dir / repo_dir.name.replace('-', '_') / 'conf' / 'locale'
        if nested_locale.exists():
            locale_dir = nested_locale
        else:
            return False

    found_any = False
    for old_name, new_name in MAPPINGS.items():
        if old_name == new_name:  # Skip pt_BR -> pt_BR
            continue

        old_lang_dir = locale_dir / old_name
        new_lang_dir = locale_dir / new_name

        if old_lang_dir.exists() and old_lang_dir.is_dir():
            found_any = True
            print(f"  [Python] {old_name}/ -> {new_name}/")
            merge_po_files(old_lang_dir, new_lang_dir)

    return found_any


def cleanup_repo(repo_dir):
    """Clean up a single repo (tries both MFE and Python patterns)."""

    print(f"\n📁 {repo_dir.name}")

    mfe_cleaned = cleanup_mfe_repo(repo_dir)
    python_cleaned = cleanup_python_repo(repo_dir)

    if not mfe_cleaned and not python_cleaned:
        print(f"  No files to clean up")
        return False

    return True


def main():
    """Main function to process all repos."""

    if not CUSTOM_DIR.exists():
        print(f"ERROR: {CUSTOM_DIR} directory not found!")
        print("Make sure you're running this from the openedx-translations root directory")
        return

    print("=" * 60)
    print("Cleaning up non-standard language codes in ALL custom repos")
    print("=" * 60)
    print(f"Mappings: {MAPPINGS}")
    print(f"Scanning: {CUSTOM_DIR}/")

    total_repos_processed = 0

    for repo_dir in sorted(CUSTOM_DIR.iterdir()):
        if not repo_dir.is_dir():
            continue

        if cleanup_repo(repo_dir):
            total_repos_processed += 1

    print("\n" + "=" * 60)
    print(f"✓ Done! Processed {total_repos_processed} repos")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review changes: git diff translations-custom/")
    print("2. Commit: git add translations-custom/ && git commit -m 'fix: standardize language codes'")
    print("3. Push changes to actual custom repos")
    print("4. Run workflow - translations/ will auto-update with correct codes")


if __name__ == '__main__':
    main()
