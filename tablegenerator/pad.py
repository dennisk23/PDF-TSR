import numpy as np
import os
import sys
import imageio

def pad(a, img_res):
	"""Return bottom right padding."""
	zeros = np.full(img_res, 255)
	zeros[:a.shape[0], :a.shape[1], :a.shape[2]] = a
	return zeros

def pad_image(location1, location2, res):
    max_size_diff = 4000
    resolution = (res, res, 3)

    img1 = imageio.imread(location1, pilmode='RGB').astype(np.float)
    if img1.shape[0] > res or img1.shape[1] > res:
        os.remove(location1)
        os.remove(location2)
        return False
    img2 = imageio.imread(location2, pilmode='RGB').astype(np.float)

    if((img1.shape[0] <= res and img1.shape[1] <= res) or (img2.shape[0] <= res and img2.shape[1] <= res)) and \
        abs(img1.shape[0] - img2.shape[0]) <= max_size_diff and abs(img1.shape[1] - img2.shape[1]) <= max_size_diff:
        padded = pad(img1, resolution)
        imageio.imsave(location1, padded)
        padded = pad(img2, resolution)
        imageio.imsave(location2, padded)
        return True
    else:
        os.remove(location1)
        os.remove(location2)
        return False

# pad_image('irr5/png/train/4-5.png', 'irr5/png/train_labels/4-5.png', 1024)
