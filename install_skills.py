#!/usr/bin/env python3
import os
import shutil
import argparse

def install_skills(source_dir, target_dcode, target_claude):
    """
    Recursively traverses the source directory and installs skills into 
    the specified dcode and Claude Code directories.
    """
    print(f"Scanning for skills in: {os.path.abspath(source_dir)}")
    
    # Define what constitutes a 'skill' - e.g., presence of SKILL.md or similar
    # For this implementation, we look for any directory containing a .md file 
    # that might be a skill definition.
    
    skills_found = []

    for root, dirs, files in os.walk(source_dir):
        # Skip git directories and submodules themselves to avoid infinite loops/redundancy
        if '.git' in dirs:
            dirs.remove('.git')
        
        # Check if this directory is a skill (contains a markdown file)
        is_skill = any(f.endswith('.md') for f in files)
        
        if is_skill:
            # Determine relative path from source root to identify the skill name/path
            rel_path = os.path.relpath(root, source_dir)
            if rel_path == ".":
                skill_name = "root_skills"
            else:
                skill_name = rel_path
            
            skills_found.append((root, skill_name))

    if not skills_found:
        print("No skills found.")
        return

    print(f"Found {len(skills_found)} potential skills.")

    for skill_root, skill_name in skills_found:
        # 1. Install for DeepAgents dcode
        # Assuming dcode expects skills in a specific structure like ~/.deepagents/agent/skills/
        dcode_dest = os.path.join(target_dcode, skill_name)
        try:
            os.makedirs(os.path.dirname(dcode_dest), exist_ok=True)
            if os.path.exists(dcode_dest):
                if os.path.isdir(dcode_dest):
                    shutil.rmtree(dcode_dest)
                else:
                    os.remove(dcode_dest)
            
            # Copy the skill directory (or just the relevant files)
            # For simplicity, we copy the folder containing the skill definition
            shutil.copytree(skill_root, dcode_dest, dirs_exist_ok=True)
            print(f"  [dcode] Installed: {skill_name}")
        except Exception as e:
            print(f"  [dcode] Failed to install {skill_name}: {e}")

        # 2. Install for Claude Code
        claude_dest = os.path.join(target_claude, skill_name)
        try:
            os.makedirs(os.path.dirname(claude_dest), exist_ok=True)
            if os.path.exists(claude_dest):
                if os.path.isdir(claude_dest):
                    shutil.rmtree(claude_dest)
                else:
                    os.remove(claude_dest)
            
            # Copy the skill directory
            shutil.copytree(skill_root, claude_dest, dirs_exist_ok=True)
            print(f"  [Claude] Installed: {skill_name}")
            print(f"  [Claude] Failed to install {skill_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install skills for dcode and Claude Code.")
    parser.add_argument("--source", required=True, help="Source directory containing submodules/skills")
    parser.add_argument("--dcode-path", required=True, help="Target path for DeepAgents dcode skills")
    parser.add_argument("--claude-path", required=True, help="Target path for Claude Code skills")

    args = parser.parse_args()
    install_skills(args.source, args.dcode_path, args.claude_path)
