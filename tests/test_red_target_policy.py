from types import SimpleNamespace
import unittest
from src.prototype.skystar_openmv.red_target_policy import RedTargetPolicy,target_offsets


def blob(x=40,y=35,w=16,h=14):
    return SimpleNamespace(area=w*h,rect=(x,y,w,h),cx=x+w//2,cy=y+h//2)


class RedTargetPolicyTests(unittest.TestCase):
    def test_acquisition_then_loss_and_reacquisition(self):
        policy=RedTargetPolicy();b=blob()
        self.assertIsNone(policy.choose([b]));self.assertIsNone(policy.choose([b]))
        self.assertIs(policy.choose([b]),b)
        self.assertEqual(target_offsets(b),(-32,18,1))
        self.assertIsNone(policy.choose([]));self.assertEqual(policy.reason,'MISSING')
        self.assertIsNone(policy.choose([b]));self.assertIsNone(policy.choose([b]))
        self.assertIs(policy.choose([b]),b)

    def test_larger_blob_is_not_identity_when_two_candidates_exist(self):
        policy=RedTargetPolicy(stable_frames=1)
        self.assertIsNone(policy.choose([blob(),blob(90,40,25,25)]))
        self.assertEqual(policy.reason,'AMBIGUOUS')
        self.assertEqual(target_offsets(None),(0,0,0))

    def test_all_edges_rejected_even_with_in_range_centroid(self):
        policy=RedTargetPolicy(stable_frames=1)
        for b in (blob(x=0),blob(y=0),blob(x=144),blob(y=106)):
            self.assertIsNone(policy.choose([b]));self.assertEqual(policy.reason,'EDGE')

    def test_existing_area_threshold_and_inner_margin_boundary(self):
        policy=RedTargetPolicy(stable_frames=1)
        self.assertIsNone(policy.choose([blob(w=4,h=4)]))
        self.assertEqual(policy.reason,'MISSING')
        b=blob(1,1,4,5);self.assertIs(policy.choose([b]),b)

    def test_bad_geometry_rejected(self):
        policy=RedTargetPolicy(stable_frames=1)
        for b in (blob(x=-1),blob(x=155,w=16),blob(y=115),SimpleNamespace(area=30,rect=(4,4,6,5),cx=80,cy=60)):
            self.assertIsNone(policy.choose([b]));self.assertEqual(policy.reason,'GEOMETRY')

    def test_method_api_compatible_and_camera_state_isolated(self):
        b=blob();method=SimpleNamespace(**{k:(lambda value=v:value) for k,v in vars(b).items()})
        a,c=RedTargetPolicy(stable_frames=2),RedTargetPolicy(stable_frames=2)
        self.assertIsNone(a.choose([method]));self.assertIs(a.choose([method]),method)
        self.assertIsNone(c.choose([b]));self.assertEqual(c.reason,'WARMUP')
        self.assertEqual(target_offsets(method),target_offsets(b))
