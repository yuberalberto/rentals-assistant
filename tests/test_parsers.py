from rentals_assistant.scrapers.parsers import parse_bathrooms, parse_floor_level


class TestParseFloorLevel:
    """Test enhanced basement detection patterns."""

    def test_new_basement_pattern_lower_level(self):
        assert parse_floor_level("lower level apartment") == "basement"
        assert parse_floor_level("nice lower level unit") == "basement"

    def test_new_basement_pattern_lower_unit(self):
        assert parse_floor_level("lower unit available") == "basement"
        assert parse_floor_level("spacious lower unit") == "basement"

    def test_new_basement_pattern_garden_level(self):
        assert parse_floor_level("garden level suite") == "basement"
        assert parse_floor_level("beautiful garden level") == "basement"

    def test_new_basement_pattern_walkout_basement(self):
        assert parse_floor_level("walkout basement with separate entrance") == "basement"
        assert parse_floor_level("nice walkout basement") == "basement"

    def test_new_basement_pattern_bsmt(self):
        assert parse_floor_level("bsmt apt for rent") == "basement"
        assert parse_floor_level("cozy bsmt unit") == "basement"

    def test_new_basement_pattern_bsmnt(self):
        assert parse_floor_level("bsmnt apartment") == "basement"
        assert parse_floor_level("large bsmnt") == "basement"

    def test_existing_basement_pattern_still_works(self):
        assert parse_floor_level("basement apartment") == "basement"
        assert parse_floor_level("finished basement") == "basement"

    def test_upper_floor_patterns_unchanged(self):
        assert parse_floor_level("upper floor unit") == "upper"
        assert parse_floor_level("upper unit") == "upper"
        assert parse_floor_level("2nd floor") == "upper"
        assert parse_floor_level("second floor") == "upper"
        assert parse_floor_level("third floor") == "upper"
        assert parse_floor_level("3rd floor") == "upper"

    def test_main_floor_patterns_unchanged(self):
        assert parse_floor_level("main floor") == "main"
        assert parse_floor_level("ground floor") == "main"
        assert parse_floor_level("1st floor") == "main"
        assert parse_floor_level("first floor") == "main"
        assert parse_floor_level("garden floor") == "main"

    def test_no_floor_level_returns_none(self):
        assert parse_floor_level("no floor info here") is None
        assert parse_floor_level("apartment for rent") is None


class TestParseBathrooms:
    """Test bathroom count parsing."""

    def test_decimal_bathrooms(self):
        assert parse_bathrooms("1.5 bath") == 1.5
        assert parse_bathrooms("2.5 bathrooms") == 2.5
        assert parse_bathrooms("1.5 bath apartment") == 1.5

    def test_integer_bathrooms(self):
        assert parse_bathrooms("2 bath") == 2.0
        assert parse_bathrooms("3 bathrooms") == 3.0
        assert parse_bathrooms("1 bath") == 1.0

    def test_word_variant_one_and_half(self):
        assert parse_bathrooms("one and a half bath") == 1.5
        assert parse_bathrooms("one and a half bathrooms") == 1.5

    def test_half_bath_with_full_bath(self):
        assert parse_bathrooms("half bath and full bath") == 1.5
        assert parse_bathrooms("full bath with half bath") == 1.5

    def test_powder_room_with_full_bath(self):
        assert parse_bathrooms("powder room and full bath") == 1.5
        assert parse_bathrooms("full bath plus powder room") == 1.5

    def test_no_bathrooms_mentioned_returns_none(self):
        assert parse_bathrooms("no bathroom info") is None
        assert parse_bathrooms("apartment for rent") is None
        assert parse_bathrooms("") is None

    def test_half_bath_alone_returns_none(self):
        assert parse_bathrooms("half bath") is None
        assert parse_bathrooms("powder room") is None

    def test_case_insensitive(self):
        assert parse_bathrooms("1.5 BATH") == 1.5
        assert parse_bathrooms("2 Bathrooms") == 2.0
        assert parse_bathrooms("ONE AND A HALF BATH") == 1.5
