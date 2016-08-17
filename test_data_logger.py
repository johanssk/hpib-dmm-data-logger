# import mock
import pytest
import os.path

from hypothesis import given, assume
import hypothesis.strategies as st
from hypothesis.extra.datetime import datetimes
# from pytest_mock import mocker
from data_logger import write_file

@given(st.lists(st.tuples(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))))
def test_write_file(tmpdir, out):
    assume(len(out) > 0)
    OUTPUT_SAVE_EXTENTION = ".csv"
    OUTPUT_SAVE_PATH = str(tmpdir)
    OUTPUT_SAVE_NAME = "Data"
    file_name = write_file(out, OUTPUT_SAVE_PATH, OUTPUT_SAVE_NAME, OUTPUT_SAVE_EXTENTION)
    assert(os.path.isfile(file_name))
    # with open(file_name, 'r') as check:
    #     for i, line in enumerate(check):
    #         print i
    #         output = out[i]
    #         assert line == "%s,%s\n" % (str(output[0]), str(output[1]))