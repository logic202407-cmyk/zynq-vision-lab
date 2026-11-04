"""Reject wiring mistakes that are plausible during multi-gimbal preparation."""
import unittest

from tools.check_skystar_wiring import CONFIG, parse, validate


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.pwm, self.rx = parse(CONFIG.read_text(encoding='utf-8'))

    def test_selected_assignment(self):
        self.assertEqual(validate(self.pwm, self.rx), [])
        self.assertEqual(self.rx[1:], [(1, 'PC7', 'USART6', 8), (2, 'PD2', 'UART5', 8)])
        self.assertEqual(self.pwm[2:], [
            (1, 0, 'PD14', 'TIM4', 3, 2), (1, 1, 'PD15', 'TIM4', 4, 2),
            (2, 0, 'PE9', 'TIM1', 1, 1), (2, 1, 'PE11', 'TIM1', 2, 1)])

    def test_alternate_pin_is_not_an_extra_uart(self):
        self.rx[1] = (1, 'PD6', 'USART2', 7)
        self.assertTrue(any('UART peripheral' in e for e in validate(self.pwm, self.rx)))

    def test_fpga_conflict_even_on_alternate_pin(self):
        self.rx[1] = (1, 'PB11', 'USART3', 7)
        self.assertTrue(any('FPGA USART3' in e for e in validate(self.pwm, self.rx)))

    def test_fpga_physical_pin_conflict(self):
        self.rx[1] = (1, 'PC11', 'USART3', 7)
        self.assertTrue(any('Pin conflicts' in e for e in validate(self.pwm, self.rx)))

    def test_duplicate_pwm_pin_and_channel(self):
        self.pwm[3] = (1, 1, 'PD14', 'TIM4', 3, 2)
        errors = validate(self.pwm, self.rx)
        self.assertIn('Duplicate physical pin allocation', errors)
        self.assertIn('Duplicate timer channel allocation', errors)

    def test_wrong_af(self):
        self.rx[2] = (2, 'PD2', 'UART5', 7)
        self.assertTrue(any('Unsupported RX' in e for e in validate(self.pwm, self.rx)))

    def test_sdio_conflict(self):
        self.assertTrue(validate(self.pwm, self.rx, sdio_enabled=True))

    def test_missing_axis(self):
        self.assertTrue(validate(self.pwm[:-1], self.rx))

    def test_rejects_unrecognized_configuration(self):
        with self.assertRaises(ValueError):
            parse('GIMBAL_RX(2, PD2, UART5, 8)\nenable_outputs();')


if __name__ == '__main__':
    unittest.main()
