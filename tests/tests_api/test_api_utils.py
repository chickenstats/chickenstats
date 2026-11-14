from chickenstats.api._api_utils import _to_int_list, _to_str_list


class TestToIntList:
    def test_none(self):
        assert _to_int_list(None) is None

    def test_scalar(self):
        assert _to_int_list(42) == [42]

    def test_list(self):
        assert _to_int_list([1, "2", 3]) == [1, 2, 3]


class TestToStrList:
    def test_none(self):
        assert _to_str_list(None) is None

    def test_scalar(self):
        assert _to_str_list("20232024") == ["20232024"]

    def test_list(self):
        assert _to_str_list(["20222023", "20232024"]) == ["20222023", "20232024"]
