"""
Extract cookies from Edge browser for Facebook
Uses browser_cookie3 to safely extract cookies without file locking issues
"""
import json
from pathlib import Path
import browser_cookie3


def get_facebook_cookies():
    """Extract Facebook cookies from Edge using browser_cookie3"""
    try:
        # Get Edge cookies
        cj = browser_cookie3.edge(domain_name='facebook.com')
        
        cookies = []
        for cookie in cj:
            cookies.append({
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path
            })
        
        return cookies
    except Exception as e:
        print(f"[!] Failed to get Edge cookies: {e}")
        print("[*] Trying Chrome as fallback...")
        try:
            cj = browser_cookie3.chrome(domain_name='facebook.com')
            cookies = []
            for cookie in cj:
                cookies.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path
                })
            return cookies
        except:
            return []


if __name__ == "__main__":
    try:
        print("[*] Extracting cookies from Edge...")
        cookies = get_facebook_cookies()
        print(f"[+] Found {len(cookies)} Facebook cookies")
        
        # Save to file
        output = Path(__file__).parent / 'fb_cookies.json'
        with open(output, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"[+] Cookies saved to: {output}")
        
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
