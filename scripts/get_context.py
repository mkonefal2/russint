import argparse
import json
from pathlib import Path
import sys
import os
import subprocess
import platform

def find_post_json(search_term, base_dir):
    """Finds a JSON file matching the search term in the base directory."""
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory {base_dir} does not exist.")
        return None

    # Search recursively
    matches = list(base_path.rglob(f"*{search_term}*.json"))
    
    if not matches:
        return None
    
    # Prefer exact match if possible (though unlikely with partial search)
    return matches[0]

def main():
    parser = argparse.ArgumentParser(description="Get context for Copilot analysis.")
    parser.add_argument("search_term", help="Post ID or part of the filename to search for.")
    args = parser.parse_args()

    # Adjust path relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    raw_dir = project_root / "data" / "raw" / "facebook"

    json_file = find_post_json(args.search_term, raw_dir)

    if json_file:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print("\n--- COPILOT CONTEXT START ---")
            print(f"File: {json_file.name}")
            print("```json")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("```")
            print("--- COPILOT CONTEXT END ---\n")
            print("Copy the block above and paste it into Copilot chat along with the image.")

            # Try to open the screenshot automatically
            screenshot_rel = data.get('screenshot')
            if screenshot_rel:
                # Try to resolve path
                possible_paths = [
                    project_root / screenshot_rel,
                    project_root / "data" / "evidence" / "facebook" / Path(screenshot_rel).name,
                    project_root / "data" / "evidence" / "facebook" / "screenshots" / Path(screenshot_rel).name
                ]
                
                found_img = None
                for p in possible_paths:
                    if p.exists():
                        found_img = p
                        break
                
                if found_img:
                    print(f"\n[INFO] Opening image: {found_img.name}")
                    try:
                        if sys.platform == "win32":
                            os.startfile(found_img)
                        elif sys.platform == "darwin":
                            subprocess.call(["open", str(found_img)])
                        else:
                            subprocess.call(["xdg-open", str(found_img)])
                    except Exception as e:
                        print(f"[WARN] Could not open image: {e}")
                else:
                    print(f"\n[WARN] Screenshot file not found: {screenshot_rel}")
            
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"No JSON file found matching '{args.search_term}' in {raw_dir}")

if __name__ == "__main__":
    main()
