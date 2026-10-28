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

git clone [https://github.com/dit-brugernavn/comal80-interpreter.git](https://github.com/dit-brugernavn/comal80-interpreter.git)
cd comal80-interpreter
pip install -r requirements.txt**4. LICENSE**
En open-source licens er nødvendig, hvis koden skal deles frit. MIT-licensen er standard for denne type projekter, da den tillader fri brug og modifikation.


Terminal og miljøkommandoer
Terminalen fungerer i to tilstande: Direct mode (hvor kommandoer udføres øjeblikkeligt uden linjenummer) og Program mode (hvor linjer gemmes i hukommelsen, hvis de forudsiges af et heltal).

NEW: Sletter det aktuelle program i hukommelsen.

LIST: Udskriver hele programmet til skærmen i numerisk rækkefølge.

RUN: Eksekverer programmet fra hukommelsen.

AUTO [start], [step]: Starter automatisk linjenummerering (f.eks. AUTO 10, 10). Afbrydes ved at trykke Enter på en tom linje.

SAVE "filnavn": Gemmer kildekoden lokalt som en tekstfil (tilføjer automatisk .cml, hvis det mangler).

LOAD "filnavn": Indlæser et program fra en fil.

Variabler og datatyper
Datatyper udledes automatisk ud fra variablens suffiks. Tildeling kan ske fleksibelt med enten den klassiske COMAL-operator := eller standard lighedstegn =.

Heltal (Integer): Angives med %. Decimaler afskæres.A% := 42 eller A% = 42

Tekststrenge (String): Angives med $.NAVN$ := "Piccoline"

Kommatal (Real): Variabler uden suffiks behandles som flydende kommatal.PI = 3.14159

Arrays: Flerdimensionelle arrays oprettes og tilgås implicit via parenteser.TABEL(1, 5) := 100

Operatorer
Fortolkeren respekterer standard matematisk operatorpræcedens (BODMAS/PEMDAS).

Aritmetiske: + (addition/streng-sammensætning), - (subtraktion), * (multiplikation), / (division), ^ (potens), MOD (modulo/rest), DIV (heltalsdivision).

Relationelle: = (lig med), <> (ikke lig med), < (mindre end), > (større end), <= (mindre end eller lig med), >= (større end eller lig med). Returnerer 1 for sand, 0 for falsk.

Logiske: AND, OR, NOT.

Input og output
PRINT: Udskriver tekst og variabler til skærmen. Elementer adskilt af komma , indsætter et tabulatorspring. Elementer adskilt af semikolon ; udskrives i forlængelse af hinanden uden linjeskift.PRINT "Værdien er: "; X%; " enheder", Y$

INPUT: Prompter brugeren for indtastning via en dialogboks. Kan inkludere en ledetekst.INPUT "Indtast dit navn: ": N$

Kontrolstrukturer
COMAL-80 udmærker sig ved sine strukturerede blokke, der eliminerer behovet for GOTO (selvom strukturerne er fleksible).

IF-betingelser
Findes både som lukkede blokke og i en kompakt enkeltlinje-version.

Kodestykke
// Blok-struktur
IF A > 100 THEN
    PRINT "Meget stor"
ELIF A > 50 THEN
    PRINT "Mellem"
ELSE
    PRINT "Lille"
ENDIF

// Enkeltlinje-struktur (kræver ikke ENDIF)
IF B = 0 THEN B := 1
FOR-løkker
Itererer over en talrække. STEP er valgfrit (standard er 1).

Kodestykke
FOR I := 10 TO 0 STEP -2 DO
    PRINT I
ENDFOR
WHILE-løkker
Udfører blokken så længe betingelsen er sand. Evalueres i toppen.

Kodestykke
WHILE X < 100 DO
    X := X * 2
ENDWHILE
REPEAT-løkker
Udfører blokken indtil betingelsen bliver sand. Evalueres i bunden (kører mindst én gang).

Kodestykke
REPEAT
    X := X - 1
UNTIL X = 0
Procedurer og funktioner
Procedurer (PROC) tillader opdeling af koden i logiske moduler. Variabler i parameterlisten oprettes i et lokalt scope isoleret fra det globale program.

Procedurer kan kaldes enten eksplicit med EXEC eller implicit blot ved at skrive navnet. Parenteser er valgfrie, hvis der ikke overføres parametre.

Kodestykke
PROC UDSKRIV_KASSE(TEKST$)
    PRINT "----------"
    PRINT TEKST$
    PRINT "----------"
ENDPROC

// Gyldige kald af proceduren:
EXEC UDSKRIV_KASSE("Hej verden")
UDSKRIV_KASSE("COMAL-80")

PROC TOM_TEST()
    PRINT "Kaldt uden parametre"
ENDPROC

TOM_TEST()
TOM_TEST
Datahåndtering
Brug DATA til at gemme konstante værdier i programmet, som efterfølgende indlæses sekventielt med READ. RESTORE nulstiller læse-pointeren, så dataene kan læses forfra.

Kodestykke
DATA 10, 20, "Tekst", 3.14
READ A, B, C$, D
RESTORE
READ X // X bliver nu 10
Øvrige systemkommandoer
REM eller //: Indikerer en kommentar. Resten af linjen ignoreres under kørsel.

PAGE: Rydder skærmen ved at udskrive 30 tomme linjer (emulerer en skærmrensning i Piccoline terminalen).

STOP / END: Afbryder programkørslen øjeblikkeligt.

Komplette programeksempler
Eksempel 1: Temperaturkonvertering (Procedurer og Input)

Kodestykke
10 PAGE
20 PRINT "--- TEMPERATUR KONVERTERING ---"
30 INPUT "Indtast temperatur i Celsius: ": C
40 FAHRENHEIT(C)
50 STOP
60 
70 PROC FAHRENHEIT(CELSIUS)
80   F = (CELSIUS * 9/5) + 32
90   PRINT CELSIUS; " grader Celsius er "; F; " grader Fahrenheit."
100 ENDPROC
Eksempel 2: Multiplikationstabel (Nested FOR-løkker)

Kodestykke
10 PAGE
20 INPUT "Hvilken tabel vil du se? (1-10): ": TABEL%
30 IF TABEL% < 1 OR TABEL% > 10 THEN
40   PRINT "Ugyldigt valg!"
50   STOP
60 ENDIF
70 
80 PRINT "Tabel ", TABEL%
90 PRINT "------------"
100 FOR I% = 1 TO 10 DO
110   RES% = I% * TABEL%
120   PRINT I%; " * "; TABEL%; " = ", RES%
130 ENDFOR

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