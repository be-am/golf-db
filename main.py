from ctypes import alignment
import sys
from tokenize import group
from PyQt5.QtWidgets import (QWidget, QSlider, QHBoxLayout, QPushButton, QCheckBox, QInputDialog,
                             QLabel, QApplication, QFrame, QSplitter, QGroupBox, QRadioButton, QVBoxLayout, QGridLayout, QFileDialog)
from PyQt5.QtGui import QPainter, QPixmap, QImage, QPen, QFont, QFontDatabase, QColor
from PyQt5.QtCore import Qt, QFile, QTextStream, QRect
import PyQt5.QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QTreeView
from PyQt5 import QtWidgets, QtCore, QtGui
from BreezeStyleSheets.test.ui import AlignHCenter, AlignRight, AlignVCenter
from PyQt5.Qt import QStandardItemModel, QStandardItem#, QAbstractView
import breeze_resources
import os
import cv2
import numpy as np
from threading import Thread
from asyncio import sleep
import time
import matplotlib.pyplot as plt
from utils import count_dbot, get_pixel_area, count_pixel_per_grass_grade
from db import controller

class StandardItem(QStandardItem):
    def __init__(self, txt='', font_size=12, set_bold=False, color=QColor(0, 0, 0)):
        super().__init__()

        fnt = QFont('Open Sans', font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)

class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mousePressEvent(event)

    # def mouseMoveEvent(self, event):
    #     ex.pix_coordnate.setText('pos {}'.format(event.pos()))


class MainView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.running = 0
    
    def initUI(self):
        self.setWindowTitle('Dexterous Technology / UFO-astronaut')
        self.setGeometry(300, 300, 1200, 950)

        title1 = QLabel()
        title1.setStyleSheet("border: 1px solid black;")
        title1.setAlignment(AlignHCenter | AlignVCenter)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setStyleSheet("border: 1px solid black;")
        # self.tree_view.doubleClicked.connect(self.getValue)
        self.parse_data_from_db()
        self.tree_view.setSelectionMode(2)

        self.image_viewer_activator = QPushButton('show')
        self.image_viewer_activator.setStyleSheet("border: 1px solid black;")
        self.image_viewer_activator.clicked.connect(self.activator_butten_clicked)

        self.image_viewer_layout = PhotoViewer(self)
        self.image_viewer_layout.setStyleSheet("border: 1px solid black;")
        self.image_viewer_layout.setAlignment(AlignHCenter | AlignVCenter)


        self.statistics_layout = QLabel()
        self.statistics_layout.setStyleSheet("border: 1px solid black;")
        self.statistics_layout.setAlignment(AlignHCenter | AlignVCenter)

        grid = QGridLayout()
        grid.addWidget(title1, 0, 0, 2, 10) #title
        grid.addWidget(self.tree_view, 2, 0, 7, 2) # tree_view
        grid.addWidget(self.image_viewer_activator, 9, 0, 1, 2)  # image_viewer_activator
        grid.addWidget(self.image_viewer_layout, 2, 2, 7, 6)  # image_viewer_layout
        grid.addWidget(self.image_info_layout(), 9, 2, 1, 8)  # image_info_layout
        grid.addWidget(self.statistics_layout, 2, 8, 7, 2) # statistics_layout
        self.setLayout(grid)
        self.show()

    def image_info_layout(self):
        groupbox = QGroupBox()
        groupbox.setStyleSheet("border: 1px solid black;")
        
        self.tif_path_label = QLabel()
        self.tif_path_label.setStyleSheet("border: 0px solid black;")

        self.pix_coordnate = QLabel()
        self.pix_coordnate.setStyleSheet("border: 0px solid black;")

        grid = QGridLayout()
        grid.addWidget(self.tif_path_label, 0, 0, 1, 1)
        grid.addWidget(self.pix_coordnate, 0, 1, 1, 1)
        groupbox.setLayout(grid)
        
        return groupbox

    def parse_data_from_db(self):
        data_by_id = controller.bring_data_by_id()
        area_list = data_by_id('Area')
    
        self.treeModel = QStandardItemModel()
        rootNode = self.treeModel.invisibleRootItem()
        

        for area_id, area in area_list:
            tree1 = StandardItem(area, 16, set_bold=True)
            rootNode.appendRow(tree1)
            field_list = data_by_id('Field', area_id)
            
            
            for _, field_id, field_name in field_list:
                tree2 = StandardItem(field_name, 14, color=QColor(155, 0, 0))
                tree1.appendRow(tree2)
                course_list = data_by_id('Course', field_id)
                
                for _, course_id, course in course_list:
                    tree3 = StandardItem(course, 12, color=QColor(155, 0, 0))
                    tree2.appendRow(tree3)
                    hole_list = data_by_id('Hole', course_id)
                    
                    for _, hole_id, hole in hole_list:
                        tree4 = StandardItem(hole, 10, color=QColor(155, 0, 0))
                        tree3.appendRow(tree4)
                        state_list = data_by_id('State', hole_id)

                        for state in state_list:
                            info = state[2]
                            for key in info.keys():
                                tree5 = StandardItem(key, 14)
                                tree4.appendRow(tree5)

        self.tree_view.setModel(self.treeModel)


    def activator_butten_clicked(self):
        self.image_viewer_layout.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        indexes = self.tree_view.selectedIndexes()
        db_cont = controller.bring_data_by_name()

        print(indexes)
        label_data = []
        
        for index in indexes:
            temp_keys = []
            
            while index.data() != None:
                temp_keys.append(index.data())
                index = index.parent()

            label_data.append(temp_keys[::-1])

        total_data = []

        for label in label_data:
            data_dict = {}
            path_list_from_db = db_cont.get_item_from_db(label)

            for path in path_list_from_db:
                data_dict['date'] = path[0]
                data_dict[label[-1]] = path[1][label[-1]]
                total_data.append(data_dict)

        print('total_data=',  total_data)

        init_date = ''
        last_date = ''

        path_list = {}
        data_dict
        for data in total_data:
            for key in data.keys():
                if key != 'date':
                    path_list[key] = data[key]

        qimg, statistics_info = self.make_qpix_image(path_list)
        self.image_viewer_layout.setPhoto(qimg)

        self.set_statistics_info(statistics_info)


    def set_statistics_info(self, statistics_info):
        statistics_txt = ''
        statistics_info.keys()
        for key in statistics_info.keys():
            if key == 'dbot':
                statistics_txt += f'\ndbot count = {statistics_info[key]}\n'
            elif key == 'grass_grade':
                statistics_txt += f'\npixel count per grass_grade\n grade1 =  {statistics_info[key][0]}\n grade2 =  {statistics_info[key][1]}\n grade3 =  {statistics_info[key][2]}\n grade4 =  {statistics_info[key][3]}\n grade5 =  {statistics_info[key][4]}\n'
            elif key == 'twin':
                statistics_txt += f'\npixel count where twin grass =  {statistics_info[key]}\n'
            
        
        self.statistics_layout.setText(statistics_txt)

    def make_qpix_image(self, path_list):
        statistics_info = {}

        if len(path_list) == 1:
            key = list(path_list.keys())[0]
            path = path_list[key]

            if key == 'img':
                cvimage = cv2.imread(path)

            else:
                cvimage = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if key == 'dbot':
                    statistics_info['dbot'] = count_dbot(cvimage)
                elif key == 'grass_grade':
                    statistics_info['grass_grade'] = count_pixel_per_grass_grade(cvimage)
                elif key == 'twin':
                    statistics_info['twin'] = get_pixel_area(cvimage)

            qimg = self.cvimg2qpixmap(cvimage.astype(np.uint8))
            # self.image_viewer_layout.setPhoto(qimg)
        else:
            keys = list(path_list.keys())
            if 'img' in keys:
                keys.remove('img')
                img = cv2.imread(path_list['img']).astype(np.uint8)
                total_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                
                for key in keys:
                    mask = cv2.imread(path_list[key], cv2.IMREAD_GRAYSCALE)
                    total_mask += mask
                    if key == 'dbot':
                        statistics_info['dbot'] = count_dbot(mask)
                    elif key == 'grass_grade':
                        statistics_info['grass_grade'] = count_pixel_per_grass_grade(mask)
                    elif key == 'twin':
                        statistics_info['twin'] = get_pixel_area(mask)

                total_mask_01 = np.where(total_mask == 0, 0, 1)
                total_mask = np.array(total_mask/np.max(total_mask) * 255, dtype=np.uint8)
                total_mask_color = cv2.applyColorMap(total_mask, cv2.COLORMAP_JET)
                total_mask_color = total_mask_color * total_mask_01[...,np.newaxis]
                cvimage = cv2.addWeighted(img.astype(np.uint8), 1, total_mask_color.astype(np.uint8), 1, 0.0)
                qimg = self.cvimg2qpixmap(cvimage)
                
                
                

            else:
                for idx, key in enumerate(keys):
                    if idx == 0:
                        mask = cv2.imread(path_list[key], cv2.IMREAD_GRAYSCALE)
                        if key == 'dbot':
                            statistics_info['dbot'] = count_dbot(mask)
                        elif key == 'grass_grade':
                            statistics_info['grass_grade'] = count_pixel_per_grass_grade(mask)
                        elif key == 'twin':
                            statistics_info['twin'] = get_pixel_area(mask)
                    else:
                        temp = cv2.imread(path_list[key], cv2.IMREAD_GRAYSCALE)  
                        mask += temp
                        if key == 'dbot':
                            statistics_info['dbot'] = count_dbot(mask)
                        elif key == 'grass_grade':
                            statistics_info['grass_grade'] = count_pixel_per_grass_grade(mask)
                        elif key == 'twin':
                            statistics_info['twin'] = get_pixel_area(mask)    

                mask_01 = np.where(mask == 0, 0, 1)
                mask = np.array(mask/np.max(mask) * 255, dtype=np.uint8)
                cvimage = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
                cvimage = cvimage * mask_01[...,np.newaxis]
                
                qimg = self.cvimg2qpixmap(cvimage.astype(np.uint8))

        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\nstatistics_info = ', statistics_info)
                

        return qimg, statistics_info

    def cvimg2qpixmap(self, cvImg):
        if len(cvImg.shape) == 3:
            cvImg = cv2.cvtColor(cvImg, cv2.COLOR_BGR2RGB)
            height, width, channel = cvImg.shape
            bytesPerLine = 3 * width
            qImg = QPixmap(QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_RGB888))

        elif len(cvImg.shape) == 2:
            height, width = cvImg.shape
            cvImg = cvImg/np.max(cvImg) * 255
            cvImg = cvImg.astype(np.uint8)
            totalBytes = cvImg.nbytes
            bytesPerLine = int(totalBytes/height)
            qImg = QPixmap(QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_Grayscale8))

        return qImg
            # added_image = cv2.addWeighted(background,0.8,overlay,0.2,0)
    # def createVideoPlayerView(self):
    #     groupbox = QGroupBox()
    #     groupbox.setStyleSheet("border:1px;")
    #     self.video_view = Laber_with_rect()
    #     self.video_view.setMouseTracking(True)

    #     self.video_pos_slider = QSlider(Qt.Horizontal, self)
    #     self.video_pos_slider.setRange(0, 100)
    #     self.video_pos_slider.setFocusPolicy(Qt.NoFocus)
    #     self.video_pos_slider.setPageStep(1)

    #     self.video_pos_slider.valueChanged.connect(self.updateLabel)

    #     self.video_pos_label = QLabel('0', self)
    #     self.video_pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #     self.video_pos_label.setMinimumWidth(80)
    #     # self.video_pos_label.mouseMoveEvent = self.mousepressed
    #     # self.video_pos_label.mouseReleaseEvent

    #     self.open_video_button = QPushButton("open", self)

    #     self.open_video_button.setStyleSheet("border:1px solid #808080;")

    #     self.open_video_button.clicked.connect(self.openButtenClicked)
    #     self.play_video_button.clicked.connect(self.playButtenClicked)
    #     self.pause_video_button.clicked.connect(self.pauseButtenClicked)
    #     self.resume_video_button.clicked.connect(self.resumeButtenClicked)
    #     self.video_pos_slider.sliderPressed.connect(self.pauseButtenClicked)
    #     self.video_pos_slider.sliderReleased.connect(self.setvideoframe)

    #     self.udp_check_box = QCheckBox("UDP")

    #     grid = QGridLayout()
    #     grid.addWidget(self.video_view, 0, 0, 10, 6)
    #     grid.addWidget(self.video_pos_slider, 10, 0, 1, 5)
    #     grid.addWidget(self.video_pos_label, 10, 5, 1, 1)

    #     grid.addWidget(self.udp_check_box, 11, 0, 1, 1)
    #     grid.addWidget(self.open_video_button, 11, 1, 1, 1)
    #     grid.addWidget(self.play_video_button, 11, 2, 1, 1)
    #     grid.addWidget(self.pause_video_button, 11, 3, 1, 1)
    #     grid.addWidget(self.resume_video_button, 11, 4, 1, 1)
    #     groupbox.setLayout(grid)

    #     return groupbox



if __name__ == '__main__':
    # controller.main()

    # area_list = controller.bring_data('Area')
    # field_list = controller.bring_data('Field')
    # course_list = controller.bring_data('Course')
    # hole_list = controller.bring_data('Hole')
    # state_list = controller.bring_data('State')
    # print('area_list = ', area_list)
    # print('field_list = ', field_list)
    # print('course_list = ', course_list)
    # print('hole_list = ', hole_list)
    # print('state_list = ', state_list)


    
    
    app = QApplication(sys.argv)
    file = QFile(":/dark/stylesheet.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())

    global ex
    ex = MainView()
    sys.exit(app.exec_())
