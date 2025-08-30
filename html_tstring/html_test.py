def test_t_strings():
    # Temporary. Ensure our CI action is running the 3.14 RC
    template = t"hello {42}"
    assert len(template.strings) == 2
    assert len(template.interpolations) == 1
