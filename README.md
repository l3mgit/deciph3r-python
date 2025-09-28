# 🧩 deciph3r-python

deciph3r-python is a versatile Python CLI tool that analyzes and deciphers encoded text using common cipher algorithms.

---

## ✨ Features
- 🔍 Automatic Cipher Detection
  - Identifies the most likely cipher type (e.g., ROT13, ROT47, Caesar, Base64, etc.)
- 🔐 Decryption Support
  - Supports:  
    ROT13, ROT47, Caesar, Atbash, Base64, Hex, Morse, Numeric (binary/octal/decimal/hex)
- 📄 File or CLI Input
  - Accepts ciphertext directly (-c) or from a text file (-f / --file)
- 💾 Automatic Output
  - Saves deciphered text in [cipher_type]dp.txt
- 🧠 Intelligent Guessing
  - Scores possible decodings by English-likeness for accurate results

---

## ⚙️ Installation

Clone the repository and run the script directly:

```bash
git clone https://github.com/l3mgit/deciph3r-python.git

cd deciph3r-python

python3 deciph3r-python.py -h
