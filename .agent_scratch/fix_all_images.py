import re

files = [
    "paper/sections/methodology.tex",
    "paper/sections/results.tex",
    "paper/sections/appendix.tex"
]

def fix_image_blocks(content):
    # Regex to find \includegraphics[...]
    # Replace it with \begin{adjustbox}{max width=\textwidth} \includegraphics{path} \end{adjustbox}
    # Also remove the [width=..., height=...] parameters to let adjustbox handle it.
    
    # First, let's fix the ols_residuals_6countries.png filename to residuals_breakdown.png
    content = content.replace("ols_residuals_6countries.png", "residuals_breakdown.png")
    
    # Regex pattern: \includegraphics[anything]{path}
    pattern = r'\\includegraphics\[.*?\]\{(.*?)\}'
    
    def replacer(match):
        path = match.group(1)
        return f'\\begin{{adjustbox}}{{max width=\\textwidth}}\n    \\includegraphics{{{path}}}\n  \\end{{adjustbox}}'
        
    # We might have some \includegraphics without [] 
    pattern_no_brackets = r'\\includegraphics\{(.*?)\}'
    
    new_content = re.sub(pattern, replacer, content)
    
    # For any remaining \includegraphics{path} that are not wrapped in adjustbox (be careful not to double wrap)
    # Actually, the first regex catches all of them because they all have [width=...].
    return new_content

for fpath in files:
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    
    new_text = fix_image_blocks(text)
    
    # Also ensure that adjustbox package is included in main.tex if not already, but it's used for tables so it's there.
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_text)

print("Images wrapped in adjustbox and fixed!")
