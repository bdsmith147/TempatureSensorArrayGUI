# TempatureSensorArrayGUI
A data-logger GUI for an Arduino-based, 8-channel thermocouple reader array.

## Dependencies
* PyQt5
* numpy
* matplotlib
* PySerial

## Features:
1. Time-stamped temperature data for all 8 thermocouple channels
2. The that is collected can be saved to a .csv file of the user's choice.
3. Custom channel names can be specified, saved to a .csv file, and loaded back into the program later on.
4. A backup .csv file of all the collected data (`backup_data.csv`) is available in case the program crashes.

## Getting started:
To run the GUI, run the `run_TempSensor.bat` file. It may be necessary to modify the .bat file to include the path to the `\Anaconda3\Scripts\activate.bat` file on your computer; this allows python to be loaded into the shell where the program is run.
