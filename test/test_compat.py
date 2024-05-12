import pytest
from juliapkg.compat import Compat, Range, Version


class TestRange:
    @pytest.mark.parametrize(
        "input, expected_output",
        [
            # caret
            ("^1.2.3", Range("1.2.3", "2.0.0")),
            ("^1.2", Range("1.2.0", "2.0.0")),
            ("^1", Range("1.0.0", "2.0.0")),
            ("^0.2.3", Range("0.2.3", "0.3.0")),
            ("^0.0.3", Range("0.0.3", "0.0.4")),
            ("^0.0", Range("0.0.0", "0.1.0")),
            ("^0", Range("0.0.0", "1.0.0")),
            # implied caret
            ("1.2.3", Range("1.2.3", "2.0.0")),
            ("1.2", Range("1.2.0", "2.0.0")),
            ("1", Range("1.0.0", "2.0.0")),
            ("0.2.3", Range("0.2.3", "0.3.0")),
            ("0.0.3", Range("0.0.3", "0.0.4")),
            ("0.0", Range("0.0.0", "0.1.0")),
            ("0", Range("0.0.0", "1.0.0")),
            # tilde
            ("~1.2.3", Range("1.2.3", "1.3.0")),
            ("~1.2", Range("1.2.0", "1.3.0")),
            ("~1", Range("1.0.0", "2.0.0")),
            ("~0.2.3", Range("0.2.3", "0.3.0")),
            ("~0.0.3", Range("0.0.3", "0.0.4")),
            ("~0.0", Range("0.0.0", "0.1.0")),
            ("~0", Range("0.0.0", "1.0.0")),
            # equality
            ("=1.2.3", Range("1.2.3", "1.2.4")),
            # hyphen
            ("1.2.3 - 4.5.6", Range("1.2.3", "4.5.7")),
            ("0.2.3 - 4.5.6", Range("0.2.3", "4.5.7")),
            ("1.2 - 4.5.6", Range("1.2.0", "4.5.7")),
            ("1 - 4.5.6", Range("1.0.0", "4.5.7")),
            ("0.2 - 4.5.6", Range("0.2.0", "4.5.7")),
            ("0.2 - 0.5.6", Range("0.2.0", "0.5.7")),
            ("1.2.3 - 4.5", Range("1.2.3", "4.6.0")),
            ("1.2.3 - 4", Range("1.2.3", "5.0.0")),
            ("1.2 - 4.5", Range("1.2.0", "4.6.0")),
            ("1.2 - 4", Range("1.2.0", "5.0.0")),
            ("1 - 4.5", Range("1.0.0", "4.6.0")),
            ("1 - 4", Range("1.0.0", "5.0.0")),
            ("0.2.3 - 4.5", Range("0.2.3", "4.6.0")),
            ("0.2.3 - 4", Range("0.2.3", "5.0.0")),
            ("0.2 - 4.5", Range("0.2.0", "4.6.0")),
            ("0.2 - 4", Range("0.2.0", "5.0.0")),
            ("0.2 - 0.5", Range("0.2.0", "0.6.0")),
            ("0.2 - 0", Range("0.2.0", "1.0.0")),
        ],
    )
    def test_parse(self, input, expected_output):
        output = Range.parse(input)
        assert output == expected_output

    @pytest.mark.parametrize(
        "range, expected_output",
        [
            (Range("0.0.3", "0.0.4"), "=0.0.3"),
            (Range("1.2.3", "1.2.4"), "=1.2.3"),
            (Range("1.2.3", "2.0.0"), "^1.2.3"),
            (Range("1.2.0", "2.0.0"), "^1.2"),
            (Range("1.0.0", "2.0.0"), "^1"),
            (Range("0.2.3", "0.3.0"), "^0.2.3"),
            (Range("0.0.0", "0.1.0"), "^0.0"),
            (Range("0.0.0", "1.0.0"), "^0"),
            (Range("1.2.3", "1.3.0"), "~1.2.3"),
            (Range("1.2.0", "1.3.0"), "~1.2"),
            (Range("1.2.3", "4.5.7"), "1.2.3 - 4.5.6"),
            (Range("0.2.3", "4.5.7"), "0.2.3 - 4.5.6"),
            (Range("1.2.0", "4.5.7"), "1.2.0 - 4.5.6"),
            (Range("1.0.0", "4.5.7"), "1.0.0 - 4.5.6"),
            (Range("0.2.0", "4.5.7"), "0.2.0 - 4.5.6"),
            (Range("0.2.0", "0.5.7"), "0.2.0 - 0.5.6"),
            (Range("1.2.3", "4.6.0"), "1.2.3 - 4.5"),
            (Range("1.2.3", "5.0.0"), "1.2.3 - 4"),
            (Range("1.2.0", "4.6.0"), "1.2.0 - 4.5"),
            (Range("1.2.0", "5.0.0"), "1.2.0 - 4"),
            (Range("1.0.0", "4.6.0"), "1.0.0 - 4.5"),
            (Range("1.0.0", "5.0.0"), "1.0.0 - 4"),
            (Range("0.2.3", "4.6.0"), "0.2.3 - 4.5"),
            (Range("0.2.3", "5.0.0"), "0.2.3 - 4"),
            (Range("0.2.0", "4.6.0"), "0.2.0 - 4.5"),
            (Range("0.2.0", "5.0.0"), "0.2.0 - 4"),
            (Range("0.2.0", "0.6.0"), "0.2.0 - 0.5"),
            (Range("0.2.0", "1.0.0"), "0.2.0 - 0"),
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
                    Range("1.0.0", "2.0.0"),
                    [
                        (Version("0.0.0"), False),
                        (Version("0.1.0"), False),
                        (Version("0.1.2"), False),
                        (Version("1.0.0"), True),
                        (Version("1.2.0"), True),
                        (Version("1.2.3"), True),
                        (Version("2.0.0"), False),
                        (Version("2.3.0"), False),
                        (Version("2.3.4"), False),
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
            (Range("0.0.0", "0.0.0"), True),
            (Range("0.0.0", "0.0.1"), False),
            (Range("0.0.0", "0.1.0"), False),
            (Range("0.0.0", "1.0.0"), False),
            (Range("0.0.1", "1.0.0"), False),
            (Range("0.1.0", "1.0.0"), False),
            (Range("1.0.0", "1.0.0"), True),
            (Range("1.2.0", "1.0.0"), True),
            (Range("1.2.3", "1.0.0"), True),
            (Range("2.0.0", "1.0.0"), True),
        ],
    )
    def test_is_empty(self, range, expected_output):
        output = range.is_empty()
        assert output == expected_output

    @pytest.mark.parametrize(
        "range1, range2, expected_output",
        [
            (Range("0.0.0", "0.0.0"), Range("2.0.0", "1.0.0"), Range("2.0.0", "0.0.0")),
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
            ("1.2.3", Compat([Range("1.2.3", "2.0.0")])),
            (
                "1, 2.3, 4.5.6",
                Compat(
                    [
                        Range("1.0.0", "2.0.0"),
                        Range("2.3.0", "3.0.0"),
                        Range("4.5.6", "5.0.0"),
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
            (Compat([Range("1.2.3", "2.0.0")]), "^1.2.3"),
            (
                Compat(
                    [
                        Range("1.0.0", "2.0.0"),
                        Range("2.3.0", "3.0.0"),
                        Range("4.5.6", "5.0.0"),
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
                            Range("1.0.0", "2.0.0"),
                            Range("2.3.0", "3.0.0"),
                            Range("4.5.6", "5.0.0"),
                        ]
                    ),
                    [
                        (Version("0.0.0"), False),
                        (Version("0.0.1"), False),
                        (Version("0.1.0"), False),
                        (Version("1.0.0"), True),
                        (Version("1.2.0"), True),
                        (Version("1.2.3"), True),
                        (Version("2.0.0"), False),
                        (Version("2.1.0"), False),
                        (Version("2.3.0"), True),
                        (Version("2.3.4"), True),
                        (Version("2.4.5"), True),
                        (Version("3.0.0"), False),
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
                        Range("1.0.0", "2.0.0"),
                        Range("2.3.0", "3.0.0"),
                        Range("4.5.6", "5.0.0"),
                    ]
                ),
                Compat(
                    [
                        Range("0.1.0", "2.5.0"),
                        Range("3.0.0", "5.0.0"),
                        Range("6.0.0", "7.0.0"),
                    ]
                ),
                Compat(
                    [
                        Range("1.0.0", "2.0.0"),
                        Range("2.3.0", "2.5.0"),
                        Range("4.5.6", "5.0.0"),
                    ]
                ),
            )
        ],
    )
    def test_and(self, compat1, compat2, expected_output):
        output = compat1 & compat2
        assert output == expected_output
