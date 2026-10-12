import re
import docx
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from pathlib import Path

def create_docx(md_path, docx_path):
    doc = docx.Document()
    
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_table = False
    table_rows = []
    
    def process_table():
        if not table_rows:
            return
        
        rows = [r for r in table_rows if not re.match(r'^[|\s-]*$', r.strip())]
        if not rows:
            return
            
        num_cols = len([x for x in rows[0].strip().split('|') if x.strip() or True]) - 2 
        if num_cols <= 0:
            return
            
        table = doc.add_table(rows=len(rows), cols=num_cols)
        table.style = 'Table Grid'
        
        for i, row in enumerate(rows):
            cells = [x.strip() for x in row.strip().split('|')][1:-1]
            for j, cell_text in enumerate(cells):
                if j < num_cols:
                    text = cell_text.replace('**', '').replace('__', '')
                    table.cell(i, j).text = text
                    
        doc.add_paragraph()

    def process_inline_markdown(p, text):
        # Extremely simple bold/italic parser that ensures we strip the asterisks
        # Split by ** or __ for bold
        parts = re.split(r'(\*\*.*?\*\*|__.*?__)', text)
        for part in parts:
            if (part.startswith('**') and part.endswith('**')) or (part.startswith('__') and part.endswith('__')):
                run = p.add_run(part[2:-2])
                run.bold = True
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                run = p.add_run(part[1:-1])
                run.italic = True
            else:
                # clean up any leftover basic asterisks if needed (or just leave text)
                clean_part = part.replace('`', '')
                p.add_run(clean_part)

    in_code_block = False

    for line in lines:
        line = line.strip()
        
        if line.startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            p = doc.add_paragraph(line)
            # Use Courier New for code blocks
            for run in p.runs:
                run.font.name = 'Courier New'
            continue
            
        if not line:
            if in_table:
                process_table()
                table_rows = []
                in_table = False
            continue
            
        if line.startswith('|'):
            in_table = True
            table_rows.append(line)
            continue
            
        if in_table:
            process_table()
            table_rows = []
            in_table = False
            
        # Headings
        if line.startswith('### '):
            doc.add_heading(line[4:].replace('**', ''), level=3)
        elif line.startswith('## '):
            doc.add_heading(line[3:].replace('**', ''), level=2)
        elif line.startswith('# '):
            h = doc.add_heading(line[2:].replace('**', ''), level=1)
            h.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        # Horizontal rules
        elif line == '---':
            doc.add_paragraph('_' * 50)
        # Lists
        elif line.startswith('- '):
            p = doc.add_paragraph(style='List Bullet')
            process_inline_markdown(p, line[2:])
        # Blockquotes
        elif line.startswith('> '):
            p = doc.add_paragraph(style='Quote')
            process_inline_markdown(p, line[2:])
        # Images
        elif line.startswith('![') and '](' in line and line.endswith(')'):
            img_path = line.split('](')[1][:-1]
            img_full_path = Path("docs") / img_path
            if img_full_path.exists():
                doc.add_picture(str(img_full_path), width=Inches(6.0))
            else:
                p = doc.add_paragraph(f"[Image not found: {img_path}]")
        # Normal text
        else:
            p = doc.add_paragraph()
            process_inline_markdown(p, line)

    if in_table:
        process_table()

    doc.save(docx_path)
    print(f"Created {docx_path}")

if __name__ == "__main__":
    md = Path("docs/Assignment_3_Report.md")
    out = Path("docs/Assignment_3_Report.docx")
    create_docx(md, out)
