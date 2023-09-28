import numpy as np
from numpy import ndarray
from PySide6.QtGui import QImage, QColor
import qimage2ndarray as q2a
from scipy import sparse
from scipy.ndimage import binary_dilation
import matplotlib.pyplot as plt

def getPixelData(mask: ndarray, img: ndarray) -> ndarray:
    x, y = np.where(mask)
    pixelData = np.zeros((np.sum(mask), 5))
    pixelData[:,0] = x
    pixelData[:,1] = y

    for i in range(3):
        pixelData[:,i+2] = img[x, y, i]

    return pixelData

def plotQImage(img: QImage):
    arr = q2a.rgb_view(img)
    plt.figure()
    plt.imshow(arr)
    plt.show()

def trimImage(img: QImage, mask: QImage) -> QImage:
    alpha = q2a.recarray_view(mask)['alpha']
    boundX0 = 0
    boundX1 = alpha.shape[0]
    boundY0 = 0
    boundY1 = alpha.shape[1]

    for x in range(alpha.shape[0]):
        if np.sum(alpha[x,:]):
            boundX0 = x
            break

    for x in reversed(range(alpha.shape[0])):
        if np.sum(alpha[x,:]):
            boundX1 = x
            break

    for y in range(alpha.shape[1]):
        if np.sum(alpha[:,y]):
            boundY0 = y
            break

    for y in reversed(range(alpha.shape[1])):
        if np.sum(alpha[:,y]):
            boundY1 = y
            break

    boundX0 = max(0, boundX0 - 3)
    boundX1 = min(alpha.shape[0], boundX1 + 3)
    boundY0 = max(0, boundY0 - 3)
    boundY1 = min(alpha.shape[1], boundY1 + 3)

    newImg = QImage((boundY1 - boundY0), (boundX1 - boundX0), QImage.Format.Format_ARGB32)
    newImg.fill(QColor(0, 0, 0, 0))

    for x in range(newImg.size().height()):
        for y in range(newImg.size().width()):
            newImg.setPixelColor(y, x, img.pixelColor(y + boundY0, x + boundX0))
    
    return newImg

def convertQ2N(img: QImage) -> ndarray:
    return q2a.rgb_view(img)

def convertN2Q(img: ndarray) -> QImage:
    return q2a.array2qimage(img)

def D_matrix(n: int) -> ndarray:
    e = np.ones(n)
    D = sparse.spdiags([e, -e], [0, 1], n-1, n)
    return D

def poisson_edit(source: ndarray, target: ndarray, mask: ndarray) -> ndarray:
    combinedImage = source.copy()
    dilatedMask = binary_dilation(mask, np.ones((3, 3)))
    combinedImage[dilatedMask] = target[dilatedMask]

    nx, ny, nc = source.shape
    m = mask.reshape(ny*nx, order='F')

    Dx = sparse.kron(sparse.identity(ny), D_matrix(nx))
    Dy = sparse.kron(D_matrix(ny), sparse.identity(nx))
    Dhat = sparse.vstack([Dx, Dy])

    n = nx*ny
    nr = np.sum(m)

    data = np.ones(nr)
    j = range(nr)
    i = np.where(m)[0]
    I = sparse.coo_matrix((data, (i, j)), shape=(n, nr))

    final = np.zeros(n*nc, dtype=int)
    final = final.reshape((nx, ny, nc))
    for ch in range(nc):
        f = source[:,:,ch].reshape(nx*ny, order='F')
        h = combinedImage[:,:,ch].reshape(nx*ny, order='F')
        A = Dhat@I
        b = -Dhat@((1-m)*f)
        b_addition = Dhat@h
        x = sparse.linalg.lsqr(A, (b + b_addition))[0]

        u = np.zeros(n, dtype=int)
        u[~m] = f[~m]
        u[m] = x
        uImg = u.reshape((nx, ny), order='F')
        final[:,:,ch] = uImg

    return final