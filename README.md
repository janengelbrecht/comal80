# RC759 COMAL-80 Fortolker

En komplet COMAL-80 fortolker skrevet i Python, komplet med en PySide6-baseret terminal, der emulerer den klassiske Regnecentralen RC759 Piccoline oplevelse fra 1980'erne.

Projektet bygger på klassisk compiler-arkitektur med en Lexer, en Recursive Descent Parser (AST) og en Interpreter.

## Funktioner
* **Piccoline Miljø**: Interaktiv terminal med understøttelse af miljøkommandoer som `RUN`, `LIST`, `NEW`, `AUTO`, `SAVE` og `LOAD`.
* **Struktureret Logik**: Understøtter `IF-ELIF-ELSE-ENDIF`, `FOR-TO-STEP-DO-ENDFOR`, `WHILE` og `REPEAT-UNTIL`.
* **Procedurer**: Fuld understøttelse af `PROC` og `EXEC` med parameteroverførsel og lokalt variabel-scope via en intern Call Stack.
* **Datatyper**: Implicit typehåndtering af strenge (`$`), heltal (`%`) og reelle tal.

## Installation & Kørsel
Klon respositoriet og installer afhængigheder:

```bash
git clone [https://github.com/dit-brugernavn/comal80-interpreter.git](https://github.com/dit-brugernavn/comal80-interpreter.git)
cd comal80-interpreter
pip install -r requirements.txt**4. LICENSE**
En open-source licens er nødvendig, hvis koden skal deles frit. MIT-licensen er standard for denne type projekter, da den tillader fri brug og modifikation.

MIT License

Copyright (c) 2026 Jan Engelbrecht Pedersen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
