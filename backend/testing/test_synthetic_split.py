"""The per-user synthetic folders are a lossless split of the combined data and upload to the expected scores."""
import json
import pathlib

from backend.scoring_engine.engine import compute_score
from data.feature_engineering import get_all_user_features
from data.split_synthetic import CATEGORIES, load_split_dataset

SYN = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic"


def _user_dirs():
    return [(c, d) for c in CATEGORIES if (SYN / c).is_dir() for d in sorted((SYN / c).iterdir()) if d.is_dir()]


def test_split_is_lossless_and_complete():
    combined_demo = {d["user_id"]: d for d in json.loads((SYN / "demographics.json").read_text())}
    demo, tx = load_split_dataset(str(SYN))
    assert {d["user_id"] for d in demo} == set(combined_demo) and len(demo) == len(combined_demo) == 20
    assert all(d == combined_demo[d["user_id"]] for d in demo)
    from data.feature_engineering import load_transactions
    assert len(tx) == len(load_transactions(str(SYN / "transactions.csv")))


def test_each_user_only_holds_own_transactions_and_sits_in_right_category():
    for category, folder in _user_dirs():
        expected = json.loads((folder / "expected_score.json").read_text())
        uid = expected["user_id"]
        rows = (folder / "transactions.csv").read_text().splitlines()[1:]
        assert rows and all(f",{uid}," in r for r in rows), folder
        assert json.loads((folder / "demographics.json").read_text())[0]["user_id"] == uid
        assert expected["risk_category"].lower() == category


def test_expected_scores_match_engine_on_combined_data():
    feats = get_all_user_features(str(SYN))
    for _, folder in _user_dirs():
        e = json.loads((folder / "expected_score.json").read_text())
        assert compute_score(feats[e["user_id"]]).total_score == e["total_score"]


def test_every_user_folder_uploads_to_its_expected_score(client):
    folders = _user_dirs()
    assert len(folders) == 20
    for category, folder in folders:
        expected = json.loads((folder / "expected_score.json").read_text())
        r = client.post("/upload-raw", files={
            "transactions": ("transactions.csv", (folder / "transactions.csv").read_bytes()),
            "demographics": ("demographics.json", (folder / "demographics.json").read_bytes())})
        res = r.json()["results"][0]
        assert res["score"]["total_score"] == expected["total_score"], folder
        assert res["score"]["risk_category"].lower() == category
