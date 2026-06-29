import csv, os

# --- copied verbatim from pilot5_0.py (make_latin_square_cue_mapping) ---
def make_latin_square_cue_mapping(participantNumber, nConditions=6):
    try:
        participantNumber = int(participantNumber)
    except Exception:
        participantNumber = sum(ord(ch) for ch in str(participantNumber))

    latinSquareRow = (participantNumber - 1) % nConditions
    latinSquareCycle = (participantNumber - 1) // nConditions

    mapping = {}
    for conditionIndex in range(nConditions):
        cueIdentity = ((conditionIndex + latinSquareRow) % nConditions) + 1
        mapping[conditionIndex] = cueIdentity

    return mapping, latinSquareRow + 1, latinSquareCycle + 1
# --- end verbatim ---

COND_HEADERS = ["cond0_1p_FR1","cond1_1p_FR5","cond2_1p_FR10",
                "cond3_5p_FR1","cond4_5p_FR5","cond5_5p_FR10"]

outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "latin_python.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["participant","row","cycle"] + COND_HEADERS)
    for p in range(1, 51):
        mapping, row, cycle = make_latin_square_cue_mapping(p)
        w.writerow([p, row, cycle] + [mapping[c] for c in range(6)])
print("wrote latin_python.csv")
