"""Offline monocular size-based reference; not a hardware range measurement."""
import argparse
import json
import math
from pathlib import Path


def _positive(value, label):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be finite and positive')
    return value


def reference(object_width_cm, distance_cm, observed_width_px, image_width, image_height,
              frontal_confirmed=False):
    if frontal_confirmed is not True:
        raise ValueError('reference target frontal orientation not confirmed')
    width = _positive(object_width_cm, 'object_width_cm')
    distance = _positive(distance_cm, 'distance_cm')
    pixels = _positive(observed_width_px, 'observed_width_px')
    image_width = _positive(image_width, 'image_width')
    image_height = _positive(image_height, 'image_height')
    if pixels >= image_width:
        raise ValueError('reference target must not span the image width')
    return {'object_width_cm': width, 'reference_distance_cm': distance,
            'reference_width_px': pixels, 'image_width': image_width, 'image_height': image_height,
            'frontal_confirmed': True,
            'focal_px_approx': pixels * distance / width,
            'status': 'single_reference_unvalidated'}


def estimate(calibration, bbox, image_width, image_height, valid, complete,
             target_frontal_confirmed=False):
    if calibration.get('frontal_confirmed') is not True:
        raise ValueError('reference target frontal orientation not confirmed')
    if target_frontal_confirmed is not True:
        raise ValueError('target frontal orientation not confirmed')
    if valid is not True or complete is not True:
        raise ValueError('target or frame invalid')
    width = _positive(image_width, 'image_width')
    height = _positive(image_height, 'image_height')
    if width != calibration['image_width'] or height != calibration['image_height']:
        raise ValueError('image resolution differs from reference')
    if len(bbox) != 4:
        raise ValueError('bbox needs four coordinates')
    x0, y0, x1, y1 = map(float, bbox)
    if not all(math.isfinite(x) for x in (x0, y0, x1, y1)):
        raise ValueError('bbox must be finite')
    if not (0 < x0 <= x1 < width - 1 and 0 < y0 <= y1 < height - 1):
        raise ValueError('bbox clipped, reversed or outside image')
    pixels = x1 - x0 + 1
    reference_distance = _positive(calibration['reference_distance_cm'], 'reference_distance_cm')
    reference_pixels = _positive(calibration['reference_width_px'], 'reference_width_px')
    if reference_pixels >= width:
        raise ValueError('reference target must not span the image width')
    distance = reference_distance * reference_pixels / pixels
    return {'estimated_distance_cm': distance, 'observed_width_px': pixels,
            'status': 'approximate_not_validated',
            'requires': ['same camera and resolution', 'same known object',
                         'unclipped single-target mask', 'approximately frontal target',
                         'independent multi-distance validation']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--object-width-cm', type=float, required=True)
    p.add_argument('--reference-distance-cm', type=float, required=True)
    p.add_argument('--reference-width-px', type=float, required=True)
    p.add_argument('--image-width', type=int, required=True)
    p.add_argument('--image-height', type=int, required=True)
    p.add_argument('--frontal-confirmed', action='store_true',
                   help='Operator confirms reference target is approximately frontal')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        result = reference(a.object_width_cm, a.reference_distance_cm,
                           a.reference_width_px, a.image_width, a.image_height,
                           frontal_confirmed=a.frontal_confirmed)
    except ValueError as exc:
        p.exit(2, 'BLOCKED: ' + str(exc) + '\n')
    a.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('REFERENCE_CREATED single_reference_unvalidated')


if __name__ == '__main__':
    main()
