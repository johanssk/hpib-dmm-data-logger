import csv
import datetime
import itertools
import logging
import os.path
import sys
import time

import serial
import serial.tools.list_ports as lports
from configobj import ConfigObj
from retrying import retry
from validate import Validator

import error_codes

__version__ = 4

logging.basicConfig(
    level=logging.DEBUG, format=' %(asctime)s - %(levelname)s- %(message)s')
logging.disable(logging.DEBUG)


def parse_config():
    config = ConfigObj('config.ini', configspec='configspec.ini')

    validator = Validator()
    result = config.validate(validator)

    if result is True:
        # Save Options
        save_data = {}
        save_data["path"] = config["Save"]["OUTPUT_SAVE_PATH"]
        save_data["name"] = config["Save"]["OUTPUT_SAVE_NAME"]
        save_data["ext"] = config["Save"]["OUTPUT_SAVE_EXTENTION"]

        # System Commands
        commands = {}
        commands["setup"] = config["Commands"]["SETUP_CMD"]
        commands["send"] = config["Commands"]["SEND_CMD"]

        # Sample and run time
        times = {}
        times["sample_time"] = config["Times"]["SAMPLE_TIME"]
        times["runtime"] = config["Times"]["TOTAL_RUNTIME"]

        return save_data, commands, times
    else:
        print "Could not validate config file"
        logging.critical("Could not validate config file")
        sys.exit()


def determine_loop_count(total_runtime, sample_time):
    """
    Used to determine number of loops the program should run
    by dividing total_runtime and sample_time

    INPUT:
        total_runtime: float
        sample_time: float

    OUTPUT:
        returns -1 if total_runtime is -1, num_loops otherwise
    """
    num_loops = round(total_runtime / sample_time)
    if num_loops > 0:
        logging.info("Loops to run: %i", num_loops)
        return num_loops
    else:
        logging.info("Infinite loops")
        return -1


def read_write(my_ser, commands, times):
    """
    Sets up device and sends commands, then reads response

    INPUT
    my_ser = serial connection

    OUTPUT
    out: List of tuples of format (time_of_reading, reading)
    """
    # Assigns variables from configuration file to local variables
    # Used to speed up while loop
    send = commands["send"]
    sample = times["sample_time"]

    logging.debug("Send command: %s", send)
    logging.debug("Sample time: %s", sample)

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

    run_loops = determine_loop_count(times["runtime"], sample)

    logging.info("Beginning data logging")

    try:
        relative_time_offset = current_time()
        for run_count in itertools.count():
            if run_count == run_loops:
                break
            logging.debug("Run count: %s", run_count)
            start_time = current_time()

            logging.info("Sending command: %s", send)
            write("%s\n" % send)

            return_string = rstrip(str(read(256)))
            logging.info("Return string: %s", return_string)

            if len(return_string) > 0:
                print return_string
                append((current_time() - relative_time_offset, return_string))
            else:
                logging.critical("No response from system")
                raise error_codes.ReturnError

            offset = current_time() - start_time
            logging.debug("Offset: %f", offset)
            if sample - offset > 0:
                sleep(sample - offset)
            print current_time() - start_time
    except KeyboardInterrupt:
        pass
    logging.info("Done collecting data")
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

    if os.environ.has_key("USERPROFILE"):
        user_path = os.environ["USERPROFILE"]
    else:
        user_path = os.path.expanduser("~")
    save_path = os.path.join(user_path, save_data["path"])
    full_filename = os.path.join(save_path, filename)
    logging.info("Saving as: %s", full_filename)
    with open(full_filename, 'w') as output_file:
        output_writer = csv.writer(output_file)
        for pair in out:
            output_writer.writerow(pair)
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
    ports = list(
        lports.comports())  # Change to .grep once determine what port returns
    logging.debug(ports)
    for com_port in ports:
        connect_ser = serial.Serial(com_port.device, 9600, timeout=0.5)

        # Send command to ensure device is responding
        # and connected to correct port
        logging.info("Inputting device settings to: %s", com_port.device)
        logging.info("Setup settings: %s", commands["setup"])
        connect_ser.write("%s\n" % commands["setup"])
        connect_ser.write("%s\n" % commands["send"])
        return_string = connect_ser.read(256)
        return_string = str(return_string).rstrip()
        if len(return_string) > 0:
            return connect_ser
    logging.warning("No connection to device")
    raise error_codes.ConnectError


if __name__ == '__main__':
    START_TOTAL_TIME = time.time()
    ser = serial.Serial()

    try:
        try:
            SAVE_DATA, COMMANDS, TIMES = parse_config()
            ser = auto_connect_device(COMMANDS)
            READ_TIME_START = time.time()
            OUTPUT = read_write(ser, COMMANDS, TIMES)
            READ_TIME_TOTAL = time.time() - READ_TIME_START
            write_file(OUTPUT, SAVE_DATA)
            ser.close()
            print "Total time sampled: %s" % str(READ_TIME_TOTAL)
        except error_codes.ConnectError:
            logging.critical("Unable to connect to device")
            sys.exit()
        except error_codes.ReturnError:
            logging.critical("Exiting program")
            sys.exit()
        print "Total Time: %s" % (time.time() - START_TOTAL_TIME)

    except serial.SerialException, e:
        logging.critical(e)
    except KeyboardInterrupt, e:
        ser.close()
        logging.critical(e)
    except error_codes.TimeError:
        logging.critical(
            "SAMPLE_TIME and TIME_SLEEP_READ must be greater than zero. Fix in configuration file.")
        print "Error in configuration file"
    except error_codes.PathError:
        logging.critical("Invalid save path. Fix in configuration file.")
        print "Error in configuration file"
