import sys
import matplotlib.pyplot as plt 
import PIL
import cv2
from osgeo import gdal
import numpy as np


# def save_1bit_image(img, save_path):
#     img = util.img_as_bool(img)
#     img = PIL.Image.fromarray(img)
#     img.save(save_path,bits=1,optimize=True)


def count_dbot(img_or_imgpath):

    if type(img_or_imgpath) == str:
        if img_or_imgpath[-4:].lower() == ".tif":
            tifDataset = gdal.Open(img_or_imgpath)
            mask = tifDataset.ReadAsArray()
        else:
            mask = plt.imread(img_or_imgpath)
    else:
        mask = img_or_imgpath

    mask_8bit = np.uint8(mask * 255)
    contours, _ = cv2.findContours(mask_8bit, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    count = 0

    for cnt in contours:
        # if (9 < cv2.contourArea(cnt)) and (cv2.contourArea(cnt) < 60):
        if (2 < cv2.contourArea(cnt)) and (cv2.contourArea(cnt) < 1000):
            count += 1

    return count

def get_pixel_area(img):
    temp = img.copy()
    if len(temp.shape) == 3:
        temp = cv2.cvtColor(temp, cv2.COLOR_RGB2GRAY)
    temp = np.where(temp != 0, 1, 0)
    area = np.sum(temp)

    return area

def get_img_perimeter(img):
    gray = img.copy()
    gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
    temp = np.zeros((gray.shape[0] + 10,gray.shape[1]+10), dtype = np.uint8)
    temp[5:-5, 5:-5, ...] = gray
    img_bin = np.where(temp !=0, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(img_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    cvt = contours[0]
    length = cv2.arcLength(cvt, True)
    return length


def make_masked_image(img, mask):
    draw = np.zeros_like(img)
    mask = np.where(mask, 255,0)
    draw[:,:,0] = mask
    
    draw = cv2.addWeighted(img, 1, draw, 1, 0)

    return draw  

def count_pixel_per_grass_grade(grass_grade):
    pixels = []
    for i in range(1, 6):
        pixels.append(np.sum(np.where(grass_grade == i, 1, 0)))

    return pixels

if __name__ == "__main__":

    mask_save_path = 'dataset/dbot/testimage_res.png'
    print(count_dbot(mask_save_path))
