from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QImage, QColor, QPixmap, QPainter, QMouseEvent, QTransform, QCursor
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from src.utils import plotQImage, trimImage

class Merge(QLabel):
    def __init__(self, path):
        super(Merge, self).__init__()
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

        self.insertImg = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        self.insertImg.fill(QColor(0, 0, 0, 0))

        self.originalImg = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        self.originalImg.fill(QColor(0, 0, 0, 0))

        self.transformX = 0
        self.transformY = 0
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.transformScale = QTransform()
        self.isEdit = False
        self.isScaling = False
        self.lastCursorPos = QPointF()

        self.mousePressed = False
        self.setMouseTracking(True)

        self.render()

    def render(self, scaleHighlight = False):
        self.image.fill(QColor(0, 0, 0, 0))
        qpainter = QPainter(self.image)
        qpainter.drawImage(0, 0, self.bgImage)
        if self.isEdit:
            transform = QTransform()
            qpainter.setTransform(transform.translate(self.transformX, self.transformY))
            qpainter.drawImage(0, 0, self.insertImg)

            if scaleHighlight:
                pen = qpainter.pen()
                pen.setWidth(3)
                pen.setColor(QColor('#FFFFFF'))
                qpainter.setPen(pen)
            qpainter.drawRect(0, 0, self.insertImg.size().width() ,self.insertImg.size().height())
        self.setPixmap(QPixmap.fromImage(self.image))

    def paste(self, img: QImage):
        img = trimImage(img, img)
        imgX = img.size().width()
        imgY = img.size().height()
        targetX = self.insertImg.size().width()
        targetY = self.insertImg.size().height()

        ratioX = imgX / targetX
        ratioY = imgY / targetY


        if imgY > targetY and ratioY > ratioX:
            newHeight = targetY
            newWidth = newHeight * (imgX / imgY)
            self.transformScale.scale(newWidth / imgX, newHeight / imgY)
            img = img.transformed(self.transformScale)
        elif imgX > targetX and ratioX > ratioY:
            newWidth = targetX
            newHeight = newWidth * (imgY / imgX)
            self.transformScale.scale(newWidth / imgX, newHeight / imgY)
            img = img.transformed(self.transformScale)

        self.originalImg = img
        self.insertImg = self.originalImg.copy()

        self.isEdit = True
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        self.render()

    def applyResult(self, result: QImage):
        self.bgImage = result
        self.reset()
        self.render()

    def reset(self):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.insertImg = QImage(self.bgWidth, self.bgHeight, QImage.Format.Format_ARGB32)
        self.insertImg.fill(QColor(0, 0, 0, 0))
        self.transformX = 0
        self.transformY = 0
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.transformScale = QTransform()
        self.isEdit = False
        self.isScaling = False
        self.lastCursorPos = QPointF()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if not self.isEdit:
            return super().mouseMoveEvent(ev)
        
        point = ev.position()
        oldPoint = self.lastCursorPos
        distanceX = point.x() - oldPoint.x()
        distanceY = point.y() - oldPoint.y()
        insertX = self.insertImg.size().width()
        insertY = self.insertImg.size().height()
        
        if self.isScaling and self.mousePressed:
            self.scaleX = self.scaleX + distanceX
            self.scaleY = self.scaleY + distanceY
            self.insertImg = self.originalImg.scaledToWidth(self.originalImg.size().width() + self.scaleX)
            self.lastCursorPos = ev.position()
            self.render(scaleHighlight=True)

            return super().mouseMoveEvent(ev)
        elif self.mousePressed:
            self.transformX += distanceX
            self.transformY += distanceY
            self.lastCursorPos = ev.position()
            self.render()
            return super().mouseMoveEvent(ev)

        
        leftBound = (self.transformX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY - 2)
        rightBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX + insertX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY - 2)
        topBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + 2 >= point.y() >= self.transformY - 2)
        bottomBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY + insertY - 2)

        if rightBound and bottomBound:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            self.render(scaleHighlight=True)
        # elif leftBound or rightBound:
            # self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        # elif topBound or bottomBound:
            # self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.render()
        
        return super().mouseMoveEvent(ev)

    def mousePressEvent(self, ev: QMouseEvent):
        if not self.isEdit:
            return super().mousePressEvent(ev)

        point = ev.position()
        insertX = self.insertImg.size().width()
        insertY = self.insertImg.size().height()

        leftBound = (self.transformX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY - 2)
        rightBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX + insertX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY - 2)
        topBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + 2 >= point.y() >= self.transformY - 2)
        bottomBound = (self.transformX + insertX + 2 >= point.x() >= self.transformX - 2 and
                     self.transformY + insertY + 2 >= point.y() >= self.transformY + insertY - 2)
        
        if rightBound and bottomBound:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            self.isScaling = True
        # elif leftBound or rightBound:
            # self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            # self.isScaling = True
        # elif topBound or bottomBound:
            # self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
            # self.isScaling = True
        else:
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self.isScaling = False

        self.lastCursorPos = ev.position()
        self.mousePressed = True

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self.isEdit:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        self.isScaling = False
        self.mousePressed = False
        return super().mouseReleaseEvent(ev)