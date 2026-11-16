// Dumps the voice line catalogue (single source of truth: js/voice.js) to tools/tts/lines.json for build_vo.py.
// Usage: node tools/tts/export_lines.js
'use strict';
const fs = require('fs');
const path = require('path');
global.window = global.window || {};
require(path.join(__dirname, '..', '..', 'js', 'voice.js'));
const V = window.SGS.Voice;
const lines = V.exportLines();
fs.writeFileSync(path.join(__dirname, 'lines.json'), JSON.stringify({ speakers: V.speakers, lines }, null, 1) + '\n');
console.log('wrote tools/tts/lines.json: ' + lines.length + ' lines, ' + V.speakers.length + ' speakers');
