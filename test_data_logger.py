# import mock
import os.path

import hypothesis.strategies as st
from hypothesis import assume, given

# from pytest_mock import mocker
from data_logger import determine_loop_count, write_file


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
