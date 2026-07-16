with open("paper/sections/methodology.tex", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the broken tikzpicture
text = text.replace(
    "    every node/.style={draw, rectangle, rounded corners, inner sep=10pt, align=center, font=\\small},\n      arrow/.style={->, >=stealth, thick}\n    ]\n      \\node (weather) {Thời tiết \\& Khí hậu \\\\ (Wind, Solar, Temp)};",
    """    \\begin{adjustbox}{max width=\\textwidth}
    \\begin{tikzpicture}[
      node distance=2.5cm and 3cm,
      every node/.style={draw, rectangle, rounded corners, inner sep=10pt, align=center, font=\\small},
      arrow/.style={->, >=stealth, thick}
    ]
      \\node (weather) {Thời tiết \\& Khí hậu \\\\ (Wind, Solar, Temp)};"""
)

# And add the end adjustbox
text = text.replace(
    "      \\draw[arrow] (fuel) -- (price) node[midway, below, sloped, draw=none] {+};\n  \\end{tikzpicture}\n    \\captionof{figure}",
    "      \\draw[arrow] (fuel) -- (price) node[midway, below, sloped, draw=none] {+};\n    \\end{tikzpicture}\n    \\end{adjustbox}\n    \\captionof{figure}"
)

# Just in case the second replace fails because of indentation, let's do a regex for the end block
import re
text = re.sub(r'(\\draw\[arrow\] \(fuel\).*?\{.*?\}\;)(\s*)\\end\{tikzpicture\}', r'\1\2\\end{tikzpicture}\n    \\end{adjustbox}', text, flags=re.DOTALL)

with open("paper/sections/methodology.tex", "w", encoding="utf-8") as f:
    f.write(text)

print("Tikzpicture fixed!")
