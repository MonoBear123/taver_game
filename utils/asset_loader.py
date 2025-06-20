import pygame
import os


class AssetLoader:
    def __init__(self):
        self._image_cache = {}
        self._animation_cache = {}

    def get_image(self, path, size = None):
        cache_key = (path, size)
        if cache_key not in self._image_cache:
                full_path = path
                if not os.path.exists(full_path):
                    full_path = os.path.join('assets', 'objects', path) + '.png'
                
                image = pygame.image.load(full_path).convert_alpha()
                if size:
                    image = pygame.transform.scale(image, size)
                self._image_cache[cache_key] = image
        return self._image_cache[cache_key]

    def get_item_image(self, filename, size=None):
        if not filename.endswith('.png'):
            filename += '.png'
        path = os.path.join('assets', 'items', filename)
        return self.get_image(path, size)

    def get_animations(self, base_path, size = None):
        cache_key = (base_path, size)
        if cache_key in self._animation_cache:
            return self._animation_cache[cache_key]

        animations = {}
        
        for anim_name in os.listdir(base_path):
            anim_path = os.path.join(base_path, anim_name)
            if os.path.isdir(anim_path):
                images = []
                try:
                    sorted_files = sorted(os.listdir(anim_path), key=lambda x: int(os.path.splitext(x)[0]))
                except (ValueError, IndexError):
                    sorted_files = sorted(os.listdir(anim_path))

                for frame_file in sorted_files:
                    if frame_file.endswith('.png'):
                        frame_path = os.path.join(anim_path, frame_file)
                        images.append(self.get_image(frame_path, size=size))
                animations[anim_name] = images

        self._animation_cache[cache_key] = animations
        return animations

asset_loader = AssetLoader()
