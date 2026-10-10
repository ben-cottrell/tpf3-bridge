# Challenge03 — shallow double-track flying junction

10 October 2026. Built and designer-reviewed; user visual review pending.
Accepted Challenge01/02 and their plans remain unchanged. Sol implemented reusable
operator capabilities; the coordinator selected the geometry and operated the game.

## Result and limits

Four required directed native TRAIN paths pass: A_UP→B_UP, A_UP→C_UP,
B_DOWN→A_DOWN, C_DOWN→A_DOWN. No B↔C route, station, signalling or train-operation
claim. Sixteen current track edges, one straight level bridge; both ramps use NORMAL
track and native earthworks. The bridge was built independently before the ramps.

Final arrangement: 12° crossing, deck world z18.77 above rails z3, approximately
96.2-unit deck length. Its ends are 7.5 units laterally beyond the outer through
rails. This implements the user's approximate 5–10-unit visual guidance, not a
universal clearance minimum. Both crossing observations retain BRIDGE classification
and separate endpoint identities. Native acceptance and those observations do not
constitute an independent physical-clearance certificate.

Sampled actual rail footprint is 717.8×94.7 units, excluding earthwork/structure
extent. The revised family is longer but substantially narrower than the original
approximately 570×210 arrangement. C receiving direction changed from −35° to −12°;
therefore these are whole-family comparisons, not matched-endpoint route savings.
Measured native paths are 570.0 units for each A/B direction, 722.8 for A_UP→C_UP,
and 729.0 for C_DOWN→A_DOWN. Peak sampled absolute grade is approximately 10.20%.

The native screenshot shows a narrow coherent crossing with the short deck between
earth-supported approaches. Some terrain scarring from the removed trial remains;
landscaping is not the construction challenge's acceptance criterion. This is the
designer's assessment, not user acceptance or proof across arbitrary junctions.

## Plan, sequence and local fitting

Origin (−1650,−4890,3). The A/B principal pair stays straight and level. C_UP diverges
on the near side; C_DOWN crosses above both tracks, returning to the paired C mouth.
The entire R5 arrangement and profile were selected before removing R4. See
[whole plan](plan-r5.svg), [profile](profile-r5.svg),
[actual overlay](final-overlay.svg) and [actual profile](final-profile.svg).
Original revisions and reasons remain in [design history](DESIGN_HISTORY.md).

R5 removed eight old flyover edges and two obsolete C boundary stubs using fresh
geometry matched after a normal save/load. It created new C stubs and the standalone
deck. The proposed x40 turnout coincided with an existing segment end left by the
old junction; x60 fell inside the adapter's excluded first 5% of the long edge.
Neither produced a native construction proposal. This is a bridge selection
restriction, not proof of native impossibility. R5b moved the turnout upstream to
x10, retained a level lead to x70, then rose to the deck. The three remaining
connections all built on their first native evaluated proposal. No blind replay.

The final plan's turnout moved within the same approach family. The recorded R5b
continuation is the authority for that local fit; the selected R5 whole plan remains
available for comparison. Native continuation preserved all completed steps.

## Lessons

- Select crossing angle, deck extent, paired landing and both ramps together.
  For a narrow flyover, compare a shallow crossing before accepting a short but
  wide steep-angle crossing. Here 10–15° was the user's design preference.
- Build the controlling level deck first, then fit earth-supported ramps to it.
  A long rising bridge is not a substitute for deciding where the deck should end.
- Preserve a level turnout lead when immediate vertical curvature is rejected.
  R3 failed at a sampled 7.6%, but R4 built at 11.2% after a level first section.
  Installed maxSlopeBuild=0.085 is therefore not a universal acceptance ceiling.
  Tested simple/standard/high-speed templates shared the same slope fields;
  other resources may differ. Native complete proposals decide the actual fit.
- Report adapter eligibility, bridge policy and native rejection separately.
  The existing 5–95% edge-interior restriction merits a focused future improvement;
  it must not be described as a game rule or used to justify sprawling geometry.
- User correction exposed a spatial planning weakness even though R4 built.
  Solving the bridge API and producing a good railway remain separate tasks.

## Evidence and efficiency

Session pif_1791618506_4804957, final run 3567a544a3fc4ac4, preceding R5 deck/removal
run d74fe176fce34580. Four native route checks and both crossing observations pass.
Full local evidence: .local_runs/operator/3567a544a3fc4ac4/review.json.
R5 construction attempts used 42 native calls and 21.91 seconds of recorded native
call time, excluding planning, reads outside builds, save/reload, review and discussion.
This is not total elapsed time or measured GPT-token savings. Construction used
reusable JSON plans/MCP; Computer Use was needed only for the normal adapter reload.
Final camera, screenshot and save completed through the native operator.

Save: Design Challenge 03 - Shallow Flying Junction R5.sav; callback and file verified,
36,468,851 bytes, SHA256 d782031f6eaa4585f5a1c1dee308459e2c09c669e9429bb269129c85c4e34a3a.
Screenshot: game userdata screenshots/2026-10-10_09-07-46_img_0.png.
Final checkpoint has not been reloaded. No remote push.
