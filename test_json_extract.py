import re

html_file = 'data/raw/facebook/fb_BraterstwaLudziWolnych_20251124_150907.html'

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"HTML size: {len(content)} chars")
print(f"Contains 'timeline_list_feed_units': {'timeline_list_feed_units' in content}")
script_tag = '<script type="application/json"'
print(f"Contains script tag: {script_tag in content}")

# Count script tags
script_pattern = r'<script type="application/json"[^>]*>(.*?)</script>'
matches = list(re.finditer(script_pattern, content, re.DOTALL))
print(f"\nFound {len(matches)} script tags with JSON")

for i, match in enumerate(matches):
    script_content = match.group(1)
    has_timeline = '"timeline_list_feed_units"' in script_content
    print(f"  Script #{i+1}: {len(script_content)} chars, has_timeline={has_timeline}")
    
    if has_timeline:
        # Count Story instances
        story_count = script_content.count('"__typename":"Story"')
        print(f"    Contains {story_count} Story instances")
        
        # Try to find one Story node
        story_pattern = r'"node":\s*\{[^}]*"__typename":\s*"Story"'
        story_matches = list(re.finditer(story_pattern, script_content))
        print(f"    Found {len(story_matches)} story node matches")
        
        # Try actual extraction
        if story_matches:
            print("\n    Testing node extraction:")
            for sm in story_matches[:1]:  # Just first one
                print(f"      Match at position: {sm.start()}")
                post_id_match = re.search(r'"id":\s*"([^"]+)"', script_content[sm.start():sm.start()+500])
                if post_id_match:
                    post_id = post_id_match.group(1)
                    print(f"      Found ID: {post_id}")
                    
                    # Try to extract full node
                    search_area = script_content[max(0, sm.start()-100):sm.start()+100]
                    print(f"      Context around match: ...{search_area[:200]}...")
                    
                    node_start = script_content.rfind('{"node":', 0, sm.start())
                    print(f"      rfind result: {node_start}")
                    if node_start != -1:
                        print(f"      Node starts at position: {node_start}")
                        # Show first 200 chars
                        print(f"      First 200 chars: {script_content[node_start:node_start+200]}")
                    else:
                        print("      ERROR: rfind returned -1")
                else:
                    print("      No ID found")
