import pytest

from juliapkg.compat import Compat, Range, Version

v = Version.parse


class TestRange:
    @pytest.mark.parametrize(
        "input, expected_output",
        [
            # caret
            ("^1.2.3", Range(v("1.2.3"), v("2.0.0"))),
            ("^1.2", Range(v("1.2.0"), v("2.0.0"))),
            ("^1", Range(v("1.0.0"), v("2.0.0"))),
            ("^0.2.3", Range(v("0.2.3"), v("0.3.0"))),
            ("^0.0.3", Range(v("0.0.3"), v("0.0.4"))),
            ("^0.0", Range(v("0.0.0"), v("0.1.0"))),
            ("^0", Range(v("0.0.0"), v("1.0.0"))),
            # implied caret
            ("1.2.3", Range(v("1.2.3"), v("2.0.0"))),
            ("1.2", Range(v("1.2.0"), v("2.0.0"))),
            ("1", Range(v("1.0.0"), v("2.0.0"))),
            ("0.2.3", Range(v("0.2.3"), v("0.3.0"))),
            ("0.0.3", Range(v("0.0.3"), v("0.0.4"))),
            ("0.0", Range(v("0.0.0"), v("0.1.0"))),
            ("0", Range(v("0.0.0"), v("1.0.0"))),
            # tilde
            ("~1.2.3", Range(v("1.2.3"), v("1.3.0"))),
            ("~1.2", Range(v("1.2.0"), v("1.3.0"))),
            ("~1", Range(v("1.0.0"), v("2.0.0"))),
            ("~0.2.3", Range(v("0.2.3"), v("0.3.0"))),
            ("~0.0.3", Range(v("0.0.3"), v("0.0.4"))),
            ("~0.0", Range(v("0.0.0"), v("0.1.0"))),
            ("~0", Range(v("0.0.0"), v("1.0.0"))),
            # equality
            ("=1.2.3", Range(v("1.2.3"), v("1.2.4"))),
            # hyphen
            ("1.2.3 - 4.5.6", Range(v("1.2.3"), v("4.5.7"))),
            ("0.2.3 - 4.5.6", Range(v("0.2.3"), v("4.5.7"))),
            ("1.2 - 4.5.6", Range(v("1.2.0"), v("4.5.7"))),
            ("1 - 4.5.6", Range(v("1.0.0"), v("4.5.7"))),
            ("0.2 - 4.5.6", Range(v("0.2.0"), v("4.5.7"))),
            ("0.2 - 0.5.6", Range(v("0.2.0"), v("0.5.7"))),
            ("1.2.3 - 4.5", Range(v("1.2.3"), v("4.6.0"))),
            ("1.2.3 - 4", Range(v("1.2.3"), v("5.0.0"))),
            ("1.2 - 4.5", Range(v("1.2.0"), v("4.6.0"))),
            ("1.2 - 4", Range(v("1.2.0"), v("5.0.0"))),
            ("1 - 4.5", Range(v("1.0.0"), v("4.6.0"))),
            ("1 - 4", Range(v("1.0.0"), v("5.0.0"))),
            ("0.2.3 - 4.5", Range(v("0.2.3"), v("4.6.0"))),
            ("0.2.3 - 4", Range(v("0.2.3"), v("5.0.0"))),
            ("0.2 - 4.5", Range(v("0.2.0"), v("4.6.0"))),
            ("0.2 - 4", Range(v("0.2.0"), v("5.0.0"))),
            ("0.2 - 0.5", Range(v("0.2.0"), v("0.6.0"))),
            ("0.2 - 0", Range(v("0.2.0"), v("1.0.0"))),
        ],
    )
    def test_parse(self, input, expected_output):
        output = Range.parse(input)
        assert output == expected_output

    @pytest.mark.parametrize(
        "range, expected_output",
        [
            (Range(v("0.0.3"), v("0.0.4")), "=0.0.3"),
            (Range(v("1.2.3"), v("1.2.4")), "=1.2.3"),
            (Range(v("1.2.3"), v("2.0.0")), "^1.2.3"),
            (Range(v("1.2.0"), v("2.0.0")), "^1.2"),
            (Range(v("1.0.0"), v("2.0.0")), "^1"),
            (Range(v("0.2.3"), v("0.3.0")), "^0.2.3"),
            (Range(v("0.0.0"), v("0.1.0")), "^0.0"),
            (Range(v("0.0.0"), v("1.0.0")), "^0"),
            (Range(v("1.2.3"), v("1.3.0")), "~1.2.3"),
            (Range(v("1.2.0"), v("1.3.0")), "~1.2"),
            (Range(v("1.2.3"), v("4.5.7")), "1.2.3 - 4.5.6"),
            (Range(v("0.2.3"), v("4.5.7")), "0.2.3 - 4.5.6"),
            (Range(v("1.2.0"), v("4.5.7")), "1.2.0 - 4.5.6"),
            (Range(v("1.0.0"), v("4.5.7")), "1.0.0 - 4.5.6"),
            (Range(v("0.2.0"), v("4.5.7")), "0.2.0 - 4.5.6"),
            (Range(v("0.2.0"), v("0.5.7")), "0.2.0 - 0.5.6"),
            (Range(v("1.2.3"), v("4.6.0")), "1.2.3 - 4.5"),
            (Range(v("1.2.3"), v("5.0.0")), "1.2.3 - 4"),
            (Range(v("1.2.0"), v("4.6.0")), "1.2.0 - 4.5"),
            (Range(v("1.2.0"), v("5.0.0")), "1.2.0 - 4"),
            (Range(v("1.0.0"), v("4.6.0")), "1.0.0 - 4.5"),
            (Range(v("1.0.0"), v("5.0.0")), "1.0.0 - 4"),
            (Range(v("0.2.3"), v("4.6.0")), "0.2.3 - 4.5"),
            (Range(v("0.2.3"), v("5.0.0")), "0.2.3 - 4"),
            (Range(v("0.2.0"), v("4.6.0")), "0.2.0 - 4.5"),
            (Range(v("0.2.0"), v("5.0.0")), "0.2.0 - 4"),
            (Range(v("0.2.0"), v("0.6.0")), "0.2.0 - 0.5"),
            (Range(v("0.2.0"), v("1.0.0")), "0.2.0 - 0"),
        ],
    )
    def test_str(self, range, expected_output):
        output = str(range)
        assert output == expected_output

    @pytest.mark.parametrize(
        "version, range, expected_output",
        [
            (version, range, output)
            for range, pairs in [
                (
                    Range(v("1.0.0"), v("2.0.0")),
                    [
                        (v("0.0.0"), False),
                        (v("0.1.0"), False),
                        (v("0.1.2"), False),
                        (v("1.0.0"), True),
                        (v("1.2.0"), True),
                        (v("1.2.3"), True),
                        (v("2.0.0"), False),
                        (v("2.3.0"), False),
                        (v("2.3.4"), False),
                    ],
                ),
            ]
            for version, output in pairs
        ],
    )
    def test_contains(self, version, range, expected_output):
        output = version in range
        assert output == expected_output

    @pytest.mark.parametrize(
        "range, expected_output",
        [
            (Range(v("0.0.0"), v("0.0.0")), True),
            (Range(v("0.0.0"), v("0.0.1")), False),
            (Range(v("0.0.0"), v("0.1.0")), False),
            (Range(v("0.0.0"), v("1.0.0")), False),
            (Range(v("0.0.1"), v("1.0.0")), False),
            (Range(v("0.1.0"), v("1.0.0")), False),
            (Range(v("1.0.0"), v("1.0.0")), True),
            (Range(v("1.2.0"), v("1.0.0")), True),
            (Range(v("1.2.3"), v("1.0.0")), True),
            (Range(v("2.0.0"), v("1.0.0")), True),
        ],
    )
    def test_is_empty(self, range, expected_output):
        output = range.is_empty()
        assert output == expected_output

    @pytest.mark.parametrize(
        "range1, range2, expected_output",
        [
            (
                Range(v("0.0.0"), v("0.0.0")),
                Range(v("2.0.0"), v("1.0.0")),
                Range(v("2.0.0"), v("0.0.0")),
            ),
        ],
    )
    def test_and(self, range1, range2, expected_output):
        output = range1 & range2
        assert output == expected_output


class TestCompat:
    @pytest.mark.parametrize(
        "input, expected_output",
        [
            ("", Compat([])),
            ("1.2.3", Compat([Range(v("1.2.3"), v("2.0.0"))])),
            (
                "1, 2.3, 4.5.6",
                Compat(
                    [
                        Range(v("1.0.0"), v("2.0.0")),
                        Range(v("2.3.0"), v("3.0.0")),
                        Range(v("4.5.6"), v("5.0.0")),
                    ]
                ),
            ),
        ],
    )
    def test_parse(self, input, expected_output):
        output = Compat.parse(input)
        assert output == expected_output

    @pytest.mark.parametrize(
        "compat, expected_output",
        [
            (Compat([]), ""),
            (Compat([Range(v("1.2.3"), v("2.0.0"))]), "^1.2.3"),
            (
                Compat(
                    [
                        Range(v("1.0.0"), v("2.0.0")),
                        Range(v("2.3.0"), v("3.0.0")),
                        Range(v("4.5.6"), v("5.0.0")),
                    ]
                ),
                "^1, ^2.3, ^4.5.6",
            ),
        ],
    )
    def test_str(self, compat, expected_output):
        output = str(compat)
        assert output == expected_output

    @pytest.mark.parametrize(
        "version, compat, expected_output",
        [
            (version, compat, expected_output)
            for (compat, pairs) in [
                (
                    Compat(
                        [
                            Range(v("1.0.0"), v("2.0.0")),
                            Range(v("2.3.0"), v("3.0.0")),
                            Range(v("4.5.6"), v("5.0.0")),
                        ]
                    ),
                    [
                        (v("0.0.0"), False),
                        (v("0.0.1"), False),
                        (v("0.1.0"), False),
                        (v("1.0.0"), True),
                        (v("1.2.0"), True),
                        (v("1.2.3"), True),
                        (v("2.0.0"), False),
                        (v("2.1.0"), False),
                        (v("2.3.0"), True),
                        (v("2.3.4"), True),
                        (v("2.4.5"), True),
                        (v("3.0.0"), False),
                    ],
                )
            ]
            for (version, expected_output) in pairs
        ],
    )
    def test_contains(self, version, compat, expected_output):
        output = version in compat
        assert output == expected_output

    @pytest.mark.parametrize(
        "compat1, compat2, expected_output",
        [
            (
                Compat(
                    [
                        Range(v("1.0.0"), v("2.0.0")),
                        Range(v("2.3.0"), v("3.0.0")),
                        Range(v("4.5.6"), v("5.0.0")),
                    ]
                ),
                Compat(
                    [
                        Range(v("0.1.0"), v("2.5.0")),
                        Range(v("3.0.0"), v("5.0.0")),
                        Range(v("6.0.0"), v("7.0.0")),
                    ]
                ),
                Compat(
                    [
                        Range(v("1.0.0"), v("2.0.0")),
                        Range(v("2.3.0"), v("2.5.0")),
                        Range(v("4.5.6"), v("5.0.0")),
                    ]
                ),
            )
        ],
    )
    def test_and(self, compat1, compat2, expected_output):
        output = compat1 & compat2
        assert output == expected_output
