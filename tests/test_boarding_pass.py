"""Tests boarding_pass module."""
from pbtravellog.boarding_pass import BoardingPass

def test_valid_single_leg_parsing(bcbp_data):
    """Checks parsing BCBP with one leg."""
    data = bcbp_data("1_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 1

def test_valid_double_leg_parsing(bcbp_data):
    """Checks parsing BCBP with two legs."""
    data = bcbp_data("2_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 2
