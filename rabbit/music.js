/* The island's sound: an original calypso for steel pan, marimba, bass and hand drums, played live in the
   visitor's browser (no recordings), plus the sea, gulls and small sounds for the game. On by default;
   browsers only allow sound after a first tap, so the page shows "♪ Tap for sound" until then.
   window.COVE_SOUND = { start, on, set({ music, radio, tense, place }), sfx(name), speak(clips), hush(), toggle(remember) }
   Each place on the island plays the tune in its own arrangement (STYLES). */
(() => {
  const BPM = 104, STEP = 60 / BPM / 4, SWING = 0.16;   // sixteenth notes, the off sixteenths a little late
  /* the tune: 16 bars, A then B; each note is [sixteenth in the bar, midi note, length in sixteenths] */
  const A = [
    [[0, 72, 2], [2, 69, 1], [3, 72, 2], [6, 74, 2], [8, 72, 3], [11, 69, 1], [12, 65, 4]],
    [[0, 70, 2], [2, 74, 1], [3, 77, 2], [6, 74, 2], [8, 77, 3], [11, 74, 1], [12, 70, 4]],
    [[0, 76, 2], [2, 74, 1], [3, 72, 2], [6, 70, 2], [8, 67, 3], [11, 70, 1], [12, 72, 4]],
    [[0, 69, 3], [3, 72, 3], [6, 77, 6], [12, 76, 2], [14, 74, 2]],
    [[0, 72, 2], [2, 69, 1], [3, 72, 2], [6, 74, 2], [8, 77, 3], [11, 79, 1], [12, 81, 4]],
    [[0, 79, 2], [2, 77, 1], [3, 74, 2], [6, 77, 2], [8, 74, 3], [11, 72, 1], [12, 69, 4]],
    [[0, 70, 2], [2, 74, 2], [4, 79, 2], [6, 77, 2], [8, 76, 2], [10, 74, 2], [12, 72, 2], [14, 70, 2]],
    [[0, 69, 4], [4, 65, 2], [6, 69, 2], [8, 72, 8]],
  ];
  const B = [
    [[2, 74, 2], [4, 74, 2], [6, 77, 4], [12, 74, 2], [14, 72, 2]],
    [[0, 69, 6], [8, 72, 2], [10, 69, 2], [12, 65, 4]],
    [[2, 70, 2], [4, 70, 2], [6, 74, 4], [12, 72, 2], [14, 70, 2]],
    [[0, 69, 8], [10, 72, 2], [12, 74, 2], [14, 76, 2]],
    [[0, 77, 3], [3, 74, 3], [6, 69, 2], [8, 74, 3], [11, 77, 1], [12, 81, 4]],
    [[0, 79, 3], [3, 74, 3], [6, 70, 2], [8, 74, 4], [12, 79, 4]],
    [[0, 76, 2], [2, 79, 2], [4, 76, 2], [6, 72, 2], [8, 70, 2], [10, 67, 2], [12, 64, 4]],
    [[0, 65, 4], [4, 69, 2], [6, 72, 2], [8, 77, 8]],
  ];
  const TUNE = [...A, ...B];
  /* chords and bass roots per bar (two per bar where the harmony moves on beat 3) */
  const CH = { F: [[53, 57, 60], 41, 48], Bb: [[58, 62, 65], 46, 53], C7: [[55, 58, 60, 64], 48, 43], Dm: [[57, 62, 65], 50, 45], Gm: [[55, 58, 62], 43, 50] };
  const HARM = ["F", "Bb", "C7", "F", "F", "Dm", ["Gm", "C7"], "F", "Bb", "F", "C7", "F", "Dm", "Gm", "C7", "F"];
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);
  /* ---------- the island's songbook: all original, written for this game ----------
     Each song: bpm, 16 bars of tune ([sixteenth, midi note, length]), the harmony bar by bar and its chords
     ([chord notes, bass root, bass fifth]). Radio Coco plays them in turn; every place has its own (PLACES below). */
  const C_ = { C: [[55, 60, 64], 48, 43], F: [[53, 57, 60], 41, 48], G7: [[55, 59, 62, 65], 43, 50], Am: [[57, 60, 64], 45, 52], Dm: [[57, 62, 65], 50, 45] };
  const SONGS = {
    coco: { name: "Coco Calypso", bpm: 104, tune: TUNE, harm: HARM, ch: CH, air: { k: 1, drums: "full", bass: 1, mar: 1, lead: "pan" } },
    /* a lazy reggae for low tide, G minor */
    lowtide: { name: "Low Tide", bpm: 74, air: { drums: "onedrop", bass: 1.2, lead: "organ" }, ch: { Gm: [[55, 58, 62], 43, 50], Cm: [[55, 60, 63], 48, 43], D7: [[54, 57, 60], 50, 45], Eb: [[55, 58, 63], 51, 46], F: [[53, 57, 60], 41, 48], Bb: [[53, 58, 62], 46, 53] },
      harm: ["Gm", "Gm", "Cm", "Cm", "Gm", "Eb", "D7", "D7", "Eb", "F", "Bb", "Gm", "Cm", "D7", "Gm", "Gm"],
      tune: [
        [[2, 74, 2], [4, 74, 1], [6, 72, 2], [8, 70, 4], [14, 67, 2]], [[0, 70, 3], [4, 69, 2], [6, 67, 6]],
        [[2, 72, 2], [4, 72, 1], [6, 75, 2], [8, 74, 2], [10, 72, 2], [12, 70, 4]], [[0, 67, 8], [12, 72, 2], [14, 74, 2]],
        [[0, 74, 3], [3, 77, 3], [6, 74, 2], [8, 70, 4], [12, 67, 4]], [[2, 70, 2], [4, 75, 2], [6, 74, 2], [8, 70, 2], [10, 67, 6]],
        [[0, 66, 2], [2, 69, 2], [4, 72, 2], [6, 74, 4], [12, 72, 2], [14, 69, 2]], [[0, 66, 4], [4, 69, 2], [6, 74, 10]],
        [[0, 79, 3], [3, 77, 3], [6, 75, 2], [8, 74, 4], [12, 75, 4]], [[0, 77, 3], [3, 74, 3], [6, 72, 2], [8, 69, 8]],
        [[2, 74, 2], [4, 77, 2], [6, 74, 2], [8, 70, 2], [10, 74, 2], [12, 77, 4]], [[0, 79, 6], [8, 74, 4], [12, 70, 4]],
        [[0, 75, 2], [2, 72, 2], [4, 75, 2], [6, 79, 4], [12, 77, 2], [14, 75, 2]], [[0, 74, 4], [4, 72, 2], [6, 69, 2], [8, 66, 8]],
        [[2, 67, 2], [4, 70, 2], [6, 74, 4], [12, 72, 2], [14, 70, 2]], [[0, 67, 12]],
      ] },
    /* a soca for the market, fast and bright, C major */
    mango: { name: "Mango Run", bpm: 126, air: { drums: "soca", bass: 1, mar: 1, lead: "pan", agogo: 1 }, ch: C_,
      harm: ["C", "C", "F", "G7", "C", "Am", "Dm", "G7", "F", "F", "C", "Am", "Dm", "G7", "C", "C"],
      tune: [
        [[0, 72, 1], [2, 72, 1], [3, 76, 2], [6, 79, 2], [8, 76, 1], [10, 76, 1], [11, 72, 2], [14, 74, 2]], [[0, 76, 3], [3, 72, 3], [6, 67, 2], [8, 72, 8]],
        [[0, 77, 1], [2, 77, 1], [3, 81, 2], [6, 84, 2], [8, 81, 1], [10, 81, 1], [11, 77, 2], [14, 79, 2]], [[0, 79, 3], [3, 77, 3], [6, 74, 2], [8, 71, 4], [12, 74, 4]],
        [[0, 72, 1], [2, 72, 1], [3, 76, 2], [6, 79, 2], [8, 84, 2], [10, 83, 2], [12, 79, 4]], [[0, 81, 3], [3, 79, 3], [6, 76, 2], [8, 72, 4], [12, 76, 4]],
        [[0, 77, 2], [2, 74, 2], [4, 77, 2], [6, 81, 2], [8, 79, 2], [10, 77, 2], [12, 74, 2], [14, 71, 2]], [[0, 74, 4], [4, 79, 4], [8, 77, 2], [10, 74, 2], [12, 71, 4]],
        [[0, 81, 6], [6, 79, 2], [8, 77, 4], [12, 72, 4]], [[0, 74, 2], [2, 77, 2], [4, 81, 2], [6, 84, 6], [12, 81, 4]],
        [[0, 79, 6], [6, 76, 2], [8, 72, 4], [12, 76, 4]], [[0, 76, 2], [2, 79, 2], [4, 84, 2], [6, 81, 6], [12, 76, 4]],
        [[0, 77, 3], [3, 81, 3], [6, 77, 2], [8, 74, 4], [12, 77, 4]], [[0, 79, 3], [3, 77, 3], [6, 74, 2], [8, 71, 2], [10, 74, 2], [12, 77, 4]],
        [[0, 76, 1], [2, 76, 1], [3, 79, 2], [6, 84, 2], [8, 79, 2], [10, 76, 2], [12, 74, 4]], [[0, 72, 4], [6, 72, 1], [7, 72, 9]],
      ] },
    /* a slow bossa for a hammock and a cold drink, D major sevenths */
    hammock: { name: "Hammock Hours", bpm: 84, air: { drums: "bossa", bass: 0.9, lead: "pan", strum: 1, soft: 1 }, ch: { Dmaj7: [[54, 57, 61], 50, 45], Bm7: [[54, 57, 62], 47, 42], Em7: [[55, 59, 62], 52, 47], A7: [[55, 61, 64], 45, 52], Gmaj7: [[54, 59, 62], 43, 50], "F#m7": [[52, 57, 61], 42, 49] },
      harm: ["Dmaj7", "Dmaj7", "Bm7", "Bm7", "Em7", "A7", "Dmaj7", "A7", "Gmaj7", "Gmaj7", "F#m7", "Bm7", "Em7", "A7", "Dmaj7", "Dmaj7"],
      tune: [
        [[0, 78, 6], [6, 76, 2], [8, 73, 4], [12, 71, 4]], [[0, 73, 8], [10, 74, 2], [12, 76, 4]],
        [[0, 74, 6], [6, 73, 2], [8, 71, 4], [12, 69, 4]], [[0, 71, 10], [12, 73, 2], [14, 74, 2]],
        [[0, 76, 6], [6, 74, 2], [8, 71, 4], [12, 67, 4]], [[0, 69, 4], [4, 73, 4], [8, 76, 4], [12, 79, 4]],
        [[0, 78, 10], [12, 76, 2], [14, 73, 2]], [[0, 69, 12]],
        [[0, 74, 4], [4, 78, 4], [8, 83, 6], [14, 81, 2]], [[0, 79, 8], [8, 78, 4], [12, 74, 4]],
        [[0, 73, 4], [4, 76, 4], [8, 81, 6], [14, 79, 2]], [[0, 78, 8], [8, 74, 4], [12, 71, 4]],
        [[0, 79, 4], [4, 78, 2], [6, 76, 2], [8, 74, 4], [12, 71, 4]], [[0, 73, 4], [4, 76, 4], [8, 79, 4], [12, 76, 4]],
        [[0, 74, 4], [4, 73, 2], [6, 74, 2], [8, 78, 8]], [[0, 74, 12]],
      ] },
    /* an old-time mento from a tin-roofed shed, G major */
    tinroof: { name: "Tin Roof Shuffle", bpm: 112, air: { drums: "mento", bass: 1, lead: "pluck" }, ch: { G: [[55, 59, 62], 43, 50], C: [[55, 60, 64], 48, 43], D7: [[54, 57, 60], 50, 45], Em: [[55, 59, 64], 52, 47] },
      harm: ["G", "G", "C", "G", "D7", "D7", "G", "G", "C", "C", "G", "Em", "C", "D7", "G", "G"],
      tune: [
        [[0, 71, 2], [2, 74, 2], [4, 79, 2], [6, 78, 1], [7, 79, 3], [10, 74, 2], [12, 71, 4]], [[0, 72, 2], [2, 71, 2], [4, 69, 2], [6, 67, 2], [8, 71, 8]],
        [[0, 76, 2], [2, 79, 2], [4, 84, 2], [6, 83, 1], [7, 84, 3], [10, 79, 2], [12, 76, 4]], [[0, 74, 3], [3, 71, 3], [6, 67, 2], [8, 74, 8]],
        [[0, 72, 2], [2, 74, 2], [4, 78, 2], [6, 81, 2], [8, 78, 2], [10, 74, 2], [12, 72, 4]], [[0, 74, 2], [2, 72, 2], [4, 69, 2], [6, 66, 2], [8, 69, 4], [12, 72, 4]],
        [[0, 71, 3], [3, 74, 3], [6, 79, 2], [8, 74, 2], [10, 71, 2], [12, 67, 4]], [[0, 67, 4], [4, 71, 2], [6, 74, 2], [8, 79, 8]],
        [[2, 76, 2], [4, 76, 2], [6, 79, 4], [12, 76, 2], [14, 72, 2]], [[0, 72, 6], [8, 76, 2], [10, 79, 2], [12, 84, 4]],
        [[2, 74, 2], [4, 74, 2], [6, 79, 4], [12, 74, 2], [14, 71, 2]], [[0, 71, 6], [8, 76, 2], [10, 79, 2], [12, 83, 4]],
        [[0, 84, 3], [3, 79, 3], [6, 76, 2], [8, 72, 4], [12, 76, 4]], [[0, 78, 3], [3, 74, 3], [6, 72, 2], [8, 69, 4], [12, 66, 4]],
        [[0, 67, 2], [2, 71, 2], [4, 74, 2], [6, 79, 2], [8, 78, 2], [10, 74, 2], [12, 71, 2], [14, 74, 2]], [[0, 79, 4], [6, 67, 2], [8, 67, 8]],
      ] },
    /* a bolero for the moon over the water, A minor */
    moon: { name: "Moon Over the Pier", bpm: 68, air: { drums: "soft", bass: 0.7, lead: "flute", arp: 1, pad: 0.5 }, ch: { Am: [[57, 60, 64], 45, 52], Dm: [[57, 62, 65], 50, 45], E7: [[56, 59, 62], 40, 47], F: [[53, 57, 60], 41, 48], G: [[55, 59, 62], 43, 50], C: [[55, 60, 64], 48, 43] },
      harm: ["Am", "Am", "Dm", "Dm", "E7", "E7", "Am", "Am", "F", "G", "C", "Am", "Dm", "E7", "Am", "Am"],
      tune: [
        [[0, 76, 6], [6, 74, 2], [8, 72, 4], [12, 71, 4]], [[0, 69, 12], [12, 71, 2], [14, 72, 2]],
        [[0, 74, 6], [6, 72, 2], [8, 74, 4], [12, 77, 4]], [[0, 76, 8], [8, 74, 4], [12, 72, 4]],
        [[0, 71, 6], [6, 72, 2], [8, 74, 4], [12, 76, 4]], [[0, 74, 6], [6, 72, 2], [8, 71, 4], [12, 68, 4]],
        [[0, 69, 4], [4, 72, 4], [8, 76, 4], [12, 81, 4]], [[0, 76, 12]],
        [[0, 77, 6], [6, 76, 2], [8, 77, 4], [12, 81, 4]], [[0, 79, 6], [6, 77, 2], [8, 74, 4], [12, 71, 4]],
        [[0, 72, 6], [6, 74, 2], [8, 76, 4], [12, 79, 4]], [[0, 76, 8], [8, 72, 4], [12, 69, 4]],
        [[0, 74, 6], [6, 77, 2], [8, 81, 4], [12, 77, 4]], [[0, 76, 6], [6, 74, 2], [8, 71, 4], [12, 68, 4]],
        [[0, 69, 6], [6, 71, 2], [8, 72, 4], [12, 71, 4]], [[0, 69, 12]],
      ] },
    /* a skipping tune for the schoolyard, C major */
    school: { name: "Chalk and Sand", bpm: 120, ch: C_,
      harm: ["C", "F", "C", "G7", "C", "F", "G7", "C", "Am", "F", "C", "G7", "Am", "F", "G7", "C"],
      tune: [
        [[0, 72, 2], [2, 74, 2], [4, 76, 2], [6, 72, 2], [8, 79, 4], [12, 79, 4]], [[0, 81, 2], [2, 81, 2], [4, 81, 2], [6, 81, 2], [8, 77, 8]],
        [[0, 76, 2], [2, 76, 2], [4, 76, 2], [6, 74, 2], [8, 72, 4], [12, 76, 4]], [[0, 74, 2], [2, 76, 2], [4, 74, 2], [6, 71, 2], [8, 67, 8]],
        [[0, 72, 2], [2, 74, 2], [4, 76, 2], [6, 72, 2], [8, 79, 4], [12, 79, 4]], [[0, 81, 2], [2, 79, 2], [4, 77, 2], [6, 76, 2], [8, 74, 4], [12, 81, 4]],
        [[0, 79, 2], [2, 77, 2], [4, 74, 2], [6, 71, 2], [8, 74, 4], [12, 71, 4]], [[0, 72, 4], [4, 79, 2], [6, 76, 2], [8, 72, 8]],
        [[0, 76, 3], [3, 76, 1], [4, 72, 2], [6, 76, 2], [8, 81, 4], [12, 79, 4]], [[0, 77, 3], [3, 77, 1], [4, 72, 2], [6, 77, 2], [8, 81, 4], [12, 77, 4]],
        [[0, 76, 3], [3, 76, 1], [4, 79, 2], [6, 84, 2], [8, 79, 4], [12, 76, 4]], [[0, 74, 3], [3, 74, 1], [4, 71, 2], [6, 74, 2], [8, 79, 8]],
        [[0, 81, 2], [2, 84, 2], [4, 81, 2], [6, 76, 2], [8, 72, 4], [12, 76, 4]], [[0, 77, 2], [2, 81, 2], [4, 77, 2], [6, 72, 2], [8, 69, 4], [12, 72, 4]],
        [[0, 74, 2], [2, 77, 2], [4, 79, 2], [6, 83, 2], [8, 79, 2], [10, 77, 2], [12, 74, 4]], [[0, 72, 4], [4, 67, 2], [6, 72, 2], [8, 72, 8]],
      ] },
    /* a chant for the hill drums, E minor, call and answer */
    hills: { name: "Three Hills", bpm: 98, ch: { Em: [[55, 59, 64], 40, 47], D: [[54, 57, 62], 38, 45], C: [[55, 60, 64], 36, 43] },
      harm: ["Em", "Em", "D", "Em", "Em", "Em", "C", "D", "Em", "D", "Em", "D", "C", "D", "Em", "Em"],
      tune: [
        [[0, 76, 2], [2, 76, 2], [4, 79, 2], [6, 76, 2], [8, 74, 4], [12, 71, 4]], [[0, 71, 2], [3, 74, 2], [6, 76, 2], [8, 76, 8]],
        [[0, 74, 2], [2, 74, 2], [4, 78, 2], [6, 74, 2], [8, 71, 4], [12, 69, 4]], [[0, 71, 6], [8, 64, 8]],
        [[0, 64, 2], [2, 67, 2], [4, 69, 2], [6, 71, 2], [8, 74, 2], [10, 71, 2], [12, 69, 4]], [[0, 67, 2], [3, 64, 2], [6, 67, 2], [8, 71, 8]],
        [[0, 72, 4], [4, 71, 4], [8, 67, 4], [12, 64, 4]], [[0, 66, 4], [4, 69, 4], [8, 74, 8]],
        [[0, 83, 2], [2, 83, 2], [4, 81, 4]], [[8, 78, 2], [10, 78, 2], [12, 74, 4]],
        [[0, 83, 2], [2, 83, 2], [4, 86, 4]], [[8, 81, 2], [10, 78, 2], [12, 74, 4]],
        [[0, 79, 4], [4, 76, 4], [8, 72, 4], [12, 76, 4]], [[0, 78, 4], [4, 74, 4], [8, 69, 4], [12, 74, 4]],
        [[0, 76, 2], [2, 79, 2], [4, 76, 2], [6, 74, 2], [8, 71, 4], [12, 74, 4]], [[0, 76, 12]],
      ] },
    /* something deep is being measured: bells and a ticking ostinato, D minor */
    survey: { name: "Something Deep", bpm: 92, ch: { Dm: [[57, 62, 65], 38, 45], Bb: [[53, 58, 62], 46, 41], Gm: [[55, 58, 62], 43, 50], A7: [[55, 61, 64], 45, 40] },
      harm: ["Dm", "Dm", "Bb", "A7", "Dm", "Dm", "Gm", "A7", "Bb", "Bb", "Gm", "Gm", "Dm", "Bb", "A7", "Dm"],
      tune: [
        [[0, 74, 4], [6, 77, 2], [8, 76, 6]], [[0, 74, 2], [2, 69, 10]],
        [[0, 70, 4], [6, 74, 2], [8, 77, 6]], [[0, 76, 4], [4, 73, 8]],
        [[0, 74, 4], [6, 81, 2], [8, 79, 6]], [[0, 77, 2], [2, 76, 2], [4, 74, 8]],
        [[0, 70, 4], [4, 74, 4], [8, 79, 6]], [[0, 76, 4], [4, 73, 4], [8, 69, 8]],
        [[0, 77, 6], [6, 74, 2], [8, 70, 8]], [[0, 72, 2], [2, 74, 2], [4, 77, 4], [8, 82, 8]],
        [[0, 79, 6], [6, 77, 2], [8, 74, 8]], [[0, 70, 4], [4, 74, 4], [8, 79, 8]],
        [[0, 81, 6], [6, 77, 2], [8, 74, 8]], [[0, 77, 4], [4, 74, 4], [8, 70, 8]],
        [[0, 73, 4], [4, 76, 4], [8, 79, 4], [12, 76, 4]], [[0, 74, 12]],
      ] },
  };
  /* what Radio Coco plays, one after the other (two times round each), on the island and in the site header */
  const PLAYLIST = ["coco", "mango", "lowtide", "tinroof", "hammock", "moon"];

  const S = { place: "island", placeT: "island", song: "coco", pl: 0, ctx: null, on: false, want: true, master: null, music: null, amb: null, rev: null, radio: null, mvol: 1, tense: false, bar: 0, step: 0, next: 0, timer: 0, noise: null, sea: null };
  /* the island's sound is on when the game opens (the site's own rule: sound on by default); a player who turns it off is
     remembered for this tab only (sessionStorage), so a new visit starts with the sound again. The site's radio switch
     (assets/radio.js) does not reach in here: an island with the sound off is not what a visitor came for. */
  const MEM = "tauhud-rabbit-sound";
  try { S.want = sessionStorage.getItem(MEM) !== "off"; } catch (e) {}

  function build() {
    /* iPhones: play even with the ring switch on silent, like any game (Safari 16.4+) */
    try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
    const c = S.ctx = new (window.AudioContext || window.webkitAudioContext)();
    S.master = c.createGain(); S.master.gain.value = 0.8; S.master.connect(c.destination);
    /* a small room of reverb, made from decaying noise */
    const len = c.sampleRate * 1.8, ir = c.createBuffer(2, len, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3); }
    S.rev = c.createConvolver(); S.rev.buffer = ir; const rg = c.createGain(); rg.gain.value = 0.22; S.rev.connect(rg); rg.connect(S.master);
    /* the music bus; at the radio it goes through a small speaker (a band-pass) */
    S.music = c.createGain(); S.music.gain.value = 0;
    S.radio = c.createBiquadFilter(); S.radio.type = "allpass";
    S.music.connect(S.radio); S.radio.connect(S.master); S.radio.connect(S.rev);
    S.amb = c.createGain(); S.amb.gain.value = 0; S.amb.connect(S.master);
    const nb = c.createBuffer(1, c.sampleRate * 2, c.sampleRate), nd = nb.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1; S.noise = nb;
    /* the sea: noise through a low filter that breathes like waves on a beach */
    const sea = c.createBufferSource(); sea.buffer = nb; sea.loop = true;
    const lp = c.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 420;
    const sg = c.createGain(); sg.gain.value = 0.18;
    const lfo = c.createOscillator(), lg = c.createGain(); lfo.frequency.value = 0.11; lg.gain.value = 0.14; lfo.connect(lg); lg.connect(sg.gain);
    const lfo2 = c.createOscillator(), lg2 = c.createGain(); lfo2.frequency.value = 0.07; lg2.gain.value = 260; lfo2.connect(lg2); lg2.connect(lp.frequency);
    sea.connect(lp); lp.connect(sg); sg.connect(S.amb); sea.start(); lfo.start(); lfo2.start();
    S.next = c.currentTime + 0.1;
    S.timer = setInterval(tick, 25);
    setInterval(() => { if (S.on && Math.random() < 0.35) gull(); }, 7000);
  }
  /* ---------- the instruments ---------- */
  function env(g, t, a, peak, d) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + d); }
  function pan(t, m, dur, v = 0.22) {   // steel pan: a bright fundamental, its octave and twelfth, a slight shimmer
    const c = S.ctx, out = c.createGain(); out.connect(S.music);
    [[1, 1], [2, 0.5], [3, 0.2], [4.02, 0.08]].forEach(([r, a], i) => {
      const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; o.detune.value = (i ? 4 : 0);
      env(g, t, 0.006, v * a, Math.min(1.4, 0.35 + dur * 0.9) / (1 + i * 0.6)); o.connect(g); g.connect(out); o.start(t); o.stop(t + 2);
    });
    const vib = c.createOscillator(), vg = c.createGain(); vib.frequency.value = 5.5; vg.gain.value = 0.05; vib.connect(vg); vg.connect(out.gain); vib.start(t); vib.stop(t + 2);
  }
  function marimba(t, m, v = 0.08) {
    const c = S.ctx;
    [[1, 1, 0.28], [3.93, 0.25, 0.06]].forEach(([r, a, d]) => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; env(g, t, 0.004, v * a, d); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + 0.5); });
  }
  function bass(t, m, dur, v = 1) {
    const c = S.ctx, o = c.createOscillator(), o2 = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = "triangle"; o.frequency.value = hz(m); o2.frequency.value = hz(m) / 2; f.type = "lowpass"; f.frequency.value = 700;
    env(g, t, 0.01, 0.32 * v, Math.max(0.18, dur * STEP * 1.2)); o.connect(f); o2.connect(f); f.connect(g); g.connect(S.music); o.start(t); o2.start(t); o.stop(t + 1); o2.stop(t + 1);
  }
  function hit(t, type, v = 1) {
    const c = S.ctx, g = c.createGain(); g.connect(S.music);
    if (type === "shaker") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "highpass"; f.frequency.value = 6500; env(g, t, 0.004, 0.05 * v, 0.045); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.1); }
    if (type === "conga" || type === "congaHi") { const o = c.createOscillator(); const f0 = type === "conga" ? 190 : 285; o.frequency.setValueAtTime(f0 * 1.3, t); o.frequency.exponentialRampToValueAtTime(f0, t + 0.05); env(g, t, 0.003, 0.22 * v, 0.22); o.connect(g); o.start(t); o.stop(t + 0.4); }
    if (type === "clave") { const o = c.createOscillator(); o.frequency.value = 2400; env(g, t, 0.002, 0.07 * v, 0.05); o.connect(g); o.start(t); o.stop(t + 0.1); }
    if (type === "rim") { const o = c.createOscillator(); o.type = "square"; o.frequency.value = 1700; env(g, t, 0.001, 0.035 * v, 0.03); o.connect(g); o.start(t); o.stop(t + 0.06); }
    if (type === "hat") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "highpass"; f.frequency.value = 9000; env(g, t, 0.002, 0.04 * v, 0.03); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.06); }
    if (type === "agogo" || type === "agogoLo") { [1, 2.7].forEach((r, i) => { const o = c.createOscillator(); o.frequency.value = (type === "agogo" ? 880 : 660) * r; const gg = c.createGain(); env(gg, t, 0.002, (i ? 0.02 : 0.06) * v, 0.18); o.connect(gg); gg.connect(g); o.start(t); o.stop(t + 0.3); }); g.gain.value = 1; }
    if (type === "timp") { const o = c.createOscillator(); o.frequency.setValueAtTime(98, t); o.frequency.exponentialRampToValueAtTime(87, t + 0.4); env(g, t, 0.005, 0.3 * v, 0.7); o.connect(g); o.start(t); o.stop(t + 0.9); }
    if (type === "snare") { const n = c.createBufferSource(), f = c.createBiquadFilter(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 2200; f.Q.value = 0.8; env(g, t, 0.002, 0.08 * v, 0.12); n.connect(f); f.connect(g); n.start(t, Math.random()); n.stop(t + 0.2); }
    if (type === "clap") { [0, 0.012, 0.024].forEach(d => { const n = c.createBufferSource(), f = c.createBiquadFilter(), gg = c.createGain(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 1500; f.Q.value = 1.2; env(gg, t + d, 0.002, 0.05 * v, 0.06); n.connect(f); f.connect(gg); gg.connect(g); n.start(t + d, Math.random()); n.stop(t + d + 0.1); }); }
    if (type === "clank") { [1, 2.41, 3.77].forEach((r, i) => { const o = c.createOscillator(), gg = c.createGain(); o.type = "square"; o.frequency.value = 380 * r; env(gg, t, 0.001, (i ? 0.012 : 0.025) * v, 0.12); o.connect(gg); gg.connect(g); o.start(t); o.stop(t + 0.2); }); }
    if (type === "knock") { const o = c.createOscillator(); o.frequency.setValueAtTime(520, t); o.frequency.exponentialRampToValueAtTime(300, t + 0.04); env(g, t, 0.001, 0.12 * v, 0.07); o.connect(g); o.start(t); o.stop(t + 0.12); }
    if (type === "kick") { const o = c.createOscillator(); o.frequency.setValueAtTime(120, t); o.frequency.exponentialRampToValueAtTime(48, t + 0.12); env(g, t, 0.004, 0.35 * v, 0.2); o.connect(g); o.start(t); o.stop(t + 0.3); }
  }
  function gull() {
    const c = S.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain(); o.type = "sawtooth";
    const f = c.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = 2200; f.Q.value = 6;
    for (let i = 0; i < 3; i++) { o.frequency.setValueAtTime(1500, t + i * 0.22); o.frequency.exponentialRampToValueAtTime(900, t + i * 0.22 + 0.18); }
    g.gain.setValueAtTime(0.0001, t); for (let i = 0; i < 3; i++) { g.gain.exponentialRampToValueAtTime(0.025, t + i * 0.22 + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.22 + 0.19); }
    o.connect(f); f.connect(g); g.connect(S.amb); o.start(t); o.stop(t + 0.8);
  }
  /* ---------- the band ---------- */
  const CLAVE = [[0, 6, 12], [4, 8]];   // two bars, three then two
  /* every place on the island has its own soundtrack: a song from the songbook (s) in that place's arrangement:
     k tempo against the song's own, drums, bass, marimba, the tune's voice, and something only that place has.
     Without a song (s) the place plays Radio Coco's playlist. */
  const STYLES = {
    island: { k: 1, drums: "full", bass: 1, mar: 1, lead: "pan" },                                    // the island: Radio Coco, one song after the other
    radio:  { k: 1.06, drums: "full", bass: 1.1, mar: 1, lead: "pan", hat: 1 },                       // on air: a touch faster, with a hi-hat, through the speaker
    hall:   { s: "coco", k: 0.78, drums: "march", bass: 0.8, mar: 0, lead: "brass", pad: 1 },          // the council: a small brass anthem over an organ
    north:  { s: "survey", k: 0.9, drums: "none", bass: 0.5, mar: 0, lead: "bell", arp: 1, pad: 0.6 }, // the North Wind: cool bells over what is being measured
    south:  { s: "coco", k: 0.9, drums: "bossa", bass: 0.9, mar: 1, lead: "pan", soft: 1 },            // the South Current: an easy bossa
    bar:    { s: "hammock", k: 1.08, drums: "bossa", bass: 1, mar: 0, lead: "pan", strum: 1, conga: 1 },// La Ola: a cold drink, a guitar, the whole bar humming
    book:   { s: "moon", k: 0.85, drums: "none", bass: 0, mar: 0, lead: "bell", pad: 0.8, sparse: 1 }, // the lighthouse: almost silence, a few bells
    market: { s: "mango", k: 1, drums: "soca", bass: 1, mar: 1, lead: "pan", agogo: 1 },                // the square: a soca, a cowbell, everybody shouting prices
    cafe:   { s: "hammock", k: 0.9, drums: "bossa", bass: 0.8, mar: 1, lead: "pluck", strum: 1, soft: 1 }, // the Parasol Café: a slow bossa between the cups
    pier:   { s: "moon", k: 1, drums: "soft", bass: 0.6, mar: 0, lead: "flute", arp: 1 },               // the pier: a slow flute over the water
    school: { s: "school", k: 1, drums: "soft", bass: 0.7, mar: 0, lead: "mar", clap: 1 },              // the school: a skipping tune on the xylophone, children clapping
    dive:   { s: "lowtide", k: 1, drums: "onedrop", bass: 1.2, mar: 0, lead: "organ", bubble: 1 },     // the dive centre: reggae from under the water, bubbles
    works:  { s: "tinroof", k: 1, drums: "mento", bass: 1, mar: 0, lead: "organ", clank: 1 },           // the Coconut Works: three bicycles and a church organ
    camp:   { s: "survey", k: 1, drums: "tick", bass: 0.8, mar: 0, lead: "mar", arp: 1 },               // the surveyors: a ticking instrument, metre by metre
    ship:   { s: "lowtide", k: 0.92, drums: "soft", bass: 0.8, mar: 0, lead: "flute", pad: 0.5, creak: 1 }, // Wren's ship: an old sea song, the hull creaking
    ama:    { s: "hills", k: 0.8, drums: "none", bass: 0.4, mar: 0, lead: "flute", pad: 0.6 },          // Ama's house: the old chant, slow, on a flute
    canoe:  { s: "tinroof", k: 0.82, drums: "soft", bass: 0.6, mar: 0, lead: "pluck", knock: 1 },       // Kiko's canoe: a guitar and a mallet on wood
    stone:  { s: "hills", k: 0.7, drums: "none", bass: 0, mar: 0, lead: "bell", pad: 0.7, sparse: 1 },  // the Tide Stone: the chant in bells, the sea behind
    drums:  { s: "hills", k: 1, drums: "hand", bass: 0.9, mar: 0, lead: "flute", conga: 1 },             // the hill drums: the drums carry the song
    circle: { s: "hills", k: 0.9, drums: "soft", bass: 0.6, mar: 0, lead: "pan", pad: 0.8, soft: 1 },    // the stone circle: quiet, everyone listening
    grotto: { s: "survey", k: 0.6, drums: "none", bass: 0.3, mar: 0, lead: "bell", pad: 0.9, sparse: 1, drip: 1 }, // the cave: bells and dripping water
  };
  /* the arrangement playing now: the place's own, or on the radio the song's own (a touch brighter at the station) */
  function styleNow() {
    const y = STYLES[S.place] || STYLES.island, a = !y.s && (SONGS[S.song] || {}).air;
    return a ? Object.assign({ k: 1 }, a, S.place === "radio" ? { hat: a.drums === "full" ? 1 : 0, k: (a.k || 1) * 1.04 } : {}) : y;
  }
  const songOf = pl => (STYLES[pl] && STYLES[pl].s) || PLAYLIST[S.pl % PLAYLIST.length];
  const stepOf = y => 60 / (SONGS[S.song] || SONGS.coco).bpm / 4 / (y.k || 1);
  function play(bar, st, t) {
    const y = S.y || styleNow(), so = SONGS[S.song] || SONGS.coco, b = bar % 16, h = so.harm[b], ch = so.ch[Array.isArray(h) ? (st < 8 ? h[0] : h[1]) : h], dt = stepOf(y);
    /* drums */
    if (y.drums === "full") {
      hit(t, "shaker", st % 2 ? 0.6 : (st % 4 === 2 ? 1.2 : 0.8));
      if (st === 0 || st === 8) hit(t, "kick", 0.8);
      if (st === 6 || st === 14) hit(t, "conga", 0.9); if (st === 7 || st === 15 || st === 3) hit(t, "congaHi", 0.6);
      if (y.conga && (st === 10 || st === 11)) hit(t, "congaHi", 0.5);
      if (CLAVE[bar % 2].includes(st)) hit(t, "clave");
    }
    if (y.drums === "soft" && st % 4 === 2) hit(t, "shaker", 0.7);
    if (y.drums === "bossa") { if (st === 0 || st === 8) hit(t, "kick", 0.55); if ([0, 3, 6, 10, 13].includes(st) && bar % 2 === 0 || [2, 6, 10].includes(st) && bar % 2) hit(t, "rim", 0.8); if (st % 2 === 0) hit(t, "shaker", 0.5); if (y.conga && (st === 6 || st === 14)) hit(t, "conga", 0.5); }
    if (y.drums === "march") { if (st === 0) hit(t, "timp", 1); if (st === 8) hit(t, "timp", 0.7); if (st === 12 || st === 14) hit(t, "snare", st === 12 ? 0.6 : 0.4); }
    /* reggae: the kick and the rim together on the third beat, nothing on the one */
    if (y.drums === "onedrop") { if (st === 8) { hit(t, "kick", 0.9); hit(t, "rim", 1); } if (st % 2 === 0) hit(t, "hat", st % 4 === 2 ? 0.9 : 0.5); if (st === 14 && bar % 4 === 3) hit(t, "snare", 0.5); }
    /* soca: four on the floor, a snare on two and four, the hi-hat between */
    if (y.drums === "soca") { if (st % 4 === 0) hit(t, "kick", 0.85); if (st === 4 || st === 12) hit(t, "snare", 0.6); if (st % 4 === 2) hit(t, "hat", 1); if (st === 3 || st === 11) hit(t, "congaHi", 0.6); if (st === 7 || st === 15) hit(t, "conga", 0.7); }
    /* mento: a shaker on every sixteenth and a rumba box (the bass) on the beat */
    if (y.drums === "mento") { hit(t, "shaker", st % 4 === 0 ? 1.1 : 0.55); if (st === 4 || st === 12) hit(t, "rim", 0.6); if (st === 6 || st === 14) hit(t, "conga", 0.6); }
    /* the hill drums: three drums talking across each other, three against four */
    if (y.drums === "hand") { if ([0, 6, 12].includes(st)) hit(t, "conga", 1); if ([3, 9, 15].includes(st)) hit(t, "congaHi", 0.8); if (st % 4 === 0) hit(t, "timp", st ? 0.35 : 0.6); if (st % 2) hit(t, "shaker", 0.4); if (bar % 4 === 3 && st >= 12) hit(t, "congaHi", 0.9); }
    /* the surveyors: a clockwork tick and a low clave */
    if (y.drums === "tick") { if (st % 2 === 0) hit(t, "rim", st % 8 ? 0.35 : 0.8); if (st === 0) hit(t, "kick", 0.5); if (CLAVE[bar % 2].includes(st)) hit(t, "clave", 0.6); }
    if (y.hat && st % 2 === 0) hit(t, "hat", st % 4 ? 0.6 : 1);
    if (y.agogo && [0, 3, 6, 8, 10].includes(st)) hit(t, st === 3 || st === 10 ? "agogoLo" : "agogo", 0.8);
    if (y.clap && (st === 4 || st === 12)) hit(t, "clap", 0.8);
    if (y.clank && (st === 6 || (st === 13 && bar % 2))) hit(t, "clank", 0.7);
    if (y.knock && (st === 0 || st === 10)) hit(t, "knock", st ? 0.6 : 0.9);
    if (y.bubble && st === 0 && bar % 2 === 0) bubbles(t);
    if (y.creak && st === 0 && bar % 4 === 1) creak(t);
    if (y.drip && st === 4 && bar % 3 === 0) drip(t + Math.random() * dt * 6);
    /* bass: the calypso bounce, the reggae drop, the mento box, or only the roots where the place is quiet */
    const BASS = y.drums === "full" || y.drums === "soca" ? { 0: [1, 3], 3: [1, 1], 6: [2, 2], 8: [1, 3], 11: [1, 1], 14: [2, 2] }
      : y.drums === "onedrop" ? { 0: [1, 4], 6: [1, 2], 8: [2, 3], 11: [1, 1], 12: [2, 3] }
      : y.drums === "mento" || y.drums === "hand" ? { 0: [1, 2], 4: [2, 2], 8: [1, 2], 12: [2, 2] } : { 0: [1, 6], 8: [2, 6] };
    if (y.bass && BASS[st]) bass(t, ch[BASS[st][0]], BASS[st][1], y.bass);
    if (S.tense) return;   // a tense moment: drums and bass only
    if (y.pad && st === 0) pad(t, ch[0], dt * 16, y.pad);
    if (y.pad && st === 8 && Array.isArray(h)) pad(t, ch[0], dt * 8, y.pad);
    if (y.mar && st % 4 === 2) ch[0].forEach((m, i) => marimba(t + i * 0.008, m + 12, y.soft ? 0.035 : 0.05));
    if (y.arp && st % 2 === 0) { const n = ch[0][(st / 2) % ch[0].length]; marimba(t, n + (st >= 8 ? 24 : 12), 0.045); }
    if (y.strum && (st === 2 || st === 6 || st === 10 || st === 14)) strum(t, ch[0]);
    if (y.drums === "onedrop" && (st === 4 || st === 12)) strum(t, ch[0].map(m => m + 12), 0.5);   // the skank on the off beat
    if (y.drums === "mento" && st % 4 === 2) ch[0].forEach((m, i) => pluck(t + i * 0.01, m + 12, 0.03));   // the banjo
    /* the tune, on the voice of the place; the second time round lower, with a harmony a third under */
    for (const [s, m, d] of so.tune[b]) if (s === st) {
      if (y.sparse && d < 3) continue;
      const lap = Math.floor(bar / 16) % 2, mm = lap ? m - 12 : m;
      if (y.lead === "pan") { pan(t, mm, d * dt, y.soft ? 0.14 : 0.2); if (lap) pan(t + 0.01, m - 15 - (m % 12 === 9 ? 1 : 0), d * dt, 0.08); }
      if (y.lead === "bell") bell(t, m + 12, d * dt);
      if (y.lead === "brass") brass(t, m - 12, d * dt);
      if (y.lead === "flute") flute(t, m, d * dt);
      if (y.lead === "organ") organ(t, lap ? m - 12 : m, d * dt);
      if (y.lead === "pluck") pluck(t, m, 0.09);
      if (y.lead === "mar") { marimba(t, m + 12, 0.11); if (d >= 4) marimba(t + dt * 2, m + 12, 0.06); }
    }
  }
  function organ(t, m, dur) {   // a church organ that wandered into a coconut factory: three drawbars and a wobble
    const c = S.ctx, g = c.createGain(), vib = c.createOscillator(), vg = c.createGain(); vib.frequency.value = 6; vg.gain.value = 3;
    vib.connect(vg);
    [[1, 0.05], [2, 0.03], [3, 0.015]].forEach(([r, a]) => { const o = c.createOscillator(); o.frequency.value = hz(m) * r; vg.connect(o.frequency); const og = c.createGain(); og.gain.value = a; o.connect(og); og.connect(g); o.start(t); o.stop(t + dur + 0.2); });
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(1, t + 0.02); g.gain.setValueAtTime(1, t + Math.max(0.03, dur - 0.04)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.12);
    g.connect(S.music); vib.start(t); vib.stop(t + dur + 0.2);
  }
  function pluck(t, m, v) {   // a plucked string: a bright saw that closes fast
    const c = S.ctx, o = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = "sawtooth"; o.frequency.value = hz(m); f.type = "lowpass"; f.frequency.setValueAtTime(3200, t); f.frequency.exponentialRampToValueAtTime(500, t + 0.25);
    env(g, t, 0.002, v, 0.45); o.connect(f); f.connect(g); g.connect(S.music); o.start(t); o.stop(t + 0.6);
  }
  function bubbles(t) {   // air from a diver, rising
    const c = S.ctx;
    for (let i = 0; i < 5; i++) { const o = c.createOscillator(), g = c.createGain(), at = t + i * 0.09 + Math.random() * 0.05, f0 = 500 + Math.random() * 500; o.frequency.setValueAtTime(f0, at); o.frequency.exponentialRampToValueAtTime(f0 * 2.2, at + 0.06); env(g, at, 0.003, 0.025, 0.06); o.connect(g); g.connect(S.amb); o.start(at); o.stop(at + 0.1); }
  }
  function creak(t) {   // an old hull settling
    const c = S.ctx, o = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = "sawtooth"; o.frequency.setValueAtTime(70, t); o.frequency.linearRampToValueAtTime(95, t + 0.6); f.type = "bandpass"; f.frequency.value = 600; f.Q.value = 8;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.05, t + 0.2); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.7); o.connect(f); f.connect(g); g.connect(S.amb); o.start(t); o.stop(t + 0.8);
  }
  function drip(t) {   // a drop in a cave
    const c = S.ctx, o = c.createOscillator(), g = c.createGain(); o.frequency.setValueAtTime(1400 + Math.random() * 600, t); o.frequency.exponentialRampToValueAtTime(500, t + 0.08);
    env(g, t, 0.002, 0.06, 0.12); o.connect(g); g.connect(S.rev); g.connect(S.amb); o.start(t); o.stop(t + 0.2);
  }
  function pad(t, notes, dur, v) {   // a soft organ: two detuned sines per note, slow in and out
    const c = S.ctx;
    notes.forEach(m => [0, 7].forEach(dn => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m); o.detune.value = dn; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.03 * v, t + 0.4); g.gain.setValueAtTime(0.03 * v, t + Math.max(0.5, dur - 0.4)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.3); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + dur + 0.4); }));
  }
  function bell(t, m, dur) {   // a glass bell: inharmonic partials, a long ring
    const c = S.ctx;
    [[1, 0.12, 2.2], [2.76, 0.05, 1.2], [5.4, 0.025, 0.6]].forEach(([r, a, d]) => { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = hz(m) * r; env(g, t, 0.003, a, d + dur * 0.4); o.connect(g); g.connect(S.music); o.start(t); o.stop(t + d + dur + 0.2); });
  }
  function brass(t, m, dur) {   // a small brass band: a filtered saw that opens as it speaks
    const c = S.ctx, o = c.createOscillator(), o2 = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain();
    o.type = o2.type = "sawtooth"; o.frequency.value = hz(m); o2.frequency.value = hz(m); o2.detune.value = 8;
    f.type = "lowpass"; f.frequency.setValueAtTime(500, t); f.frequency.linearRampToValueAtTime(1800, t + 0.08); f.frequency.linearRampToValueAtTime(1100, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.07, t + 0.04); g.gain.setValueAtTime(0.06, t + Math.max(0.05, dur - 0.05)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.15);
    o.connect(f); o2.connect(f); f.connect(g); g.connect(S.music); o.start(t); o2.start(t); o.stop(t + dur + 0.2); o2.stop(t + dur + 0.2);
  }
  function flute(t, m, dur) {   // a wooden flute: a sine with breath and a late vibrato
    const c = S.ctx, o = c.createOscillator(), g = c.createGain(), vib = c.createOscillator(), vg = c.createGain();
    o.frequency.value = hz(m); vib.frequency.value = 5; vg.gain.setValueAtTime(0, t); vg.gain.linearRampToValueAtTime(5, t + Math.min(0.5, dur)); vib.connect(vg); vg.connect(o.frequency);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.09, t + 0.06); g.gain.setValueAtTime(0.08, t + Math.max(0.07, dur - 0.05)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.25);
    o.connect(g); g.connect(S.music); o.start(t); vib.start(t); o.stop(t + dur + 0.3); vib.stop(t + dur + 0.3);
    const n = c.createBufferSource(), nf = c.createBiquadFilter(), ng = c.createGain(); n.buffer = S.noise; nf.type = "bandpass"; nf.frequency.value = hz(m) * 2; nf.Q.value = 2; env(ng, t, 0.02, 0.012, 0.12); n.connect(nf); nf.connect(ng); ng.connect(S.music); n.start(t, Math.random()); n.stop(t + 0.2);
  }
  function strum(t, notes, k = 1) {   // a nylon guitar, strummed down
    const c = S.ctx;
    [...notes, notes[0] + 12].forEach((m, i) => { const o = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain(); o.type = "sawtooth"; o.frequency.value = hz(m); f.type = "lowpass"; f.frequency.value = 1400; env(g, t + i * 0.012, 0.003, 0.028 * k, 0.3 * k); o.connect(f); f.connect(g); g.connect(S.music); o.start(t + i * 0.012); o.stop(t + i * 0.012 + 0.45); });
  }
  function tick() {
    if (!S.ctx || !S.on) return;
    /* a break between two songs: the band is silent until gap() lets the next song in */
    if (S.gap) { if (S.placeT === S.place) { S.next = S.ctx.currentTime + 0.12; return; } S.gap = null; S.pl++; S.song = songOf(S.place); S.bar = 0; S.step = 15; }
    while (S.next < S.ctx.currentTime + 0.12) {
      const y = S.y || (S.y = styleNow()), d = stepOf(y), t = S.next + (S.step % 2 ? d * SWING : 0);
      play(S.bar, S.step, t);
      S.next += d; S.step++;
      if (S.step === 16) {
        S.step = 0; S.bar++;
        /* a new place: its own song from the top; on the radio, the next song after two times round */
        if (S.placeT !== S.place) { S.place = S.placeT; const so = songOf(S.place); if (so !== S.song) { S.song = so; S.bar = 0; } else S.bar -= S.bar % 4; }
        else if (!(STYLES[S.place] || {}).s && S.bar >= 32) { S.y = styleNow(); gap(); return; }
        S.y = styleNow();
      }
    }
  }
  /* ---------- between two songs on the radio ----------
     the band stops after the song's last bar: its home chord rings out over the sea, whoever runs the show (S.brk, set
     with onbreak: game.js on the island, assets/radio.js elsewhere) says a word, and the next song starts from the top.
     The word waits for a line Rico is still saying; with nobody to say anything there is a short pause. The handler
     returns (or resolves with) the seconds it talks; the break never lasts longer than two and a half minutes. */
  function gap() {
    const from = S.song, to = PLAYLIST[(S.pl + 1) % PLAYLIST.length], g = S.gap = { from, to, at: S.ctx.currentTime };
    ringOut(S.next, SONGS[from] || SONGS.coco);
    const go = () => { if (S.gap !== g) return; S.gap = null; S.pl++; S.song = songOf(S.place); S.bar = 0; S.step = 0; if (S.ctx) S.next = S.ctx.currentTime + 0.2; S.y = styleNow(); };
    const later = secs => setTimeout(go, Math.max(1.4, (+secs || 0) + 0.7) * 1000);
    setTimeout(go, 150000);
    let waited = 0;
    const ask = () => {
      if (S.gap !== g) return;
      if (S.talking && waited < 20) { waited += 0.4; return setTimeout(ask, 400); }   // Rico finishes his sentence first
      if (!S.brk || !S.on) return later(0);
      let r; try { r = S.brk({ from, to, name: (SONGS[to] || {}).name || "" }); } catch (e) { r = 0; }
      Promise.resolve(r).then(later, () => later(0));
    };
    setTimeout(ask, 900);   // after the last chord has spoken
  }
  function ringOut(t, so) {   // the song's last chord, held and fading, a touch of reverb
    const c = S.ctx, h = so.harm[so.harm.length - 1], ch = so.ch[Array.isArray(h) ? h[h.length - 1] : h];
    if (!c || !ch) return;
    t = Math.max(t, c.currentTime);
    [...ch[0], ch[1]].forEach((m, i) => {
      const o = c.createOscillator(), g = c.createGain(); o.type = i === ch[0].length ? "triangle" : "sine"; o.frequency.value = hz(m);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(i === ch[0].length ? 0.09 : 0.035, t + 0.04); g.gain.exponentialRampToValueAtTime(0.0001, t + 3.2);
      o.connect(g); g.connect(S.music); o.start(t); o.stop(t + 3.3);
    });
  }
  /* ---------- small sounds for the game ---------- */
  function sfx(name) {
    if (!S.ctx || !S.on) return;
    const c = S.ctx, t = c.currentTime;
    const tone = (f, at, d, v = 0.12, type = "sine") => { const o = c.createOscillator(), g = c.createGain(); o.type = type; o.frequency.value = f; env(g, t + at, 0.005, v, d); o.connect(g); g.connect(S.master); o.start(t + at); o.stop(t + at + d + 0.1); };
    if (name === "tap") tone(1320, 0, 0.06, 0.05);
    if (name === "open") { tone(784, 0, 0.12, 0.06); tone(1175, 0.06, 0.16, 0.05); }
    if (name === "coin") { tone(1568, 0, 0.08, 0.08, "square"); tone(2093, 0.07, 0.2, 0.06, "square"); }
    if (name === "yes") { tone(523, 0, 0.18, 0.1); tone(659, 0.09, 0.18, 0.1); tone(784, 0.18, 0.4, 0.1); }
    if (name === "no") { tone(220, 0, 0.3, 0.14, "triangle"); tone(185, 0.12, 0.4, 0.12, "triangle"); }
    if (name === "stamp") { const n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "lowpass"; f.frequency.value = 900; env(g, t, 0.002, 0.5, 0.12); n.connect(f); f.connect(g); g.connect(S.master); n.start(t); n.stop(t + 0.2); }
    if (name === "cheer") { for (let i = 0; i < 4; i++) { const n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 900 + i * 500; f.Q.value = 1.4; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.06, t + 0.3 + i * 0.1); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.4); n.connect(f); f.connect(g); g.connect(S.master); n.start(t, i * 0.3); n.stop(t + 2.6); } [0, 0.15, 0.3].forEach((a, i) => pan(t + a, [77, 81, 84][i], 0.5, 0.18)); }
    if (name === "glitch") { for (let i = 0; i < 6; i++) tone(200 + Math.random() * 1800, i * 0.035, 0.03, 0.05, "square"); }
    if (name === "jingle") { [[0, 77], [0.11, 81], [0.22, 84], [0.4, 89]].forEach(([a, m], i) => pan(t + a, m, i === 3 ? 0.5 : 0.12, 0.1)); }
    /* the morning show starts: a snare roll that grows, a run up the steel pan, three blasts of the station horn, a crash,
       and the band comes in from the top of the next song */
    if (name === "wake") {
      for (let i = 0; i < 18; i++) { const at = i * 0.055, n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "bandpass"; f.frequency.value = 2400; f.Q.value = 0.9; env(g, t + at, 0.002, 0.02 + i * 0.006, 0.06); n.connect(f); f.connect(g); g.connect(S.master); n.start(t + at, Math.random()); n.stop(t + at + 0.1); }
      [65, 69, 72, 77, 81, 84, 89].forEach((m, i) => pan(t + 0.3 + i * 0.07, m, 0.1, 0.12));
      [1.05, 1.3, 1.55].forEach((at, i) => { [0, 7, -5].forEach(dn => { const o = c.createOscillator(), f = c.createBiquadFilter(), g = c.createGain(); o.type = "sawtooth"; o.frequency.setValueAtTime(hz(i === 2 ? 70 : 69), t + at); o.frequency.linearRampToValueAtTime(hz(i === 2 ? 70 : 69) * 0.94, t + at + (i === 2 ? 0.5 : 0.2)); o.detune.value = dn; f.type = "lowpass"; f.frequency.value = 2600; g.gain.setValueAtTime(0.0001, t + at); g.gain.exponentialRampToValueAtTime(0.045, t + at + 0.02); g.gain.setValueAtTime(0.04, t + at + (i === 2 ? 0.45 : 0.16)); g.gain.exponentialRampToValueAtTime(0.0001, t + at + (i === 2 ? 0.6 : 0.22)); o.connect(f); f.connect(g); g.connect(S.master); o.start(t + at); o.stop(t + at + 0.7); }); });
      { const n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain(); n.buffer = S.noise; f.type = "highpass"; f.frequency.value = 3000; env(g, t + 2.15, 0.003, 0.12, 1.4); n.connect(f); f.connect(g); g.connect(S.master); g.connect(S.rev); n.start(t + 2.15); n.stop(t + 3.7); }
      hit(t + 2.15, "kick", 1.2); hit(t + 2.15, "timp", 1);
      S.next = Math.max(S.next, t + 2.15); S.bar = 0; S.step = 0;
    }
    if (name === "meow") { const o = c.createOscillator(), g = c.createGain(), f = c.createBiquadFilter(); o.type = "sawtooth"; f.type = "bandpass"; f.frequency.value = 1100; f.Q.value = 3; o.frequency.setValueAtTime(520, t); o.frequency.linearRampToValueAtTime(780, t + 0.18); o.frequency.linearRampToValueAtTime(420, t + 0.5); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.07, t + 0.06); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.55); o.connect(f); f.connect(g); g.connect(S.master); o.start(t); o.stop(t + 0.6); }
  }
  /* ---------- the mix ---------- */
  const want = { music: 1, radio: false, tense: false, amb: 1, place: null };
  function apply() {
    if (!S.ctx) return;
    const t = S.ctx.currentTime;
    S.music.gain.setTargetAtTime(S.on ? 0.55 * want.music * (S.duck ? 0.3 : 1) : 0, t, S.duck ? 0.15 : 0.4);
    S.amb.gain.setTargetAtTime(S.on ? want.amb : 0, t, 0.6);
    S.radio.type = want.radio ? "bandpass" : "allpass"; S.radio.frequency.value = 1400; S.radio.Q.value = want.radio ? 0.9 : 0.0001;
    S.tense = want.tense;
    /* a new place: the band changes at the next bar; when the change comes from far, it starts within half a bar */
    const pl = want.place && STYLES[want.place] ? want.place : "island";
    if (pl !== S.placeT) { S.placeT = pl; if (S.step >= 8 || S.place === "island" || pl === "island") { S.step = 15; } }
  }
  function start() {
    if (!S.want) return false;
    try {
      if (!S.ctx) { build(); S.ctx.onstatechange = () => S.cb && S.cb(); }
      S.on = true; apply();
      if (S.ctx.state !== "running") S.ctx.resume().then(() => S.cb && S.cb(), () => {});
      return S.ctx.state === "running";
    } catch (e) { return false; }
  }
  /* a voice (rico.js): the clips one after the other, after the jingle, through a small-radio colour; the music
     steps back while someone talks. Resolves with how many seconds they will talk. */
  async function speak(bufs, o = {}) {
    if (!S.ctx || !S.on) return false;
    const c = S.ctx, list = [];
    // a clip is an ArrayBuffer, or { b, tel, who } for a caller heard through the telephone
    /* the callback form as well: older WebKit (iPhones before iOS 14.1) never resolves the promise form */
    const decode = b => new Promise((ok, no) => { try { const p = c.decodeAudioData(b, ok, no); if (p && p.then) p.then(ok, no); } catch (e) { no(e); } });
    for (const b of bufs) { try { list.push({ buf: await decode(b.b || b), tel: !!b.tel, who: b.who }); } catch (e) { S.why = "decode"; return false; } }
    if (c.state !== "running") { try { await c.resume(); } catch (e) {} }
    if (!S.voice) {
      const hp = c.createBiquadFilter(), pk = c.createBiquadFilter(), g = c.createGain(), comp = c.createDynamicsCompressor();
      hp.type = "highpass"; hp.frequency.value = 160; pk.type = "peaking"; pk.frequency.value = 2600; pk.Q.value = 0.8; pk.gain.value = 3;
      comp.threshold.value = -20; comp.ratio.value = 3; g.gain.value = 1.1;
      hp.connect(pk); pk.connect(comp); comp.connect(g); g.connect(S.master); S.voice = hp;
    }
    /* a line on air (a rumour you paid for) is heard to its end: whoever speaks next waits for it */
    const onAir = c.currentTime < (S.airEnd || 0);
    if (S.talking && !onAir) S.talking.forEach(n => { try { n.stop(); } catch (e) {} });
    let at = onAir ? S.airEnd + 0.4 : c.currentTime + 0.55; S.talking = [];
    if (!S.tel && list.some(x => x.tel)) {
      const lo = c.createBiquadFilter(), hi = c.createBiquadFilter(), drive = c.createWaveShaper(), curve = new Float32Array(256);
      for (let i = 0; i < 256; i++) { const x = i / 128 - 1; curve[i] = Math.tanh(2.2 * x); }
      hi.type = "highpass"; hi.frequency.value = 320; lo.type = "lowpass"; lo.frequency.value = 3200; drive.curve = curve;
      hi.connect(lo); lo.connect(drive); drive.connect(S.voice); S.tel = hi;
    }
    /* each clip goes through a meter on its way out, so a face can open its mouth when the voice is loud and shut it in
       the pauses (lip()); a clip remembers whose voice it is and when it plays */
    if (!S.meter) S.meter = { voice: meter(c, S.voice), tel: null, clips: [], peak: {} };
    if (list.some(x => x.tel) && !S.meter.tel) S.meter.tel = meter(c, S.tel);
    const said = [];
    for (const { buf, tel, who } of list) {
      const n = c.createBufferSource(); n.buffer = buf; n.connect(tel ? S.meter.tel.node : S.meter.voice.node); n.start(at); S.talking.push(n);
      said.push({ who: tel ? who || "" : o.who || "", bus: tel ? "tel" : "voice", a: at, b: at + buf.duration });
      at += buf.duration + (tel ? 0.45 : 0.18);
    }
    S.meter.clips = onAir ? S.meter.clips.filter(k => k.b > c.currentTime).concat(said) : said;   // the ones stopped above are gone
    if (o.air) S.airEnd = at;
    S.duck = true; apply();
    const mine = S.talking;
    const secs = at - c.currentTime;
    setTimeout(() => { if (S.talking === mine) { S.duck = false; S.talking = null; apply(); } }, secs * 1000);
    return secs;
  }
  /* a meter: an analyser in front of a bus */
  function meter(c, bus) {
    const a = c.createAnalyser(); a.fftSize = 1024; a.smoothingTimeConstant = 0; a.connect(bus);
    return { node: a, data: new Uint8Array(a.fftSize), at: -1, rms: 0 };
  }
  function loud(m, now) {   // how loud the bus is right now (once per frame)
    if (m.at === now) return m.rms;
    m.node.getByteTimeDomainData(m.data); let e = 0;
    for (let i = 0; i < m.data.length; i++) { const v = (m.data[i] - 128) / 128; e += v * v; }
    m.at = now; return (m.rms = Math.sqrt(e / m.data.length));
  }
  /* how far someone's mouth is open, 0 (shut) to 1, from their own voice as it is heard: null when no clip of theirs
     is playing or waiting, so the face falls back to its drawn talking; 0 between clips, before the first, and in
     every pause inside a clip */
  const LIP = {};
  function lip(id) {
    const M = S.meter, c = S.ctx;
    if (!c || !id) return null;
    const now = c.currentTime - (c.outputLatency || c.baseLatency || 0);   // what the ear hears now, not what was just sent
    const mine = M ? M.clips.filter(k => k.who === id && k.b > now - 0.05) : [];
    if (!mine.length) return S.expect && S.expect.has(id) ? 0 : null;   // a clip on its way: shut until it plays
    const k = mine.find(k => k.a <= now && now < k.b), L = LIP[id] || (LIP[id] = { v: 0, t: 0 });
    let want = 0;
    if (k && M[k.bus]) {
      const r = loud(M[k.bus], c.currentTime), p = M.peak[id] = Math.max(0.04, r, (M.peak[id] || 0.12) * 0.997);   // each voice against its own loudest
      want = Math.max(0, Math.min(1, (r / p - 0.1) / 0.6));
    }
    const dt = Math.min(0.1, Math.max(0, c.currentTime - L.t)); L.t = c.currentTime;
    L.v += (want - L.v) * Math.min(1, dt * (want > L.v ? 40 : 22));   // opens fast, shuts a little slower
    return L.v;
  }
  /* a line in someone's voice is being fetched: their mouth stays shut until it plays */
  function expect(id, on) { S.expect = S.expect || new Set(); if (on) S.expect.add(id); else S.expect.delete(id); }
  /* whoever is talking stops (a card closed) */
  function hush() {
    if (S.ctx && S.ctx.currentTime < (S.airEnd || 0)) return;   // a line on air finishes
    if (S.meter) S.meter.clips = [];
    if (S.talking) S.talking.forEach(n => { try { n.stop(); } catch (e) {} });
    S.talking = null; if (S.duck) { S.duck = false; apply(); }
  }
  window.COVE_SOUND = {
    start, sfx, speak, hush, lip, expect,
    /* on: the music is really playing (a browser lets it start only after the first click, tap or key) */
    get on() { return S.on && !!S.ctx && S.ctx.state === "running"; }, get talking() { return !!S.talking; }, get wanted() { return S.want; },
    get state() { return S.ctx ? S.ctx.state : "none"; },
    /* the song playing now (its name for the radio strip), and the songbook */
    get song() { return { id: S.song, name: (SONGS[S.song] || {}).name || "" }; }, songs: Object.keys(SONGS), get why() { return S.why || ""; },
    set onchange(f) { S.cb = f; },
    /* between two songs on the radio: f({ from, to, name }) says something and returns the seconds it talks */
    set onbreak(f) { S.brk = f; }, get gap() { return S.gap ? { from: S.gap.from, to: S.gap.to } : null; },
    set(o) { Object.assign(want, o); apply(); },
    /* remember: the choice is kept for this tab (the game's own buttons); the site's radio passes false, its switch is its own */
    toggle(remember = true) {
      S.want = !S.want; if (remember) try { sessionStorage.setItem(MEM, S.want ? "on" : "off"); } catch (e) {}
      if (S.want) start(); else { S.on = false; if (S.talking) S.talking.forEach(n => { try { n.stop(); } catch (e) {} }); S.talking = null; if (S.meter) S.meter.clips = []; S.duck = false; apply(); }
      return S.want;
    },
  };
})();
