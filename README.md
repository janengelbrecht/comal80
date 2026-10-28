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


Komplet brugervejledning for comal80.py — RC759 Piccoline COMAL-80 Fortolker
Inspireret af den originale PICCOLINE RcComal 80 Brugervejledning (RC, januar 1985), men tilpasset den nuværende Python/PySide6-implementering.

Indholdsfortegnelse
Introduktion

Opstart og indtastning af programmer

Symboler og reserverede ord

Tal og tekst

Kontrolstrukturer

Indlæsning og udskrivning

Tal- og teksttabeller

Procedurer og funktioner

Kommandoer

Grafik (RC759 GSX / Turtle)

Nøgleord (reference)

Fejlmeddelelser

Avanceret fejlretning (Debugger)

Store programeksempler

Automatisk opstart

1. Introduktion
comal80.py er en komplet COMAL-80-fortolker med grafisk brugerflade, der emulerer RC759 Piccoline. Sproget er COMAL-80 Rev. 2.02 med en række udvidelser fra den originale RcComal80-implementering:

Kernestandard: alle kontrolstrukturer, tabeller, procedurer, funktioner, REF-parametre, CLOSED-scoping, IMPORT/GLOBAL

Streng-slicing med 1-baseret indeksering

Filer: sekventielle og RANDOM-filer

TRAP/HANDLER/ENDTRAP fejlhåndtering

RC759 GSX-grafik + Turtle-grafik

Interaktiv debugger med breakpoints, single-step, call stack, variable-watch

Immediate Mode med persistent tilstand

PRINT USING med #-felter

Fortolkeren er implementeret i comal80.py og kræver PySide6.

2. Opstart og indtastning af programmer
2.1 Start af fortolkeren
bash
python comal80.py
Vinduet åbnes med:

Venstre panel: grøn terminal (Piccoline-terminal)

Højre top: kildekode-visning + RC759-grafikskærm

Højre bund: debugger-paneler (variabler, call stack, DATA-buffer, SCAN)

Værktøjslinje: Kør, Trin ind, Trin over, Fortsæt, Pause, Stop, Scan, Renum, Åbn, Gem

Ved opstart indlæses et demonstrationsprogram (DEMO_PROGRAM), der viser de vigtigste faciliteter.

2.2 Terminalen
Terminalen fungerer som en interaktiv COMAL-80-skal:

> prompt betyder "klar til indtastning"

Nummererede linjer (10 PRINT "hej") gemmes i programhukommelsen

Ikke-nummererede linjer udføres straks (Immediate Mode)

Piletaster op/ned bladrer gennem kommando-historik

Esc afbryder kørende programmer

F5 kører programmet

F10 trin over, F11 trin ind, F8 fortsæt

F6 pause, Esc-knap stop

2.3 Kommandoer til programindtastning
Kommando	Virkning
NEW	Sletter program- og datahukommelse, rydder Immediate Mode-tilstand
AUTO [start[,trin]]	Automatisk linjenummerering (standard 10,10)
RENUMBER [start[,trin]]	Omnummererer programmet og opdaterer GOTO/RESTORE-referencer
DEL <fra>[-<til>]	Sletter linjeinterval
LIST [fra[-til]]	Viser program med auto-indrykning
EDIT <linje>	Redigerer en linje (kopierer til terminalen)
SAVE "fil"	Gemmer program som .cml
LOAD "fil"	Indlæser program fra .cml
DIR / CAT	Viser .cml/.txt-filer i mappen
SCAN	Statisk struktur- og syntaksanalyse
VARS	Udskriver alle globale variabler og tabeller
HELP	Viser kommandooversigt
2.4 Udførelse (RUN og CON)
Kommando	Virkning
RUN (F5)	Kører programmet i hukommelsen
CON / CONTINUE (F8)	Fortsætter efter STOP, END eller breakpoint
Ved RUN kaldes interpret() som først kører pre_scan() (registrerer PROC/FUNC/DATA/labels) og derefter visit() på hele AST'en.

3. Symboler og reserverede ord
3.1 Identifikatorer
En identifikator:

Starter med et bogstav (a-å, A-Å)

Efterfulgt af op til 15 bogstaver, cifre eller _

Samlet max 16 tegn

Skelner ikke mellem store/små bogstaver (men bevarer original i fejlmeddelelser)

Type-suffikser (valgfri, men anbefalet):

Suffiks	Type
%	Heltal (INTEGER)
$	Streng (STRING)
intet	Reelt tal (REAL)
3.2 Reserverede ord (nøgleord)
text
ABS    AND    AT     ATN    AUTO   BYE
CASE   CHAIN  CHR$   CIRCLE CLEAR  CLOSE
CLOSED CON    COPY   COS    CREATE DATA
DATE$  DEL    DELETE DIM    DIR    DISABLE
DIV    DO     DRAW   DRAWTO EDIT   ENABLE
END    ENDCASE ENDFOR ENDFUNC ENDIF ENDLOOP
ENDPROC ENDTRAP ENDWHILE ENTER EOD    EOF
EOR    ERR    ERRLINE ERRTEXT$ ESC   EXEC
EXIT   EXP    FALSE  FILE   FOR    FUNC
GET$   GLOBAL GOTO   GSX    HANDLER HOME
IF     IMPORT IN     INPUT  INT    KEY$
KEYS   LEFT   LEN    LET    LIST   LN
LOAD   LOCATE LOG    LOOP   LOWER$ MOD
MOUNT  MOVE   MOVETO NEW    NEXT   NOT
NULL   OF     ON     OPEN   OR     ORD
OTHERWISE OUTPUT PAGE   PALETTE PENCOLOR
PI     PRINT  PROC   RANDOM RANDOMIZE READ
RECT   REF    REM    RENUM  RENUMBER REPEAT
RESTORE RETRY  RETURN RIGHT  RND    ROUND
RUN    SAVE   SGN    SIN    SQR    STEP
STOP   STR$   TAB    TAN    TEXT   THEN
TIME   TIMER  TO     TRACE  TRAP   TRIM$
TRUE   UNTIL  UPPER$ USING  VAL    VAR
WHEN   WHILE  WINDOW WRITE  XOR    ZONE
4. Tal og tekst
4.1 Numeriske variable
Tildeling med :=, :+, :-:

comal
10 pris := 10.85
20 antal := 5
30 total := pris * antal
40 total :+ 1.5       // total := total + 1.5
50 total :- 0.5       // total := total - 0.5
Eksponentiel notation: 1.4E+100, -1.234E-10, 2E17

4.2 Beregningsudtryk
Operatorer (prioritet):

Prioritet	Operator	Funktion
1	+, - (unær)	Fortegn
2	^	Potens (højre-associativ)
3	*, /, DIV, MOD	Multiplikation, division
4	+, -	Addition, subtraktion
5	=, <>, <, >, <=, >=, IN	Sammenligning
6	NOT	Logisk negation
7	AND	Logisk og
8	OR, EOR	Logisk eller, eksklusiv eller
Beregningspræcision: 13 betydende cifre, eksponentområde -128 til +126.

4.3 Strengvariable
Strengvariable skal erklæres med DIM:

comal
10 DIM navn$ OF 30
20 navn$ := "Regnecentralen"
30 PRINT LEN(navn$)        // 14
4.4 Strengbehandling
Strengkonstanter i "...". Escaped "" giver ét ".

LEN-funktionen: LEN(s$) returnerer aktuel længde.

Delstrenge (1-baseret, inklusiv):

comal
tekst$ := "RcComal80 brugermanual"
tekst$(1:7)           // "RcComal"
tekst$(8:9)           // "80"
tekst$(11:LEN(tekst$))// "brugermanual"
tekst$(9:)            // "0 brugermanual"
tekst$(:7)            // "RcComal"
Delstrengstildeling:

comal
10 s$ := "COMAL-75 PRO"
20 s$(7:8) := "80"
30 PRINT s$               // "COMAL-80 PRO"
Sammensætning med +:

comal
nr$ := "700"
tekst$ := "rc" + nr$      // "rc700"
4.5 Logiske udtryk
comal
10 PRINT 7 > 3              // 1 (sand)
20 PRINT 3 > 7              // 0 (falsk)
30 PRINT (0 < tal) AND (tal < 10)
IN-operatoren: "b" IN "abc" → 2, "z" IN "abc" → 0

Strengsammenligning: alfabetisk efter ASCII, "AAA" < "AAB", "RC" < "RCPartner".

5. Kontrolstrukturer
5.1 IF-sætninger
Simpel IF-THEN:

comal
10 IF beløb > 100 THEN PRINT "Større end 100"
IF-THEN-ENDIF:

comal
10 IF beløb > 100 THEN
20   PRINT "Større end 100"
30   beløb := beløb * 0.9
40 ENDIF
IF-THEN-ELSE-ENDIF:

comal
10 IF beløb > 100 THEN
20   PRINT "Stor"
30 ELSE
40   PRINT "Lille"
50 ENDIF
Enkeltrække IF ... THEN ... ELSE:

comal
10 IF x > 0 THEN s$ := "positiv" ELSE s$ := "ikke positiv"
5.2 CASE-WHEN-ENDCASE
comal
10 CASE SGN(tal) OF
20 WHEN -1
30   PRINT tal; " er negativ"
40 WHEN 0
50   PRINT "nul"
60 WHEN 1
70   PRINT tal; " er positiv"
80 OTHERWISE
90   PRINT "???"
100 ENDCASE
WHEN-matchers:

WHEN 1, 2, 3 — liste

WHEN 1..10 eller WHEN 1:10 — interval

WHEN < 0, WHEN >= 100 — relation

WHEN TRUE — brugt som "if-else-kæde"

5.3 FOR-NEXT
comal
10 FOR x := 1 TO 100 DO PRINT x, x*x, x*x*x
20 FOR x := 1 TO 100 STEP 10 DO ...
30 FOR x := 10 TO 2 STEP -2 DO ...
Flerlinje:

comal
10 FOR x := 1 TO 100 DO
20   FOR potens := 1 TO 3 DO PRINT x^potens,
30   PRINT
40 NEXT x
5.4 REPEAT-UNTIL
comal
10 REPEAT
20   INPUT "Terning 1: ": t1
30   INPUT "Terning 2: ": t2
40 UNTIL t1 = t2
Sætningerne mellem REPEAT og UNTIL udføres altid mindst én gang.

5.5 WHILE-ENDWHILE
comal
10 WHILE saldo < slutbeløb DO
20   termin := termin + 1
30   saldo := saldo * (1 + rente/100)
40   PRINT USING "#### ###.##": termin, saldo
50 ENDWHILE
5.6 LOOP-EXIT-ENDLOOP
comal
10 LOOP
20   l_idx := l_idx + 1
30   l_sum := l_sum + l_idx
40   EXIT WHEN l_idx = 10
50 ENDLOOP
5.7 GOTO og labels
comal
10 GOTO spring_over
20 PRINT "Springer over"
30 spring_over:
40 PRINT "Her lander vi"
Labels må ikke være inde i strukturer (IF, FOR, WHILE, REPEAT, CASE, PROC) — GOTO må kun hoppe inden for samme niveau.

6. Indlæsning og udskrivning
6.1 INPUT
comal
10 INPUT alder, højde
20 INPUT "Indtast alder og højde > ": alder, højde
30 INPUT AT(10, 5), "Beløb: ": beløb
Numerisk input afsluttes med komma eller Retur

Streng-input afsluttes med Retur

; til sidst: næste udskrift fortsætter umiddelbart efter input

6.2 PRINT
comal
10 PRINT "tekst"
20 PRINT x, y, z            // ZONE-adskilt
30 PRINT "a"; 5; "b"        // ; giver 1 mellemrum ved tal
40 PRINT "linje 1";          // ; til sidst: ingen linjeskift
50 PRINT AT(5, 10); "tekst"  // positioneret
6.3 PRINT USING
Formatfelter med # (heltal) og . (decimal). Eksempler:

Format	Værdi	Udskrift
###	50	50
###	-37	-37
###	1.52	2
####.##	1234.567	1234.57
+####.##	1234.567	+1234.57
###.#	-42.1	-42.1
###	-4096	****
Flere felter i samme formatstreng understøttes:

comal
PRINT USING "  TESTRAPPORT: ### ud af ### tests (Fejl: ##)": ok, total, fejl
// → "  TESTRAPPORT:  98 ud af 118 tests (Fejl:  0)"
6.4 Filer og ydre enheder
Filnavn: unit/navn.type. Eksempel: 1/datafil, 2/prog.cml.

Ydre enheder (indbyggede):

1/CONSOLE — skærm + tastatur

1/KEYBOARD — tastatur (uden ekko)

1/PRINTER — printer

1/V24 — terminalport

<port>/PORT — HW-port

6.5 Sekventielle filer
comal
10 OPEN FILE 1, "datafil", WRITE
20 REPEAT
30   INPUT "Tal (0=slut) ": tal
40   WRITE FILE 1: tal
50 UNTIL tal = 0
60 CLOSE FILE 1
70 OPEN FILE 1, "datafil", READ
80 WHILE NOT EOF(1) DO
90   READ FILE 1: tal
100  PRINT tal
110 ENDWHILE
120 CLOSE FILE 1
WRITE FILE — binært format

PRINT FILE — ASCII-format

READ FILE — læser binært (matcher WRITE)

INPUT FILE — læser ASCII (matcher PRINT)

EOF(n) — sand når slut

GET$(n, antal) — læser N tegn "formatløst"

6.6 RANDOM-filer
comal
10 CREATE "medlemsdata", 20
20 OPEN FILE 1, "medlemsdata", RANDOM 47
30 WRITE FILE 1, 17: nr, navn$, klasse$
40 READ FILE 1, 17: nr, navn$, klasse$
50 CLOSE FILE 1
Poststørrelse beregnes: numerisk = 8 tegn, streng = længde + 2.

6.7 Filkopiering og sletning
comal
DELETE "gammel.dat"
RENAME "gammel.dat", "ny.dat"
COPY "kilde", "mål"
7. Tal- og teksttabeller
7.1 Taltabeller
comal
10 DIM pris(10), antal(3, 3:6)
20 DIM vektor(-3:3)
30 matrix(2, 3) := 42.5
40 vektor(-3) := 9
50 FOR i := 1 TO 10 DO pris(i) := i * 10
7.2 Teksttabeller
comal
10 DIM navn$(10) OF 30
20 navn$(1) := "Peter"
30 PRINT navn$(1)(1:3)        // "Pet"
40 FOR i := 1 TO 10 DO navn$(i) := "Elev " + STR$(i)
7.3 2D-tabeller
comal
10 DIM matrix(3, 3)
20 FOR i := 1 TO 3 DO
30   FOR j := 1 TO 3 DO matrix(i,j) := i * j
40 NEXT i
8. Procedurer og funktioner
8.1 Simple procedurer
comal
10 PROC hils
20   PRINT "Hej med dig!"
30 ENDPROC hils

40 EXEC hils
EXEC kan udelades: hils kalder samme procedure.

8.2 Parametre
comal
10 PROC skrivtabel(REF a(), dima)
20   FOR i := 1 TO dima DO PRINT a(i),
30   PRINT
40 ENDPROC skrivtabel

50 DIM alder(100)
60 EXEC skrivtabel(alder, 100)
Parameter-type	Eksempel
Tal	PROC p(i) → EXEC p(7)
Array	PROC p(REF v()) → EXEC p(v)
Matrix	PROC p(REF m(,,,)) → EXEC p(m)
Streng	PROC p(s$) → EXEC p("tekst")
Teksttabel	PROC p(REF t$()) → EXEC p(t$)
8.3 REF-parametre
REF returnerer værdier til kalderen:

comal
10 PROC findledigtnr(REF nr)
20   nr := 1
30   WHILE nr <= max AND status$(nr:nr) = "O" DO nr := nr + 1
40 ENDPROC findledigtnr

50 EXEC findledigtnr(elevnr)
Ulovligt: EXEC findledigtnr(8) — kun variable, ikke konstanter.

Array-parametre kræver altid REF.

8.4 CLOSED-procedurer
comal
10 PROC stjerner CLOSED
20   FOR x := 1 TO 10 DO PRINT "*";
30   PRINT
40 ENDPROC stjerner

50 FOR x := 1 TO 10 DO
60   EXEC stjerner
70 NEXT x
Uden CLOSED ville den ydre og indre x kollidere. Med CLOSED er x i proceduren lokal.

8.5 GLOBAL og IMPORT
comal
10 PROC p CLOSED
20   GLOBAL j          // bruger global j
30   i := 10           // lokal i
40   j := 10           // global j
50 ENDPROC p
Forskel GLOBAL vs IMPORT (kun synlig ved indlejrede CLOSED-procedurer):

GLOBAL x — henter fra hovedprogrammets scope

IMPORT x — henter fra kaldestedets scope

comal
10 PROC p CLOSED
20   PROC q CLOSED
30     GLOBAL i         // → i = 0 (hovedprogram)
40     PRINT i
50   ENDPROC q
60   i := 10
70   EXEC q
80 ENDPROC p

90 i := 0
100 EXEC p             // udskriver 0

// med IMPORT i stedet: udskriver 10
8.6 Externe procedurer
Ikke implementeret i denne fortolker (kræver fil-baserede procedurebiblioteker). Se PROC ... EXTERNAL i referencemanualen.

8.7 Funktioner
comal
10 FUNC max(a, b)
20   IF a > b THEN RETURN a ELSE RETURN b
30 ENDFUNC max

40 PRINT max(7, 9)          // 9
50 j := 32
60 størst := max(max(1, j), 11)
70 PRINT størst             // 32
Strengfunktioner:

comal
10 FUNC uppercase$(s$) CLOSED
20   FOR i := 1 TO LEN(s$) DO
30     IF s$(i:) >= CHR$(96) THEN s$(i:) := CHR$(ORD(s$(i:)) - 32)
40   NEXT i
50   RETURN s$
60 ENDFUNC uppercase$

70 PRINT uppercase$("RcComal80")(3:7)  // "COMAL"
8.8 TRAP/HANDLER (fortolkerens fejlhåndtering)
comal
10 TRAP
20   x := 10 / 0
30 HANDLER
40   PRINT "Fejl "; ERR; " i linje "; ERRLINE
50   PRINT ERRTEXT$
60 ENDTRAP
Nesting understøttes. TRAP ESC+/TRAP ESC- styrer Esc-håndtering.

8.9 RETRY, CONTINUE, RETURN i HANDLER
Ikke implementeret i denne version — brug TRAP/HANDLER som vist ovenfor.

9. Kommandoer
9.1 Oversigt
Kommando	Kategori
NEW, AUTO, RENUMBER, DEL, EDIT	Programindtastning
LIST, SAVE, LOAD	Programlagring
RUN, CON	Programafvikling
SCAN, VARS	Analyse
DIR, CAT	Filoversigt
HELP	Hjælp
BREAK, UNBREAK	Breakpoints
9.2 Immediate Mode
Sætninger uden linjenummer udføres straks:

comal
> a := 42
> PRINT a
42
> FOR i := 1 TO 3 DO PRINT i
1
2
3
Persistens: a bevares mellem kommandoer takket være den persistente immediate_interp. NEW rydder tilstanden.

9.3 Datamaten som bordkalkulator
comal
> NEW
> antal := 20
> stkpris := 47.85
> PRINT antal * stkpris
957
9.4 Fejlfinding med Immediate Mode
comal
> p1 := 14
> p2 := 99
> EXEC ombyt_ref(p1, p2)
> PRINT p1; p2
99  14
Bemærk: EXEC af procedures kræver at programmet er RUN først (så pre_scan har registreret dem), medmindre man er i et program.

10. Grafik
10.1 RC759 GSX-grafik
Fortolkeren emulerer RC759 GSX med følgende enheder:

Enhed	Type
1	Monokrom skærm
2	Farveskærm
11	Plotter
21	Skriver
Grafikskærmen i højre panel viser kommandoer live.

10.2 Grundlæggende grafik
comal
10 EXEC CLEAR
20 EXEC HOME
30 EXEC PENCOLOR(2)
40 EXEC RECT(-180, -130, 180, 130, 0)
50 EXEC CIRCLE(0, 0, 95, 0)
60 EXEC TEXT(-165, 110, "RC759 PICCOLINE")
Kommando	Virkning
EXEC CLEAR	Rydder skærmen
EXEC HOME	Sætter turtle til (0,0) med retning 0
EXEC PENCOLOR(n)	Vælger farve (0-7)
EXEC PLOT(x, y)	Plotter punkt
EXEC LINE(x1, y1, x2, y2)	Tegner linje
EXEC RECT(x1, y1, x2, y2, fill)	Tegner rektangel
EXEC CIRCLE(x, y, r, fill)	Tegner cirkel
EXEC TEXT(x, y, "s")	Skriver tekst
10.3 Turtle-grafik
comal
10 EXEC CLEAR
20 EXEC HOME
30 EXEC PENDOWN
40 FOR k := 1 TO 18 DO
50   EXEC PENCOLOR((k MOD 7) + 1)
60   FOR s := 1 TO 4 DO
70     EXEC FORWARD(90)
80     EXEC RIGHT(90)
90   ENDFOR s
100  EXEC RIGHT(20)
110 ENDFOR k
Kommando	Virkning
EXEC FORWARD(d) / FD(d)	Gå frem
EXEC BACK(d) / BK(d)	Gå tilbage
EXEC LEFT(a) / LT(a)	Drej venstre
EXEC RIGHT(a) / RT(a)	Drej højre
EXEC PENUP / PU	Løft pen
EXEC PENDOWN / PD	Sænk pen
EXEC SETPOS(x, y)	Gå til position (tegner hvis pen nede)
EXEC MOVETO(x, y)	Flyt uden at tegne
EXEC SETH(a)	Sæt retning
10.4 Farvepalet
Kode	Farve
0	Mørkegrøn (baggrund)
1	Lys grøn
2	Orange
3	Cyan
4	Rød
5	Magenta
6	Gul
7	Hvid
11. Nøgleord (reference)
Forkortet oversigt — se den originale manual for detaljer om hvert nøgleord.

11.1 Matematik
Funktion	Virkning
ABS(x)	Numerisk værdi
ATN(x)	Arcus tangens (radianer)
COS(x)	Cosinus
DEG(x)	Radianer → grader
EXP(x)	e^x
INT(x)	Gulv
LN(x)	Naturlig logaritme
LOG(x)	10-tals logaritme
RAD(x)	Grader → radianer
RND	Tilfældig 0-1
RND(a,b)	Tilfældig a-b
ROUND(x, n)	Afrund til n decimaler
SGN(x)	Fortegn (-1, 0, 1)
SIN(x)	Sinus
SQR(x)	Kvadratrod
TAN(x)	Tangens
11.2 Strenge
Funktion	Virkning
CHR$(n)	ASCII-tegn
INSTR(hay, needle)	Position (1-baseret, 0 = ikke fundet)
LEN(s$)	Længde
LOWER$(s$)	Små bogstaver
ORD(s$)	ASCII-værdi af første tegn
STR$(n)	Tal → streng
TRIM$(s$)	Fjern ledende/efterfølgende mellemrum
UPPER$(s$)	Store bogstaver
VAL(s$)	Streng → tal
11.3 System
Funktion	Virkning
DATE$	Dato (ikke implementeret)
EOD	1 hvis DATA udtømt
EOF(n)	1 hvis fil slut
ERR	Sidste fejlkode
ERRLINE	Linje hvor fejl opstod
ERRTEXT$	Fejlbeskrivelse
KEY$ / INKEY$	Sidste tastetryk
PI	3.14159...
TIME	Sekunder siden opstart
TRUE / FALSE	1 / 0
11.4 Streng-slicing
Se afsnit 4.4.

11.5 IN-operatoren
"sub" IN "streng" — position eller 0.

12. Fejlmeddelelser
12.1 Fejlkoder
Kode	Betydning
10	Leksikalsk fejl
20	Syntaksfejl
30	Kørselsfejl (generel)
41	Tabel-dimension mismatch
42	Indeks uden for grænser
43	Strenglængde overstiger DIM OF
44	Strengindeks uden for grænser
51	Division med nul
60	EOF ved fil-læsning
61	Løbet tør for DATA
62	Fil-åbningsfejl
100	ESC afbrydelse
12.2 Fejlformat
text
Kørselsfejl i linje 310: Division med nul
Syntaksfejl i linje 50, kolonne 12: Forventede ')', men fandt ':' 
Leksikalsk fejl i linje 100, kolonne 5: Uafsluttet tekststreng
12.3 Typiske fejl og løsninger
Fejl	Årsag	Løsning
Uafsluttet tekststreng	Manglende "	Tilføj afsluttende "
Forventede ')', men fandt ...	Ubalancerede parenteser	Tjek parenteser
Indeks uden for grænser	Array-adgang uden for DIM	Tjek DIM-grænser
Procedure ikke defineret	RUN ikke kørt	Kør RUN først
Strengindeks uden for	Slice uden for streng	Tjek LEN(s$)
13. Avanceret fejlretning (Debugger)
13.1 Breakpoints
Klik på en linje i kildekode-visningen → sæt/fjern breakpoint (●)

BREAK 180 i terminalen → sæt breakpoint

UNBREAK 180 → fjern

UNBREAK → fjern alle

13.2 Single-step
Tast	Handling
F11	Trin ind (step into)
F10	Trin over (step over — springer over procedure-kald)
F8	Fortsæt (continue)
F6	Pause
Esc	Stop
13.3 Debugger-paneler
🔎 Variabler & Tabeller (Watch):

Viser lokale variable i øverste call frame

Viser globale variable

Viser arrays med deres elementer

REF-bindinger vises med desc (f.eks. REF p1)

📚 Kald-stak (Call Stack):

Viser alle aktive frames

Scope: CLOSED eller ÅBEN

Kaldt fra linje

📊 DATA-buffer:

Viser alle DATA-værdier

▶ NÆSTE markerer næste læste

🛠 Statisk Analyse (SCAN):

Strukturfejl (uafsluttede blokke, manglende ENDIF osv.)

Syntaksfejl fundet ved at parse hele programmet

13.4 Eksempel på debug-session
comal
10 p1 := 14
20 p2 := 99
30 EXEC ombyt_ref(p1, p2)   ← BREAK her
40 PRINT p1; p2
Klik på linje 30 → breakpoint

F5 (RUN)

Programmet pauser ved linje 30

Inspicér p1 og p2 i Variabler-panelet: P1 = 14, P2 = 99

F11 (trin ind) → nu er du inde i ombyt_ref

Call stack viser ombyt_ref → main

F11 (trin) gennem midl := a, a := b, b := midl

F8 (fortsæt)

Programmet udskriver 99 14 ✅

14. Store programeksempler
14.1 Renters rente
comal
0010 PAGE
0020 ZONE 20
0030 MARGIN 80
0040 start := 100
0050 slutsaldo := 200
0060 rente := 16
0070 PRINT "År   Saldo"
0080 år := 1983
0090 saldo := start
0100 WHILE saldo < slutsaldo DO
0110   år := år + 1
0120   saldo := saldo * (1 + rente/100)
0130   PRINT år, saldo
0140 ENDWHILE
0150 PRINT "END AT "; STR$(år)
14.2 Elevregister (skitse)
comal
0010 PROC opstart
0020   DIM klasse$(1:500) OF 5, navn$(1:500) OF 30
0030   DIM status$(1:500) OF 1
0040   FOR i := 1 TO 500 DO status$(i) := "L"
0050 ENDPROC opstart

0060 PROC fåelevnr
0070   REPEAT
0080     INPUT "Elevnr: ": elevnr
0090     ok := elevnr >= 1 AND elevnr <= 500 AND status$(elevnr:elevnr) = "O"
0100     IF NOT ok THEN PRINT "*** Eleven eksisterer ikke"
0110   UNTIL ok
0120 ENDPROC fåelevnr

0130 PROC findledigtnr(REF nr)
0140   nr := 1
0150   WHILE nr <= 500 AND status$(nr:nr) <> "L" DO nr := nr + 1
0160   PRINT "Eleven har fået nummer "; nr
0170 ENDPROC findledigtnr

0200 EXEC opstart
0210 REPEAT
0220   INPUT "Kommando (I/R/S/F): ": k$
0230   CASE k$ OF
0240   WHEN "I", "i"
0250     EXEC fåelevnr
0260     INPUT "Navn: ": n$
0270     INPUT "Klasse: ": kl$
0280     navn$(elevnr) := n$
0290     klasse$(elevnr) := kl$
0300     status$(elevnr:elevnr) := "O"
0310   WHEN "R", "r"
0320     EXEC fåelevnr
0330     PRINT "Navn: "; navn$(elevnr)
0340     PRINT "Klasse: "; klasse$(elevnr)
0350   WHEN "S", "s"
0360     EXEC fåelevnr
0370     status$(elevnr:elevnr) := "S"
0380   WHEN "F", "f"
0390     PRINT "Farvel"
0400   OTHERWISE
0410     PRINT "*** Ukendt kommando"
0420   ENDCASE
0430 UNTIL k$ = "F" OR k$ = "f"
14.3 Romertal
comal
0010 FUNC romertal$(tal%) CLOSED
0020   DIM v%(1:7), sym$(1:7) OF 2
0030   v%(1) := 1000; sym$(1) := "M"
0040   v%(2) := 900;  sym$(2) := "CM"
0050   v%(3) := 500;  sym$(3) := "D"
0060   v%(4) := 100;  sym$(4) := "C"
0070   v%(5) := 50;   sym$(5) := "L"
0080   v%(6) := 10;   sym$(6) := "X"
0090   v%(7) := 4;    sym$(7) := "IV"
0100   res$ := ""
0110   rest% := tal%
0120   FOR i% := 1 TO 7 DO
0130     WHILE rest% >= v%(i%) DO
0140       res$ := res$ + TRIM$(sym$(i%))
0150       rest% :- v%(i%)
0160     ENDWHILE
0170   ENDFOR i%
0180   RETURN res$
0190 ENDFUNC romertal$

0200 PRINT romertal$(1984)    // MCMLXXXIV
14.4 Fibonacci
comal
0010 FUNC fib(n%) CLOSED
0020   IF n% <= 1 THEN RETURN 1 - (1 - n%)
0030   RETURN fib(n% - 1) + fib(n% - 2)
0040 ENDFUNC fib

0050 PRINT "Fib(10) = "; fib(10)
14.5 Euklids algoritme (SFD)
comal
0010 FUNC sfd(a%, b%) CLOSED
0020   IF b% = 0 THEN RETURN a%
0030   RETURN sfd(b%, a% MOD b%)
0040 ENDFUNC sfd

0050 PRINT "sfd(1071, 462) = "; sfd(1071, 462)   // 21
14.6 Turtle-stjerne
comal
0010 PROC tegn_stjerne(side) CLOSED
0020   EXEC CLEAR
0030   EXEC HOME
0040   EXEC PENDOWN
0050   FOR k := 1 TO 18 DO
0060     EXEC PENCOLOR((k MOD 7) + 1)
0070     FOR s := 1 TO 4 DO
0080       EXEC FORWARD(side)
0090       EXEC RIGHT(90)
0100     ENDFOR s
0110     EXEC RIGHT(20)
0120   ENDFOR k
0130   EXEC PENUP
0140 ENDPROC tegn_stjerne

0150 EXEC tegn_stjerne(90)
14.7 Enarmet tyveknægt (forenklet)
comal
0010 RANDOMIZE
0020 penge := 0
0030 PRINT "Tryk Esc for at stoppe"
0040 REPEAT
0050   t1 := RND(1, 6)
0060   t2 := RND(1, 6)
0070   t3 := RND(1, 6)
0080   penge :- 1
0090   PRINT "Terninger: "; t1; " "; t2; " "; t3
0100   IF t1 = t2 AND t2 = t3 THEN
0110     gevinst := t1 * 10
0120     penge :+ gevinst
0130     PRINT "JACKPOT! +"; gevinst; " mønter"
0140   ELSE
0150     PRINT "Ingen gevinst"
0160   ENDIF
0170   PRINT "Saldo: "; penge
0180 UNTIL FALSE
15. Automatisk opstart
15.1 LOGON-fil
Fortolkeren kan automatisk indlæse en fil ved opstart. I denne Python-version er dette ikke implementeret i selve terminalen, men du kan nemt tilføje det:

python
# I ComalMainWindow.__init__ efter refresh_code_view():
import os
if os.path.exists("LOGON.cml"):
    self.terminal.load_from_file("LOGON.cml")
    self.start_execution(step_mode=False)
15.2 Kommando-linje parametre
I den originale RcComal80 kunne man skrive COMAL80 MENU for at loade en bestemt fil. I Python-versionen:

bash
python comal80.py
og derefter LOAD "menu.cml" + RUN.

For automatisk at loade en fil ved opstart:

python
# Modificér __main__ blok:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComalMainWindow()
    if len(sys.argv) > 1:
        window.terminal.load_from_file(sys.argv[1])
    window.show()
    sys.exit(app.exec())
Appendix A — Sammenligning med original RcComal80
Facilitet	Original RcComal80	Denne fortolker
Kernestandard	✅	✅
PROC/FUNC/CLOSED/REF	✅	✅
IMPORT/GLOBAL	✅	✅
DATA/READ/RESTORE	✅	✅
Streng-slicing	✅	✅
Sekventielle filer	✅	✅
RANDOM-filer	✅	✅ (basis)
TRAP/HANDLER	✅	✅
PROC-EXTERNAL	✅	❌
HANDLER RETRY/CONTINUE	✅	❌
PRINT USING	✅	✅ (forbedret)
TAB / AT	✅	✅ (delvist)
GSX-grafik	✅	✅ (emuleret)
LOCATE/GPARM	✅	❌
MOUNT/DIR	✅	✅ (Python-filer)
Funktionstaster	✅	✅ (PySide6-genveje)
CHAIN	✅	❌
SCREENS	✅	❌
Debugger	❌	✅ (Python-version)
Breakpoints	❌	✅
Call stack	❌	✅
Variable-watch	❌	✅
Persistent Immediate Mode	✅	✅
Appendix B — Fejlkode-tabel (fuld)
Kode	Fejl	Løsning
10	Leksikalsk fejl	Tjek ulovlige tegn, uafsluttede strenge
20	Syntaksfejl	Tjek parenteser, nøgleord, struktur
30	Generel kørselsfejl	Se besked
41	DIM-dimension mismatch	Tjek antal indekser
42	Indeks uden for grænser	Tjek DIM-grænser
43	Strenglængde > DIM OF	Kortere streng eller større OF
44	Strengindeks uden for	Tjek LEN(s$)
51	Division med nul	Tjek nævner
60	EOF	Tjek EOF(n) før READ FILE
61	Ikke flere DATA	Tjek EOD
62	Fil-åbningsfejl	Tjek filnavn
100	ESC afbrydelse	Forventet
Appendix C — Tastaturgenveje
Tast	Handling
F5	RUN
F6	Pause
F8	Fortsæt
F10	Trin over
F11	Trin ind
Esc	Stop kørende program
Pil Op/Ned	Kommando-historik
Ctrl+C	(i terminalen) kopier
Ctrl+V	(i terminalen) indsæt flere linjer
Appendix D — Filformat
Programmer gemmes som .cml-filer i tekstformat:

text
0010 // Kommentar
0020 PRINT "Hej"
0030 END
Ved SAVE tilføjes automatisk .cml hvis filnavnet ikke har endelse. Ved LOAD indlæses linjerne i program_memory dict.

Filnavn-konventioner:

*.cml — COMAL-programmer

*.dat — data-filer

*.txt — tekst-filer

*.csv — (originalt COMAL-format, ikke brugt i denne version)

Appendix E — Avanceret: Arkitektur
Fortolkeren består af følgende dele:

text
comal80.py
├── DEL 1: Lexer (tokenize)
├── DEL 2: AST-noder
├── DEL 3: Parser (AST-opbygning)
├── DEL 4: Interpreter (visit_xxx metoder)
├── DEL 5: ComalCodeTools (format, SCAN)
├── DEL 6: PiccolineGraphicsCanvas (GSX/Turtle)
├── DEL 7: PiccolineTerminal (interaktiv terminal)
└── DEL 8: ComalMainWindow (GUI + debugger)
Kernemetoder i Interpreter:

visit_<NodeType>(node) — dispatch per AST-node

get_var/set_var — scope-opslag

_create_ref_binding — REF-håndtering med ejende frame

_prepare_call_frame — argument-binding

_apply_slice_read/_write — streng-slicing

_format_using — PRINT USING med flere felter

pre_scan — registrerer PROC/FUNC/DATA/labels

interpret — hoved-loop

Debugger-integration: debug_hook(self, stmt) kaldes før hver statement og kan pause eksekveringen.

Appendix F — Kilder
PICCOLINE RcComal 80 Brugervejledning, A/S Regnecentralen af 1979, januar 1985

COMAL-80 kernestandard (Børge Christensen et al., 1979)

Python 3.10+, PySide6

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
