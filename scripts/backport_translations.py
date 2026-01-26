#!/usr/bin/env python3
"""
Backport translations from old wm-*.po files to new custom translations structure.

Usage:
    python backport_translations.py /path/to/old/translations/conf/locale

This script will:
1. Read all wm-django.po and wm-djangojs.po files from the old structure
2. Create placeholders for languages that don't exist in custom repos yet
3. Search for matching msgids in translations-custom/
4. Copy translations to all matching locations
5. Generate a report of what was migrated and what wasn't found
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import polib

# Get the current directory (should be openedx-translations root)
REPO_ROOT = Path.cwd()
CUSTOM_DIR = REPO_ROOT / "translations-custom"


class TranslationBackporter:
    def __init__(self, old_locale_path):
        self.old_locale_path = Path(old_locale_path)
        self.stats = {
            'languages_processed': 0,
            'old_strings_found': 0,
            'strings_migrated': 0,
            'strings_not_found': 0,
            'files_updated': 0,
            'placeholders_created': 0,
        }
        self.not_found = []
        self.migrated = []

        if not self.old_locale_path.exists():
            print(f"ERROR: Path does not exist: {self.old_locale_path}")
            sys.exit(1)

        if not CUSTOM_DIR.exists():
            print(f"ERROR: translations-custom/ directory not found at {CUSTOM_DIR}")
            print("Make sure you're running this from the openedx-translations root directory")
            sys.exit(1)

    def get_old_translations(self):
        """Get all translations from old wm-*.po files."""
        print("\n=== Step 1: Reading old wm-*.po files ===")
        old_translations = {}

        for lang_dir in self.old_locale_path.iterdir():
            if not lang_dir.is_dir():
                continue

            lang_code = lang_dir.name
            lc_messages_dir = lang_dir / "LC_MESSAGES"

            if not lc_messages_dir.exists():
                continue

            print(f"\nProcessing language: {lang_code}")
            old_translations[lang_code] = {}

            # Read wm-django.po
            wm_django = lc_messages_dir / "wm-django.po"
            if wm_django.exists():
                try:
                    po = polib.pofile(str(wm_django))
                    count = 0
                    for entry in po:
                        if entry.msgid and entry.msgstr and not entry.obsolete:
                            old_translations[lang_code][entry.msgid] = entry.msgstr
                            count += 1
                    print(f"  Found {count} translations in wm-django.po")
                    self.stats['old_strings_found'] += count
                except Exception as e:
                    print(f"  ERROR reading {wm_django}: {e}")

            # Read wm-djangojs.po
            wm_djangojs = lc_messages_dir / "wm-djangojs.po"
            if wm_djangojs.exists():
                try:
                    po = polib.pofile(str(wm_djangojs))
                    count = 0
                    for entry in po:
                        if entry.msgid and entry.msgstr and not entry.obsolete:
                            old_translations[lang_code][entry.msgid] = entry.msgstr
                            count += 1
                    print(f"  Found {count} translations in wm-djangojs.po")
                    self.stats['old_strings_found'] += count
                except Exception as e:
                    print(f"  ERROR reading {wm_djangojs}: {e}")

            if lang_code in old_translations and old_translations[lang_code]:
                self.stats['languages_processed'] += 1

        print(
            f"\n✓ Total: {self.stats['old_strings_found']} translations from {self.stats['languages_processed']} languages")
        return old_translations

    def find_and_update_po_files(self, lang_code, msgid, msgstr):
        """Find and update .po files in custom repos (handles nested structures)."""
        updated_count = 0
        repos_updated = []

        # Search more broadly to catch nested structures
        for po_file in CUSTOM_DIR.glob(f"**/{lang_code}/LC_MESSAGES/*.po"):
            try:
                po = polib.pofile(str(po_file))
                found = False

                for entry in po:
                    if entry.msgid == msgid:
                        if not entry.msgstr or entry.msgstr != msgstr:
                            entry.msgstr = msgstr
                            found = True
                            break

                if found:
                    po.save()
                    updated_count += 1
                    repo_name = po_file.relative_to(CUSTOM_DIR).parts[0]
                    repos_updated.append(f"{repo_name}/{po_file.name}")

            except Exception as e:
                print(f"  WARNING: Error processing {po_file}: {e}")

        return updated_count, repos_updated

    def find_and_update_json_files(self, lang_code, msgid, msgstr):
        """Find and update MFE .json files using key-based lookup."""
        updated_count = 0
        repos_updated = []

        # Search for transifex_input.json in various locations
        for transifex_file in CUSTOM_DIR.glob("**/transifex_input.json"):
            # Skip if it's not in an i18n directory or repo root
            if "i18n" not in str(transifex_file) and transifex_file.parent.name != transifex_file.parent.parent.name:
                continue

            try:
                # Read transifex_input.json to find key for this msgid
                with open(transifex_file, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)

                # Find keys that have this English string as value
                matching_keys = [key for key, value in input_data.items() if value == msgid]

                if not matching_keys:
                    continue

                # Determine where the language file should be
                if "src/i18n" in str(transifex_file):
                    lang_file = transifex_file.parent / "messages" / f"{lang_code}.json"
                else:
                    # Root level transifex_input.json
                    lang_file = transifex_file.parent / "messages" / f"{lang_code}.json"

                if not lang_file.exists():
                    continue

                with open(lang_file, 'r', encoding='utf-8') as f:
                    lang_data = json.load(f)

                file_updated = False
                for key in matching_keys:
                    if key in lang_data:
                        if not lang_data[key] or lang_data[key] != msgstr:
                            lang_data[key] = msgstr
                            file_updated = True

                if file_updated:
                    with open(lang_file, 'w', encoding='utf-8') as f:
                        json.dump(lang_data, f, indent=2, sort_keys=True, ensure_ascii=False)

                    updated_count += 1
                    repo_name = transifex_file.relative_to(CUSTOM_DIR).parts[0]
                    repos_updated.append(f"{repo_name}/{lang_file.name}")

            except Exception as e:
                print(f"  WARNING: Error processing {transifex_file}: {e}")

        return updated_count, repos_updated

    def ensure_language_placeholders(self, lang_code):
        """Create placeholder files for a language if they don't exist."""
        created_count = 0

        for repo_dir in CUSTOM_DIR.iterdir():
            if not repo_dir.is_dir():
                continue

            # MFE repos - check for transifex_input.json in multiple locations
            transifex_locations = [
                repo_dir / "src" / "i18n" / "transifex_input.json",
                # Some repos might have it at root
                repo_dir / "transifex_input.json",
            ]

            for transifex_file in transifex_locations:
                if transifex_file.exists():
                    # Found transifex_input.json, create language file
                    messages_dir = transifex_file.parent
                    if transifex_file.name == "transifex_input.json" and "i18n" in str(transifex_file):
                        messages_dir = transifex_file.parent / "messages"
                    elif transifex_file.name == "transifex_input.json":
                        # At root level, create messages dir
                        messages_dir = transifex_file.parent / "messages"

                    messages_dir.mkdir(exist_ok=True)
                    lang_file = messages_dir / f"{lang_code}.json"

                    if not lang_file.exists():
                        try:
                            with open(transifex_file, 'r', encoding='utf-8') as f:
                                input_data = json.load(f)

                            placeholder_data = {key: "" for key in input_data.keys()}

                            with open(lang_file, 'w', encoding='utf-8') as f:
                                json.dump(placeholder_data, f, indent=2, sort_keys=True, ensure_ascii=False)

                            created_count += 1
                        except Exception as e:
                            pass
                    break  # Found and processed, don't check other locations

            # Django/Python repos - check for conf/locale in multiple locations
            locale_locations = [
                repo_dir / "conf" / "locale" / "en" / "LC_MESSAGES",
                # Some repos have nested structure like openedx_wikilearn_features/conf/locale
                repo_dir / repo_dir.name.replace("-", "_") / "conf" / "locale" / "en" / "LC_MESSAGES",
            ]

            for en_locale_dir in locale_locations:
                if en_locale_dir.exists():
                    # Calculate the base locale directory
                    base_locale_dir = en_locale_dir.parent.parent
                    lang_locale_dir = base_locale_dir / lang_code / "LC_MESSAGES"

                    if not lang_locale_dir.exists():
                        lang_locale_dir.mkdir(parents=True, exist_ok=True)

                    # django.po
                    django_po = lang_locale_dir / "django.po"
                    if not django_po.exists():
                        en_django = en_locale_dir / "django.po"
                        if en_django.exists():
                            try:
                                en_po = polib.pofile(str(en_django))
                                new_po = polib.POFile()
                                new_po.metadata = en_po.metadata.copy()

                                for entry in en_po:
                                    if entry.msgid:
                                        new_po.append(polib.POEntry(
                                            msgid=entry.msgid,
                                            msgstr="",
                                            occurrences=entry.occurrences
                                        ))

                                new_po.save(str(django_po))
                                created_count += 1
                            except Exception as e:
                                pass

                    # djangojs.po
                    djangojs_po = lang_locale_dir / "djangojs.po"
                    if not djangojs_po.exists():
                        en_djangojs = en_locale_dir / "djangojs.po"
                        if en_djangojs.exists():
                            try:
                                en_po = polib.pofile(str(en_djangojs))
                                new_po = polib.POFile()
                                new_po.metadata = en_po.metadata.copy()
                                new_po.metadata['Domain'] = 'djangojs'

                                for entry in en_po:
                                    if entry.msgid:
                                        new_po.append(polib.POEntry(
                                            msgid=entry.msgid,
                                            msgstr="",
                                            occurrences=entry.occurrences
                                        ))

                                new_po.save(str(djangojs_po))
                                created_count += 1
                            except Exception as e:
                                pass

                    break  # Found and processed, don't check other locations

        if created_count > 0:
            print(f"  ✓ Created {created_count} placeholder files for {lang_code}")
            self.stats['placeholders_created'] += created_count

        return created_count

    def backport_translations(self, old_translations):
        """Main backport logic."""
        print("\n=== Step 2: Backporting translations to custom repos ===")

        for lang_code, translations in old_translations.items():
            if not translations:
                continue

            print(f"\nProcessing language: {lang_code} ({len(translations)} strings)")

            # Create placeholders for this language
            self.ensure_language_placeholders(lang_code)

            lang_migrated = 0
            lang_not_found = 0

            for i, (msgid, msgstr) in enumerate(translations.items(), 1):
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(translations)} strings processed...")

                po_updated, po_repos = self.find_and_update_po_files(lang_code, msgid, msgstr)
                json_updated, json_repos = self.find_and_update_json_files(lang_code, msgid, msgstr)

                total_updated = po_updated + json_updated
                all_repos = po_repos + json_repos

                if total_updated > 0:
                    self.stats['strings_migrated'] += 1
                    self.stats['files_updated'] += total_updated
                    lang_migrated += 1
                    self.migrated.append((lang_code, msgid, all_repos))
                else:
                    self.stats['strings_not_found'] += 1
                    lang_not_found += 1
                    self.not_found.append((lang_code, msgid, msgstr))

            print(f"  ✓ {lang_code}: Migrated {lang_migrated}, Not found {lang_not_found}")

    def generate_report(self):
        """Generate detailed report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = REPO_ROOT / f"backport_report_{timestamp}.txt"

        print(f"\n=== Step 3: Generating report ===")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("TRANSLATION BACKPORT REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Old translations path: {self.old_locale_path}\n\n")

            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Languages processed:           {self.stats['languages_processed']}\n")
            f.write(f"Old translation strings:       {self.stats['old_strings_found']}\n")
            f.write(f"Strings successfully migrated: {self.stats['strings_migrated']}\n")
            f.write(f"Strings not found:             {self.stats['strings_not_found']}\n")
            f.write(f"Files updated:                 {self.stats['files_updated']}\n")
            f.write(f"Placeholder files created:     {self.stats['placeholders_created']}\n\n")

            if self.stats['old_strings_found'] > 0:
                success_rate = (self.stats['strings_migrated'] / self.stats['old_strings_found']) * 100
                f.write(f"Migration success rate:        {success_rate:.1f}%\n\n\n")

            f.write("=" * 80 + "\n")
            f.write("STRINGS NOT FOUND IN CUSTOM REPOS\n")
            f.write("=" * 80 + "\n\n")

            by_lang = {}
            for lang, msgid, msgstr in self.not_found:
                if lang not in by_lang:
                    by_lang[lang] = []
                by_lang[lang].append((msgid, msgstr))

            for lang in sorted(by_lang.keys()):
                f.write(f"\n{lang} ({len(by_lang[lang])} strings):\n")
                f.write("-" * 80 + "\n")
                for msgid, msgstr in by_lang[lang][:50]:
                    f.write(f"  msgid:  {msgid[:70]}\n")
                    f.write(f"  msgstr: {msgstr[:70]}\n\n")

                if len(by_lang[lang]) > 50:
                    f.write(f"  ... and {len(by_lang[lang]) - 50} more\n\n")

            f.write("\n\n" + "=" * 80 + "\n")
            f.write("SAMPLE OF SUCCESSFULLY MIGRATED STRINGS\n")
            f.write("=" * 80 + "\n\n")

            for lang, msgid, repos in self.migrated[:100]:
                f.write(f"{lang}: {msgid[:60]}\n")
                f.write(f"  → Updated in: {', '.join(repos)}\n\n")

        print(f"✓ Report saved to: {report_file}")
        return report_file

    def run(self):
        """Main execution flow."""
        print("=" * 80)
        print("TRANSLATION BACKPORT TOOL")
        print("=" * 80)
        print(f"Old translations: {self.old_locale_path}")
        print(f"Custom translations: {CUSTOM_DIR}\n")

        old_translations = self.get_old_translations()

        if not old_translations:
            print("\nERROR: No translations found in old structure!")
            sys.exit(1)

        self.backport_translations(old_translations)
        report_file = self.generate_report()

        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE!")
        print("=" * 80)
        print(f"✓ Languages processed:    {self.stats['languages_processed']}")
        print(f"✓ Strings migrated:       {self.stats['strings_migrated']}")
        print(f"✓ Files updated:          {self.stats['files_updated']}")
        print(f"✓ Placeholders created:   {self.stats['placeholders_created']}")
        print(f"⚠ Strings not found:      {self.stats['strings_not_found']}")
        print(f"\n📄 Full report: {report_file}")
        print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python backport_translations.py /path/to/old/translations/conf/locale")
        print("\nExample:")
        print("  python backport_translations.py /home/user/old-edx-platform/conf/locale")
        sys.exit(1)

    old_locale_path = sys.argv[1]
    backporter = TranslationBackporter(old_locale_path)
    backporter.run()
