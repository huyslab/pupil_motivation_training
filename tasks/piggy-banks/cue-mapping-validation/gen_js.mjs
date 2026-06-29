import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// --- copied verbatim from tasks/piggy-banks/vigour-utils.js ---
const VIGOUR_N_CUE_IDENTITIES = 6;

function vigourLatinSquareMapping(participantNumber, nConditions = VIGOUR_N_CUE_IDENTITIES) {
  const row = (((participantNumber - 1) % nConditions) + nConditions) % nConditions;
  const cycle = Math.floor((participantNumber - 1) / nConditions);
  const mapping = {};
  for (let c = 0; c < nConditions; c++) {
    mapping[c] = ((c + row) % nConditions) + 1;
  }
  return { mapping, row: row + 1, cycle: cycle + 1 };
}
// --- end verbatim ---

const COND_HEADERS = ["cond0_1p_FR1","cond1_1p_FR5","cond2_1p_FR10",
                      "cond3_5p_FR1","cond4_5p_FR5","cond5_5p_FR10"];

const rows = [["participant","row","cycle",...COND_HEADERS].join(",")];
for (let p = 1; p <= 50; p++) {
  const { mapping, row, cycle } = vigourLatinSquareMapping(p);
  const cues = [];
  for (let c = 0; c < 6; c++) cues.push(mapping[c]);
  rows.push([p, row, cycle, ...cues].join(","));
}
const outdir = dirname(fileURLToPath(import.meta.url));
writeFileSync(join(outdir, "latin_js.csv"), rows.join("\n") + "\n");
console.log("wrote latin_js.csv");
