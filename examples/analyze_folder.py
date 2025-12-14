"""
Recursively analyze a folder structure and return both dictionary and tree text output.

Usage:
    python analyze_folder.py <folder_path>
    
Or import as module:
    from analyze_folder import analyze_folder
    result = analyze_folder(Path("some/folder"))
"""

from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional
import sys


def analyze_folder(folder_path: Path) -> Dict[str, Any]:
    """
    Analyze the folder structure recursively and return a dictionary.
    
    Returns:
        Dictionary with:
        - 'root_path': absolute path to the root folder
        - 'folders': list of all subdirectories (relative paths)
        - 'files': dict with file types as keys and lists of files as values
        - 'structure': nested dictionary representing the folder structure
        - 'stats': statistics (total files, folders, etc.)
    """
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    result = {
        'root_path': str(folder_path.absolute()),
        'folders': [],
        'files': defaultdict(list),
        'structure': {},
        'stats': {
            'total_folders': 0,
            'total_files': 0,
            'files_by_type': defaultdict(int)
        }
    }
    
    # Build structure dictionary
    structure = {}
    
    # Recursively scan all items
    for item in sorted(folder_path.rglob('*')):
        rel_path = item.relative_to(folder_path)
        parts = rel_path.parts
        
        if item.is_dir():
            result['folders'].append(str(rel_path))
            result['stats']['total_folders'] += 1
            
            # Build nested structure
            current = structure
            for part in parts:
                if part not in current:
                    current[part] = {'type': 'folder', 'children': {}}
                current = current[part]['children']
        elif item.is_file():
            file_type = item.suffix.lower() if item.suffix else 'no_extension'
            result['files'][file_type].append(str(rel_path))
            result['stats']['total_files'] += 1
            result['stats']['files_by_type'][file_type] += 1
            
            # Add to structure
            if len(parts) > 1:
                # File is in a subdirectory
                current = structure
                for part in parts[:-1]:  # All parts except the filename
                    if part not in current:
                        current[part] = {'type': 'folder', 'children': {}}
                    current = current[part]['children']
                current[parts[-1]] = {'type': 'file', 'extension': file_type}
            else:
                # File is in root
                structure[parts[0]] = {'type': 'file', 'extension': file_type}
    
    result['structure'] = structure
    
    return result


def format_tree_text(analysis: Dict[str, Any], max_depth: Optional[int] = None) -> str:
    """
    Format the folder structure as a tree using special characters.
    
    Args:
        analysis: Dictionary returned by analyze_folder()
        max_depth: Maximum depth to display (None for unlimited)
    
    Returns:
        Formatted tree string
    """
    lines = []
    root_path = analysis['root_path']
    
    lines.append("=" * 80)
    lines.append(f"Folder Structure: {Path(root_path).name}")
    lines.append(f"Full Path: {root_path}")
    lines.append("=" * 80)
    lines.append("")
    
    # Add statistics
    stats = analysis['stats']
    lines.append("📊 Statistics:")
    lines.append(f"  📁 Total folders: {stats['total_folders']}")
    lines.append(f"  📄 Total files: {stats['total_files']}")
    lines.append("")
    
    if stats['files_by_type']:
        lines.append("📋 Files by type:")
        for file_type, count in sorted(stats['files_by_type'].items(), key=lambda x: -x[1]):
            icon = get_file_icon(file_type)
            type_name = file_type if file_type != 'no_extension' else '(no extension)'
            lines.append(f"  {icon} {type_name}: {count}")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("Tree Structure:")
    lines.append("=" * 80)
    lines.append("")
    
    # Build tree visualization
    structure = analysis['structure']
    
    def build_tree(node: Dict, prefix: str = "", is_last: bool = True, depth: int = 0):
        """Recursively build tree structure."""
        if max_depth is not None and depth > max_depth:
            return
        
        items = sorted(node.items(), key=lambda x: (x[1].get('type') != 'folder', x[0]))
        
        for i, (name, info) in enumerate(items):
            is_last_item = (i == len(items) - 1)
            current_prefix = "└── " if is_last_item else "├── "
            next_prefix = prefix + ("    " if is_last_item else "│   ")
            
            if info['type'] == 'folder':
                icon = "📁"
                lines.append(f"{prefix}{current_prefix}{icon} {name}/")
                if 'children' in info:
                    build_tree(info['children'], next_prefix, is_last_item, depth + 1)
            else:
                icon = get_file_icon(info.get('extension', ''))
                lines.append(f"{prefix}{current_prefix}{icon} {name}")
    
    if structure:
        # Root level items
        root_items = sorted(structure.items(), key=lambda x: (x[1].get('type') != 'folder', x[0]))
        
        for i, (name, info) in enumerate(root_items):
            is_last_item = (i == len(root_items) - 1)
            current_prefix = "└── " if is_last_item else "├── "
            next_prefix = "    " if is_last_item else "│   "
            
            if info['type'] == 'folder':
                icon = "📁"
                lines.append(f"{current_prefix}{icon} {name}/")
                if 'children' in info:
                    build_tree(info['children'], next_prefix, is_last_item, 1)
            else:
                icon = get_file_icon(info.get('extension', ''))
                lines.append(f"{current_prefix}{icon} {name}")
    else:
        lines.append("(empty folder)")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def get_file_icon(extension: str) -> str:
    """Get an appropriate icon for a file extension."""
    icon_map = {
        '.txt': '📝',
        '.pdf': '📄',
        '.doc': '📄',
        '.docx': '📄',
        '.xls': '📊',
        '.xlsx': '📊',
        '.ppt': '📊',
        '.pptx': '📊',
        '.py': '🐍',
        '.js': '📜',
        '.html': '🌐',
        '.css': '🎨',
        '.json': '📋',
        '.xml': '📋',
        '.csv': '📊',
        '.md': '📝',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.png': '🖼️',
        '.gif': '🖼️',
        '.zip': '📦',
        '.tar': '📦',
        '.gz': '📦',
    }
    return icon_map.get(extension.lower(), '📎')


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_folder.py <folder_path>")
        print("\nExample:")
        print("  python analyze_folder.py examples/unstructured_folder")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    
    try:
        # Analyze folder
        print(f"Analyzing folder: {folder_path.absolute()}...")
        analysis = analyze_folder(folder_path)
        
        # Print tree text
        tree_text = format_tree_text(analysis)
        print(tree_text)
        
        # Optionally save to file
        output_file = folder_path / "folder_analysis.txt"
        output_file.write_text(tree_text, encoding="utf-8")
        print(f"\n✅ Analysis saved to: {output_file}")
        
        # Print dictionary summary
        print("\n" + "=" * 80)
        print("Dictionary Structure (summary):")
        print("=" * 80)
        print(f"Keys: {list(analysis.keys())}")
        print(f"Root path: {analysis['root_path']}")
        print(f"Total folders: {len(analysis['folders'])}")
        print(f"File types found: {list(analysis['files'].keys())}")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

