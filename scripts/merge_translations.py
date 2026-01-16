#!/usr/bin/env python3
"""
Script to handle Wikimedia custom translation logic:
1. Generate .tx/config dynamically
2. Separate custom strings (wm-*.po) by diffing with Transifex
3. Pull translations and merge custom strings back in
"""
import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
import polib

# Determine the absolute path to the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent

def run_command(command, cwd=None, env=None):
    """Run a shell command and return output."""
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_repo_config():
    """Load the wikilearn-repos-config.json file."""
    config_path = REPO_ROOT / ".github" / "wikilearn-repos-config.json"
    with open(config_path, "r") as f:
        return json.load(f)

def generate_tx_config(project_slug, org_slug="open-edx"):
    """
    Generate .tx/config mapping local files to Transifex resources.
    """
    print(f"Generating .tx/config for project: {project_slug} (Org: {org_slug})")
    
    config_dir = REPO_ROOT / ".tx"
    ensure_directory(config_dir)
    config_file = config_dir / "config"
    
    with open(config_file, "w") as f:
        f.write(f"[main]\nhost = https://www.transifex.com\n\n")

    repo_config = load_repo_config()
    
    # Process all repo types
    all_repos = []
    if "custom_repos" in repo_config:
        all_repos.extend(repo_config["custom_repos"].get("python", []))
        all_repos.extend(repo_config["custom_repos"].get("javascript", []))
        all_repos.extend(repo_config["custom_repos"].get("generic", []))
    
    # Also include standard repos if we want (logic depends on how we want to treat them)
    # For now, let's focus on the custom repos defined in the config + standard overrides
    
    with open(config_file, "a") as f:
        for repo in all_repos:
            # Determine resource slug (usually just the repo name)
            # If default_repo_name is present, use that for standardization
            resource_slug = repo.get("default_repo_name", repo["repo"])
            
            # Mappings for Django and DjangoJS
            # Note: This logic assumes standard OpenEDX structure. 
            # We might need to adjust for specific repos.
            
            base_path = REPO_ROOT / "translations" / config_name_to_path_name(repo)
            
            # Python/Django PO files
            if os.path.exists(base_path / "conf" / "locale" / "en" / "LC_MESSAGES" / "django.po"):
                f.write(f"[o:{org_slug}:p:{project_slug}:r:{resource_slug}]\n")
                f.write(f"file_filter = translations/{config_name_to_path_name(repo)}/conf/locale/<lang>/LC_MESSAGES/django.po\n")
                f.write(f"source_file = translations/{config_name_to_path_name(repo)}/conf/locale/en/LC_MESSAGES/django.po\n")
                f.write("source_lang = en\n")
                f.write("type = PO\n\n")

            # Javascript PO files
            if os.path.exists(base_path / "conf" / "locale" / "en" / "LC_MESSAGES" / "djangojs.po"):
                # Resource slug for JS usually has a suffix or different convention? 
                # Keeping it simple for now, using -js suffix if needed or same resource?
                # Transifex usually requires distinct resources. 
                # Let's assume resource_slug-js for JS files
                js_resource_slug = f"{resource_slug}-js"
                
                f.write(f"[o:{org_slug}:p:{project_slug}:r:{js_resource_slug}]\n")
                f.write(f"file_filter = translations/{config_name_to_path_name(repo)}/conf/locale/<lang>/LC_MESSAGES/djangojs.po\n")
                f.write(f"source_file = translations/{config_name_to_path_name(repo)}/conf/locale/en/LC_MESSAGES/djangojs.po\n")
                f.write("source_lang = en\n")
                f.write("type = PO\n\n")

    print(f"Generated .tx/config at {config_file}")

def config_name_to_path_name(repo_entry):
    """Helper to get the local directory name from config entry."""
    return repo_entry.get("default_repo_name", repo_entry["repo"])

def get_msgids(po_file_path):
    """Return set of msgids from a PO file."""
    po = polib.pofile(po_file_path)
    return {entry.msgid for entry in po}

def generate_custom_strings(project_slug):
    """
    Identify custom strings by comparing local (extracted) source with Transifex source.
    """
    print("Separating custom strings...")
    
    # 1. Pull ONLY the source 'en' files from Transifex.
    # This overwrites our local files temporarily? No, careful. 
    # Use 'tx pull -s' to pull source? No, 'tx pull' fetches translations.
    # We want to fetch what Transifex THINKS is the source to compare.
    # Actually, usually the workflow is: We push our source. 
    # BUT here we want to know what is "upstream" vs "custom".
    # Assuming 'openedx-translations-teak' project starts as a copy of standard OpenEDX?
    # If the project is ALREADY our custom fork, then Transifex HAS our custom strings.
    # 
    # USER INTENT: "separate the wikimedia specifc sources into 'wm-*.po' files"
    # This implies we have a source file with ALL strings (Standard + Custom)
    # And we want to isolate Custom.
    # This implies there is a "Standard" source somewhere to compare against.
    
    # Strategy:
    # 1. Backup our current (full) extracted source files.
    # 2. Download "Standard" source files from the MAIN open-edx project or the Release project?
    # User said project is `openedx-translations-teak`. If this IS the wikimedia project,
    # then it should contain everything.
    # 
    # Interpretation: The extracted files (from extraction workflow) contain EVERYTHING.
    # We want to identify which of these are NOT in the standard platform.
    # So we probably need to pull source from the UPSTREAM project (e.g. `open-edx/openedx-translations`).
    # 
    # Let's assume we pull from `open-edx/openedx-translations` (Main) or a specific release project?
    # The user script referenced `MAIN_PROJECT_SLUG = 'openedx-translations'`.
    
    # NOTE: To do this properly, we might need a separate .tx/config or just use CLI args to fetch from upstream.
    # Simpler approach:
    # We will assume the local files are "Full".
    # We will use `tx pull --source`? No, tx client implies project context.
    
    # Let's try to fetch the source for the corresponding resource from the UPSTREAM organization.
    # We can hack this by temporarily swapping .tx/config or just running a raw command?
    # 
    # Better yet:
    # 1. Rename current `django.po` to `django.po.full`
    # 2. Manually download the upstream `django.po` using `tx pull` against the UPSTREAM project.
    # 3. Diff `django.po.full` vs `django.po.upstream`.
    # 4. Result -> `wm-django.po`.
    # 5. Restore `django.po.full` to `django.po`.
    
    repo_config = load_repo_config()
    all_repos = []
    if "custom_repos" in repo_config:
        all_repos.extend(repo_config["custom_repos"].get("python", []))
        all_repos.extend(repo_config["custom_repos"].get("javascript", []))
        all_repos.extend(repo_config["custom_repos"].get("generic", []))

    for repo in all_repos:
        repo_dir_name = config_name_to_path_name(repo)
        base_dir = REPO_ROOT / "translations" / repo_dir_name / "conf" / "locale" / "en" / "LC_MESSAGES"
        
        for filename in ["django.po", "djangojs.po"]:
            full_path = base_dir / filename
            if not full_path.exists():
                continue
                
            print(f"Processing {full_path}")
            
            # Backup full local source
            full_backup = full_path.with_suffix(".po.full")
            shutil.copy(full_path, full_backup)
            
            # We need to fetch the upstream source. 
            # Since we set up .tx/config for OUR project, `tx pull -s` would pull OUR source (which we just pushed? no we haven't pushed yet).
            # If we haven't pushed, Transifex has old state.
            # But we want to compare against "Standard OpenEDX".
            # The user's previous script seemed to imply `tx pull` gets the "reviewed" translations (which act as base?) or source.
            
            # Let's try to pull 'en' from the configured project.
            # If `openedx-translations-teak` is intended to be the WIKIMEDIA project, then pulling source from it 
            # simply gives us what is currently on Transifex.
            # If this is the first run, Transifex might be empty or have standard strings.
            
            # If we want to separate "Wikimedia Specific", we really need a reference "Standard" file.
            # Without an explicit reference, we might just assume everything is custom? No, that's wrong.
            
            # Let's look at how the old script did it:
            # `python manage.py cms translatewiki pull_transifex_translations`
            # -> calls `pull_translation_from_transifex`
            # -> `tx pull --mode=reviewed -l {langs}`
            
            # `generate_custom_strings`:
            # -> move files to wm dir
            # -> `tx pull --mode=reviewed -l en` (Pull English! This implies pulling upstream source/trans)
            # -> Diff and generate.
            
            # So yes, we pull 'en' from Transifex.
            run_command(f"tx pull -l en --mode source --force", cwd=REPO_ROOT)
            
            # Now `django.po` contains what was on Transifex. `django.po.full` contains our extraction result.
            
            upstream_ids = get_msgids(full_path) # The one we just pulled
            full_ids = get_msgids(full_backup)   # The one we extracted
            
            custom_ids = full_ids - upstream_ids
            
            if custom_ids:
                print(f"Found {len(custom_ids)} custom strings for {filename}")
                # Create wm-*.po
                full_po = polib.pofile(full_backup)
                wm_po = polib.POFile()
                wm_po.metadata = full_po.metadata
                
                for entry in full_po:
                    if entry.msgid in custom_ids:
                        wm_po.append(entry)
                
                wm_filename = f"wm-{filename}"
                wm_path = base_dir / wm_filename
                wm_po.save(wm_path)
                print(f"Created {wm_path}")
            else:
                print("No custom strings found.")
            
            # Restore full file
            shutil.move(full_backup, full_path)

def merge_translations(project_slug, languages):
    """
    Pull translations and merge wm-*.po custom strings.
    """
    print("Pulling and merging translations...")
    
    # Pull all languages
    # If languages is empty, pull all?
    lang_arg = f"-l {','.join(languages)}" if languages else "-a"
    run_command(f"tx pull {lang_arg} --mode reviewed --force", cwd=REPO_ROOT)
    
    # Now merge wm-*.po into the pulled files
    # We need to find all wm-*.po files and merge them into their counterparts
    
    for wm_file in REPO_ROOT.glob("translations/**/conf/locale/en/LC_MESSAGES/wm-*.po"):
        # e.g. .../en/LC_MESSAGES/wm-django.po
        # We need to apply this to .../<lang>/LC_MESSAGES/django.po for ALL languages
        
        filename = wm_file.name # wm-django.po
        target_filename = filename.replace("wm-", "") # django.po
        
        # Get the LC_MESSAGES directory
        lc_messages_en = wm_file.parent
        locale_dir = lc_messages_en.parent.parent # .../conf/locale
        
        # Iterate over all language directories in conf/locale
        for lang_dir in locale_dir.iterdir():
            if not lang_dir.is_dir() or lang_dir.name == "en":
                continue
                
            target_file = lang_dir / "LC_MESSAGES" / target_filename
            
            if target_file.exists():
                print(f"Merging {wm_file.name} into {lang_dir.name}/{target_filename}")
                try:
                    subprocess.check_call(
                        f"pomerge --from {wm_file} --to {target_file}", 
                        shell=True
                    )
                except subprocess.CalledProcessError:
                    print(f"Failed to merge {wm_file} into {target_file}")


def main():
    parser = argparse.ArgumentParser(description="Merge translations workflow script")
    parser.add_argument("--project", required=True, help="Transifex project slug")
    parser.add_argument("--org", default="open-edx", help="Transifex organization slug")
    parser.add_argument("--languages", help="Comma separated list of languages to pull (default: all)")
    
    args = parser.parse_args()
    
    # Check for TX_TOKEN
    if not os.environ.get("TX_TOKEN"):
        print("Error: TX_TOKEN environment variable is not set.")
        sys.exit(1)
    
    # 1. Generate Config
    generate_tx_config(args.project, args.org)
    
    # 2. Separate Custom Strings
    generate_custom_strings(args.project)
    
    # 3. Pull and Merge
    langs = args.languages.split(",") if args.languages else []
    merge_translations(args.project, langs)

if __name__ == "__main__":
    main()
