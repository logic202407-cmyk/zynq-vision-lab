import copy
import unittest
from tools.c1_calibration import assess,fit_axis


def fixture(kind='synthetic'):
    samples=[]
    for axis in ('pan','tlt'):
        for pulse in (1495,1500,1505):
            for repeat in range(2):
                samples.append(dict(axis=axis,pan_us=pulse if axis=='pan' else 1500,
                    tlt_us=pulse if axis=='tlt' else 1500,
                    dx=-(pulse-1500) if axis=='pan' else 0,
                    dy=(pulse-1500)*2 if axis=='tlt' else 0,
                    evidence_kind=kind))
    return samples


class CalibrationTests(unittest.TestCase):
    def test_signed_error_response_and_axis_independence(self):
        samples=fixture()
        self.assertEqual(fit_axis(samples,'pan')['proposed_control_sign'],1)
        self.assertEqual(fit_axis(samples,'tlt')['proposed_control_sign'],-1)
        self.assertEqual(fit_axis(samples,'pan')['cross_ratio'],0)

    def test_one_static_target_does_not_determine_mechanics(self):
        with self.assertRaises(ValueError):fit_axis(fixture()[:2],'pan')

    def test_nonfinite_or_flat_or_other_axis_changed_rejected(self):
        for mode in ('nan','flat','cross_control'):
            samples=fixture()
            if mode=='nan':samples[0]['dx']=float('nan')
            elif mode=='flat':
                for s in samples:s['dx']=0
            else:samples[0]['tlt_us']=1501
            with self.assertRaises(ValueError):fit_axis(samples,'pan')

    def test_synthetic_fit_never_qualifies_measured_calibration(self):
        result=assess(dict(gimbal_id=0,same_target_observed=True,samples=fixture()))
        self.assertEqual(result['status'],'BLOCKED')
        self.assertFalse(result['motion_authorized'])
        self.assertIn('PAN_SIMULATION_IS_NOT_CALIBRATION',result['blockers'])
        self.assertIn('EPOCH_HARDWARE_BLOCKER',result['blockers'])

    def test_no_automatic_authorization_even_complete_declared_evidence(self):
        record=dict(gimbal_id=0,same_target_observed=True,camera_geometry_verified=True,
            independent_pwm_waveform_verified=True,mechanical_window_verified=True,
            epoch_provider_certified=True,samples=fixture('measured'),
            response_acceptance_policy=dict(min_abs_slope=.1,max_cross_ratio=.2,max_residual_px=.5))
        result=assess(record)
        self.assertEqual(result['status'],'EVIDENCE_REVIEW_REQUIRED')
        self.assertFalse(result['motion_authorized'])
        bad=copy.deepcopy(record)
        for s in bad['samples']:
            if s['axis']=='pan':s['dy']=s['dx']
        self.assertIn('PAN_RESPONSE_POLICY_FAILED',assess(bad)['blockers'])
