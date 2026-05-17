from rentals_assistant.scorer import score_listing

BASE = {
    "utilities": "extra",
    "floor_level": "main",
    "outdoor_space": 0,
    "parking_spots": 1,
    "city": "Kitchener",
}


def listing(**kwargs) -> dict:
    return {**BASE, **kwargs}


class TestScorePoints:
    def test_utilities_included_adds_one(self):
        assert score_listing(listing(utilities="included")).score == 1

    def test_utilities_extra_no_point(self):
        assert score_listing(listing(utilities="extra")).score == 0

    def test_utilities_unknown_no_point(self):
        assert score_listing(listing(utilities="unknown")).score == 0

    def test_upper_floor_adds_one(self):
        assert score_listing(listing(floor_level="upper")).score == 1

    def test_main_floor_no_point(self):
        assert score_listing(listing(floor_level="main")).score == 0

    def test_floor_unknown_no_point(self):
        assert score_listing(listing(floor_level="unknown")).score == 0

    def test_outdoor_space_adds_one(self):
        assert score_listing(listing(outdoor_space=1)).score == 1

    def test_no_outdoor_space_no_point(self):
        assert score_listing(listing(outdoor_space=0)).score == 0

    def test_two_parking_adds_one(self):
        assert score_listing(listing(parking_spots=2)).score == 1

    def test_more_than_two_parking_adds_one(self):
        assert score_listing(listing(parking_spots=3)).score == 1

    def test_one_parking_no_point(self):
        assert score_listing(listing(parking_spots=1)).score == 0


class TestTierAssignment:
    def test_score_four_is_perfect(self):
        result = score_listing(
            listing(utilities="included", floor_level="upper", outdoor_space=1, parking_spots=2)
        )
        assert result.score == 4
        assert result.tier == "perfect"

    def test_score_three_is_strong(self):
        result = score_listing(
            listing(utilities="included", floor_level="upper", outdoor_space=1)
        )
        assert result.score == 3
        assert result.tier == "strong"

    def test_score_two_is_strong(self):
        result = score_listing(listing(utilities="included", floor_level="upper"))
        assert result.score == 2
        assert result.tier == "strong"

    def test_score_one_is_check(self):
        result = score_listing(listing(utilities="included"))
        assert result.score == 1
        assert result.tier == "check"

    def test_score_zero_is_check(self):
        result = score_listing(listing())
        assert result.score == 0
        assert result.tier == "check"


class TestFlags:
    def test_utilities_included_star_flag(self):
        assert "★" in score_listing(listing(utilities="included")).flags

    def test_upper_floor_flag(self):
        assert "🏢" in score_listing(listing(floor_level="upper")).flags

    def test_outdoor_space_flag(self):
        assert "🌿" in score_listing(listing(outdoor_space=1)).flags

    def test_parking_flag(self):
        assert "🚗" in score_listing(listing(parking_spots=2)).flags

    def test_cambridge_proximity_flag(self):
        assert "📍" in score_listing(listing(city="Cambridge")).flags

    def test_south_kitchener_proximity_flag(self):
        assert "📍" in score_listing(listing(city="South Kitchener")).flags

    def test_kitchener_no_proximity_flag(self):
        assert "📍" not in score_listing(listing(city="Kitchener")).flags

    def test_waterloo_no_proximity_flag(self):
        assert "📍" not in score_listing(listing(city="Waterloo")).flags

    def test_proximity_flag_does_not_add_score(self):
        result = score_listing(listing(city="Cambridge"))
        assert result.score == 0

    def test_perfect_listing_has_all_flags(self):
        result = score_listing(
            listing(
                utilities="included",
                floor_level="upper",
                outdoor_space=1,
                parking_spots=2,
                city="Cambridge",
            )
        )
        assert "★" in result.flags
        assert "🏢" in result.flags
        assert "🌿" in result.flags
        assert "🚗" in result.flags
        assert "📍" in result.flags

    def test_no_flags_on_bare_listing(self):
        result = score_listing(listing())
        assert result.flags == []


class TestUnknownFields:
    def test_none_utilities_no_score(self):
        assert score_listing(listing(utilities=None)).score == 0

    def test_none_floor_level_no_score(self):
        assert score_listing(listing(floor_level=None)).score == 0

    def test_none_outdoor_space_no_score(self):
        assert score_listing(listing(outdoor_space=None)).score == 0

    def test_none_parking_spots_no_score(self):
        assert score_listing(listing(parking_spots=None)).score == 0

    def test_missing_city_no_proximity_flag(self):
        result = score_listing(
            {"utilities": "extra", "floor_level": "main", "outdoor_space": 0, "parking_spots": 1}
        )
        assert "📍" not in result.flags

    def test_empty_listing_returns_zero_check(self):
        result = score_listing({})
        assert result.score == 0
        assert result.tier == "check"
        assert result.flags == []
