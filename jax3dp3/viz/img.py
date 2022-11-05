import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

def save_depth_image(image, max_depth, filename):
    cm = plt.get_cmap('turbo')
    max_depth = 3.0
    img = Image.fromarray(
        np.rint(cm(np.array(image) / max_depth) * 255.0).astype(np.int8), mode="RGBA"
    )
    img.save(filename)

def save_rgb_image(image, max_val, filename):
    img = Image.fromarray(
        np.rint(
            image / max_val * 255.0
        ).astype(np.int8),
        mode="RGB",
    )
    img.save(filename)

def save_rgba_image(image, max_val, filename):
    img = Image.fromarray(
        np.rint(
            image / max_val * 255.0
        ).astype(np.int8),
        mode="RGBA",
    )
    img.save(filename)
