# Independent PC red-paper localization

The live camera can contain a dark red paper rectangle alongside warm furniture
and red text. The frozen PL threshold counts all qualifying pixels, so a few
background pixels can expand its global box. This optional PC prototype searches
the entire current camera frame for a dominant red rectangular component and
draws a separate blue box. It never replaces or changes the received PL fields.

Install the optional dependencies with:

    python -m pip install -r src/pc/requirements-paper.txt
    python -m src.pc.camera_viewer

The viewer offers PC paper localization, PL statistics, and both overlays.
The default is PC localization when its dependencies are available. Blue means
PC processing; green means the existing median-smoothed PL display. The footer
retains the raw PL count and box when PC display is selected. Saved PNG/RGB565
remain original camera pixels.

Version pc-red-paper-hsv/1 uses OpenCV HSV hue 0–10 or 170–179, saturation >=65
and value >=25, followed by a 3x3 opening and a 5x5 closing. Components need
both sides >=12 pixels, area >=max(150, 0.0005*frame area), aspect ratio
between 1/3 and 3, and component fill >=0.82. The largest area*fill candidate
is selected. Coordinates use inclusive box endpoints and the integer part of
the component centroid. These are new PC proposal parameters, not a change
to the frozen RGB565 reference, RTL, UDP, or formal board acceptance.

There is no fixed target ROI or previous-frame position prior. Detection is
recomputed from each displayed live frame; no detection clears the PC result.
The method can select a larger unrelated red rectangle, reject tiny markers,
or lose substantially occluded/perspective-distorted paper. Candidate count
and fill are descriptive values, not calibrated probabilities or identity.

Validation must separate synthetic geometric cases, saved camera snapshots,
and current live display. Synthetic inputs must include dim paper, translation,
border contact, small paper, no target, orange/neutral/blue backgrounds,
isolated noise and irregular red components. Existing post-capture manual
bounds on private snapshots are diagnostic estimates and cannot replace a
pre-capture formal ROI. PC localization is not PL positive-target acceptance.
