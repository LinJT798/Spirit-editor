from PIL import Image
import numpy as np
import cv2
import json
import os
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class SpriteInfo:
    name: str
    x: int
    y: int
    width: int
    height: int
    image: Optional[Image.Image] = None
    selected: bool = False


class SpriteCutter:
    def __init__(self, image_path: str = None):
        self.image_path = image_path
        self.image = None
        self.sprites = []
        
        if image_path:
            self.load_image(image_path)
    
    def load_image(self, image_path: str):
        self.image_path = image_path
        self.image = Image.open(image_path).convert('RGBA')
        self.width, self.height = self.image.size
        return self.image
    
    def grid_cut_by_size(self, cell_width: int, cell_height: int, 
                         padding_x: int = 0, padding_y: int = 0,
                         offset_x: int = 0, offset_y: int = 0) -> List[SpriteInfo]:
        if not self.image:
            raise ValueError("No image loaded")
        
        sprites = []
        sprite_index = 0
        
        y = offset_y
        while y + cell_height <= self.height:
            x = offset_x
            while x + cell_width <= self.width:
                sprite_img = self.image.crop((x, y, x + cell_width, y + cell_height))
                
                if not self._is_empty_sprite(sprite_img):
                    sprite_info = SpriteInfo(
                        name=f"sprite_{sprite_index:03d}",
                        x=x,
                        y=y,
                        width=cell_width,
                        height=cell_height,
                        image=sprite_img
                    )
                    sprites.append(sprite_info)
                    sprite_index += 1
                
                x += cell_width + padding_x
            y += cell_height + padding_y
        
        self.sprites = sprites
        return sprites
    
    def grid_cut_by_count(self, rows: int, cols: int, 
                         padding_x: int = 0, padding_y: int = 0) -> List[SpriteInfo]:
        if not self.image:
            raise ValueError("No image loaded")
        
        available_width = self.width - padding_x * (cols - 1)
        available_height = self.height - padding_y * (rows - 1)
        
        cell_width = available_width // cols
        cell_height = available_height // rows
        
        return self.grid_cut_by_size(cell_width, cell_height, padding_x, padding_y)
    
    def auto_cut(self, min_sprite_size: int = 8, 
                 threshold: int = 10) -> List[SpriteInfo]:
        if not self.image:
            raise ValueError("No image loaded")
        
        img_array = np.array(self.image)
        alpha_channel = img_array[:, :, 3]
        
        binary = (alpha_channel > threshold).astype(np.uint8) * 255
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        sprites = []
        sprite_index = 0
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w >= min_sprite_size and h >= min_sprite_size:
                sprite_img = self.image.crop((x, y, x + w, y + h))
                
                sprite_info = SpriteInfo(
                    name=f"sprite_{sprite_index:03d}",
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    image=sprite_img
                )
                sprites.append(sprite_info)
                sprite_index += 1
        
        sprites.sort(key=lambda s: (s.y, s.x))
        
        for i, sprite in enumerate(sprites):
            sprite.name = f"sprite_{i:03d}"
        
        self.sprites = sprites
        return sprites
    
    def manual_cut(self, regions: List[Tuple[int, int, int, int]], 
                   names: Optional[List[str]] = None) -> List[SpriteInfo]:
        if not self.image:
            raise ValueError("No image loaded")
        
        sprites = []
        
        for i, (x, y, width, height) in enumerate(regions):
            x = max(0, min(x, self.width))
            y = max(0, min(y, self.height))
            width = min(width, self.width - x)
            height = min(height, self.height - y)
            
            sprite_img = self.image.crop((x, y, x + width, y + height))
            
            name = names[i] if names and i < len(names) else f"sprite_{i:03d}"
            
            sprite_info = SpriteInfo(
                name=name,
                x=x,
                y=y,
                width=width,
                height=height,
                image=sprite_img
            )
            sprites.append(sprite_info)
        
        self.sprites = sprites
        return sprites
    
    def trim_sprites(self, sprites: Optional[List[SpriteInfo]] = None) -> List[SpriteInfo]:
        if sprites is None:
            sprites = self.sprites
        
        trimmed_sprites = []
        
        for sprite in sprites:
            if sprite.image:
                trimmed_img, new_bounds = self._trim_transparent(sprite.image)
                
                if trimmed_img:
                    new_sprite = SpriteInfo(
                        name=sprite.name,
                        x=sprite.x + new_bounds[0],
                        y=sprite.y + new_bounds[1],
                        width=new_bounds[2] - new_bounds[0],
                        height=new_bounds[3] - new_bounds[1],
                        image=trimmed_img
                    )
                    trimmed_sprites.append(new_sprite)
        
        return trimmed_sprites
    
    def export_selected_sprites(self, output_dir: str, format: str = 'png', 
                                trim: bool = False, mode: str = 'individual',
                                atlas_padding: int = 2, atlas_name: str = 'atlas',
                                name_prefix: str = 'sprite_') -> Dict[str, any]:
        selected_sprites = [s for s in self.sprites if s.selected]
        if not selected_sprites:
            raise ValueError("No sprites selected for export")
        
        os.makedirs(output_dir, exist_ok=True)
        
        sprites_to_export = self.trim_sprites(selected_sprites) if trim else selected_sprites
        
        if mode == 'individual':
            return self._export_individual_sprites(sprites_to_export, output_dir, format, name_prefix)
        elif mode == 'atlas':
            return self._export_atlas(sprites_to_export, output_dir, format, atlas_padding, atlas_name)
        else:
            raise ValueError(f"Unknown export mode: {mode}")
    
    def _export_individual_sprites(self, sprites: List[SpriteInfo], output_dir: str, 
                                  format: str, name_prefix: str = 'sprite_') -> Dict[str, any]:
        metadata = {
            'export_mode': 'individual',
            'sprite_count': len(sprites),
            'sprites': []
        }
        
        for sprite in sprites:
            if sprite.image:
                file_name = f"{sprite.name}.{format}"
                file_path = os.path.join(output_dir, file_name)
                sprite.image.save(file_path, format.upper())
                
                sprite_meta = {
                    'name': sprite.name,
                    'file': file_name,
                    'width': sprite.width,
                    'height': sprite.height
                }
                metadata['sprites'].append(sprite_meta)
        
        metadata_path = os.path.join(output_dir, 'sprites_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def _export_atlas(self, sprites: List[SpriteInfo], output_dir: str, 
                     format: str, padding: int, atlas_name: str = 'atlas') -> Dict[str, any]:
        if not sprites:
            raise ValueError("No sprites to pack")
        
        positions = self._pack_sprites(sprites, padding)
        
        atlas_width = int(max(p['x'] + p['width'] for p in positions))
        atlas_height = int(max(p['y'] + p['height'] for p in positions))
        
        atlas_image = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        
        metadata = {
            'export_mode': 'atlas',
            'atlas_size': {'width': int(atlas_width), 'height': int(atlas_height)},
            'sprite_count': len(sprites),
            'sprites': []
        }
        
        for sprite, pos in zip(sprites, positions):
            if sprite.image:
                atlas_image.paste(sprite.image, (pos['x'], pos['y']))
                
                sprite_meta = {
                    'name': sprite.name,
                    'frame': {
                        'x': int(pos['x']),
                        'y': int(pos['y']),
                        'width': int(pos['width']),
                        'height': int(pos['height'])
                    }
                }
                metadata['sprites'].append(sprite_meta)
        
        atlas_path = os.path.join(output_dir, f'{atlas_name}.{format}')
        atlas_image.save(atlas_path, format.upper())
        
        metadata_path = os.path.join(output_dir, f'{atlas_name}.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def _pack_sprites(self, sprites: List[SpriteInfo], padding: int) -> List[Dict]:
        sorted_sprites = sorted(sprites, key=lambda s: s.height * s.width, reverse=True)
        
        positions = []
        current_x = 0
        current_y = 0
        row_height = 0
        max_width = 2048
        
        for sprite in sorted_sprites:
            width = sprite.width + padding
            height = sprite.height + padding
            
            if current_x + width > max_width:
                current_x = 0
                current_y += row_height
                row_height = 0
            
            positions.append({
                'x': current_x,
                'y': current_y,
                'width': sprite.width,
                'height': sprite.height
            })
            
            current_x += width
            row_height = max(row_height, height)
        
        return positions
    
    def export_sprites(self, output_dir: str, format: str = 'png', 
                       trim: bool = False) -> Dict[str, any]:
        if not self.sprites:
            raise ValueError("No sprites to export")
        
        os.makedirs(output_dir, exist_ok=True)
        
        sprites_to_export = self.trim_sprites() if trim else self.sprites
        
        metadata = {
            'source_image': os.path.basename(self.image_path) if self.image_path else 'unknown',
            'source_size': {'width': self.width, 'height': self.height},
            'sprite_count': len(sprites_to_export),
            'sprites': []
        }
        
        for sprite in sprites_to_export:
            if sprite.image:
                file_name = f"{sprite.name}.{format}"
                file_path = os.path.join(output_dir, file_name)
                sprite.image.save(file_path, format.upper())
                
                sprite_meta = {
                    'name': sprite.name,
                    'file': file_name,
                    'frame': {
                        'x': sprite.x,
                        'y': sprite.y,
                        'width': sprite.width,
                        'height': sprite.height
                    }
                }
                metadata['sprites'].append(sprite_meta)
        
        metadata_path = os.path.join(output_dir, 'sprites.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def _is_empty_sprite(self, image: Image.Image, threshold: int = 10) -> bool:
        img_array = np.array(image)
        if img_array.shape[2] == 4:
            alpha_channel = img_array[:, :, 3]
            return np.all(alpha_channel <= threshold)
        return False
    
    def _trim_transparent(self, image: Image.Image, threshold: int = 10) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
        img_array = np.array(image)
        if img_array.shape[2] != 4:
            return image, (0, 0, image.width, image.height)
        
        alpha_channel = img_array[:, :, 3]
        
        non_transparent = np.where(alpha_channel > threshold)
        
        if len(non_transparent[0]) == 0:
            return None, None
        
        min_y, max_y = non_transparent[0].min(), non_transparent[0].max()
        min_x, max_x = non_transparent[1].min(), non_transparent[1].max()
        
        bounds = (min_x, min_y, max_x + 1, max_y + 1)
        trimmed = image.crop(bounds)
        
        return trimmed, bounds
    
    def get_sprite_preview(self, index: int) -> Optional[Image.Image]:
        if 0 <= index < len(self.sprites):
            return self.sprites[index].image
        return None