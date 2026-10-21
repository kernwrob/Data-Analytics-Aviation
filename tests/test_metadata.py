import unittest
import contextlib
from contextlib import closing
import io
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from src.aircraft_metadata import prepare_metadata, enrich_observations, UNKNOWN
from src import prepare


class MetadataTests(unittest.TestCase):
    def observations(self):
        return pd.DataFrame({"icao24": ["abcdef", "abcdef", "123456"],
                             "time_position": [100, 200, 100], "velocity": [10., 20., 30.]}, index=[2, 5, 9])

    def test_normalization_duplicate_resolution_and_left_join(self):
        raw = pd.DataFrame({"icao24": [" ABCDEF ", "abcdef", "bad", ""],
                            "model": ["", "A320", "", ""], "typecode": ["", "A320", "", ""],
                            "icaoaircrafttype": ["L2J", "L2J", "", ""]})
        metadata, source, duplicates = prepare_metadata(raw)
        self.assertEqual(source["invalid_metadata_keys"], 2)
        self.assertEqual(source["duplicate_rows_removed"], 1)
        self.assertEqual(metadata.iloc[0].aircraft_model, "A320")
        self.assertEqual(duplicates.selected.sum(), 1)
        enriched, audit = enrich_observations(self.observations(), metadata)
        self.assertEqual(len(enriched), 3)
        self.assertEqual(enriched.velocity.tolist(), [10., 20., 30.])
        self.assertEqual(enriched.aircraft_category.tolist(), ["Jet landplane", "Jet landplane", UNKNOWN])
        self.assertEqual(audit["matched_observations"], 2)
        self.assertEqual(audit["matched_distinct_aircraft"], 1)
        self.assertAlmostEqual(audit["observation_match_fraction"], 2/3)
        self.assertEqual(audit["aircraft_match_fraction"], .5)

    def test_conflicting_description_cannot_be_a_known_category(self):
        raw = pd.DataFrame({"icao24": ["abcdef", "abcdef"], "icaoaircrafttype": ["L2J", "H1T"]})
        metadata, audit, _ = prepare_metadata(raw)
        self.assertEqual(audit["conflicting_keys"], 1)
        self.assertEqual(metadata.iloc[0].metadata_source_record, 1)
        self.assertEqual(metadata.iloc[0].aircraft_category, UNKNOWN)

    def test_absent_metadata_preserves_all_observations(self):
        metadata, source, _ = prepare_metadata()
        enriched, audit = enrich_observations(self.observations(), metadata)
        self.assertFalse(source["source_available"])
        self.assertEqual(enriched.aircraft_category.tolist(), [UNKNOWN] * 3)
        self.assertEqual(audit["observations_after"], 3)
        self.assertEqual(audit["matched_observations"], 0)

    def test_duplicate_metadata_is_rejected_if_not_resolved(self):
        metadata, _, _ = prepare_metadata(pd.DataFrame({"icao24": ["abcdef"]}))
        with self.assertRaises(pd.errors.MergeError):
            enrich_observations(self.observations(), pd.concat([metadata, metadata]))

    def test_database_builder_works_without_optional_metadata_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("data/raw/opensky", "data/raw/airports"):
                (root / folder).mkdir(parents=True)
            config = {"airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60}
            (root / "config.json").write_text(json.dumps(config))
            state = ["ABCDEF", "TEST", "Example", 100, 100, 8., 47., 1000., False, 50., 90., 0., None, 1000., None, False, 0]
            (root / "data/raw/opensky/fixture.json").write_text(json.dumps({"time": 100, "states": [state]}))
            pd.DataFrame({"ident": ["TEST"], "name": ["Test airport"], "latitude_deg": [47.],
                          "longitude_deg": [8.], "elevation_ft": [100.]}).to_csv(root / "data/raw/airports/fixture.csv", index=False)
            with patch.object(prepare, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                prepare.main()
            with closing(sqlite3.connect(root / "data/processed/aircraft.sqlite")) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM aircraft_metadata").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT icao24,aircraft_category,metadata_matched FROM observations_enriched").fetchone(),
                                 ("abcdef", UNKNOWN, 0))


if __name__ == "__main__":
    unittest.main()
