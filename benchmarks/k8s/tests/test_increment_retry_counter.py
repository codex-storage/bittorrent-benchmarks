from benchmarks.k8s.increment_retry_counter import increment_retry_counter


def test_should_add_counter_if_absent():
    assert increment_retry_counter("sometestgroup") == "sometestgroup-r1"


def test_should_increment_counter_if_present():
    assert increment_retry_counter("sometestgroup-r1") == "sometestgroup-r2"
    assert increment_retry_counter("sometestgroup-r2") == "sometestgroup-r3"
    assert increment_retry_counter("sometestgroup-r10") == "sometestgroup-r11"
    assert increment_retry_counter("sometestgroup-r100") == "sometestgroup-r101"
