# NeuroHear spoken yes/no — SIMULATED (RANDOM, STIM-INDEPENDENT)

Seed 123 · living tissue: **False** · input: 84 synthetic speech (macOS text-to-speech), 0 recorded human speech
21 speakers; held out whole: tts:Aman, tts:Eddy, tts:Fred, tts:Grandma, tts:Grandpa, tts:Samantha, tts:Sandy

| Readout (held-out speakers) | Correct | Balanced acc. | By input |
|---|---|---|---|
| Culture response, masked (result) | 13/28 | 0.46 | tts 13/28 |
| Pulse pattern only, no culture | 26/28 | 0.93 | tts 26/28 |
| Unmasked, includes artifact (diagnostic) | 13/28 | 0.46 | tts 13/28 |

**Permuted labels:** null mean 0.49, 95th pct 0.64, p = 0.701 (n_perm=200)

- SIMULATED: any advantage of the culture over input_only exists by model construction.
- No claim that cells hear, understand or learn speech; the readout is the only trained part.
