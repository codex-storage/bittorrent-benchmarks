from io import BytesIO

from benchmarks.core.utils import random_data


def test_should_generate_the_requested_amount_of_bytes():
    f = BytesIO()

    random_data(size=1024, outfile=f)

    assert len(f.getvalue()) == 1024


def test_should_generate_equal_files_for_equal_seeds():
    f1 = BytesIO()
    f2 = BytesIO()

    random_data(size=1024, outfile=f1, seed=1234)
    random_data(size=1024, outfile=f2, seed=1234)

    assert f1.getvalue() == f2.getvalue()


def test_should_generate_different_files_for_different_seeds():
    f1 = BytesIO()
    f2 = BytesIO()

    random_data(size=1024, outfile=f1, seed=1234)
    random_data(size=1024, outfile=f2, seed=1235)

    assert f1.getvalue() != f2.getvalue()
