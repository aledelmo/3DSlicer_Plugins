#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import cv2
import nrrd
import numpy as np
import argparse


__author__ = 'Alessandro Delmonte'
__email__ = 'delmonte.ale92@gmail.com'


def nothing(_):
    pass


def main():
    filename = setup()

    frames, _ = nrrd.read(filename)
    frames = frames.astype('float32')
    frames = 128 * ((frames - np.amin(frames)) / np.amax(frames))

    cv2.namedWindow('image', cv2.WINDOW_NORMAL)

    cv2.createTrackbar('frame', 'image', 0, frames.shape[2] - 1, nothing)
    cv2.createTrackbar('low', 'image', 0, int(np.amax(frames)) - 1, nothing)
    cv2.createTrackbar('high', 'image', 0, int(np.amax(frames)) - 1, nothing)

    while True:

        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break

        f = cv2.getTrackbarPos('frame', 'image')
        low = cv2.getTrackbarPos('low', 'image')  # 22
        high = cv2.getTrackbarPos('high', 'image')  # 61
        edges = cv2.Canny(frames[:, :, f].astype('uint8'), low, high)
        im_show = np.vstack((frames[:, :, f].astype('uint8'), edges))
        cv2.imshow('image', im_show)

    cv2.destroyAllWindows()


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('Input_Image', help='Name of the input file', type=check_ext)

    args = parser.parse_args()

    return args.Input_Image


def check_ext(value):
    filename, file_extension = os.path.splitext(value)
    if file_extension == '.nrrd':
        return value
    else:
        raise argparse.ArgumentTypeError(
            "Invalid file extension (file format supported: nrrd): %r" % value)


if __name__ == "__main__":
    main()
    sys.exit()
