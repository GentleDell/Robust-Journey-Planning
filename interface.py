# -*- coding: utf-8 -*-
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView

import codecs
from datetime import datetime
from robust_planning import _DEFAULT_YEAR_, path_and_probability

class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui_MainWindow, self).__init__()
        # Set the size of Main Window
        self.setFixedSize(1000, 700)
        # Initialize the layout
        self.initLayout()
        self.initLeftWidget()

    def search(self):

        source = str(self.sourceInput.text())
        dest   = str(self.destInput.text())

        date     = str(self.calendarInput.text())
        deptTime = str(self.timeInput.text())
        arrTime  = str(self.timeInputArr.text())

        maxTrans = str(self.exchangeInput.text())
        
        # for path planning and monte carlo sampling        
        max_transfer_stop = int(maxTrans)
        
        departure_month = date.split('/')[0]
        departure_day   = int(date.split('/')[1])
        departure_hour  = int(deptTime.split(':')[0])
        departure_minute= int(deptTime.split(':')[1])
        arrival_hour    = int(arrTime.split(':')[0])
        arrival_minute  = int(arrTime.split(':')[1])
        
        dep_date = datetime.strptime( departure_month+ ' {:02d} {:02d}'.format(departure_day, _DEFAULT_YEAR_), '%b %d %Y')
        dep_time = '{:02d}:{:02d}'.format(departure_hour, departure_minute)
        arr_time = '{:02d}:{:02d}'.format(arrival_hour, arrival_minute)
        
        plotplan = path_and_probability(source, dest, max_transfer_stop, dep_time, arr_time, dep_date)
        
        f = codecs.open("./data/Sample_Application.html", 'r', 'utf-8')
        html = f.read()
        self.web = QWebEngineView()
        self.web.setHtml(html)
        self.web.setFixedSize(640, 700)

        self.right_layout.addWidget(self.web, 0, 0, 12, 8)
        self.right_widget.setStyleSheet('''
            QWidget#right_widget{color:#232C51;
                                  background:white;
                                  border:1px solid darkGray;
                                  border-top-right-radius:5px;
                                  border-top-left-radius:5px;
                                  border-bottom-right-radius:5px;
                                  border-bottom-left-radius:5px;}''')

        # Prepare the data for output
        numRes = len(plotplan)
        
        # Clear the widget
        for i in reversed(range(self.left_bottom_layout.count())):
            widgetToRemove = self.left_bottom_layout.itemAt(i).widget()
            # remove it from the layout list
            self.left_bottom_layout.removeWidget(widgetToRemove)
            # remove it from the gui
            widgetToRemove.setParent(None)

        # Set Header font
        font = QtGui.QFont()
        font.setFamily("Arial Black")
        font.setPointSize(12)

        self.routeButton = {}
        for i in range(numRes):
            deptTime = plotplan[i][5][0]
            arrTime  = plotplan[i][6][-1]

            buttonTemp = QtWidgets.QPushButton()
            buttonTemp.setFixedSize(278, 70)
            buttonTemp.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

            MapLabel = QtWidgets.QLabel()
            mapIcon = QtGui.QPixmap('./image/Map.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
            MapLabel.setPixmap(mapIcon)

            # Route option
            routeLabel = QtWidgets.QLabel()
            routeLabel.setFont(font)
            routeLabel.setFixedSize(45, 20)
            routeLabel.setText(deptTime)

            routeLabel1 = QtWidgets.QLabel()
            routeLabel1.setFont(font)
            routeLabel1.setFixedSize(5, 20)
            routeLabel1.setText('--')

            routeLabel2 = QtWidgets.QLabel()
            routeLabel2.setFont(font)
            routeLabel2.setFixedSize(45, 20)
            routeLabel2.setText(arrTime)

            deptTime = datetime.strptime('2017/09/13 '+ deptTime, '%Y/%m/%d %H:%M')
            arrTime   = datetime.strptime('2017/09/13 '+ arrTime,   '%Y/%m/%d %H:%M')
            hour   = int((arrTime - deptTime).seconds / 3600)
            minute = int(((arrTime - deptTime).seconds / 3600 - hour) * 60)

            routeLabel3 = QtWidgets.QLabel()
            routeLabel3.setFont(font)
            routeLabel3.setFixedSize(80, 20)
            routeLabel3.setText('{}h {}min'.format(hour, minute))

            lay = QtWidgets.QGridLayout(buttonTemp)
            lay.addWidget(MapLabel,   0, 0, 1, 1, QtCore.Qt.AlignLeft)
            lay.addWidget(routeLabel, 0, 1, 1, 1)
            lay.addWidget(routeLabel1, 0, 2, 1, 1)
            lay.addWidget(routeLabel2, 0, 3, 1, 1)
            lay.addWidget(routeLabel3, 0, 6, 1, 4, QtCore.Qt.AlignRight)

            timeLabel = QtWidgets.QLabel()
            timeIcon = QtGui.QPixmap('./image/Time.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
            timeLabel.setPixmap(timeIcon)

            setVech = []
            font1 = QtGui.QFont()
            font1.setFamily("Arial Black")
            font1.setPointSize(8)
            for car in plotplan[i][3]:
                if car not in setVech:
                    setVech.append(car)
            for j in range(len(setVech)):
                if j == 0:
                    routeLabel4 = QtWidgets.QLabel()
                    routeLabel4.setFont(font1)
                    routeLabel4.setFixedSize(60, 20)
                    routeLabel4.setText(setVech[j])
                    lay.addWidget(routeLabel4, 1, j+1, 1, 1)
                else:
                    routeLabel5 = QtWidgets.QLabel()
                    routeLabel5.setFont(font1)
                    routeLabel5.setFixedSize(5, 20)
                    routeLabel5.setText('--')
    
                    routeLabel6 = QtWidgets.QLabel()
                    routeLabel6.setFont(font1)
                    routeLabel6.setFixedSize(60, 20)
                    routeLabel6.setText(setVech[j])
    
                    lay.addWidget(routeLabel5, 1, j*2, 1, 1)
                    lay.addWidget(routeLabel6, 1, j*2 +1, 1, 1)

            self.routeButton[i] = buttonTemp
            self.left_bottom_layout.addWidget(self.routeButton[i], i, 0, 1, 4, QtCore.Qt.AlignTop)
            
        # Complement blank space
        if numRes < 4:
            for i in range(numRes, 4):
                buttonTemp = QtWidgets.QPushButton()
                buttonTemp.setFixedHeight(70)
                sp_retain = buttonTemp.sizePolicy()
                sp_retain.setRetainSizeWhenHidden(True)
                buttonTemp.setSizePolicy(sp_retain)
                buttonTemp.setVisible(False)
                self.left_bottom_layout.addWidget(buttonTemp, i, 0, 1, 4, QtCore.Qt.AlignTop)

        self.left_bottom_layout_style += '''QPushButton{border:none;
                                                        background-color:white;
                                                        color: red;
                                                        border-bottom:1px solid darkGray;
                                                        border-radius:3px;}'''
        self.left_bottom_widget.setStyleSheet(self.left_bottom_layout_style)
        
        
    def initLayout(self):
        """
        Use grid for layout and initialize it.
        """
        # Create grid Layout for main widget
        self.main_widget = QtWidgets.QWidget()
        self.main_widget.setObjectName('main_widget')
        self.main_layout = QtWidgets.QGridLayout()
        self.main_widget.setLayout(self.main_layout)

        # Create left-side-up widget
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setObjectName('left_widget')
        self.left_layout = QtWidgets.QGridLayout()
        self.left_widget.setLayout(self.left_layout)

        # Create left-side-down widget
        self.left_down_widget = QtWidgets.QWidget()
        self.left_down_widget.setObjectName('left_down_widget')
        self.left_down_layout = QtWidgets.QGridLayout()
        self.left_down_widget.setLayout(self.left_down_layout)

        # Create left-side-bottom widget
        self.left_bottom_widget = QtWidgets.QWidget()
        self.left_bottom_widget.setObjectName('left_bottom_widget')
        self.left_bottom_layout = QtWidgets.QGridLayout()
        self.left_bottom_widget.setLayout(self.left_bottom_layout)

        # Create right-side widget
        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setObjectName('right_widget')
        self.right_layout = QtWidgets.QGridLayout()
        self.right_widget.setLayout(self.right_layout)

        # Add left-side and right side widget to main widget
        self.main_layout.addWidget(self.left_widget , 0, 0, 3, 4)
        self.main_layout.addWidget(self.left_down_widget, 3, 0, 3, 4)
        self.main_layout.addWidget(self.left_bottom_widget, 6, 0, 6, 4)
        self.main_layout.addWidget(self.right_widget, 0, 4, 12, 8)
        self.setCentralWidget(self.main_widget)

    def initLeftWidget(self):
        """
        Initialize left-side widget.
        """
        # ---------- Source region ---------- #
        # Source label
        self.sourceLabel = QtWidgets.QLabel()
        sourceIcon = QtGui.QPixmap('./image/SourceIcon.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
        self.sourceLabel.setPixmap(sourceIcon)
        # Source Input
        self.sourceInput = QtWidgets.QLineEdit()
        self.sourceInput.setPlaceholderText('Starting Point')
        self.sourceInput.setFixedHeight(30)

        # To icon
        self.toLabel = QtWidgets.QLabel()
        toIcon = QtGui.QPixmap('./image/ToIcon.svg').scaled(15, 15, QtCore.Qt.IgnoreAspectRatio)
        self.toLabel.setFixedHeight(15)
        self.toLabel.setPixmap(toIcon)

        # Search button
        self.searchButton = QtWidgets.QPushButton()
        self.searchButton.setIcon(QtGui.QIcon('./image/SearchIcon.svg'))
        self.searchButton.setIconSize(QtCore.QSize(20, 20))
        self.searchButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.searchButton.clicked.connect(self.search)

        # Exchange button
        self.exchangeButton = QtWidgets.QPushButton()
        self.exchangeButton.setIcon(QtGui.QIcon('./image/ChangeIcon.svg'))
        self.exchangeButton.setIconSize(QtCore.QSize(22, 22))
        self.exchangeButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        # Destination label
        self.destLabel = QtWidgets.QLabel()
        destIcon = QtGui.QPixmap('./image/DestIcon.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
        self.destLabel.setPixmap(destIcon)
        # Destination Input
        self.destInput = QtWidgets.QLineEdit()
        self.destInput.setPlaceholderText('Ending Point')
        self.destInput.setFixedHeight(30)

        # Set the layout
        self.left_layout.addWidget(self.sourceLabel, 0, 0, 1, 1)
        self.left_layout.addWidget(self.sourceInput, 0, 1, 1, 7)
        self.left_layout.addWidget(self.searchButton, 0, 8, 1, 1)
        self.left_layout.addWidget(self.toLabel,     1, 0, 1, 1)
        self.left_layout.addWidget(self.exchangeButton, 1, 8, 1, 1)
        self.left_layout.addWidget(self.destLabel,   2, 0, 1, 1)
        self.left_layout.addWidget(self.destInput,   2, 1, 1, 7)

        self.left_widget.setStyleSheet('''
            QPushButton{border:none;color:white;}
            QLineEdit{border-bottom:1px solid darkGray;
                      border-radius:3px;
                      padding:2px 4px;}
            QWidget#left_widget{color:#232C51;
                                background:white;
                                border-top:1px solid darkGray;
                                border-left:1px solid darkGray;
                                border-right:1px solid darkGray;
                                border-top-left-radius:5px;
                                border-top-right-radius:5px;}''')

        # ---------- Route option region ---------- #

        # Calendar label
        self.calendarLabel = QtWidgets.QLabel()
        calendarIcon = QtGui.QPixmap('./image/Calendar.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
        self.calendarLabel.setPixmap(calendarIcon)
        # Calendar Input
        self.calendarInput = QtWidgets.QLineEdit()
        self.calendarInput.setPlaceholderText('Departure Date')
        self.calendarInput.setFixedSize(120, 30)
        # Time label
        self.timeLabel = QtWidgets.QLabel()
        timeIcon = QtGui.QPixmap('./image/Time.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
        self.timeLabel.setPixmap(timeIcon)
        # Time Input
        self.timeInput = QtWidgets.QLineEdit()
        self.timeInput.setPlaceholderText('Dept Time')
        self.timeInput.setFixedHeight(30)

        # Calendar label
        self.calendarLabelArr = QtWidgets.QLabel()
        self.calendarLabelArr.setPixmap(calendarIcon)
        # Calendar Input
        self.calendarInputArr = QtWidgets.QLineEdit()
        self.calendarInputArr.setPlaceholderText('Arrival Date')
        self.calendarInputArr.setFixedSize(120, 30)
        # Time label
        self.timeLabelArr = QtWidgets.QLabel()
        self.timeLabelArr.setPixmap(timeIcon)
        # Time Input
        self.timeInputArr = QtWidgets.QLineEdit()
        self.timeInputArr.setPlaceholderText('Arrival Time')
        self.timeInputArr.setFixedHeight(30)

        # Transfer Stop
        self.transLabel = QtWidgets.QLabel()
        exchangeIcon = QtGui.QPixmap('./image/Exchange.svg').scaled(20, 20, QtCore.Qt.IgnoreAspectRatio)
        self.transLabel.setPixmap(exchangeIcon)
        # Exchange Input
        self.exchangeInput = QtWidgets.QLineEdit()
        self.exchangeInput.setPlaceholderText('Max Transfer')
        self.exchangeInput.setFixedHeight(30)

        # Set the layout
        self.left_down_layout.addWidget(self.calendarLabel, 0, 0, 1, 1)
        self.left_down_layout.addWidget(self.calendarInput, 0, 1, 1, 3)
        self.left_down_layout.addWidget(self.timeLabel,     0, 4, 1, 1)
        self.left_down_layout.addWidget(self.timeInput,     0, 5, 1, 3)
        self.left_down_layout.addWidget(self.timeLabelArr,  1, 4, 1, 1)
        self.left_down_layout.addWidget(self.timeInputArr,  1, 5, 1, 3)
        self.left_down_layout.addWidget(self.transLabel,    2, 0, 1, 1)
        self.left_down_layout.addWidget(self.exchangeInput, 2, 1, 1, 3)

        self.left_down_widget.setStyleSheet('''
            QLineEdit{border-bottom:1px solid darkGray;
                      border-radius:3px;
                      padding:2px 4px;}
            QWidget#left_down_widget{color:#232C51;
                                     background:white;
                                     border-left:1px solid darkGray;
                                     border-right:1px solid darkGray;}''')


        # # ---------- Result region ---------- #
        # scroll = QtGui.QScrollArea()
        # scroll.setWidget(console)
        # scroll.setAutoFillBackground(True)
        # scroll.setWidgetResizable(True)
        # vbox = QtGui.QVBoxLayout()
        # vbox.addWidget(scroll)
        # tab1.setLayout(vbox)

        self.left_bottom_layout_style = '''
            QLineEdit{border-bottom:1px solid darkGray;
                      border-radius:3px;
                      padding:2px 4px;}
            QWidget#left_bottom_widget{color:#232C51;
                                     background:white;
                                     border-bottom:1px solid darkGray;
                                     border-left:1px solid darkGray;
                                     border-right:1px solid darkGray;
                                     border-bottom-right-radius:5px;
                                     border-bottom-left-radius:5px;}'''
        self.left_bottom_widget.setStyleSheet(self.left_bottom_layout_style)

        # ---------- Web region ---------- #
#        f = codecs.open("./image/Sample_Application.html", 'r', 'utf-8')
#        html = f.read()
        html = ''
        self.web = QWebEngineView()
        self.web.setHtml(html)
        self.web.setFixedSize(640, 700)

        self.right_layout.addWidget(self.web, 0, 0, 12, 8)
        self.right_widget.setStyleSheet('''
            QWidget#right_widget{color:#232C51;
                                  background:white;
                                  border:1px solid darkGray;
                                  border-top-right-radius:5px;
                                  border-top-left-radius:5px;
                                  border-bottom-right-radius:5px;
                                  border-bottom-left-radius:5px;}''')

    def js_callback(self, result):
        return ("js_callback: " + str(result))


def main():
    app = QtWidgets.QApplication(sys.argv)
    gui = Ui_MainWindow()
    gui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
