#!/usr/bin/env python3
import argparse
import base64
import binascii
import re
import string
import sys
from typing import Tuple, Optional, Dict, List

COMMON_WORDS = {"the","be","to","of","and","a","in","that","have","i","it","for","not","on","with","he","as","you","do","at","this","but","his","by","from","they","we","say","her","she","or","an","will","my","one","all","would","there","their","what","so","up","out","if","about","who","get","which","go","me","like","just","now","then","when","your","can","time","no","into","than","could","over","new","only","other","see","two","first","also","even","use","made","make","way","well","our","because","any","these","most","us","right","left","round","baby","spin","youre","you","is","are","was","were","has","had","have"}

def clean_text_ratio(s: str) -> float:
    printable = set(string.printable)
    if not s:
        return 0.0
    return sum(ch in printable for ch in s) / len(s)

def englishy_score(s: str) -> float:
    s_l = s.lower()
    printable = clean_text_ratio(s)
    tokens = re.findall(r"[a-z']+", s_l)
    if not tokens:
        tokens = []
    if tokens:
        word_hits = sum(1 for t in tokens if t in COMMON_WORDS)
        word_ratio = word_hits / max(1, len(tokens))
    else:
        word_ratio = 0.0
    vowels = sum(s_l.count(v) for v in "aeiou") / max(1, len(s))
    letters = sum(c.isalpha() for c in s) / max(1, len(s))
    spaces = s.count(' ') / max(1, len(s))
    score = 0.45 * printable + 0.30 * word_ratio + 0.15 * vowels + 0.07 * letters + 0.03 * spaces
    return score

def write_output(cipher_type: str, content: str) -> str:
    safe = cipher_type.lower().replace(" ", "-")
    fname = f"{safe}dp.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    return fname

def rot47(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if 33 <= o <= 126:
            out.append(chr(33 + ((o - 33 + 47) % 94)))
        else:
            out.append(ch)
    return "".join(out)

def rot_n(s: str, n: int) -> str:
    def shift(c):
        if 'a' <= c <= 'z':
            return chr((ord(c) - 97 + n) % 26 + 97)
        if 'A' <= c <= 'Z':
            return chr((ord(c) - 65 + n) % 26 + 65)
        return c
    return "".join(shift(c) for c in s)

def atbash(s: str) -> str:
    def tr(c):
        if 'a' <= c <= 'z':
            return chr(122 - (ord(c) - 97))
        if 'A' <= c <= 'Z':
            return chr(90 - (ord(c) - 65))
        return c
    return "".join(tr(c) for c in s)

MORSE_MAP: Dict[str, str] = {".-":"A","-...":"B","-.-.":"C","-..":"D",".":"E","..-.":"F","--.":"G","....":"H","..":"I",".---":"J","-.-":"K",".-..":"L","--":"M","-.":"N","---":"O",".--.":"P","--.-":"Q",".-.":"R","...":"S","-":"T","..-":"U","...-":"V",".--":"W","-..-":"X","-.--":"Y","--..":"Z","-----":"0",".----":"1","..---":"2","...--":"3","....-":"4",".....":"5","-....":"6","--...":"7","---..":"8","----.":"9",".-.-.-":".","--..--":",","..--..":"?","-.-.--":"!",".-..-.":"\"","-....-":"-",".----.":"'", "-..-.":"/",".-.-.":"+","-.-.-.":";","-...-":"=","---...":":","..--.-":"_","-.--.":"(","-.--.-":")","...-..-":"$"}

def morse_decode(s: str) -> Optional[str]:
    s = s.strip()
    if not re.fullmatch(r"[.\-/\s]+", s):
        return None
    norm = re.sub(r"\s*/\s*", "   ", s)
    words = re.split(r"\s{3,}", norm)
    decoded_words = []
    for w in words:
        letters = re.split(r"\s+", w.strip())
        decoded_letters = []
        for code in letters:
            if not code:
                continue
            ch = MORSE_MAP.get(code)
            if ch is None:
                return None
            decoded_letters.append(ch)
        decoded_words.append("".join(decoded_letters))
    return " ".join(decoded_words)

def base64_decode(s: str) -> Optional[str]:
    t = re.sub(r"\s+", "", s)
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", t):
        return None
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        cand = t
        if len(cand) % 4 != 0:
            cand += "=" * (4 - len(cand) % 4)
        try:
            raw = decoder(cand)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace")
        except (binascii.Error, ValueError):
            continue
    return None

def hex_decode(s: str) -> Optional[str]:
    t = re.sub(r"\s+", "", s)
    if not re.fullmatch(r"[0-9A-Fa-f]+", t):
        return None
    if len(t) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(t)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")
    except ValueError:
        return None

def numbers_decode(s: str) -> Optional[Tuple[str, str]]:
    parts = [p for p in re.split(r"[\s,]+", s.strip()) if p]
    if not parts:
        return None
    def detect_base(tokens: List[str]) -> Optional[Tuple[int,str]]:
        if all(re.fullmatch(r"(0b)?[01]+", t, flags=re.IGNORECASE) for t in tokens):
            return 2, "binary"
        if any(t.lower().startswith("0x") for t in tokens) or any(re.search(r"[A-Fa-f]", t) for t in tokens):
            return 16, "hex-spaced"
        if all(re.fullmatch(r"(0o)?[0-7]+", t, flags=re.IGNORECASE) for t in tokens) and any(re.search(r"[0-7]", t) for t in tokens):
            return 8, "octal"
        if all(re.fullmatch(r"[0-9]+", t) for t in tokens):
            return 10, "decimal"
        return None
    det = detect_base(parts)
    if det is None:
        return None
    base, label = det
    vals = []
    for t in parts:
        tt = t.lower()
        if base == 2 and tt.startswith("0b"):
            tt = tt[2:]
        if base == 8 and tt.startswith("0o"):
            tt = tt[2:]
        if base == 16 and tt.startswith("0x"):
            tt = tt[2:]
        try:
            vals.append(int(tt, base))
        except ValueError:
            return None
    try:
        if all(0 <= v <= 255 for v in vals):
            raw = bytes(vals)
            try:
                return f"numbers-{label}", raw.decode("utf-8")
            except UnicodeDecodeError:
                return f"numbers-{label}", raw.decode("latin-1", errors="replace")
        else:
            txt = "".join(chr(v) for v in vals)
            return f"numbers-{label}", txt
    except Exception:
        return None

def guess_cipher(cipher: str) -> Tuple[str, str]:
    candidates = []
    r47 = rot47(cipher)
    candidates.append(("rot47", r47, englishy_score(r47)))
    r13 = rot_n(cipher, 13)
    candidates.append(("rot13", r13, englishy_score(r13)))
    best_shift = None
    best_text = None
    best_score = -1.0
    for n in range(26):
        t = rot_n(cipher, n)
        s = englishy_score(t)
        if s > best_score:
            best_score = s
            best_text = t
            best_shift = n
    candidates.append((f"caesar-{best_shift}", best_text, best_score))
    ab = atbash(cipher)
    candidates.append(("atbash", ab, englishy_score(ab)))
    b64 = base64_decode(cipher)
    if b64 is not None:
        candidates.append(("base64", b64, englishy_score(b64)))
    hx = hex_decode(cipher)
    if hx is not None:
        candidates.append(("hex", hx, englishy_score(hx)))
    mr = morse_decode(cipher)
    if mr is not None:
        candidates.append(("morse", mr, englishy_score(mr)))
    nd = numbers_decode(cipher)
    if nd is not None:
        ctype, txt = nd
        candidates.append((ctype, txt, englishy_score(txt)))
    if not candidates:
        return ("unknown", cipher)
    candidates.sort(key=lambda x: x[2], reverse=True)
    best_type, best_plain, _ = candidates[0]
    return (best_type, best_plain)

SUPPORTED_TYPES = {"rot47", "rot13", "caesar", "atbash", "base64", "hex", "morse", "numbers"}

def decipher(cipher: str, cipher_type: Optional[str], key: Optional[int]) -> Tuple[str, str]:
    if cipher_type is None or cipher_type.lower() == "auto":
        return guess_cipher(cipher)
    ct = cipher_type.lower()
    if ct == "rot47":
        return ("rot47", rot47(cipher))
    elif ct == "rot13":
        return ("rot13", rot_n(cipher, 13))
    elif ct == "caesar":
        if key is not None:
            return (f"caesar-{key}", rot_n(cipher, key % 26))
        best_type, best_plain = guess_cipher(cipher)
        if best_type.startswith("caesar-"):
            return (best_type, best_plain)
        else:
            best_shift = 0
            best_score = -1.0
            best_text = cipher
            for n in range(26):
                t = rot_n(cipher, n)
                s = englishy_score(t)
                if s > best_score:
                    best_score = s
                    best_text = t
                    best_shift = n
            return (f"caesar-{best_shift}", best_text)
    elif ct == "atbash":
        return ("atbash", atbash(cipher))
    elif ct == "base64":
        out = base64_decode(cipher)
        if out is None:
            return ("base64", "[decode failed]")
        return ("base64", out)
    elif ct == "hex":
        out = hex_decode(cipher)
        if out is None:
            return ("hex", "[decode failed]")
        return ("hex", out)
    elif ct == "morse":
        out = morse_decode(cipher)
        if out is None:
            return ("morse", "[decode failed]")
        return ("morse", out)
    elif ct == "numbers":
        out = numbers_decode(cipher)
        if out is None:
            return ("numbers", "[decode failed]")
        return out
    else:
        return guess_cipher(cipher)

def load_cipher_from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def main():
    parser = argparse.ArgumentParser(description="deciph3r-python: guess and decipher common simple ciphers.")
    parser.add_argument("pos_cipher", nargs="?", help="Ciphertext (positional, optional if using --cipher)")
    parser.add_argument("-c", "--cipher", help="Ciphertext string")
    parser.add_argument("-f", "--file", help="Path to a text file containing the cipher text")
    parser.add_argument("-m", "--mode", choices=["guess", "decipher"], help="Mode: guess the cipher type or decipher it")
    parser.add_argument("-t", "--type", help="Cipher type for decipher mode (rot47, rot13, caesar, atbash, base64, hex, morse, numbers, or 'auto')")
    parser.add_argument("-k", "--key", type=int, help="Key for Caesar (shift 0-25). If omitted, auto-pick best shift.")
    parser.add_argument("-o", "--output", action="store_true", help="Write result to a TXT file named '[cipher_type]dp.txt'")
    args = parser.parse_args()
    cipher = None
    if args.file:
        try:
            cipher = load_cipher_from_file(args.file)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    if cipher is None:
        cipher = args.cipher if args.cipher is not None else args.pos_cipher
    if not cipher:
        print("Error: no cipher text provided. Use --file/-f, --cipher/-c, or a positional value.", file=sys.stderr)
        sys.exit(1)
    mode = args.mode
    if mode is None:
        print("Choose an option:\n  1) Guess the type of a cipher\n  2) Decipher it")
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            mode = "guess"
        elif choice == "2":
            mode = "decipher"
        else:
            print("Invalid choice.", file=sys.stderr)
            sys.exit(1)
    if mode == "guess":
        ctype, plain = guess_cipher(cipher)
        report = []
        report.append("[deciph3r-python] MODE: GUESS")
        report.append(f"Detected type: {ctype}")
        report.append(f"Plaintext:\n{plain}")
        output = "\n".join(report)
        print(output)
        if args.output:
            fname = write_output(ctype, output)
            print(f"\nSaved: {fname}")
    else:
        used_type, plain = decipher(cipher, args.type, args.key)
        report = []
        report.append("[deciph3r-python] MODE: DECIPHER")
        if args.type:
            report.append(f"Requested type: {args.type.lower()}")
        report.append(f"Used type: {used_type}")
        if args.key is not None and isinstance(used_type, str) and used_type.startswith("caesar-"):
            report.append(f"Key (shift): {args.key % 26}")
        elif isinstance(used_type, str) and used_type.startswith("caesar-") and args.key is None:
            try:
                shift = int(used_type.split("-", 1)[1])
                report.append(f"Key (auto shift): {shift}")
            except Exception:
                pass
        report.append(f"Plaintext:\n{plain}")
        output = "\n".join(report)
        print(output)
        if args.output:
            fname = write_output(used_type if isinstance(used_type, str) else "numbers", output)
            print(f"\nSaved: {fname}")

if __name__ == "__main__":
    main()
