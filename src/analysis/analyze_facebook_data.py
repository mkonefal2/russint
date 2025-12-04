import json
import os
from pathlib import Path
import base64
from typing import Dict, List, Optional
import glob

# Placeholder for LLM interaction
# You would replace this with actual calls to OpenAI/Anthropic/Gemini APIs
class LLMClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def analyze(self, text_prompt: str, image_path: Optional[str] = None) -> Dict:
        """
        Simulates an LLM call. In a real scenario, this would send the prompt and image to the API.
        """
        print(f"[*] Mocking LLM call for image: {image_path}")
        # Return a dummy response for demonstration
        return {
            "summary": "Mock summary of the post.",
            "entities": [],
            "connections": [],
            "narratives": ["mock_narrative"],
            "identifiers": [],
            "risk_assessment": {"level": "unknown", "reason": "Mock analysis"}
        }

class FacebookAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.raw_posts_dir = project_root / "data" / "raw" / "facebook" / "posts"
        self.screenshots_dir = project_root / "data" / "evidence" / "facebook" / "screenshots"
        self.processed_dir = project_root / "data" / "processed" / "facebook_analysis"
        self.prompt_template_path = project_root / "schemas" / "FACEBOOK_ANALYSIS_PROMPT.md"
        
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = LLMClient() # Initialize your LLM client here

    def load_prompt_template(self) -> str:
        with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def get_image_path(self, screenshot_filename: str) -> Optional[Path]:
        if not screenshot_filename:
            return None
        image_path = self.screenshots_dir / screenshot_filename
        return image_path if image_path.exists() else None

    def encode_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def process_all_posts(self):
        prompt_template = self.load_prompt_template()
        json_files = list(self.raw_posts_dir.glob("*.json"))
        
        print(f"Found {len(json_files)} posts to analyze.")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    post_data = json.load(f)

                post_id = post_data.get('id')
                if not post_id:
                    continue

                output_file = self.processed_dir / f"{post_id}_analysis.json"
                if output_file.exists():
                    print(f"Skipping {post_id} - already analyzed.")
                    continue

                print(f"Analyzing post: {post_id}")

                # Prepare content for LLM
                raw_text = post_data.get('raw_text_preview', '')
                screenshot_filename = post_data.get('screenshot')
                image_path = self.get_image_path(screenshot_filename)
                
                # Construct the final prompt
                # In a real implementation with a Vision model, you'd send the image separately or as a base64 string
                full_prompt = f"{prompt_template}\n\n## DANE DO ANALIZY\n"
                full_prompt += f"**Autor/Handle**: {post_data.get('handle')}\n"
                full_prompt += f"**Data**: {post_data.get('collected_at')}\n"
                full_prompt += f"**Link**: {post_data.get('post_url')}\n"
                full_prompt += f"**Treść posta**:\n{raw_text}\n"
                
                if image_path:
                    full_prompt += f"\n[Dołączono obraz: {image_path.name}]"
                
                # Call LLM
                # Note: For Vision models (GPT-4o, Gemini), you would pass the image binary/base64 here.
                analysis_result = self.llm_client.analyze(full_prompt, str(image_path) if image_path else None)

                # Save result
                final_output = {
                    "original_post": post_data,
                    "analysis": analysis_result
                }

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(final_output, f, indent=2, ensure_ascii=False)
                
                print(f"Saved analysis to {output_file.name}")

            except Exception as e:
                print(f"Error processing {json_file.name}: {e}")

if __name__ == "__main__":
    # Adjust path if running from different location
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    
    analyzer = FacebookAnalyzer(project_root)
    analyzer.process_all_posts()
