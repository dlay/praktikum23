import numpy as np

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QImage, QColor, QPixmap, QPainter, QMouseEvent, QPen
from PySide6.QtCore import QLine, QPointF, Qt

from PySide6.QtWidgets import QApplication

from src.network import train
from src.utils import convertQ2N, getPixelData



class Scribble(QLabel):
    def __init__(self, path):
        super(Scribble, self).__init__()
        self.bgImage = QImage(path, format=QImage.Format.Format_ARGB32)
        yAvail = QApplication.primaryScreen().availableGeometry().height()
        xAvail = QApplication.primaryScreen().availableGeometry().width() / 2
        if self.bgImage.height() > yAvail or self.bgImage.width() > xAvail:
            self.bgImage = self.bgImage.scaled(xAvail - 100, yAvail - 100, Qt.AspectRatioMode.KeepAspectRatio)
        self.bgWidth = self.bgImage.width()
        self.bgHeight = self.bgImage.height()

        self.image = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        self.image.fill(QColor(0, 0, 0, 0))
        self.setPixmap(QPixmap.fromImage(self.image))
        self.setFixedSize(self.bgWidth, self.bgHeight)


        self.maskImage = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        self.maskImage.fill(QColor(0, 0, 0, 0))

        self.penActiveColor = QColor('#00FF00')
        self.penInactiveColor = QColor('#FF0000')
        self.penEraseColor = QColor(0, 0, 0, 0)
        self.penColor = self.penActiveColor

        tmp = 0
        self.errorTest = 10 / tmp

        self.pen = QPen(self.penColor, 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setPenWidth(10)
        self.lastCursorPos = QPointF()

        self.render()

    def render(self):
        qpainter = QPainter(self.image)
        qpainter.drawImage(0, 0, self.bgImage)
        qpainter.drawImage(0, 0, self.maskImage)
        self.setPixmap(QPixmap.fromImage(self.image))

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        painter = QPainter(self.maskImage) 
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.setPen(self.pen)
        painter.drawLine(QLine(self.lastCursorPos.toPoint(), ev.position().toPoint()))

        self.render()
        self.lastCursorPos = ev.position()
            
        return super().mouseMoveEvent(ev)

    def mousePressEvent(self, ev): 
        self.lastCursorPos = ev.position()
    
    def switchColor(self) -> QColor:
        tmp = self.penActiveColor
        self.penActiveColor = self.penInactiveColor
        self.penInactiveColor = tmp
        self.penColor = self.penActiveColor
        self.pen.setColor(self.penColor)

        return self.penColor

    def setPenWidth(self, newWidth: int):
        pix = QPixmap(newWidth, newWidth)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        painter.drawRoundedRect(0, 0, newWidth, newWidth, newWidth/2, newWidth/2)
        painter.end()
        self.setCursor(pix)
        self.pen.setWidth(newWidth)

    def toggleErase(self) -> QColor:
        if self.penColor == self.penEraseColor:
            self.penColor = self.penActiveColor
            self.pen.setColor(self.penColor)
            return self.penColor
        
        self.penColor = self.penEraseColor
        self.pen.setColor(self.penColor)

        return QColor('#000000')

    def applyMask(self):
        bgImg = convertQ2N(self.bgImage)
        convertedMask = convertQ2N(self.maskImage)

        fgMask = convertedMask[:,:,1] == 255
        bgMask = convertedMask[:,:,0] == 255

        if np.sum(fgMask) == 0:
            raise RuntimeError('Please specify some Region for segmentation (green scribble).')

        fgData = getPixelData(fgMask, bgImg)
        bgData = getPixelData(bgMask, bgImg)

        data = np.concatenate((fgData, bgData), axis=0)
        labels = np.zeros(data.shape[0])
        labels[0:fgData.shape[0]] = 1

        fullMask = np.ones([bgImg.shape[0], bgImg.shape[1]], dtype=int)
        fullImageData = getPixelData(fullMask, bgImg)

        boundary = train(data, labels, fullImageData)
        newImage = np.reshape(boundary, (-1, bgImg.shape[1]))

        self.maskImage.fill(QColor(0, 0, 0, 0))
        for x in range(self.bgWidth):
            for y in range(self.bgHeight):
                if newImage[y][x] >= 0.6:
                    self.maskImage.setPixelColor(x, y, QColor('#00FF00'))

        self.render()

    def copy(self):
        img = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        maskCount = 0
        for x in range(self.bgWidth):
            for y in range(self.bgHeight):
                if self.maskImage.pixelColor(x, y) == QColor('#00FF00'):
                    img.setPixelColor(x, y, self.bgImage.pixelColor(x, y))
                    maskCount += 1

        if maskCount == 0 or maskCount == (self.bgWidth * self.bgHeight):
            raise RuntimeError('No mask found.')

        return img