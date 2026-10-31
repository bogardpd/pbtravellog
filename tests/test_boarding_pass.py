from pbtravellog.boarding_pass import BoardingPass

def test_valid_single_leg_parsing(bcbp_data):
    data = bcbp_data("1_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 1

def test_valid_double_leg_parsing(bcbp_data):
    data = bcbp_data("2_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 2
