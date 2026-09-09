#!/usr/bin/env python3
"""Planted export faults: dropped wiring, wrong pins, invented parts and drift."""
import copy
import unittest

from export_layout3d import (
    ExportError, export_layout, serialize, source_inputs, validate_export,
)


class Layout3DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout, cls.bom = source_inputs("5f1")
        cls.baseline = export_layout("5f1", cls.layout, cls.bom)

    def test_pilot_coverage_and_determinism(self):
        original = copy.deepcopy(self.layout)
        second = export_layout("5f1", self.layout, self.bom)
        self.assertEqual(self.layout, original, "Renderer preparation must not mutate source data")
        self.assertEqual(serialize(self.baseline), serialize(second))
        self.assertEqual(len(second["components"]), 27)
        self.assertEqual(len(second["eyelets"]), 40)
        self.assertEqual(len(second["connections"]), 44)
        self.assertEqual(second["unplacedBOMRefs"], ["C2", "C4"])
        self.assertEqual(second["connectivity"]["scope"], "layout-endpoints-only")

    def test_known_wrong_heater_routes_are_withheld_and_5v_retained(self):
        self.assertFalse(any(c["kind"] == "heater" for c in self.baseline["connections"]))
        omitted = self.baseline["omittedConnections"]
        self.assertEqual([c["sourceRun"] for c in omitted], ["run:43", "run:44", "run:45", "run:46"])
        self.assertEqual(sum(c["omittedStrands"] for c in omitted), 7)
        self.assertTrue(all("sources" in c and "points" not in c for c in omitted))
        filaments = {c["id"]: (c["from"], c["to"]) for c in self.baseline["connections"]}
        self.assertEqual(filaments["run:3"], ("PT.yellow1", "V3.pin2"))
        self.assertEqual(filaments["run:4"], ("PT.yellow2", "V3.pin8"))

    def test_source_validation_rejects_unsupported_circuit(self):
        with self.assertRaisesRegex(ExportError, "Unsupported circuit"):
            export_layout("5e3", self.layout, self.bom)

    def test_source_validation_rejects_missing_bom_part(self):
        changed = copy.deepcopy(self.bom)
        del changed["R3"]
        with self.assertRaisesRegex(ExportError, "absent from BOM"):
            export_layout("5f1", self.layout, changed)

    def test_source_validation_rejects_unknown_pin(self):
        changed = copy.deepcopy(self.layout)
        changed["runs"][0]["to"] = "V3.pin99"
        with self.assertRaisesRegex(ExportError, "no pin 99"):
            export_layout("5f1", changed, self.bom)

    def test_source_validation_rejects_heater_on_signal_pin(self):
        changed = copy.deepcopy(self.layout)
        changed["runs"][44]["to"] = "V2.pin3"
        with self.assertRaisesRegex(ExportError, "not a heater/filament pin"):
            export_layout("5f1", changed, self.bom)

    def test_source_validation_rejects_new_unplaced_scope(self):
        changed = copy.deepcopy(self.layout)
        # Removing a body while retaining its source wiring cannot silently
        # turn a placed part into another accepted BOM omission.
        changed["parts"] = [p for p in changed["parts"] if p["ref"] != "R3"]
        with self.assertRaises(ExportError):
            export_layout("5f1", changed, self.bom)

    def test_changed_heater_source_requires_omission_review(self):
        changed = copy.deepcopy(self.layout)
        changed["runs"][46]["from"] = "V1.pin9"
        with self.assertRaisesRegex(ExportError, "review the pilot omission"):
            export_layout("5f1", changed, self.bom)

    def test_planted_output_faults_are_caught(self):
        def component(data, cid):
            return next(c for c in data["components"] if c["id"] == cid)

        mutations = {
            "dropped component": lambda d: d["components"].pop(),
            "invented component": lambda d: d["components"].append(copy.deepcopy(d["components"][0])),
            "wrong BOM value": lambda d: component(d, "R8").update(value="470 kΩ"),
            "wrong BOM identity": lambda d: component(d, "R8").update(ref="R9"),
            "missing socket pin": lambda d: component(d, "V1")["terminals"].pop(),
            "body moved": lambda d: component(d, "R8").update(center=[0, 0]),
            "body end moved": lambda d: component(d, "R8").update(a=[0, 0]),
            "wrong mount": lambda d: component(d, "R8").update(mount="offboard"),
            "wrong body type": lambda d: component(d, "R8").update(category="film"),
            "dropped wire": lambda d: d["connections"].pop(0),
            "reintroduced heater strand": lambda d: d["connections"].append({**copy.deepcopy(d["connections"][0]), "id": "run:43:strand:0", "kind": "heater"}),
            "missing heater exclusion": lambda d: d["omittedConnections"].pop(),
            "erased heater reason": lambda d: d["omittedConnections"][0].update(reason=""),
            "wrong excluded strand count": lambda d: d["omittedConnections"][0].update(omittedStrands=0),
            "wrong heater evidence": lambda d: d["omittedConnections"][0]["sources"][0].update(url="https://example.com/"),
            "hidden heater coverage note": lambda d: d.update(scopeNotes=[]),
            "rerouted valid pin": lambda d: d["connections"][0].update(to="V3.pin6"),
            "wrong endpoint owner": lambda d: d["connections"][0].update(toOwner="V1"),
            "invented route": lambda d: d["connections"][0]["points"].insert(1, [0, 0]),
            "lost source endpoint": lambda d: d["connections"][0].update(sourceFrom="PT.red2"),
            "fake wire colour": lambda d: d["connections"][0].update(color="#123456"),
            "dropped registry terminal": lambda d: d["terminals"].pop(),
            "wrong registry location": lambda d: d["terminals"][-1].update(point=[0, 0]),
            "wrong eyelet location": lambda d: d["eyelets"][0].update(point=[0, 0]),
            "hiding unplaced BOM": lambda d: d.update(unplacedBOMRefs=[]),
            "wrong source": lambda d: d["source"].update(url="https://example.com/"),
            "incorrect verification claim": lambda d: d["connectivity"].update(scope="verified-nets"),
            "wrong board": lambda d: d["board"].update(width=0),
            "clipped hardware bounds": lambda d: d["bounds"].update(width=0),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                damaged = copy.deepcopy(self.baseline)
                mutate(damaged)
                with self.assertRaises(ExportError):
                    validate_export(damaged, self.layout, self.bom)


if __name__ == "__main__":
    unittest.main()
