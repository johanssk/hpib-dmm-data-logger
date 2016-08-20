import os

# COM_PORT = "COM4"
GPIB_PORT = "5" # Just in case you need it for something

# LOG_SAVE_PATH = os.path.normpath("C:\Users\johan\Desktop")
OUTPUT_SAVE_PATH = os.path.join("C:", os.sep, "Users", "johan", "Desktop")
OUTPUT_SAVE_NAME = "Data"
OUTPUT_SAVE_EXTENTION = ".csv"

SETUP_CMD = "F1RAN5"
SEND_CMD = 'T3'
SAMPLE_TIME = 0.5

TIME_SLEEP_READ = 0.5       # May not read correctly if too low - Default = 1
TOTAL_RUNTIME = -1          # Set to -1 to run forever
