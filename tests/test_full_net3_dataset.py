import unittest

from generate_full_net3_dataset import observation_columns
from leakprobe.net3_benchmark import load_network


class FullNet3DatasetTests(unittest.TestCase):
    def test_observation_schema_covers_every_junction_and_pipe(self):
        network = load_network()

        columns = observation_columns(network)

        self.assertEqual(columns[0], "timestamp_utc")
        self.assertEqual(len(columns), 1 + len(network.junction_name_list) + len(network.pipe_name_list))
        self.assertTrue(all(f"pressure_{node}_m" in columns for node in network.junction_name_list))
        self.assertTrue(all(f"flow_{pipe}_lps" in columns for pipe in network.pipe_name_list))


if __name__ == "__main__":
    unittest.main()
