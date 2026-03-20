from app.services.speech import SpeechService


class TestSpeakerMapping:
    def setup_method(self):
        self.service = SpeechService.__new__(SpeechService)
        self.service._speaker_map = {}
        self.service._last_active_speaker = 1

    def test_first_speaker_maps_to_1(self):
        assert self.service._map_speaker("Guest-1") == 1

    def test_second_speaker_maps_to_2(self):
        self.service._map_speaker("Guest-1")
        assert self.service._map_speaker("Guest-2") == 2

    def test_same_speaker_returns_same_id(self):
        self.service._map_speaker("Guest-1")
        assert self.service._map_speaker("Guest-1") == 1

    def test_unknown_speaker_returns_last_active(self):
        self.service._map_speaker("Guest-1")
        self.service._map_speaker("Guest-2")
        assert self.service._map_speaker("Unknown") == 2

    def test_empty_speaker_returns_last_active(self):
        self.service._map_speaker("Guest-1")
        assert self.service._map_speaker("") == 1

    def test_third_speaker_maps_to_last_active(self):
        self.service._map_speaker("Guest-1")
        self.service._map_speaker("Guest-2")
        assert self.service._map_speaker("Guest-3") == 2
