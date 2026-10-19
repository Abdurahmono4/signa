# MaDiS motion decoding and Galtis retargeting

This describes the technical adapter and an actual MaDiS inference inspection. The model ran on an uploaded English video and generated three motion chunks. This is not an ASL quality validation.

## API and feature layout

`frontend/src/neuralMotion.ts` exports `createNeuralClip(model, motion): THREE.AnimationClip`. It accepts `features` (or `frames`) as a T×133 matrix, `fps` and optional `format: "signa-madis-133-v1"`. Values must be finite, **denormalized axis-angle radians**, not rotation-6D and not normalized network output. No SMPL-X mesh/model files are loaded by this frontend helper.

The layout follows the official MaDiS `mGPT/data/sign_loader.py::_pose_features` and `mGPT/data/H2S.py::feats2joints` at source commit `071828ea1b94530dc7ff0a6c009c0a7c6d1f0784`:

| Features | Contents |
|---|---|
| 0–29 | Ten local rotations: neck, left collar, right collar, head, left shoulder, right shoulder, left elbow, right elbow, left wrist, right wrist. |
| 30–74 | Left hand: index ×3, middle ×3, pinky ×3, ring ×3, thumb ×3. |
| 75–119 | Same order for the right hand. |
| 120–122 | Jaw rotation. |
| 123–132 | Ten SMPL-X expression coefficients. |

The inference runner is responsible for applying the official mean/std before writing JSON. The frontend rejects `normalized: true`, malformed feature counts, non-finite values and unsupported formats. Source root/lower-body parameters were excluded by the training representation.

## Actual destination bind, not initial node pose

The shipped GLB initially contains a captured pose. Treating those initial node transforms as rest gives an asymmetric baseline. Galtis also has interleaved head/body skeletons: canonical bones and `*_1` helper bones.

The adapter clones the model, collects the union of inverse-bind matrices from all skinned meshes, restores all bind worlds together, then derives local bind transforms. This keeps both 391-bone skeletons consistent. The cached original avatar is not mutated.

Source local axis angles are converted to quaternions and accumulated through the documented SMPL-X upper-body/hand parent chains. In a shared Y-up world convention, the target world orientation is the source rotation delta multiplied by the target bind-world orientation. The target local quaternion is obtained with the inverse of the current destination parent orientation. Unmapped intermediate bones retain their bind-local relation. The clip includes constant bind positions/scales and unmapped rotations so an earlier recorded dictionary pose cannot leak into the neural animation.

`Avatar3D` accepts `motion.neural_asset`, restricted to a relative `/api/` URL. `prepareMotions()` preloads and validates the JSON; the actual retarget clip is constructed for that instance's rig. Neural failures produce an error instead of substituting a dictionary gesture. Neural sampling starts at frame zero; the existing recorded-clip 1/30-second calibration skip remains specific to recorded assets. Export frame observers identify the neural asset after the requested pose has been drawn.

## Material approximation limits

- Galtis and SMPL-X have different body proportions, joint locations and skinning. This rotation adapter is not verified contact-preserving retargeting.
- Official MaDiS SMPL-X visualization uses `use_pca=False` but does not set `flat_hand_mean=True`. The standard SMPL-X implementation adds model-specific hand means. Those licensed model-dependent means are not present here; the adapter does not invent them. Absolute finger shape can therefore differ from the official SMPL-X rendering.
- The ten expression coefficients refer to a learned SMPL-X blendshape basis; Galtis uses named action-unit morphs. There is no validated one-to-one conversion. Jaw/expression coefficients are not synthesized into arbitrary morph channels; stale facial weights are cleared to baseline.
- Root/lower-body motion is absent and remains in destination bind pose.

These limits must remain visible in technical validation. Finite animation matrices or a moving avatar do not prove correct ASL meaning or readable handshape. The generated motion requires comparison with the model's intended representation and evaluation by ASL users.

## Technical checks completed

```powershell
node scripts/test-neural-motion.mjs
node scripts/test-avatar.mjs
node scripts/test-interpreter.mjs
npm.cmd run build
```

The neural helper test checks 782 head/body bind entries, all 40 mapped joint slots, left/right and finger-order isolation, noncommuting parent-chain composition, finite poses, no invented root translation, unsupported-face behavior, normalized/6D rejection, source-model immutability, and replay from a clamped final frame back to real frame zero. The existing 50 recorded clips still pass binding and styled-motion preservation checks. Production build passed after neural asset wiring.

These helper tests use synthetic input to verify the adapter. The actual generated sample is recorded below separately.

## Inspect a completed inference output

After the runner has written an actual `motion.json`, run:

```powershell
node scripts/inspect-neural-motion.mjs <motion.json> <inspection.json>
powershell -NoProfile -File scripts/render-neural-inspection.ps1 -ReportPath <inspection.json> -OutputPath <front.png>
powershell -NoProfile -File scripts/render-neural-inspection.ps1 -ReportPath <inspection.json> -OutputPath <profile.png> -ViewAngle 90
```

The inspector samples every generated frame and every deformed skin vertex, verifies finite transforms, records hand travel and feature variation, and reports signing-area framing at seven aspect ratios and three viewing angles. It records crop violations rather than converting them into a passing result. The optional PNGs project nine actual sampled skeleton poses; they are technical inspection aids, not proof of linguistic accuracy. These commands do not invoke a browser.

`scripts/render-neural-surface.mjs <motion.json> <surface.png> [frame] [angleRadians]` also produces an offline software rasterization of the actual deformed avatar vertices. This is a geometry check; it does not reproduce browser lighting or verify browser playback/export.

## Actual generated sample inspected

The API generated MaDiS features for the 21.104-second uploaded video, job `f4f9c8c3f46f4e008d9a990a4c58860d`. The current cache is `backend/data/neural/fb6e8351debc6b38aeb7b786e6a18e61/motion/`; its three chunks match the earlier `9da3a808fa829593ebc6e9061b8abd05` generation. Each current chunk contains an `inspection.json` produced from its actual `motion.json`.

| Chunk | Decoded frames at 24 fps | Motion duration | Deformed vertex samples |
|---|---:|---:|---:|
| 0000 | 88 | 3.667 s | 1,508,408 |
| 0001 | 56 | 2.333 s | 959,896 |
| 0002 | 16 | 0.667 s | 274,256 |

All 2,742,560 sampled deformed vertices and all joint transforms were finite. All 30 body and 90 hand feature dimensions varied. Every generated pose fit the checked signing area at seven aspect ratios and three angles: worst projected extent was 0.428 horizontally and 0.527 vertically, with zero tested crop violations. Front/profile skeleton sheets and one deformed-surface snapshot per chunk were produced and inspected offline under the earlier matching generation directory. The snapshots showed intact body/hand surfaces and no exploded limbs.

The short output is a material model/timing concern: the three generated clips total only 6.667 seconds for the 21.104-second source. The last six-word sentence generated only 16 frames. First-chunk wrist extents span only approximately 3–9 cm per axis; cumulative wrist paths are approximately 0.33 m left and 0.37 m right. These observations do not establish that all source meanings were expressed. The API retains `complete_translation: false` and generation metadata retains `linguistically_verified: false`. Holding a final pose or slowing a clip cannot validate omitted meaning. ASL expert review and comparison against the intended SMPL-X hand convention remain required.

The audited checkpoint SHA-256 is `d3953f89a74a2b2a8bbce6a9dd9aba4751c81c03e2d8fe8511f0ae7ce2727302`; recorded model revision is `ceaed59c964820f2c13401a0870b2988686956ad`. The model metadata declares `CC-BY-NC-ND-4.0`; this does not turn it into an unrestricted deployment dependency. Browser playback and encoded video/audio export have not been verified by this offline inspection.

## Stable neural camera close-up

Neural playback now samples a single signing envelope from all prepared generated clips. It includes every generated frame's arm/wrist/fingertip support points with 5 cm surface margins, all deformed head vertices and hair/glasses decoration bounds. A perspective fit uses this fixed sequence envelope, the viewport aspect and the selected viewing angle; it does not follow or zoom with each moving hand. The envelope persists through timeline gaps. A newly prepared source gets its own envelope. Captured dictionary clips retain their original camera.

`node scripts/test-neural-framing.mjs backend/data/neural/fb6e8351debc6b38aeb7b786e6a18e61/motion` passed on all three actual clips, 160 poses, seven aspect ratios and three angles. At aspect 0.75 the neural camera distance is 2.517 m, compared with the captured-corpus camera's 5.329 m; hands consequently occupy a materially larger portion of the panel. Worst tested neural signing extents were x=0.795 and y=0.759, with all checked surfaces within the stable camera. Invalid envelopes are rejected and sampling leaves the visible rig unchanged. The unchanged captured-camera regression also passed all 50 clips ×61 poses ×7 aspect ratios ×3 angles. Production build passed after wiring the close-up.

SMPL-X implementation reference: [body model hand-mean handling](https://github.com/vchoutas/smplx/blob/main/smplx/body_models.py). The reference source and licensed model assets are not redistributed by this adapter.
