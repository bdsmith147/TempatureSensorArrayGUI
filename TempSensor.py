# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 15:49:42 2019

@author: Benjamin Smith
"""

import sys
from PyQt5 import QtGui, uic
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import QVBoxLayout, QApplication, QMainWindow, \
QMessageBox, QTableWidgetItem, QFileDialog
from PyQt5.QtGui import QColor

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import (
	FigureCanvasQTAgg as FigureCanvas,
	NavigationToolbar2QT as NavigationToolbar)
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

import serial


import csv
import datetime as dt
import time

class Collector(QObject):
    '''
    Collector that is responsible for reading and signalling the temperature 
    data from the Arduino serial port. This object is instantiated and placed 
    on a designated thread so as to not block the GUI loop.
    '''
    measured = pyqtSignal(list) #maybe a python array
    
    def __init__(self, running, port, parent=None):
        super(Collector, self).__init__()
        self.running = running
        self.BAUD = 9600 # serial port parameters
        self.BITLENGTH = 8
        self.ser = serial.Serial(port, self.BAUD, self.BITLENGTH) # open serial

    
    def read_serial(self):
        '''Parse serial text. A serial line has the format `#ch_num: xx.xx`; 
        for example: `#2: 23.64`.'''
        
        line = self.ser.readline().decode("utf-8")
        chan = float(line.split(':')[0][1])
        temp = float(line.split(' ')[1].split('\r')[0])
        if temp == 512.50:
            temp = np.nan
        return chan, temp

        
    @pyqtSlot()    
    def read(self):
        ''' While loop to continually read from serial. Sends a signal 
        `measured` with the data list to the main GUI loop.
        '''
        
        while self.running:
            ch, t = self.read_serial()
            if ch == 1:
                time = dt.datetime.now()
                temps = []
                chans = []
                temps.append(t)
                chans.append(ch)
                for i in range(7):
                    ch, t = self.read_serial()
                    temps.append(t)
                    chans.append(ch)
                data = [time] + temps  
                self.measured.emit(data)
            else:
                continue
            

class Channel(object):
    ''' 
    Container class to hold channel information:
        - Number
        - Name
        - QTableWidget header item object
        - QLineEdit box for channel names
        - RGB color for channel name text and plotted points/lines
    '''
    
    def __init__(self, number, name, table, nameBox, rgb):
        self.num = number
        self.name = name
        self.color = rgb
#        self.column = table.column(self.num)
        self.col_header = table.horizontalHeaderItem(self.num)
        self.col_header.setText(name)
        self.nameBox = nameBox
        self.nameBox.setText(name)
        self.nameBox.setStyleSheet('color: ' + self.color + ';')
        


class TempSensorWindow(QMainWindow):
    '''Main GUI class'''
    
    def __init__(self):
        super(TempSensorWindow, self).__init__()
        self.initUI()
        self.allData = []
        self.begtime = None
        self.chan_fname = './channel_names.csv' 
        self.csv_filter = 'Comma-separated values (*.csv)'


    def initUI(self):
        '''Configures the UI and connects the signals with the slot functions.'''
        
        uic.loadUi('TempSensorUI.ui', self) # Load the .ui file
        
        # Add the main matplotlib plot
        self.fig1 = plt.Figure()
        self.canvas1 = FigureCanvas(self.fig1)
        self.plot_layout1 = QVBoxLayout()        
        self.plot_layout1.addWidget(self.canvas1)      
        self.gridLayout.addLayout(self.plot_layout1, 0, 1, 1, 1)
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('Temperature [$^\\circ$C]')
        self.toolbar1 = NavigationToolbar(self.canvas1, self)
        self.toolbar1.setFixedHeight(24)
        self.plot_layout1.addWidget(self.toolbar1)
        
        
        
        self.setWindowTitle('Temperature Array Logger')
        self.statusbar = self.statusBar()
        self.statusBar().showMessage('Connect to a port...')
        self.connectButton.setStyleSheet("background-color: green")
        
        # Configure the list of channels with their properties
        self.channels = [Channel(1, 'Ch. 1', self.dataTable, self.ch1_name, 'rgb(31,119,180)'),
                         Channel(2, 'Ch. 2', self.dataTable, self.ch2_name, 'rgb(255,127,14)'),
                         Channel(3, 'Ch. 3', self.dataTable, self.ch3_name, 'rgb(44,160,44)'),
                         Channel(4, 'Ch. 4', self.dataTable, self.ch4_name, 'rgb(214,39,40)'),
                         Channel(5, 'Ch. 5', self.dataTable, self.ch5_name, 'rgb(148,103,189)'),
                         Channel(6, 'Ch. 6', self.dataTable, self.ch6_name, 'rgb(140,86,75)'),
                         Channel(7, 'Ch. 7', self.dataTable, self.ch7_name, 'rgb(227,119,194)'),
                         Channel(8, 'Ch. 8', self.dataTable, self.ch8_name, 'rgb(127,127,127)')]
        
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.resetButton.setEnabled(False)
        self.durationLineEdit.setReadOnly(True)
        
        self.connectButton.clicked.connect(self.startThread)
        self.startButton.clicked.connect(self.startCollection)
        self.stopButton.clicked.connect(self.stopCollection)
        self.resetButton.clicked.connect(self.clearData)
        self.saveAllData.clicked.connect(self.saveData)
        self.saveChannels.clicked.connect(self.saveChannelNames)
        self.loadChannels.clicked.connect(self.loadChannelNames)
        
        self.ch1_name.textChanged.connect(lambda text: self.editChannelName(text, 1))
        self.ch2_name.textChanged.connect(lambda text: self.editChannelName(text, 2))
        self.ch3_name.textChanged.connect(lambda text: self.editChannelName(text, 3))
        self.ch4_name.textChanged.connect(lambda text: self.editChannelName(text, 4))
        self.ch5_name.textChanged.connect(lambda text: self.editChannelName(text, 5))
        self.ch6_name.textChanged.connect(lambda text: self.editChannelName(text, 6))
        self.ch7_name.textChanged.connect(lambda text: self.editChannelName(text, 7))
        self.ch8_name.textChanged.connect(lambda text: self.editChannelName(text, 8))
        
        self.show()
        
        
    def editChannelName(self, text, ch_num):
        '''Modifies the corresponding table header when the channel name 
        is changed.
        '''
        
        channel = self.channels[ch_num-1]
        channel.name = text
        channel.col_header.setText(text)


    def startThread(self):
        '''Instantiates a Collector object and places it on a designated 
        thread. Does not start collecting data yet.
        '''
        
        self.running = False
        try:
            self.Collector = Collector(self.running, self.portName.text())
            # 1 - Create a thread object, no parent.
            self.thread = QThread()
            # 2 - Connect Worker`s Signals to form method slots to post data.
            self.Collector.measured.connect(self.updateData) 
            self.startButton.clicked.connect(self.Collector.read)
            # 3 - Move the Worker object to the Thread object
            self.Collector.moveToThread(self.thread) 
            # 4 - Connect Thread started signal to Worker operational slot method
            self.thread.started.connect(self.Collector.read) 
            # 5 - Start the thread
            self.thread.start() 
            
            self.startButton.setEnabled(True)
            self.resetButton.setEnabled(False)
            self.statusBar().showMessage('Connected.')
            self.connectButton.setStyleSheet("")
            self.startButton.setStyleSheet("background-color: green")
        except:
            print('Bad Port')
            self.portErrorMessage()
    
    
    def updateData(self, data):
        '''Recieves the signal from the Collector object when the data is read.
        '''
        
        if self.running:
            self.statusBar().showMessage('Collecting...')
            self.allData.append(data)
            self.row_ind = len(self.allData)-1 # The number of rows [zero-indexed]
            self.dataTable.insertRow(self.row_ind)
            
            active = np.invert(np.isnan(np.array(data[1:]))) # which channels are active
            # For the given row, set the time:
            self.dataTable.setItem(self.row_ind,0, QTableWidgetItem(str(data[0].time()).split('.')[0]))
            for i, chan in enumerate(self.channels):
                chan.nameBox.setEnabled(active[i])
                val = str(data[i+1])
                if val != 'nan':
                    # For the given row, set each channel's temperature values:
                    self.dataTable.setItem(self.row_ind, i+1, QTableWidgetItem(val))
            
            self.drawPlot()
            self.duration = dt.datetime.now() - self.begtime
            self.timerClock()
            # Save all data to a backup file, in case of program crashes
            with open('backup_data.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(data)
            time.sleep(0.5)
            self.statusBar().showMessage('Collecting')

    
    def timerClock(self):
        '''Updates the 'Running Duration' time box.'''
        
        allseconds = self.duration.seconds
        allminutes = int(self.duration.seconds / 60)
        seconds = int(allseconds - allminutes*60)
        hours = int(allseconds / 3600)
        minutes = int(allminutes - hours*60)
        days = int(self.duration.days)
        
        ssec = self.stringTime(seconds)
        smin = self.stringTime(minutes)
        shour = self.stringTime(hours)
        sday = self.stringTime(days)
        duration_string = f'{sday}:{shour}:{smin}:{ssec}'
        self.durationLineEdit.setText(duration_string)
    
    
    def stringTime(self, time):
        '''Formats the time properly to always have two digits. 
        Returns time as a string.
        '''
        
        if time == 0:
            stime = '00'
        elif time < 10:
            stime = '0' + str(time)
        else:
            stime = str(time)
        return stime


    def drawPlot(self):
        '''Updates the matplotlib plot'''
        
        data = np.array(self.allData)
        times = data[:,0]
        temps = data[:, 1:]
        self.ax1.clear()
        self.ax1.plot(times, temps, marker='o', lw=1, markersize=4)
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('Temperature [$^\\circ$C]')
        self.canvas1.draw()


    def saveChannelNames(self):
        '''Saves the channel names as they currently are to a .csv file.'''
        
        title = 'Save Channel File'
        fname, selectedFilter = QFileDialog.getSaveFileName(self, title, self.chan_fname, self.csv_filter)
        if fname is not None:
            channel_names = [ch.name for ch in self.channels]
            with open(fname, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(channel_names)
    
    
    def loadChannelNames(self):
        '''Loads channel names from a .csv file.'''
        
        title = 'Open Channel File'
        fname, selectedFilter = QFileDialog.getOpenFileName(self, title, self.chan_fname, self.csv_filter)
        with open(fname, 'r', newline='') as f:
            reader = csv.reader(f)
            loaded_names = next(reader)
        
        if len(loaded_names) == 8:
            for i, chan in enumerate(self.channels): # Updates channel name boxes
                chan.name = loaded_names[i]
                chan.nameBox.setText(chan.name)
    
    
    def startCollection(self):
        '''Slot function for the `Start` button'''
        
        print('Reading...')
        if self.begtime == None:
            self.begtime = dt.datetime.now()
        
        self.running = True
        self.Collector.running = self.running # set the Collector running
        self.Collector.ser.reset_input_buffer()
        
        self.statusBar().showMessage('Collecting')
        self.startButton.setStyleSheet("")
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.stopButton.setStyleSheet("background-color: red")
        self.resetButton.setEnabled(False)
        
        # Write header to backup file
        channel_header = [ch.name for ch in self.channels]
        all_headers = ['Time'] + channel_header
        with open('backup_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(all_headers)
    
    
    def stopCollection(self):
        '''Slot function for the `Stop` button'''
        
        print('Stopped')
        self.running = False
        self.Collector.running = self.running # stop the Collector
        
        self.statusBar().showMessage('Stopped')
        self.stopButton.setStyleSheet("")
        self.startButton.setStyleSheet("background-color: green")
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.resetButton.setEnabled(True)
        
        
    def clearData(self):
        '''Slot function for the `Reset` button'''
        
        retval = self.clearConfirmation() # Check if user want to clear data
        if retval == QMessageBox.Yes:
            print('Reset')
            
            self.running = False
            self.Collector.running = self.running # stop the Collector
            self.allData = [] # clear the data
            self.ax1.clear() # clear the graph
            self.ax1.set_xlabel('Time')
            self.ax1.set_ylabel('Temperature [$^\\circ$C]')
            self.canvas1.draw()
            
            self.statusBar().showMessage('Ready')
            self.duration = dt.timedelta()
            self.timerClock()
            
            # Remove the rows from the table
            for i in range(self.row_ind, 0, -1): 
                self.dataTable.removeRow(i)
            self.dataTable.setRowCount(0)
            
            # Clear the backup file
            with open("backup_data.csv", "w") as f:
                f.truncate()
                
            self.resetButton.setEnabled(False)
            self.begtime = None
        
        
    def saveData(self):
        '''Function to save the data in a .csv file in the directory of choice'''
        
        title = 'Save File'
        fname, selectedFilter = QFileDialog.getSaveFileName(self, title, '.', self.csv_filter)
        if fname is not None:
            channel_header = [ch.name for ch in self.channels]
            all_headers = ['Time'] + channel_header
            
            with open(fname, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(all_headers) # Write channel headers
                writer.writerows(self.allData) # Write data rows


    def portErrorMessage(self):
        '''Dialog box to indicate there is a problem connecting to the serial 
        port.
        '''
        
        message = "There is an issue with the serial port you selected."
        label= "\"Houston, we have a problem.\""
        badPort = QMessageBox()
        badPort.setIcon(QMessageBox.Critical)
        badPort.setWindowTitle(label)
        badPort.setText(message)
        badPort.setStandardButtons(QMessageBox.Ok)
        badPort.exec_()
        return
    
    
    def clearConfirmation(self):
        '''Dialog box to verify clearing the data.
        '''
        
        question = "Are you sure you want to clear the data?"
        label= "Clearing"
        Confirmation = QMessageBox()
        Confirmation.setIcon(QMessageBox.Warning)
        Confirmation.setWindowTitle(label)
        Confirmation.setText(question)
        Confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        Confirmation.setDefaultButton(QMessageBox.No)
        retval = Confirmation.exec_()
        return retval




if __name__ == '__main__':
    if QApplication.instance(): # Checks if app is already created
        app = QApplication.instance()
    else:
        app = QApplication(sys.argv)
    window = TempSensorWindow()
    this = app.exec_()
    try:
        window.Collector.running = False
        window.Collector.ser.close()
    finally:
        sys.exit(this)
        