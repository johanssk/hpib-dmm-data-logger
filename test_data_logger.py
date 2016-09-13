# import mock
import pytest
import os.path
import time

from hypothesis import given, assume
import hypothesis.strategies as st
# from pytest_mock import mocker
from data_logger import write_file
from data_logger import determine_loop_count


# Re-write to follow correct rounding procedure
@given(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False, min_value=1))
def test_determine_loop_count(total_runtime, sample_time):
    assume(total_runtime > sample_time)
    num_loops = round(total_runtime / sample_time)
    if num_loops > 0:
        assert determine_loop_count(total_runtime, sample_time) == num_loops

@given(st.lists(st.tuples(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))))
def test_write_file(tmpdir, out):
    assume(len(out) > 0)
    OUTPUT_SAVE_EXTENTION = ".csv"
    OUTPUT_SAVE_PATH = str(tmpdir)
    OUTPUT_SAVE_NAME = "Data"
    save_data = {
        "name":OUTPUT_SAVE_NAME,
        "ext":OUTPUT_SAVE_EXTENTION,
        "path":OUTPUT_SAVE_PATH
        }
    file_name = write_file(out, save_data)
    assert(os.path.isfile(file_name))
    with open(file_name, 'r') as check:
        print out
        check.readlines() # Why is this needed?
        check = check.readlines()
        for i, line in enumerate(check[:-1]):
            print i
            output = out[i]
            assert line == "%s,%s\n" % (str(output[0]), str(output[1]))