import unittest
import spydrnet as sdn
import glob
import os
from pathlib import Path


class TestExampleNetlistFunctionality(unittest.TestCase):
    def test_example_netlist_names(self):
        filenames = glob.glob(os.path.join(sdn.base_dir, 'support_files', 'EDIF_netlists', '*'))
        # filenames = glob.glob(Path(sdn.base_dir, 'support_files', 'EDIF_netlists', '*')) # TypeError
        
        self.assertEqual(len(filenames), len(sdn.example_netlist_names))
        filenames.sort()
        for filename, example_name in zip(filenames, sdn.example_netlist_names):
            basename = Path(filename).name
            example_name_golden = basename[:basename.index('.')]
            self.assertEqual(example_name, example_name_golden)

    def test_load_example_netlist_by_name(self):
        netlist = sdn.load_example_netlist_by_name(sdn.example_netlist_names[0])
        self.assertIsNotNone(netlist)
