import os
from typing import Dict, List
from backend.core.configs import settings

class SettingsService:
    def __init__(self):
        self.env_path = os.path.join(settings.BASE_PATH, ".env")
    
    def _unescape_env_value(self, value: str) -> str:
        """
        Unescapes a value from .env storage.
        """
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
            # Replace escaped sequences
            value = value.replace("\\n", "\n")
            value = value.replace('\\"', '"')
            value = value.replace("\\'", "'")
            value = value.replace("\\\\", "\\")
        return value

    def _escape_env_value(self, value: str) -> str:
        """
        Escapes a value for .env storage.
        - Wraps in double quotes
        - Escapes internal double quotes
        - Escapes actual newlines as \n
        """
        value = str(value)
        # 1. Escape backslashes first
        value = value.replace("\\", "\\\\")
        # 2. Escape double quotes
        value = value.replace('"', '\\"')
        # 3. Escape newlines
        value = value.replace("\n", "\\n")
        return f'"{value}"'

    def get_all(self) -> List[Dict[str, object]]:
        """
        Reads .env file and returns a list of key-value pairs.
        Sensitive values are masked.
        """
        if not os.path.exists(self.env_path):
            return []
            
        results = []
        with open(self.env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                try:
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Symmetrical Unescape
                    value = self._unescape_env_value(value)
                    
                    results.append({"key": key, "value": value, "is_secret": "KEY" in key or "PASSWORD" in key or "SECRET" in key})
                except ValueError:
                    continue
                    
        return results

    def update(self, updates: Dict[str, str]):
        """
        Updates specific keys in the .env file.
        """
        if not os.path.exists(self.env_path):
            with open(self.env_path, "w") as f:
                f.write("")

        with open(self.env_path, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        processed_keys = set()
        
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                new_lines.append(line)
                continue
                
            try:
                if "=" not in line_str:
                    new_lines.append(line)
                    continue
                    
                key, _ = line_str.split("=", 1)
                key = key.strip()
                
                if key in updates:
                    new_val = self._escape_env_value(updates[key])
                    new_lines.append(f"{key}={new_val}\n")
                    processed_keys.add(key)
                else:
                    new_lines.append(line)
            except ValueError:
                new_lines.append(line)
                
        for key, val in updates.items():
            if key not in processed_keys:
                new_val = self._escape_env_value(val)
                new_lines.append(f"{key}={new_val}\n")
                
        with open(self.env_path, "w") as f:
            f.writelines(new_lines)
            
        return True

settings_service = SettingsService()
