from pathlib import Path
from pbtravellog.boarding_pass import BoardingPass

def read_bcbp_fixture(filename: str):
    """Reads a BCBP fixture from the fixtures folder."""
    data_path = Path(__file__).parent / "fixtures" / filename
    return data_path.read_text(encoding="utf-8").strip()

def test_valid_single_leg_parsing():
    data = read_bcbp_fixture("bcbp_1_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 1

def test_valid_double_leg_parsing():
    data = read_bcbp_fixture("bcbp_2_leg.txt")
    bp = BoardingPass(data)
    assert bp.valid
    assert len(bp.legs) == 2
