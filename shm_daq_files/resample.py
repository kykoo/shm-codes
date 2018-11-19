#!/usr/bin/python3
#
# RESAMPLING
#

from numpy import *


tk = 0
t0 = 0
v0 = 0

def resample(Fs, ti, vi):
    global tk, t0, v0
    Tk = []
    Vk = []

    if t0 == 0:
        t0 = ti
        v0 = vi
        tk = ceil(ti)
    elif ti < tk:
        t0 = ti
        v0 = vi
    elif tk <= ti:
        while tk <= ti:
            vk = []
            for j in range(len(vi)):
            #for j in range(vi.shape[0]):
                vk.append(interp(tk, [t0, ti], [v0[j], vi[j]]))
            Tk.append(tk)
            Vk.append(vk)
            tk = round(tk * Fs + 1)/Fs
        t0 = ti
        v0 = vi

    return Tk, Vk


if __name__ == '__main__':
    from matplotlib.pyplot import *
    xi = sort(random.rand(210,1) * 3, axis=0)
    yi = hstack((sin(2*pi*1*xi), cos(2*pi*1*xi)))
    Fs = 70
    # print(xi)

    TK = []
    VK = []
    for idx in range(xi.shape[0]):
        # print(xi[idx, 0])
        t_, v_ = resample(Fs, xi[idx, 0], list(yi[idx,:]))
        # print(t_, v_, t0, v0, tk)
        for idx, t in enumerate(t_):
            TK.append(t_[idx])
            VK.append(v_[idx])

    TK = array(TK)
    VK = array(VK)
    print(TK)

    ion()
    figure(1)
    clf()
    plot(xi, yi, '.')
    plot(TK, VK, '.-')
