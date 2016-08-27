
import os.path
import sys
import time
import datetime
import logging

import serial
import tqdm
import serial.tools.list_ports as lports
from retrying import retry

from configobj import ConfigObj
from validate import Validator

import error_codes

__version__ = 4

logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s- %(message)s')
logging.disable(logging.DEBUG)

def parse_config():
    config = ConfigObj('config.ini', configspec='configspec.ini')

    validator = Validator()
    result = config.validate(validator)

    if result:
        # Save Options
        SAVE_DATA = {}
        SAVE_DATA["path"] = config["Save"]["OUTPUT_SAVE_PATH"]
        SAVE_DATA["name"] = config["Save"]["OUTPUT_SAVE_NAME"]
        SAVE_DATA["ext"] = config["Save"]["OUTPUT_SAVE_EXTENTION"]
        # SAVE_DATA = [OUTPUT_SAVE_PATH, OUTPUT_SAVE_NAME, OUTPUT_SAVE_EXTENTION]

        # System Commands
        COMMANDS = {}
        COMMANDS["setup"] = config["Commands"]["SETUP_CMD"]
        COMMANDS["send"] = config["Commands"]["SEND_CMD"]
        # COMMANDS = [SETUP_CMD, SEND_CMD]

        # Sample and run time
        TIMES = {}
        TIMES["sample_time"] = config["Times"]["SAMPLE_TIME"]
        TIMES["runtime"] = config["Times"]["TOTAL_RUNTIME"]
        # TIMES = [SAMPLE_TIME, TOTAL_RUNTIME]

        return SAVE_DATA, COMMANDS, TIMES
    else:
        print "Could not validate config file"
        logging.critical("Could not validate config file")
        sys.exit()



def determine_loop_count(total_runtime, sample_time):
    num_loops = round(total_runtime / sample_time)
    logging.debug("Loops to run: %i" % num_loops)
    return num_loops

def read_write(my_ser, commands, times):
    """
    Sets up device and sends commands, then reads response

    INPUT
    my_ser = serial connection

    OUTPUT
    out: List of tuples of format (time_of_reading, reading)
    """
    try:
        # Assigns variables from configuration file to local variables
        # Used to speed up while loop
        send = commands["send"]
        sample = times["sample_time"]

        logging.debug("Send command: %s" % send)
        logging.debug("Sample time: %s" % sample)

        # Initialize list to contain readings
        out = []

        # Assign function lookups to variables
        # Used to speed up while loop
        current_time = time.time
        write = my_ser.write
        read = my_ser.read
        rstrip = str.rstrip
        sleep = time.sleep
        append = out.append
        if times["runtime"] != -1:
            run_loops = determine_loop_count(times[1], sample)
        else:
            run_loops = -1

        logging.info("Beginning data logging")
        run_count = 0

        while True:
            logging.debug("Run count: %s" % run_count)
            if run_count == run_loops:
                logging.info("Done logging")
                return out
            start_time = current_time()

            logging.info("Sending command: %s" % send)
            write("%s\n" % send)

            return_string = rstrip(str(read(256)))
            logging.info("Return string: %s" % return_string)

            if len(return_string) > 0:
                print return_string
                append((current_time(), return_string))
            else:
                logging.critical("No response from system")
                raise error_codes.ReturnError

            offset = current_time() - start_time
            logging.debug("Offset: %f", offset)
            if sample - offset > 0:
                sleep(sample - offset)
            print current_time() - start_time
            run_count += 1
    except KeyboardInterrupt:
        logging.info("Done logging")
        return out

def write_file(out, save_data):
    """
    Writes data to specified file

    INPUT
    out: List of tuples of format (time_of_reading, reading)

    OUTPUT
    File at location LOG_SAVE_PATH, with filename of format
    "LOG_SAVE_NAME %Y-%m-%d %H_%M_%S" and extension LOG_SAVE_EXTENTION
    """
    logging.info("Saving values to file")
    now = datetime.datetime.now()
    file_time = now.strftime("%Y-%m-%d %H_%M_%S")

    filename = "%s %s%s" % (save_data["name"], file_time, save_data["ext"])
    logging.debug(filename)

    save_path = os.path.join(os.path.expanduser("~"), save_data["path"])
    full_filename = os.path.join(save_path, filename)
    logging.info("Saving as: %s", full_filename)

    with open(full_filename, 'a') as data:
        for pair in tqdm.tqdm(out):
            write_line = "%s,%s\n" % (str(pair[0]), str(pair[1]))
            data.write(write_line)
    return full_filename

@retry(stop_max_attempt_number=7, wait_fixed=2000)
def auto_connect_device(commands):
    """
    Finds ports that are currently availiable and attempts to connect

    INPUT
    None

    OUTPUT
    connect_ser if connected and device responding
    Raise exception if no connection
    """
    logging.info("Connecting to device")
    ports = list(lports.comports())     # Change to .grep once determine what port returns
    logging.debug(ports)
    for com_port in ports:
        connect_ser = serial.Serial(com_port.device, 9600, timeout=0.5)

        # Send command to ensure device is responding
        # and connected to correct port
        logging.info("Inputting device settings to: %s" % com_port.device)
        logging.info("Setup settings: %s" % commands["setup"])
        connect_ser.write("%s\n" % commands["setup"])
        connect_ser.write("%s\n" % commands["send"])
        return_string = connect_ser.read(256)
        return_string = str(return_string).rstrip()
        if len(return_string) > 0:
            return connect_ser
        else:
            continue
    logging.warning("No connection to device")
    raise error_codes.ConnectError

if __name__ == '__main__':
    start_total_time = time.time()
    ser = serial.Serial()

    try:
        try:
            SAVE_DATA, COMMANDS, TIMES = parse_config()
            ser = auto_connect_device(COMMANDS)
            read_time_start = time.time()
            output = read_write(ser, COMMANDS, TIMES)
            read_time_total = time.time() - read_time_start
            write_file(output, SAVE_DATA)
            ser.close()
            print "Total time sampled: %s" % str(read_time_total)
        except error_codes.ConnectError:
            logging.critical("Unable to connect to device")
            sys.exit()
        except error_codes.ReturnError:
            logging.critical("Exiting program")
            sys.exit()
        print "Total Time: %s" % (time.time()-start_total_time)

    except serial.SerialException, e:
        logging.critical(e)
    except KeyboardInterrupt, e:
        ser.close()
        logging.critical(e)
    except error_codes.TimeError:
        logging.critical("SAMPLE_TIME and TIME_SLEEP_READ must be greater than zero. Fix in configuration file.")
        print "Error in configuration file"
    except error_codes.PathError:
        logging.critical("Invalid save path. Fix in configuration file.")
        print "Error in configuration file"
    