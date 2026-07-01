import unittest

from achilles.skills import marantz


class TestBuildCommand(unittest.TestCase):
    def test_power(self):
        self.assertEqual(marantz.build_command("power_on"), "PWON")
        self.assertEqual(marantz.build_command("power_off"), "PWSTANDBY")

    def test_volume(self):
        self.assertEqual(marantz.build_command("volume_up"), "MVUP")
        self.assertEqual(marantz.build_command("set_volume", 45), "MV45")
        self.assertEqual(marantz.build_command("set_volume", 5), "MV05")
        with self.assertRaises(ValueError):
            marantz.build_command("set_volume", 150)

    def test_input(self):
        self.assertEqual(marantz.build_command("set_input", "game"), "SIGAME")
        with self.assertRaises(ValueError):
            marantz.build_command("set_input", "toaster")

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            marantz.build_command("self_destruct")


class TestParseVoice(unittest.TestCase):
    def test_english(self):
        self.assertEqual(marantz.parse_voice_command("turn the receiver on"),
                         ("power_on", None))
        self.assertEqual(marantz.parse_voice_command("receiver off"),
                         ("power_off", None))
        self.assertEqual(marantz.parse_voice_command("volume 45"),
                         ("set_volume", 45))
        self.assertEqual(marantz.parse_voice_command("switch input to game"),
                         ("set_input", "game"))

    def test_hebrew(self):
        self.assertEqual(marantz.parse_voice_command("הדלק את הרסיבר"), ("power_on", None))
        self.assertEqual(marantz.parse_voice_command("הגבר ווליום"), ("volume_up", None))

    def test_unparseable(self):
        self.assertIsNone(marantz.parse_voice_command("what a nice amp"))


if __name__ == "__main__":
    unittest.main()
