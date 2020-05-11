import tensorflow as tf
import layers
import numpy as np


class Generator(tf.keras.models.Model):
    def __init__(self, num_mapping_layers=8, mapping_fmaps=32, resolution=64, type=tf.dtypes.float32, num_channels=1,
                 fmap_base=32):
        super(Generator, self).__init__()

        # Config vars
        self.num_mapping_layers = num_mapping_layers
        self.mapping_fmaps = mapping_fmaps
        self.fmap_base = fmap_base
        self.resolution_log2 = int(np.log2(resolution))

        # Layers
        # self.pixel_norm = layers.PixelNorm(type)
        self.mapping_layers = layers.Mapping(num_mapping_layers, mapping_fmaps)
        self.first_gen_block = layers.FirstGenBlock(fmap_base=fmap_base, type=type)
        self.blocks = dict()
        self.to_rgb_first = layers.ToRGB(num_channels=num_channels)
        self.to_rgb_new = dict()
        self.to_rgb_old = dict()
        self.to_rgb_last = dict()
        self.to_rgb_last_mix = dict()
        for res in range(3, self.resolution_log2 + 1):
            self.to_rgb_old[str(res)] = layers.ToRGB(num_channels=num_channels)
            self.blocks[str(res)] = layers.GenBlock(res=res, fmap_base=fmap_base, type=type)
            self.to_rgb_new[str(res)] = layers.ToRGB(num_channels=num_channels)
            self.to_rgb_last[str(res)] = layers.ToRGB(num_channels=num_channels)
            self.to_rgb_last_mix[str(res)] = layers.ToRGB(num_channels=num_channels)


        # Functions
        self.upscale = layers.upscale(2)

    def call(self, inputs):
        latents_input = inputs[0]
        lod_input = inputs[1]
        # latents = self.pixel_norm(latents_input)
        latents = self.mapping_layers(latents_input)

        x = self.first_gen_block(latents)
        result = self.to_rgb_first(x)
        lod_counter = int(np.ceil(lod_input))
        lod_remainder = lod_input - np.floor(lod_input)
        if int(np.ceil(lod_input)) > self.resolution_log2:
            print('WARNING: LoD = {}, while log(resolution) = {}'.format(lod_input, self.resolution_log2))

        for res in range(3, min(int(np.ceil(lod_input)) + 3, self.resolution_log2 + 1)):
            if lod_counter == 1 and lod_remainder > 0:
                rgb_image = self.to_rgb_old[str(res)](x)
                prev = self.upscale(rgb_image)
                x = self.blocks[str(res)]([x, latents])
                new = self.to_rgb_new[str(res)](x)
                x = new + (prev - new) * (1 - lod_remainder)
                result = self.to_rgb_last_mix[str(res)](x)
            else:
                x = self.blocks[str(res)]([x, latents])
                result = self.to_rgb_last[str(res)](x)
            lod_counter -= 1
        return result
