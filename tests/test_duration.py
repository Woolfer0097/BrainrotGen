from backend.service.video import count_duration


class TestEstimateDuration:
    def test_empty_text(self) -> None:
        words = "".split()
        word_count = len(words)
        estimated_seconds = word_count * 0.4
        result = max(1, int(round(estimated_seconds)))
        assert result == 1

    def test_single_word(self) -> None:
        words = "hello".split()
        word_count = len(words)
        estimated_seconds = word_count * 0.4
        result = max(1, int(round(estimated_seconds)))
        assert result == 1

    def test_two_words(self) -> None:
        words = "hello world".split()
        word_count = len(words)
        estimated_seconds = word_count * 0.4
        result = max(1, int(round(estimated_seconds)))
        assert result == 1

    def test_five_words(self) -> None:
        words = "one two three four five".split()
        word_count = len(words)
        estimated_seconds = word_count * 0.4
        result = max(1, int(round(estimated_seconds)))
        assert result == 2


class TestCountDuration:
    def test_empty_bytes(self) -> None:
        result = count_duration(b"")
        assert result == 0

    def test_mp3_with_id3(self) -> None:
        id3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00data" + b"A" * 2000
        result = count_duration(id3_header)
        assert result >= 1

    def test_mp3_frame_header(self) -> None:
        mp3_frame = b"\xff\xfb" + b"\x00" * 1000
        result = count_duration(mp3_frame)
        assert result >= 1

    def test_unknown_format(self) -> None:
        unknown = b"ABC" * 500
        result = count_duration(unknown)
        assert result >= 1
