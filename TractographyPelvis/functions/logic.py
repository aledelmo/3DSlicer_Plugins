import numpy as np
from .input_output import save_vtk, read_vtk
from dipy.tracking.metrics import mean_orientation


def filter(in_fpath, out_fpath, dir):
    fibers = np.array(read_vtk(in_fpath)[0])
    mean_or = [mean_orientation(f) for f in fibers]
    princ = np.array([abs(x).argmax() for x in mean_or])
    seg = fibers[princ == dir]
    save_vtk(out_fpath, seg)
