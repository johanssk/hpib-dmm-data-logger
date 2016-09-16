# import mock
import os.path

import hypothesis.strategies as st
import serial.tools.list_ports as lports
from hypothesis import assume, given
from mock import patch

import data_logger
# from pytest_mock import mocker
from data_logger import auto_connect_device, determine_loop_count, write_file


# Re-write to follow correct rounding procedure
@given(
    st.floats(
        allow_nan=False, allow_infinity=False),
    st.floats(
        allow_nan=False, allow_infinity=False, min_value=1))
def test_determine_loop_count(total_runtime, sample_time):
    """ Test loop count function """
    assume(total_runtime > sample_time)
    num_loops = round(total_runtime / sample_time)
    if num_loops > 0:
        assert determine_loop_count(total_runtime, sample_time) == num_loops
    else:
        assert determine_loop_count(total_runtime, sample_time) == -1


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
    extention = ".csv"
    path = str(tmpdir)
    save_name = "Data"
    save_data = {"name": save_name, "ext": extention, "path": path}
    file_name = write_file(out, save_data)
    assert os.path.isfile(file_name)
    with open(file_name, 'r') as check:
        check.readlines()  # Why is this needed?
        check = check.readlines()
        for i, line in enumerate(check[:-1]):
            output = out[i]
            assert line == "%s,%s\n" % (str(output[0]), str(output[1]))


@patch('data_logger.serial.Serial')
@patch('data_logger.serial.tools.list_ports_common.ListPortInfo')
def test_auto_connect_device(mock_port, mock_serial, monkeypatch):
    mock_serial.return_value.read.return_value = "hello"
    mock_port.return_value.device.return_value = "test"
    port = mock_port.return_value
    monkeypatch.setattr(lports, 'comports', lambda: [port])
    device = auto_connect_device('T1', 'T3')
    assert device
