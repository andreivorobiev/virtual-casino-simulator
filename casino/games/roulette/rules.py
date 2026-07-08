# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Set RED_NUMBERS to the value needed for the next operation.
RED_NUMBERS = {"1","3","5","7","9","12","14","16","18","19","21","23","25","27","30","32","34","36"}
# Set BLACK_NUMBERS to the value needed for the next operation.
BLACK_NUMBERS = {str(n) for n in range(1,37)} - RED_NUMBERS
# Set SINGLE_ZERO_WHEEL to the value needed for the next operation.
SINGLE_ZERO_WHEEL = ["0","32","15","19","4","21","2","25","17","34","6","27","13","36","11","30","8","23","10","5","24","16","33","1","20","14","31","9","22","18","29","7","28","12","35","3","26"]
# Set DOUBLE_ZERO_WHEEL to the value needed for the next operation.
DOUBLE_ZERO_WHEEL = ["0","28","9","26","30","11","7","20","32","17","5","22","34","15","3","24","36","13","1","00","27","10","25","29","12","8","19","31","18","6","21","33","16","4","23","35","14","2"]

# Define the color_of function used by this module.
def color_of(n: str) -> str:
    # Branch when the following condition is true.
    if n in ("0", "00", "000"):
        # Return the computed value to the caller.
        return "green"
    # Return the computed value to the caller.
    return "red" if n in RED_NUMBERS else "black"

# Define the roulette_numbers function used by this module.
def roulette_numbers(mode: str = "double") -> list[str]:
    # Return the computed value to the caller.
    return ["0"] + (["00"] if mode == "double" else []) + [str(n) for n in range(1,37)]

# Define the wheel function used by this module.
def wheel(mode: str = "double") -> list[str]:
    # Return the computed value to the caller.
    return DOUBLE_ZERO_WHEEL if mode == "double" else SINGLE_ZERO_WHEEL

# Define the dozen function used by this module.
def dozen(n: str) -> int | None:
    # Branch when the following condition is true.
    if not n.isdigit() or n == "0": return None
    # Set i to the value needed for the next operation.
    i = int(n)
    # Return the computed value to the caller.
    return 1 if 1 <= i <= 12 else 2 if 13 <= i <= 24 else 3 if 25 <= i <= 36 else None

# Define the column function used by this module.
def column(n: str) -> int | None:
    # Branch when the following condition is true.
    if not n.isdigit() or n == "0": return None
    # Set i to the value needed for the next operation.
    i = int(n)
    # Return the computed value to the caller.
    return ((i - 1) % 3) + 1

# Define the catalog function used by this module.
def catalog(mode: str = "double") -> list[dict]:
    # Set bets to the value needed for the next operation.
    bets = []
    # Set seen to the value needed for the next operation.
    seen = set()
    # Define the add function used by this module.
    def add(bet_type, label, covered, net, layout="catalog"):
        # Set covered to the value needed for the next operation.
        covered = [str(x) for x in covered]
        # Set key to the value needed for the next operation.
        key = (bet_type, tuple(sorted(covered, key=lambda x: (x not in ('0','00'), int(x) if x.isdigit() else -1, x))))
        # Branch when the following condition is true.
        if key in seen:
            # Return the computed value to the caller.
            return
        # Execute this statement as part of the module's documented control flow.
        seen.add(key)
        # Execute this statement as part of the module's documented control flow.
        bets.append({"id": f"{bet_type}_{'_'.join(covered)}", "type": bet_type, "label": label, "covered_numbers": covered, "net_payout": net, "total_return_multiplier": net+1, "layout_kind": layout})
    # Set nums to the value needed for the next operation.
    nums = roulette_numbers(mode)
    # Iterate through the collection to process each item.
    for n in nums:
        # Execute this statement as part of the module's documented control flow.
        add("straight", n, [n], 35, "cell")
    # Table-number row splits, streets, vertical splits, lines, and corners.
    # Iterate through the collection to process each item.
    for row_start in range(1, 37, 3):
        # Set row to the value needed for the next operation.
        row = [str(row_start), str(row_start+1), str(row_start+2)]
        # Execute this statement as part of the module's documented control flow.
        add("split", f"{row[0]}/{row[1]}", row[:2], 17, "edge")
        # Execute this statement as part of the module's documented control flow.
        add("split", f"{row[1]}/{row[2]}", row[1:], 17, "edge")
        # Execute this statement as part of the module's documented control flow.
        add("street", f"{row[0]}-{row[2]}", row, 11, "row")
    # Iterate through the collection to process each item.
    for n in range(1, 34):
        # Execute this statement as part of the module's documented control flow.
        add("split", f"{n}/{n+3}", [str(n), str(n+3)], 17, "edge")
    # Iterate through the collection to process each item.
    for row_start in range(1, 34, 3):
        # Execute this statement as part of the module's documented control flow.
        add("line", f"{row_start}-{row_start+5}", [str(i) for i in range(row_start, row_start+6)], 5, "row_edge")
    # Iterate through the collection to process each item.
    for row_start in range(1, 34, 3):
        # Iterate through the collection to process each item.
        for col in [0,1]:
            # Set a to the value needed for the next operation.
            a = row_start + col
            # Set covered to the value needed for the next operation.
            covered = [str(a), str(a+1), str(a+3), str(a+4)]
            # Execute this statement as part of the module's documented control flow.
            add("corner", f"{covered[0]}/{covered[1]}/{covered[2]}/{covered[3]}", covered, 8, "intersection")
    # Zero-zone adjacency. Layouts vary slightly by table; we expose common zero splits/trios.
    # Branch when the following condition is true.
    if mode == "double":
        # Execute this statement as part of the module's documented control flow.
        add("zero_split", "0/00", ["0","00"], 17, "zero")
        # Iterate through the collection to process each item.
        for pair in [("0","1"),("0","2"),("00","2"),("00","3"),("0","3")]:
            # Execute this statement as part of the module's documented control flow.
            add("zero_split", f"{pair[0]}/{pair[1]}", list(pair), 17, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "0/00/2", ["0","00","2"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "00/2/3", ["00","2","3"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "0/1/2", ["0","1","2"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "00/2/3", ["00","2","3"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("top_line", "0/00/1/2/3", ["0","00","1","2","3"], 6, "zero")
    # Handle the fallback branch when prior conditions did not match.
    else:
        # Iterate through the collection to process each item.
        for pair in [("0","1"),("0","2"),("0","3")]:
            # Execute this statement as part of the module's documented control flow.
            add("zero_split", f"{pair[0]}/{pair[1]}", list(pair), 17, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "0/1/2", ["0","1","2"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("trio", "0/2/3", ["0","2","3"], 11, "zero")
        # Execute this statement as part of the module's documented control flow.
        add("first_four", "0/1/2/3", ["0","1","2","3"], 8, "zero")
    # Execute this statement as part of the module's documented control flow.
    add("snake", "Snake", ["1","5","9","12","14","16","19","23","27","30","32","34"], 2, "special")
    # Iterate through the collection to process each item.
    for d, rng in [("1st 12", range(1,13)), ("2nd 12", range(13,25)), ("3rd 12", range(25,37))]:
        # Execute this statement as part of the module's documented control flow.
        add("dozen", d, [str(i) for i in rng], 2, "outside")
    # Iterate through the collection to process each item.
    for c in [1,2,3]:
        # Execute this statement as part of the module's documented control flow.
        add("column", f"Column {c}", [str(i) for i in range(c,37,3)], 2, "outside")
    # Set add("red", "Red", sorted(RED_NUMBERS, key to the value needed for the next operation.
    add("red", "Red", sorted(RED_NUMBERS, key=int), 1, "outside")
    # Set add("black", "Black", sorted(BLACK_NUMBERS, key to the value needed for the next operation.
    add("black", "Black", sorted(BLACK_NUMBERS, key=int), 1, "outside")
    # Execute this statement as part of the module's documented control flow.
    add("odd", "Odd", [str(i) for i in range(1,37,2)], 1, "outside")
    # Execute this statement as part of the module's documented control flow.
    add("even", "Even", [str(i) for i in range(2,37,2)], 1, "outside")
    # Execute this statement as part of the module's documented control flow.
    add("low", "1-18", [str(i) for i in range(1,19)], 1, "outside")
    # Execute this statement as part of the module's documented control flow.
    add("high", "19-36", [str(i) for i in range(19,37)], 1, "outside")
    # Return the computed value to the caller.
    return bets

# Define the find_bet function used by this module.
def find_bet(mode: str, bet_type: str, covered_numbers: list[str] | None = None, bet_id: str | None = None) -> dict | None:
    # Set target_set to the value needed for the next operation.
    target_set = set(str(x) for x in (covered_numbers or []))
    # Iterate through the collection to process each item.
    for b in catalog(mode):
        # Branch when the following condition is true.
        if bet_id and b["id"] == bet_id:
            # Return the computed value to the caller.
            return b
        # Branch when the following condition is true.
        if b["type"] == bet_type and set(b["covered_numbers"]) == target_set:
            # Return the computed value to the caller.
            return b
    # Return the computed value to the caller.
    return None

# Define the expand_call_bet function used by this module.
def expand_call_bet(mode: str, call_type: str, amount: float, number: str | None = None) -> list[dict]:
    # Amount is per component bet; caller API debits each generated chip separately.
    # Set components to the value needed for the next operation.
    components = []
    # Define the comp function used by this module.
    def comp(bet_type, covered, label, chips=1):
        # Set b to the value needed for the next operation.
        b = find_bet(mode, bet_type, covered_numbers=[str(x) for x in covered])
        # Branch when the following condition is true.
        if b:
            # Execute this statement as part of the module's documented control flow.
            components.append({"type": b["type"], "covered_numbers": b["covered_numbers"], "label": label, "amount": round(float(amount)*chips, 2)})
    # Branch when the following condition is true.
    if call_type == "snake":
        # Set b to the value needed for the next operation.
        b = find_bet(mode, "snake", covered_numbers=["1","5","9","12","14","16","19","23","27","30","32","34"])
        # Branch when the following condition is true.
        if b: components.append({"type":"snake", "covered_numbers": b["covered_numbers"], "label":"Snake", "amount": amount})
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "tiers":
        # Iterate through the collection to process each item.
        for a,b in [(5,8),(10,11),(13,16),(23,24),(27,30),(33,36)]: comp("split", [a,b], f"Tiers {a}/{b}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "orphelins":
        # Execute this statement as part of the module's documented control flow.
        comp("straight", [1], "Orphelins 1")
        # Iterate through the collection to process each item.
        for pair in [(6,9),(14,17),(17,20),(31,34)]: comp("split", pair, f"Orphelins {pair[0]}/{pair[1]}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "jeu_zero":
        # Execute this statement as part of the module's documented control flow.
        comp("straight", [26], "Jeu Zero 26")
        # Iterate through the collection to process each item.
        for pair in [(0,3),(12,15),(32,35)]: comp("split" if pair[0] else "zero_split", pair, f"Jeu Zero {pair[0]}/{pair[1]}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "voisins":
        # Standard Voisins-style composition where the available table layout supports it.
        # Set comp("trio", [0,2,3], "Voisins 0/2/3", chips to the value needed for the next operation.
        comp("trio", [0,2,3], "Voisins 0/2/3", chips=2)
        # Iterate through the collection to process each item.
        for pair in [(4,7),(12,15),(18,21),(19,22),(32,35)]: comp("split", pair, f"Voisins {pair[0]}/{pair[1]}")
        # Set comp("corner", [25,26,28,29], "Voisins 25/26/28/29", chips to the value needed for the next operation.
        comp("corner", [25,26,28,29], "Voisins 25/26/28/29", chips=2)
        # On double-zero layouts where 0/2/3 may not be present, add straight safety coverage near zero.
        # Branch when the following condition is true.
        if not components or all(c["label"] != "Voisins 0/2/3" for c in components):
            # Iterate through the collection to process each item.
            for n in ["22","18","29","7","28","12","35","3","26","0","32","15","19","4","21","2","25"]:
                # Execute this statement as part of the module's documented control flow.
                comp("straight", [n], f"Voisins {n}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "neighbors":
        # Branch when the following condition is true.
        if number not in wheel(mode): return components
        # Set w to the value needed for the next operation.
        w = wheel(mode); idx = w.index(number); L=len(w)
        # Iterate through the collection to process each item.
        for off in [-2,-1,0,1,2]:
            # Set n to the value needed for the next operation.
            n = w[(idx+off)%L]; comp("straight", [n], f"Neighbor {n}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "final":
        # Branch when the following condition is true.
        if number is None or not str(number).isdigit(): return components
        # Set final to the value needed for the next operation.
        final = str(int(number) % 10)
        # Iterate through the collection to process each item.
        for n in [str(i) for i in range(1,37) if str(i).endswith(final)]: comp("straight", [n], f"Final {final}: {n}")
    # Branch when the prior condition failed and this condition is true.
    elif call_type == "complete":
        # Branch when the following condition is true.
        if number and number in roulette_numbers(mode):
            # Execute this statement as part of the module's documented control flow.
            comp("straight", [number], f"Complete {number}")
            # Iterate through the collection to process each item.
            for b in catalog(mode):
                # Branch when the following condition is true.
                if number in b["covered_numbers"] and b["type"] in {"split","zero_split","street","corner","line","trio","first_four","top_line"}:
                    # Execute this statement as part of the module's documented control flow.
                    components.append({"type": b["type"], "covered_numbers": b["covered_numbers"], "label": f"Complete {b['label']}", "amount": amount})
    # Return the computed value to the caller.
    return components
