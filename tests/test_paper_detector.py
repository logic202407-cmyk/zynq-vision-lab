import unittest

from PIL import Image, ImageDraw
from src.pc.paper_detector import RedPaperDetector, draw_paper_result


class PaperDetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = RedPaperDetector()

    def scene(self, box, color=(120, 25, 35)):
        image = Image.new("RGB", (320, 240), (155, 155, 155))
        ImageDraw.Draw(image).rectangle(box, fill=color)
        return image

    def test_dark_red_rectangle_at_several_positions(self):
        for box in ((20, 30, 100, 90), (200, 140, 299, 219),
                    (0, 0, 70, 40), (249, 190, 319, 239)):
            with self.subTest(box=box):
                result = self.detector.detect(self.scene(box, (70, 12, 20)))
                self.assertIsNotNone(result)
                self.assertEqual(result.bbox, box)
                self.assertEqual(result.centroid,
                                 ((box[0] + box[2]) // 2,
                                  (box[1] + box[3]) // 2))

    def test_portrait_and_small_rectangles(self):
        for box in ((70, 40, 110, 150), (30, 30, 49, 45)):
            with self.subTest(box=box):
                self.assertEqual(self.detector.detect(self.scene(box)).bbox, box)

    def test_neutral_blue_and_orange_scenes_have_no_red_paper(self):
        for color in ((180, 180, 180), (30, 40, 140), (180, 110, 40)):
            with self.subTest(color=color):
                image = Image.new("RGB", (320, 240), color)
                self.assertIsNone(self.detector.detect(image))

    def test_isolated_red_noise_does_not_expand_target_box(self):
        box = (130, 95, 220, 155)
        image = self.scene(box)
        for y in range(2, 230, 13):
            for x in range(2, 310, 13):
                if not (120 <= x <= 230 and 85 <= y <= 165):
                    image.putpixel((x, y), (250, 5, 10))
        self.assertEqual(self.detector.detect(image).bbox, box)

    def test_noise_only_does_not_leave_a_stale_detection(self):
        self.assertIsNotNone(self.detector.detect(self.scene((80, 60, 180, 120))))
        image = Image.new("RGB", (320, 240), (140, 140, 140))
        for x in range(10, 300, 10):
            image.putpixel((x, 80), (255, 0, 0))
        self.assertIsNone(self.detector.detect(image))

    def test_irregular_red_component_and_text_are_rejected(self):
        image = Image.new("RGB", (320, 240), (140, 140, 140))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 29, 100), fill=(170, 10, 10))
        draw.rectangle((10, 81, 100, 100), fill=(170, 10, 10))
        draw.text((180, 30), "RED TEXT", fill=(200, 0, 0))
        self.assertIsNone(self.detector.detect(image))

    def test_larger_rectangle_wins_without_position_prior(self):
        image = self.scene((190, 120, 290, 200))
        ImageDraw.Draw(image).rectangle((10, 10, 40, 30), fill=(240, 5, 15))
        result = self.detector.detect(image)
        self.assertEqual(result.bbox, (190, 120, 290, 200))
        self.assertEqual(result.candidate_count, 2)

    def test_near_black_sensor_values_are_not_red_paper(self):
        self.assertIsNone(self.detector.detect(self.scene((50, 50, 180, 150),
                                                        (12, 1, 2))))

    def test_display_overlay_preserves_original_pixels(self):
        image = self.scene((30, 30, 120, 90))
        original = image.tobytes()
        shown = draw_paper_result(image, self.detector.detect(image))
        self.assertEqual(image.tobytes(), original)
        self.assertNotEqual(shown.tobytes(), original)
        self.assertIs(draw_paper_result(image, None), image)


if __name__ == "__main__":
    unittest.main()
