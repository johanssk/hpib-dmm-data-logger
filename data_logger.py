import datetime
import itertools
import logging
import os.path
import sys
import time

import serial
import serial.tools.list_ports as lports
import tqdm
from configobj import ConfigObj
from retrying import retry
from validate import Validator

import error_codes

logging.basicConfig(
    level=logging.DEBUG, format=' %(asctime)s - %(levelname)s- %(message)s')

# logging.disable(logging.DEBUG)


class Test(object):
    def __init__(self):
        config = ConfigObj('config.ini', configspec='configspec.ini')
        validator = Validator()
        if config.validate(validator) is True:
            # Save options
            self.save_path = config["Save"]["OUTPUT_SAVE_PATH"]
            self.save_name = config["Save"]["OUTPUT_SAVE_NAME"]
            self.save_ext = config["Save"]["OUTPUT_SAVE_EXTENTION"]

            # System Commands
            self.setup_command = config["Commands"]["SETUP_COMMAND"]
            self.send_cmd = config["Commands"]["SEND_CMD"]

            # Sample and run time
            self.sample_time = config["Times"]["SAMPLE_TIME"]
            self.runtime = config["Times"]["TOTAL_RUNTIME"]
        else:
            print "Could not validate config file"
            logging.critical("Could not validate config file")
            sys.exit()

    def determine_loop_count(self):
        """
        Used to determine number of loops the program should run
        by dividing total_runtime and sample_time

        INPUT:
            total_runtime: float
            sample_time: float

        OUTPUT:
            returns -1 if total_runtime is -1, num_loops otherwise
        """

        num_loops = round(self.runtime / self.sample_time) if (
            self.runtime > 0) else -1
        return num_loops

    @retry(stop_max_attempt_number=7, wait_fixed=2000)
    def auto_connect_device(self):
        """
        Finds ports that are currently availiable and attempts to connect

        INPUT
        None

        OUTPUT
        connect_ser if connected and device responding
        Raise exception if no connection
        """
        logging.info("Connecting to device")
        ports = list(lports.comports(
        ))  # Change to .grep once determine what port returns
        logging.debug(ports)
        for com_port in ports:
            connect_ser = serial.Serial(com_port.device, 9600, timeout=0.5)

            # Send command to ensure device is responding
            # and connected to correct port
            logging.info("Inputting device settings to: %s", com_port.device)
            logging.info("Setup settings: %s", self.setup_command)
            connect_ser.write("%s\n" % self.setup_command)
            connect_ser.write("%s\n" % self.send_cmd)
            return_string = str(connect_ser.read(256)).rstrip()
            logging.debug(return_string)
            if len(return_string) > 0:
                return connect_ser
        logging.warning("No connection to device")
        raise error_codes.ConnectError

    def collect_data(self, my_ser, run_loops):
        """
        Sets up device and sends commands, then reads response

        INPUT
        my_ser = serial connection

        OUTPUT
        out: List of tuples of format (time_of_reading, reading)
        """
        # Assigns variables from configuration file to local variables
        # Used to speed up while loop

        logging.debug("Send command: %s", self.send_cmd)
        logging.debug("Sample time: %s", self.sample_time)

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

        logging.info("Beginning data logging")

        try:
            relative_time_offset = current_time()
            for run_count in itertools.count():
                if run_count == run_loops:
                    break
                logging.debug("Run count: %s", run_count)
                start_time = current_time()

                logging.info("Sending command: %s", self.send_cmd)
                write("%s\n" % self.send_cmd)

                return_string = rstrip(str(read(256)))
                logging.info("Return string: %s", return_string)

                if len(return_string) > 0:
                    print return_string
                    append(
                        (current_time() - relative_time_offset, return_string))
                else:
                    logging.critical("No response from system")
                    raise error_codes.ReturnError

                offset = current_time() - start_time
                logging.debug("Offset: %f", offset)
                if self.sample_time - offset > 0:
                    sleep(self.sample_time - offset)
                print current_time() - start_time
        except KeyboardInterrupt:
            pass
        logging.info("Done collecting data")
        return out

    def write_file(self, out):
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

        filename = "%s %s%s" % (self.save_name, file_time, self.save_ext)
        logging.debug(filename)

        if os.environ.has_key("USERPROFILE"):
            user_path = os.environ["USERPROFILE"]
        else:
            user_path = os.path.expanduser("~")
        save_path = os.path.join(user_path, self.save_path)
        full_filename = os.path.join(save_path, filename)
        logging.info("Saving as: %s", full_filename)

        with open(full_filename, 'a+') as data:
            for pair in tqdm.tqdm(out):
                write_line = "%s,%s\n" % (str(pair[0]), str(pair[1]))
                data.write(write_line)
        return full_filename

    def run_full(self):
        try:
            try:
                START_TOTAL_TIME = time.time()
                ser = self.auto_connect_device()
                READ_TIME_START = time.time()
                output = self.collect_data(ser, self.determine_loop_count())
                READ_TIME_TOTAL = time.time() - READ_TIME_START
                print "Total time sampled: %s" % str(READ_TIME_TOTAL)
                self.write_file(output)
                ser.close()
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


if __name__ == '__main__':
    new_test = Test()
    new_test.run_full()
