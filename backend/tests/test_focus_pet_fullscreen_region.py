import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class FakePet:
    def __init__(self) -> None:
        self.x = 40
        self.y = 50
        self.width = 132
        self.height = 132

    def move(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height


class FocusPetFullscreenRegionTests(unittest.TestCase):
    def test_fullscreen_clears_shape_and_restores_it_on_exit(self) -> None:
        bridge = main.DesktopBridge()
        pet = FakePet()
        bridge._pet = pet
        bridge._living_pet = lambda: pet
        bridge._screen_for = lambda _x, _y: SimpleNamespace(x=0, y=0, width=1920, height=1080)
        bridge._defer = lambda fn, _delay=0.04: fn()

        with (
            patch.object(main, "_clear_pet_region") as clear_region,
            patch.object(main, "_shape_pet") as shape_pet,
        ):
            bridge.focus_fullscreen(True)
            clear_region.assert_called_once_with(pet)
            self.assertEqual((pet.x, pet.y, pet.width, pet.height), (0, 0, 1920, 1080))

            bridge.focus_fullscreen(False)
            shape_pet.assert_called_once_with(pet)
            self.assertEqual((pet.x, pet.y, pet.width, pet.height), (40, 50, 132, 132))


if __name__ == "__main__":
    unittest.main()
