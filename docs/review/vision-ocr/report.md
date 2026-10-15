# Google Cloud Vision OCR against the local reader (RapidOCR), 2026-10-14

Run by Joely's Claude session on the six made-up labels only (`tests/fixtures/make_label_images.py`), with the gcloud sign-in on Joely's machine against
project `smart-health-510414` (Vision API already enabled). No real photo was uploaded (decision D-063). Raw numbers: `report.json`.

| | Local reader (RapidOCR), before | Local reader, after the thread fix | Google Vision (DOCUMENT_TEXT_DETECTION) |
|---|---|---|---|
| Expected words found | 19 of 20 | 19 of 20 (same lines) | 19 of 20 |
| Time per photo | 10 to 12 s in this run (1.8 s on Hong Yi's machine) | about 0.6 s, steady | about 0.5 s |
| Text similarity to the other reader | 98 to 100 of 100 on the five readable labels | | |
| Heavily blurred label | no text found | no text found | no text found |
| Where the photo goes | stays on the machine | stays on the machine | the **original** photo, with name and NRIC, goes to Google |

## What was found
- On clean made-up labels the two readers are equal. The one miss is the same for both (the heavily blurred label has no text to read).
- The local reader was slow because RapidOCR used every core (20 logical on this laptop) and got slower with each photo (1.9 s, then about 7 s). Limiting it to
  6 threads gives about 0.6 s a photo, every time (2 threads 10 s, 4 threads 5.5 s, 6 threads 0.6 s, 8 threads 0.7 s, 12 threads 1.2 s, 16 threads 2 s).
  `SCAN_OCR_THREADS` (default 0 = automatic: 6, or every core on a smaller machine) sets it; `scan_privacy.RapidOcrAdapter` uses it.
- Vision's speed advantage is gone once the local reader is limited to 6 threads, and Vision would mean sending unmasked photos to Google, which D-063 forbids.

## What was not tested
- Real photos (angles, glare, curved bottles, small print, handwriting). Made-up labels are clean renders, so equal scores on them say little about real use.
  The only fair test of Vision on real labels needs photos that carry a real name and ID; run it only on photos you own (`--allow-real-photos`) and accept that they
  are uploaded unmasked.

## Recommendation
Keep the local reader (privacy by design) with the thread limit. Revisit Vision only if real-photo tests show the local reader missing things that matter,
and then as a decision about D-063, not as a quiet switch.
