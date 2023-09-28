from PySide6.QtWidgets import QMainWindow, QToolBar, QGridLayout, QWidget, QFileDialog, QLabel, QSpinBox, QMessageBox
from PySide6.QtGui import QAction, QImage, QColor, QPainter, QPixmap
from PySide6.QtCore import Qt

from src.merge import Merge
from src.scribble import Scribble
from src.utils import convertQ2N, convertN2Q, poisson_edit, trimImage

import os

class MyAction(QAction):
    def __init__(self):
        super(QAction, self).__init__()

    

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.merge = None
        self.scribble = None
        self.trained = False
        self.done = False

        self.setWindowTitle("Image Poisson App")
        toolbar = QToolBar("main toolbar")
        self.addToolBar(toolbar)

        tbImportScribble = QAction("Import Scribble Image", self)
        tbImportScribble.triggered.connect(self.onTbButtonOneClick)
        toolbar.addAction(tbImportScribble)

        tbImportMerge = QAction("Import Merge Image", self)
        tbImportMerge.triggered.connect(self.onTbButtonTwoClick)
        toolbar.addAction(tbImportMerge)

        self.penSpin = QSpinBox(self)
        self.penSpin.setMinimum(1)
        self.penSpin.setMaximum(100)
        self.penSpin.setSingleStep(1)
        self.penSpin.setValue(10)
        self.penSpin.valueChanged.connect(self.changePenWidth)
        self.penSpinAction = toolbar.addWidget(self.penSpin)
        self.penSpinAction.setVisible(False)

        self.tbSwitchPenColor = QAction("Switch Scribble Mode", self)
        self.tbSwitchPenColor.setVisible(False)
        toolbar.addAction(self.tbSwitchPenColor)

        self.tbModeIndicator = QLabel(self)
        self.tbModeIndicator.setVisible(True)
        toolbar.addWidget(self.tbModeIndicator)

        self.tbEraseToggle = QAction("Erase Toggle", self)
        self.tbEraseToggle.setVisible(False)
        toolbar.addAction(self.tbEraseToggle)

        self.tbTrain = QAction("Train", self)
        self.tbTrain.setVisible(False)
        toolbar.addAction(self.tbTrain)

        self.tbApplyMask = QAction("Apply Mask", self)
        self.tbApplyMask.setVisible(False)
        toolbar.addAction(self.tbApplyMask)

        self.tbPoissonEdit = QAction("Poisson Edit", self)
        self.tbPoissonEdit.setVisible(False)
        toolbar.addAction(self.tbPoissonEdit)

        self.tbSaveImage = QAction("Save Result", self)
        self.tbSaveImage.setVisible(False)
        toolbar.addAction(self.tbSaveImage)

        self.gridLayout = QGridLayout()

        mainWidget = QWidget()
        mainWidget.setLayout(self.gridLayout)
        self.setCentralWidget(mainWidget)

    def showMaskButton(self):
        if self.merge is None:
            return
        self.tbApplyMask.triggered.connect(self.copyMask)
        self.tbApplyMask.setVisible(True)

    def onTbButtonOneClick(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', './', 'Image files (*.jpg *.png)')

        if not os.path.isfile(path[0]):
            self.showErrorWindow('Error reading image', FileNotFoundError)
            return
        
        if self.scribble is not None:
            self.gridLayout.removeWidget(self.scribble)
            self.scribble.deleteLater()
            self.tbApplyMask.setVisible(False)
        else: 
            self.tbSwitchPenColor.triggered.connect(self.switchMode)
            self.tbEraseToggle.triggered.connect(self.toggleErase)
            self.tbTrain.triggered.connect(self.trainAndEval)
            
        self.scribble = Scribble(path[0])
        self.penSpinAction.setVisible(True)
        self.tbSwitchPenColor.setVisible(True)
        self.tbEraseToggle.setVisible(True)
        self.tbTrain.setVisible(True)

        self.colorIndicator(QColor('#00FF00'))
        self.changePenWidth(self.penSpin.value())

        self.gridLayout.addWidget(self.scribble, 0, 0)

    def onTbButtonTwoClick(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', './', 'Image files (*.jpg *.png)')

        if not os.path.isfile(path[0]):
            self.showErrorWindow('Error reading image', FileNotFoundError)
            return
        
        if self.merge is not None:
            self.gridLayout.removeWidget(self.merge)
            self.merge.deleteLater()
            self.tbPoissonEdit.setVisible(False)
            self.tbSaveImage.setVisible(False)

        self.merge = Merge(path[0])
        self.gridLayout.addWidget(self.merge, 0, 1)
        if self.trained:
            self.showMaskButton()

    def switchMode(self):
        color = self.scribble.switchColor()
        self.colorIndicator(color)

    def toggleErase(self):
        color = self.scribble.toggleErase()
        self.colorIndicator(color)

    def colorIndicator(self, color: QColor):
        pix = QPixmap(18, 18)
        pix.fill(color)
        self.tbModeIndicator.setPixmap(pix)

    def changePenWidth(self, val: int):
        self.scribble.setPenWidth(val)

    def trainAndEval(self):
        try:
            self.scribble.applyMask()
        except RuntimeError as e:
            self.showErrorWindow('Error in segmentation', e)
            return
        self.showMaskButton()
        self.trained = True

    def copyMask(self):
        try:
            copy = self.scribble.copy()
        except RuntimeError as e:
            self.showErrorWindow('Error retrieving mask', e)
            return
        self.merge.paste(copy)
        self.tbPoissonEdit.triggered.connect(self.applyPoisson)
        self.tbPoissonEdit.setVisible(True)

    def applyPoisson(self):
        os.environ['KMP_DUPLICATE_LIB_OK']='True'
        trimmedTargetImg = trimImage(self.scribble.bgImage, self.scribble.maskImage)
        trimmedMaskImg = trimImage(self.scribble.maskImage, self.scribble.maskImage)
        scaledTargetImg = trimmedTargetImg.transformed(self.merge.transformScale)
        scaledMaskImg = trimmedMaskImg.transformed(self.merge.transformScale)

        targetImg = QImage(self.merge.bgWidth, self.merge.bgHeight, QImage.Format.Format_ARGB32)
        targetImg.fill(QColor(0, 0, 0, 0))
        qpainterTrgt = QPainter(targetImg)
        qpainterTrgt.drawImage(self.merge.transformX,
                               self.merge.transformY,
                               scaledTargetImg.scaledToWidth(self.merge.scaleX + scaledTargetImg.size().width()))
        
        qpainterTrgt.end()

        maskImg = QImage(self.merge.bgWidth, self.merge.bgHeight, QImage.Format.Format_ARGB32)
        maskImg.fill(QColor(0, 0, 0, 0))
        qpainterMask = QPainter(maskImg)
        qpainterMask.drawImage(self.merge.transformX,
                               self.merge.transformY,
                               scaledMaskImg.scaledToWidth(self.merge.scaleX + scaledMaskImg.size().width()))
        qpainterMask.end()

        source = convertQ2N(self.merge.bgImage)
        target = convertQ2N(targetImg)
        mask = convertQ2N(maskImg)

        maskBool = mask[:,:,1] == 255
        result = poisson_edit(source, target, maskBool)

        finalImg = convertN2Q(result)
        self.merge.applyResult(finalImg)

        self.tbSaveImage.triggered.connect(self.saveImage)
        self.tbSaveImage.setVisible(True)

    def saveImage(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "result.png", "PNG (*.png)")
        self.merge.bgImage.save(path)

    def showErrorWindow(self, msg: str, err: Exception):
        dlg = QMessageBox(self)
        dlg.setWindowTitle('Error!')
        dlg.setText(f"{msg}:\n{err}")
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.exec()