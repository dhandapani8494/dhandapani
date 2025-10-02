import json
import sys
import urllib.request
import urllib.error
from urllib.parse import urljoin

def main():
    # Configuration
    json_file_path = 'example.json'
    base_url = 'https://github.com/ASX/infraeng-interview/tree/main/coding/'  
    endpoint = '/service/generate'
    full_url = urljoin(base_url, endpoint)

    try:
        # 1. Read and validate JSON
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        print(f" Successfully loaded and validated {json_file_path}")

        
        filtered_data = None
        
        if isinstance(data, dict):
            if 'private' in data:
                if data.get('private') is False:
                    filtered_data = data
                else:
                    filtered_data = {}
            else:
                
                filtered_data = {
                    key: value for key, value in data.items()
                    if isinstance(value, dict) and value.get('private') is False
                }
        elif isinstance(data, list):
            # Filter list of objects
            filtered_data = [
                item for item in data
                if isinstance(item, dict) and item.get('private') is False
            ]
        else:
            raise ValueError("JSON root must be an object or array")

        print(f"✓ Filtered data to include only non-private objects")

        # 3. Make HTTPS POST request
        json_payload = json.dumps(filtered_data).encode('utf-8')
        req = urllib.request.Request(
            full_url,
            data=json_payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        print(f"✓ Sending POST request to {full_url}")
        
        with urllib.request.urlopen(req) as response:
            response_data = json.load(response)
        
        print("✓ Received response from server")

        # 4. Print keys of objects with "valid": true
        valid_keys = []
        
        if isinstance(response_data, dict):
            for key, value in response_data.items():
                if isinstance(value, dict) and value.get('valid') is True:
                    valid_keys.append(key)
        else:
            print("⚠ Warning: Response is not a JSON object, cannot extract keys")

        if valid_keys:
            print("Keys with 'valid': true:")
            for key in valid_keys:
                print(f"  {key}")
        else:
            print("No objects found with 'valid': true")

    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Failed to connect to web service: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()