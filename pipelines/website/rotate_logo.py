"""
Script to rotate the Company Atlas logo SVG by 180 degrees.
Reads the SVG file, applies rotation transform, and saves it back.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rotate_svg_180_degrees(svg_path: Path, output_path: Path = None):
    """
    Rotate an SVG file by 180 degrees.
    
    Args:
        svg_path: Path to the input SVG file
        output_path: Path to save the rotated SVG (defaults to overwriting input)
    """
    if output_path is None:
        output_path = svg_path
    
    logger.info(f"Reading SVG from: {svg_path}")
    
    # Parse the SVG file
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Get the viewBox to determine center point
    viewbox = root.get('viewBox', '0 0 64 64')
    viewbox_parts = viewbox.split()
    if len(viewbox_parts) >= 4:
        width = float(viewbox_parts[2])
        height = float(viewbox_parts[3])
        center_x = width / 2
        center_y = height / 2
    else:
        # Default to 32, 32 if viewBox is not properly formatted
        center_x = 32
        center_y = 32
    
    logger.info(f"SVG center point: ({center_x}, {center_y})")
    
    # Check if there's already a transform on the root or first group
    # We'll wrap everything in a new group with rotation
    svg_content = root
    
    # Find the main content group (usually the first <g> or all children)
    # If there's already a group with transform, we'll add to it
    # Otherwise, wrap all children in a new group
    
    # Get all direct children that are not defs
    children_to_wrap = []
    defs_element = None
    
    for child in list(root):
        if child.tag.endswith('defs') or child.tag == '{http://www.w3.org/2000/svg}defs':
            defs_element = child
        else:
            children_to_wrap.append(child)
    
    # Check if there's already a transform group
    has_transform_group = False
    transform_group = None
    
    for child in children_to_wrap:
        if child.tag.endswith('g') or child.tag == '{http://www.w3.org/2000/svg}g':
            transform_attr = child.get('transform', '')
            if 'rotate' in transform_attr:
                has_transform_group = True
                transform_group = child
                break
    
    if has_transform_group and transform_group is not None:
        # Update existing transform to add 180 degrees
        existing_transform = transform_group.get('transform', '')
        # If it already has rotate(180), we're done
        if 'rotate(180' in existing_transform:
            logger.info("SVG already has 180-degree rotation")
        else:
            # Combine transforms or replace
            new_transform = f"rotate(180 {center_x} {center_y})"
            transform_group.set('transform', new_transform)
            logger.info("Updated existing transform group with 180-degree rotation")
    else:
        # Create a new group with rotation transform
        # Remove namespace for easier handling
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        
        # Remove children from root
        for child in children_to_wrap:
            root.remove(child)
        
        # Create new group with rotation
        new_group = ET.Element('g')
        new_group.set('transform', f'rotate(180 {center_x} {center_y})')
        
        # Add all children to the new group
        for child in children_to_wrap:
            new_group.append(child)
        
        # Add the new group to root (after defs if it exists)
        if defs_element is not None:
            # Insert after defs
            root.insert(1, new_group)
        else:
            root.insert(0, new_group)
        
        logger.info("Created new transform group with 180-degree rotation")
    
    # Write the modified SVG
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    logger.info(f"✅ Saved rotated SVG to: {output_path}")

def main():
    """Main function to rotate the favicon SVG."""
    # Path to the favicon SVG
    svg_path = Path('website/assets/favicon.svg')
    
    if not svg_path.exists():
        logger.error(f"SVG file not found: {svg_path}")
        return
    
    # Rotate and save (overwrites original)
    rotate_svg_180_degrees(svg_path)
    logger.info("✅ Logo rotation complete!")

if __name__ == "__main__":
    main()

