
import os.path
import sys
import time
import datetime
import logging

import serial
import tqdm
import serial.tools.list_ports as lports
from retrying import retry

import error_codes
from data_logger_configuration import OUTPUT_SAVE_PATH
from data_logger_configuration import OUTPUT_SAVE_NAME
from data_logger_configuration import SEND_CMD
from data_logger_configuration import SAMPLE_TIME
from data_logger_configuration import OUTPUT_SAVE_EXTENTION
from data_logger_configuration import TIME_SLEEP_READ
from data_logger_configuration import SETUP_CMD
from data_logger_configuration import TOTAL_RUNTIME

__version__ = 4

logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s- %(message)s')
logging.disable(logging.DEBUG)

def determine_loop_count(total_runtime, sample_time):
    num_loops = round(total_runtime / sample_time)
    logging.debug("Loops to run: %i" % num_loops)
    return num_loops

def read_write(my_ser):
    """
    Sets up device and sends commands, then reads response

    INPUT
    my_ser = serial connection

    OUTPUT
    out: List of tuples of format (time_of_reading, reading)
    """
    # Assigns variables from configuration file to local variables
    # Used to speed up while loop
    send = SEND_CMD
    sleep_read = TIME_SLEEP_READ
    sample = SAMPLE_TIME

    logging.debug("Send command: %s" % send)
    logging.debug("Time sleep read: %s" % sleep_read)
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
    if TOTAL_RUNTIME != -1:
        run_loops = determine_loop_count(TOTAL_RUNTIME, sample)
    else:
        run_loops = -1

    logging.info("Beginning data logging")
    run_count = 0

    try:
        while not run_count == run_loops:
            logging.debug("Run count: %s" % run_count)
            start_time = current_time()

            logging.debug("Sending command: %s" % send)
            write("%s\n" % send)

            return_string = rstrip(str(read(256)))
            logging.debug("Return string: %s" % return_string)

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
        pass
    logging.info("Done collecting data")
    return out

def write_file(out, output_save_path, output_save_name, output_save_extention):
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

    filename = "%s %s%s" % (output_save_name, file_time, output_save_extention)
    logging.debug(filename)

    full_filename = os.path.join(output_save_path, filename)
    logging.info("Saving as: %s", full_filename)

    with open(full_filename, 'a+') as data:
        for pair in tqdm.tqdm(out):
            write_line = "%s,%s\n" % (str(pair[0]), str(pair[1]))
            data.write(write_line)
    return full_filename

@retry(stop_max_attempt_number=7, wait_fixed=2000)
def auto_connect_device():
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
        logging.info("Setup settings: %s" % SETUP_CMD)
        connect_ser.write("%s\n" % SETUP_CMD)
        connect_ser.write("%s\n" % SEND_CMD)
        return_string = connect_ser.read(256)
        return_string = str(return_string).rstrip()
        if len(return_string) > 0:
            return connect_ser
    logging.warning("No connection to device")
    raise error_codes.ConnectError

if __name__ == '__main__':
    start_total_time = time.time()
    ser = serial.Serial()

    try:
        if not SAMPLE_TIME > 0:
            raise error_codes.TimeError
        if not TIME_SLEEP_READ > 0:
            raise error_codes.TimeError
        if not os.path.isdir(OUTPUT_SAVE_PATH):
            logging.debug(OUTPUT_SAVE_PATH)
            raise error_codes.PathError

        try:
            ser = auto_connect_device()
            read_time_start = time.time()
            output = read_write(ser)
            read_time_total = time.time() - read_time_start
            write_file(output, OUTPUT_SAVE_PATH, OUTPUT_SAVE_NAME, OUTPUT_SAVE_EXTENTION)
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
    