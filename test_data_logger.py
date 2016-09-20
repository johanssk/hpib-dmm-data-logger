from __future__ import print_function
# import mock
import csv
import os.path

import hypothesis.strategies as st
import serial.tools.list_ports as lports
from hypothesis import assume, given
from mock import patch

import data_logger
# from pytest_mock import mocker


# Re-write to follow correct rounding procedure
@given(
    st.floats(
        allow_nan=False, allow_infinity=False),
    st.floats(
        allow_nan=False, allow_infinity=False, min_value=1))
def test_determine_loop_count(total_runtime, sample_time):
    """ Test loop count function """
    assume(total_runtime > sample_time)
    new_test = data_logger.Test()
    new_test.runtime = total_runtime
    new_test.sample_time = sample_time
    num_loops = round(total_runtime / sample_time)
    if num_loops > 0:
        assert new_test.determine_loop_count() == num_loops
    else:
        assert new_test.determine_loop_count() == -1


@given(
    st.lists(
        st.tuples(
            st.floats(
                allow_nan=False, allow_infinity=False),
            st.floats(
                allow_nan=False, allow_infinity=False))))
def test_write_file(tmpdir, out):
    """ Write file test """
    assume(len(out) > 0)
    new_test = data_logger.Test()
    new_test.save_ext = ".csv"
    new_test.save_path = str(tmpdir)
    new_test.save_name = "Data"
    # save_data = {"name": save_name, "ext": extention, "path": path}
    file_name = new_test.write_file(out)
    assert os.path.isfile(file_name)
    with open(file_name, 'r') as check:
        fileReader = csv.reader(check)
        list_lines = list(fileReader)
        for i, row in enumerate(list_lines):
            assert float(row[0]) == out[i][0]
            assert float(row[1]) == out[i][1]


@patch('data_logger.serial.Serial')
@patch('data_logger.serial.tools.list_ports_common.ListPortInfo')
@patch('data_logger.serial.tools.list_ports.comports')
def test_auto_connect_device_positive_connect(mock_list, mock_port,
                                              mock_serial):
    mock_serial.return_value.read.return_value = "2.8549e-6"
    mock_port.return_value.device.return_value = "test"
    mock_list.return_value = [mock_port.return_value]
    new_test = data_logger.Test()
    new_test.send_cmd = 'T1'
    new_test.setup_command = 'T2'
    device = new_test.auto_connect_device()
    assert device


@given(
    sample=st.floats(
        allow_nan=False, allow_infinity=False, min_value=0, max_value=0.1),
    run_loops=st.integers(
        max_value=1, min_value=0))
@patch('data_logger.serial.Serial')
def test_collect_data(mock_serial, run_loops, sample):
    mock_serial.return_value.read.return_value = "2.8549e-6"
    ser = mock_serial
    new_test = data_logger.Test()
    new_test.send_cmd = 'T2'
    new_test.sample_time = sample
    out = new_test.collect_data(ser, run_loops)
    print(out)
    assert len(out) == run_loops
