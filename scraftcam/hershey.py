"""Text drawn as lines: the Hershey simplex font (`T.sfoe~6.4` #264).

Text in a diagram is ink strokes like everything else, so the SVG and
the editor show the same letters (#262).  `strokes()` turns a string
into polylines, `width()` measures it; both in the caller's units,
with Y up and the text's height the height of a capital letter.

Acknowledgements, which must be distributed with the font data:
* The Hershey Fonts were originally created by Dr. A. V. Hershey while
  working at the U. S. National Bureau of Standards.
* The format of the Font data in this distribution was originally
  created by James Hurt, Cognition, Inc., 900 Technology Park Drive,
  Billerica, MA 01821 (mit-eddie!ci-dandelion!hurt).

The data below is `futural.jhf` (ASCII 32-126) as kept by
`github.com/kamalmostafa/hershey-fonts`: each glyph is pairs of
letters, a coordinate being its letter's code less that of `R`; the
first pair is the glyph's left and right edges, `" R"` lifts the
pen, and Y runs down.
"""

import math

from .geometry import Point

# A capital runs from Y -12 up to the base line at Y 9 (Y down).
CAP_TOP: int = -12
BASE: int = 9
CAP: int = BASE - CAP_TOP
ZERO: int = ord("R")


# Function `strokes()`:
# Type hints on every variable inflate its count of locals.
# pylint: disable-next=too-many-locals
def strokes(
    text: str, origin: Point, height: float, angle: float = 0.0
) -> list[list[Point]]:
    """Return a string's strokes, starting at its base line's left end.

    Arguments:
    * `text` (`str`): The text; a character not in the font is `?`.
    * `origin` (`Point`): The left end of its base line.
    * `height` (`float`): The height of a capital letter.
    * `angle` (`float`):
      The base line's direction (degrees, counter-clockwise from X).

    Returns:
    * (`list[list[Point]]`): One polyline per pen stroke.
    """
    # Each glyph is laid out along the base line, then turned.
    scale: float = height / CAP
    cosine: float = math.cos(math.radians(angle))
    sine: float = math.sin(math.radians(angle))
    found: list[list[Point]] = []
    advance: float = 0.0
    character: str
    for character in text:
        left: int
        right: int
        lines: list[list[tuple[int, int]]]
        left, right, lines = _glyph(character)
        line: list[tuple[int, int]]
        for line in lines:
            polyline: list[Point] = []
            for x, y in line:
                along: float = advance + (x - left) * scale
                up: float = (BASE - y) * scale
                polyline.append(
                    (
                        origin[0] + along * cosine - up * sine,
                        origin[1] + along * sine + up * cosine,
                    )
                )
            found.append(polyline)
        advance += (right - left) * scale
    return found


# Function `width()`:
def width(text: str, height: float) -> float:
    """Return how long a string's base line is.

    Arguments:
    * `text` (`str`): The text.
    * `height` (`float`): The height of a capital letter.

    Returns:
    * (`float`): The sum of its glyphs' widths.
    """
    # Add up each glyph's right less left edge.
    total: int = 0
    character: str
    for character in text:
        left: int
        right: int
        left, right, _ = _glyph(character)
        total += right - left
    return total * height / CAP


# Function `_glyph()`:
def _glyph(character: str) -> tuple[int, int, list[list[tuple[int, int]]]]:
    """Return a glyph's edges and pen strokes, Y down.

    Arguments:
    * `character` (`str`): The character; `?` when not in the font.

    Returns:
    * (`tuple[int, int, list[list[tuple[int, int]]]]`):
      Its left and right edges and its polylines.
    """
    # The first pair is the edges; `" R"` starts a new stroke.
    data: str = GLYPHS.get(character, GLYPHS["?"])
    left: int = ord(data[0]) - ZERO
    right: int = ord(data[1]) - ZERO
    lines: list[list[tuple[int, int]]] = [[]]
    index: int
    for index in range(2, len(data), 2):
        pair: str = data[index : index + 2]
        if pair == " R":
            lines.append([])
        else:
            lines[-1].append((ord(pair[0]) - ZERO, ord(pair[1]) - ZERO))
    return left, right, [line for line in lines if line]


# The glyphs of `futural.jhf`, by character.
GLYPHS: dict[str, str] = {
    " ": "JZ",
    "!": "MWRFRT RRYQZR[SZRY",
    '"': "JZNFNM RVFVM",
    "#": "H]SBLb RYBRb RLOZO RKUYU",
    "$": "H\\PBP_ RTBT_ RYIWGTFPFMGKIKKLMMNOOUQWRXSYUYXWZT[P[MZKX",
    "%": ("F^[FI[ RNFPHPJOLMMKMIKIIJGLFNFPGSHVHYG[F RWTUUTWTYV[X[ZZ[X[VYTWT"),
    "&": (
        "E_\\O\\N[MZMYNXPVUTXRZP[L[JZIYHWHUISJRQNRMSKSIRGPFNGMIMKNN"
        "PQUXWZY[[[\\Z\\Y"
    ),
    "'": "MWRHQGRFSGSIRKQL",
    "(": "KYVBTDRGPKOPOTPYR]T`Vb",
    ")": "KYNBPDRGTKUPUTTYR]P`Nb",
    "*": "JZRLRX RMOWU RWOMU",
    "+": "E_RIR[ RIR[R",
    ",": "NVSWRXQWRVSWSYQ[",
    "-": "E_IR[R",
    ".": "NVRVQWRXSWRV",
    "/": "G][BIb",
    "0": "H\\QFNGLJKOKRLWNZQ[S[VZXWYRYOXJVGSFQF",
    "1": "H\\NJPISFS[",
    "2": "H\\LKLJMHNGPFTFVGWHXJXLWNUQK[Y[",
    "3": "H\\MFXFRNUNWOXPYSYUXXVZS[P[MZLYKW",
    "4": "H\\UFKTZT RUFU[",
    "5": "H\\WFMFLOMNPMSMVNXPYSYUXXVZS[P[MZLYKW",
    "6": "H\\XIWGTFRFOGMJLOLTMXOZR[S[VZXXYUYTXQVOSNRNOOMQLT",
    "7": "H\\YFO[ RKFYF",
    "8": ("H\\PFMGLILKMMONSOVPXRYTYWXYWZT[P[MZLYKWKTLRNPQOUNWMXKXIWGTFPF"),
    "9": "H\\XMWPURRSQSNRLPKMKLLINGQFRFUGWIXMXRWWUZR[P[MZLX",
    ":": "NVROQPRQSPRO RRVQWRXSWRV",
    ";": "NVROQPRQSPRO RSWRXQWRVSWSYQ[",
    "<": "F^ZIJRZ[",
    "=": "E_IO[O RIU[U",
    ">": "F^JIZRJ[",
    "?": "I[LKLJMHNGPFTFVGWHXJXLWNVORQRT RRYQZR[SZRY",
    "@": (
        "E`WNVLTKQKOLNMMPMSNUPVSVUUVS RQKOMNPNSOUPV RWKVSVUXVZV\\T"
        "]Q]O\\L[JYHWGTFQFNGLHJJILHOHRIUJWLYNZQ[T[WZYYZX RXKWSWUXV"
    ),
    "A": "I[RFJ[ RRFZ[ RMTWT",
    "B": "G\\KFK[ RKFTFWGXHYJYLXNWOTP RKPTPWQXRYTYWXYWZT[K[",
    "C": "H]ZKYIWGUFQFOGMILKKNKSLVMXOZQ[U[WZYXZV",
    "D": "G\\KFK[ RKFRFUGWIXKYNYSXVWXUZR[K[",
    "E": "H[LFL[ RLFYF RLPTP RL[Y[",
    "F": "HZLFL[ RLFYF RLPTP",
    "G": "H]ZKYIWGUFQFOGMILKKNKSLVMXOZQ[U[WZYXZVZS RUSZS",
    "H": "G]KFK[ RYFY[ RKPYP",
    "I": "NVRFR[",
    "J": "JZVFVVUYTZR[P[NZMYLVLT",
    "K": "G\\KFK[ RYFKT RPOY[",
    "L": "HYLFL[ RL[X[",
    "M": "F^JFJ[ RJFR[ RZFR[ RZFZ[",
    "N": "G]KFK[ RKFY[ RYFY[",
    "O": "G]PFNGLIKKJNJSKVLXNZP[T[VZXXYVZSZNYKXIVGTFPF",
    "P": "G\\KFK[ RKFTFWGXHYJYMXOWPTQKQ",
    "Q": "G]PFNGLIKKJNJSKVLXNZP[T[VZXXYVZSZNYKXIVGTFPF RSWY]",
    "R": "G\\KFK[ RKFTFWGXHYJYLXNWOTPKP RRPY[",
    "S": "H\\YIWGTFPFMGKIKKLMMNOOUQWRXSYUYXWZT[P[MZKX",
    "T": "JZRFR[ RKFYF",
    "U": "G]KFKULXNZQ[S[VZXXYUYF",
    "V": "I[JFR[ RZFR[",
    "W": "F^HFM[ RRFM[ RRFW[ R\\FW[",
    "X": "H\\KFY[ RYFK[",
    "Y": "I[JFRPR[ RZFRP",
    "Z": "H\\YFK[ RKFYF RK[Y[",
    "[": "KYOBOb RPBPb ROBVB RObVb",
    "\\": "KYKFY^",
    "]": "KYTBTb RUBUb RNBUB RNbUb",
    "^": "JZRDJR RRDZR",
    "_": "I[Ib[b",
    "`": "NVSKQMQORPSORNQO",
    "a": "I\\XMX[ RXPVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "b": "H[LFL[ RLPNNPMSMUNWPXSXUWXUZS[P[NZLX",
    "c": "I[XPVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "d": "I\\XFX[ RXPVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "e": "I[LSXSXQWOVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "f": "MYWFUFSGRJR[ ROMVM",
    "g": "I\\XMX]W`VaTbQbOa RXPVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "h": "I\\MFM[ RMQPNRMUMWNXQX[",
    "i": "NVQFRGSFREQF RRMR[",
    "j": "MWRFSGTFSERF RSMS^RaPbNb",
    "k": "IZMFM[ RWMMW RQSX[",
    "l": "NVRFR[",
    "m": "CaGMG[ RGQJNLMOMQNRQR[ RRQUNWMZM\\N]Q][",
    "n": "I\\MMM[ RMQPNRMUMWNXQX[",
    "o": "I\\QMONMPLSLUMXOZQ[T[VZXXYUYSXPVNTMQM",
    "p": "H[LMLb RLPNNPMSMUNWPXSXUWXUZS[P[NZLX",
    "q": "I\\XMXb RXPVNTMQMONMPLSLUMXOZQ[T[VZXX",
    "r": "KXOMO[ ROSPPRNTMWM",
    "s": "J[XPWNTMQMNNMPNRPSUTWUXWXXWZT[Q[NZMX",
    "t": "MYRFRWSZU[W[ ROMVM",
    "u": "I\\MMMWNZP[S[UZXW RXMX[",
    "v": "JZLMR[ RXMR[",
    "w": "G]JMN[ RRMN[ RRMV[ RZMV[",
    "x": "J[MMX[ RXMM[",
    "y": "JZLMR[ RXMR[P_NaLbKb",
    "z": "J[XMM[ RMMXM RM[X[",
    "{": (
        "KYTBRCQDPFPHQJRKSMSOQQ RRCQEQGRISJTLTNSPORSTTVTXSZR[Q]Q_"
        "Ra RQSSUSWRYQZP\\P^Q`RaTb"
    ),
    "|": "NVRBRb",
    "}": (
        "KYPBRCSDTFTHSJRKQMQOSQ RRCSESGRIQJPLPNQPURQTPVPXQZR[S]S_"
        "Ra RSSQUQWRYSZT\\T^S`RaPb"
    ),
    "~": "F^IUISJPLONOPPTSVTXTZS[Q RISJQLPNPPQTTVUXUZT[Q[O",
}

# Drawn for scraftcam in the same style, not Hershey's (#276).
GLYPHS.update(
    {
        # The plus or minus sign.
        "±": "E_RIRW RIP[P RI[[[",
        # The degree sign.
        "°": "KYQFSFUHUJSLQLOJOHQF",
        # The diameter sign.
        "⌀": "F^PIMJKMKSMVPWTWWVYSYMWJTIPI RIZ[F",
    }
)
