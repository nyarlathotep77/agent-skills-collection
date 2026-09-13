import json
import argparse
import sys
import os
from jsonschema import validate, ValidationError

def validate_plugin(schema_path, plugin_path):
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        return False
    
    if not os.path.exists(plugin_path):
        print(f"Error: Plugin file not found at {plugin_path}")
        return False

    try:
        with open(schema_path, 'r') as s_file:
            schema = json.load(s_file)
        
        with open(plugin_path, 'r') as p_file:
            plugin_data = json.load(p_file)
        
        validate(instance=plugin_data, schema=schema)
        print(f"✅ Success: {plugin_path} is a valid plugin according to the schema.")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON in {plugin_path}: {e}")
    except ValidationError as e:
        print(f"❌ Error: Plugin validation failed for {plugin_path}:")
        print(f"   Path: {list(e.path)}")
        print(f"   Message: {e.message}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {argparse.format_arg(e)}")
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a plugin's marketplace.json against the standard schema.")
    parser.add_argument("plugin_path", help="Path to the marketplace.json file to validate")
    parser.add_argument("--schema", default="/home/davide/dev/workspace/public/ai/agent-skills-collection/schema/plugin_schema.json", help="Path to the JSON schema file")

    args = parser.parse_args()

    if validate_plugin(args.schema, args.plugin_path):
        sys.exit(0)
    else:
        sys.exit(1)
