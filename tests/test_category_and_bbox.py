"""Offline checks for the typecode category (CC-7, #12) and the bbox snapshot filter (#52). Small fixtures only."""
import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from tests.cleaning_config import with_cleaning
from src import prepare
from src.aircraft_metadata import (CATEGORIES, UNKNOWN, OTHER, description_category, load_typecode_categories,
                                   prepare_metadata, read_metadata_csv, TYPECODE_REFERENCE)

TYPECODES = pd.DataFrame({"typecode": ["A320", "B77W", "G200"], "category": ["Kurzstrecke", "Langstrecke", "Business-Jet"],
                          "example_model": "", "source_note": ""})
NEW_BBOX = {"lamin": 45.6, "lamax": 48.2, "lomin": 5.2, "lomax": 10.6}
OLD_BBOX = {"lamin": 45.7, "lamax": 48.0, "lomin": 5.8, "lomax": 10.6}
T0 = 1794000000


def state(icao24, adsb=0):
    return [icao24, "T", "X", T0, T0, 8.0, 47.0, 1000., False, 100., 90., 0., None, 1000., None, False, 0, adsb]


class CategoryTests(unittest.TestCase):
    def category_of(self, **record):
        metadata, audit, _ = prepare_metadata(pd.DataFrame([{"icao24": "abcdef", **record}]), TYPECODES)
        return metadata.iloc[0].aircraft_category, metadata.iloc[0].category_source

    def test_typecode_first_then_description_then_unknown(self):
        self.assertEqual(self.category_of(typecode="a320", icaoaircrafttype="L2J"), ("Kurzstrecke", "typecode"))
        # Typecode wins over a wrong description (G200 is a jet, the source says piston).
        self.assertEqual(self.category_of(typecode="G200", icaoaircrafttype="L1P"), ("Business-Jet", "typecode"))
        self.assertEqual(self.category_of(typecode="XXXX", icaoaircrafttype="L2T"), ("Turboprop", "icao_description"))
        for code in ("L1P", "H1T", "G1P"):
            self.assertEqual(self.category_of(typecode="", icaoaircrafttype=code), (OTHER, "icao_description"))
        # Jets without a known typecode are not guessed; empty records stay unknown, never Sonstige.
        self.assertEqual(self.category_of(typecode="XXXX", icaoaircrafttype="L2J"), (UNKNOWN, "none"))
        self.assertEqual(self.category_of(typecode="", icaoaircrafttype=""), (UNKNOWN, "none"))
        self.assertEqual(self.category_of(icaoaircrafttype="S1P"), (UNKNOWN, "none"))

    def test_description_rules_are_exact(self):
        self.assertEqual(description_category("L4T"), "Turboprop")
        self.assertIsNone(description_category("L2TX"))
        self.assertIsNone(description_category(""))

    def test_typecode_conflict_is_unknown_and_counted(self):
        raw = pd.DataFrame({"icao24": ["abcdef", "ABCDEF", "123456"], "typecode": ["A320", "B77W", "A320"],
                            "icaoaircrafttype": ["L2J", "L2J", "L2J"]})
        metadata, audit, duplicates = prepare_metadata(raw, TYPECODES)
        row = metadata.set_index("icao24").loc["abcdef"]
        self.assertEqual((row.aircraft_category, row.category_source, row.category_conflict), (UNKNOWN, "none", 1))
        self.assertEqual(metadata.set_index("icao24").loc["123456"].aircraft_category, "Kurzstrecke")
        self.assertEqual(audit["typecode_conflicting_keys"], 1)
        self.assertEqual(audit["description_conflicting_keys"], 0)
        self.assertTrue(duplicates.typecode_conflict.all())

    def test_reference_table_is_valid_and_holds_the_schema_examples(self):
        table = load_typecode_categories(TYPECODE_REFERENCE)
        self.assertTrue(set(table.category) <= set(CATEGORIES) - {UNKNOWN})
        lookup = dict(zip(table.typecode, table.category))
        for typecode, category in [("A20N", "Kurzstrecke"), ("BCS3", "Kurzstrecke"), ("E195", "Regionaljet"),
                                   ("A359", "Langstrecke"), ("DH8D", "Turboprop"), ("PC12", "Turboprop"),
                                   ("C56X", "Business-Jet"), ("H135", OTHER)]:
            self.assertEqual(lookup[typecode], category)

    def test_reference_table_rejects_unknown_categories_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.csv"
            for rows in (["A320,Narrowbody,,"], ["A320,Kurzstrecke,,", "a320,Kurzstrecke,,"], ["A320,Unbekannt,,"]):
                path.write_text("typecode,category,example_model,source_note\n" + "\n".join(rows) + "\n")
                with self.assertRaises(ValueError):
                    load_typecode_categories(path)


class ReadMetadataTests(unittest.TestCase):
    def test_both_dump_formats_give_the_same_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp) / "old.csv", Path(tmp) / "new.csv"
            old.write_text('"icao24","manufacturername","model","typecode","icaoaircrafttype"\n'
                           '"abcdef","Airbus","A320-214","A320","L2J"\n')
            # Monthly complete dump: single quotes, camelCase, icaoAircraftClass, unquoted values and a comma in quotes.
            new.write_text("'icao24','timestamp','icaoAircraftClass','manufacturerName','model','typecode'\n"
                           "'abcdef','2025-01-01 00:00:00',L2J,'Airbus','A320-214, sharklets',A320\n"
                           "'123456','2025-01-01 00:00:00','','','',''\n")
            for path in (old, new):
                metadata, _, _ = prepare_metadata(read_metadata_csv(path), TYPECODES)
                row = metadata.set_index("icao24").loc["abcdef"]
                self.assertEqual((row.aircraft_typecode, row.aircraft_icao_description, row.aircraft_manufacturer),
                                 ("A320", "L2J", "Airbus"))
                self.assertEqual(row.aircraft_category, "Kurzstrecke")
            self.assertEqual(read_metadata_csv(new).loc[0, "model"], "A320-214, sharklets")


class PrepareFixture(unittest.TestCase):
    """A tiny project: two snapshot files, a manifest, one airport, optional pinned metadata."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for folder in ("opensky", "airports", "aircraft_metadata"):
            (self.root / "data/raw" / folder).mkdir(parents=True)
        pd.DataFrame({"ident": ["TEST"], "name": ["Test"], "latitude_deg": [47.], "longitude_deg": [8.],
                      "elevation_ft": [100.]}).to_csv(self.root / "data/raw/airports/a.csv", index=False)
        self.config = with_cleaning({"bbox": NEW_BBOX, "airport_idents": ["TEST"], "max_age_seconds": 60,
                                     "near_km": 30, "far_km": 60, "require_current_bbox": True,
                                     "metadata_file": "", "metadata_sha256": ""})

    def snapshot(self, name, states, bbox=None, backslash=False):
        path = f"data/raw/opensky/{name}.json"
        (self.root / path).write_text(json.dumps({"time": T0, "states": states}))
        if bbox is not None:
            entry = {"source": "snapshot", "outcome": "success", "params": {**bbox, "extended": 1},
                     "path": path.replace("/", "\\") if backslash else path}
            with (self.root / "data/raw/manifest.jsonl").open("a") as f:
                f.write(json.dumps(entry) + "\n")

    def run_prepare(self):
        (self.root / "config.json").write_text(json.dumps(self.config))
        with patch.object(prepare, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            prepare.main()
        return closing(sqlite3.connect(self.root / "data/processed/aircraft.sqlite"))

    def query(self, sql):
        with closing(sqlite3.connect(self.root / "data/processed/aircraft.sqlite")) as db:
            return db.execute(sql).fetchall()


class BboxFilterTests(PrepareFixture):
    def setUp(self):
        super().setUp()
        self.snapshot("old", [state("aaaaaa"), state("bbbbbb")], OLD_BBOX)
        self.snapshot("new", [state("cccccc")], NEW_BBOX, backslash=True)  # Windows-style manifest path
        self.snapshot("unlisted", [state("dddddd")])

    def test_only_current_bbox_snapshots_are_kept_and_exclusions_counted(self):
        with self.run_prepare():
            pass
        self.assertEqual(self.query("SELECT icao24 FROM observations"), [("cccccc",)])
        audit, = self.query("""SELECT snapshots_total, snapshots_kept, snapshots_old_bbox, rows_old_bbox,
                                      snapshots_missing_manifest, rows_missing_manifest FROM snapshot_bbox_audit""")
        self.assertEqual(audit, (3, 1, 1, 2, 1, 1))
        stages = dict(self.query("SELECT stage, rows FROM integration_audit"))
        self.assertEqual((stages["raw_all_snapshots"], stages["current_bbox"], stages["raw"]), (4, 1, 1))

    def test_flag_off_keeps_every_snapshot(self):
        self.config["require_current_bbox"] = False
        with self.run_prepare():
            pass
        self.assertEqual(len(self.query("SELECT icao24 FROM observations")), 4)
        self.assertEqual(self.query("SELECT snapshots_kept, snapshots_missing_manifest FROM snapshot_bbox_audit"), [(3, 0)])

    def test_no_matching_snapshot_stops_with_a_clear_message(self):
        self.config["bbox"] = {"lamin": 1, "lamax": 2, "lomin": 3, "lomax": 4}
        with self.assertRaisesRegex(SystemExit, "No snapshot matches"):
            self.run_prepare()


class PinnedMetadataTests(PrepareFixture):
    def setUp(self):
        super().setUp()
        self.snapshot("new", [state("abcdef", 4), state("123456", 0), state("654321", 8), state("fedcba", 6)], NEW_BBOX)
        csv = ("'icao24','icaoAircraftClass','manufacturerName','model','typecode'\n"
               "'abcdef',L2J,'Airbus','A320',A320\n'123456',L2J,'X','Unknown jet',ZZZZ\n'654321',H1T,'','',''\n")
        self.metadata = self.root / "data/raw/aircraft_metadata/meta.csv"
        self.metadata.write_text(csv)
        self.config.update(metadata_file="data/raw/aircraft_metadata/meta.csv",
                           metadata_sha256=hashlib.sha256(csv.encode()).hexdigest())

    def test_view_category_source_adsb_label_audits_and_unmapped_list(self):
        with self.run_prepare():
            pass
        rows = self.query("""SELECT icao24, aircraft_category, category_source, adsb_category_label, metadata_matched
                             FROM observations_enriched ORDER BY icao24""")
        self.assertEqual(rows, [("123456", UNKNOWN, "none", "No information", 1),
                                ("654321", OTHER, "icao_description", "Rotorcraft", 1),
                                ("abcdef", "Kurzstrecke", "typecode", "Large (75000-300000 lbs)", 1),
                                ("fedcba", UNKNOWN, "none", "Heavy (> 300000 lbs)", 0)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM typecode_categories")[0][0],
                         len(load_typecode_categories()))
        audit = dict(self.query("SELECT aircraft_category || '/' || category_source, observations FROM category_audit"))
        self.assertEqual(audit, {"Unbekannt/none": 2, "Sonstige/icao_description": 1, "Kurzstrecke/typecode": 1})
        fraction, source = self.query("SELECT typecode_mapped_fraction, pinned_source FROM metadata_integration_audit")[0]
        self.assertAlmostEqual(fraction, 1 / 3)
        self.assertEqual(source, "data/raw/aircraft_metadata/meta.csv")
        unmapped = pd.read_csv(self.root / "outputs/tables/unmapped_typecodes.csv")
        self.assertEqual(unmapped[["typecode", "observations", "aircraft"]].values.tolist(), [["ZZZZ", 1, 1]])

    def test_wrong_checksum_or_missing_file_stops(self):
        self.config["metadata_sha256"] = "0" * 64
        with self.assertRaisesRegex(SystemExit, "SHA-256"):
            self.run_prepare()
        self.config["metadata_file"] = "data/raw/aircraft_metadata/missing.csv"
        with self.assertRaisesRegex(SystemExit, "not found"):
            self.run_prepare()

    def test_empty_metadata_entry_keeps_everything_unknown(self):
        self.config.update(metadata_file="", metadata_sha256="")
        with self.run_prepare():
            pass
        self.assertEqual(self.query("SELECT DISTINCT aircraft_category, category_source FROM observations_enriched"),
                         [(UNKNOWN, "none")])


if __name__ == "__main__":
    unittest.main()
