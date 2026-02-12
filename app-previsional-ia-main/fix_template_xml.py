import zipfile
import re
import os
import shutil

def fix_docx_xml(docx_path, output_path):
    temp_dir = "temp_docx_extract"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    # Process word/document.xml
    xml_path = os.path.join(temp_dir, "word", "document.xml")
    
    if os.path.exists(xml_path):
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to find integer attributes getting float values
        # Attributes causing issues: left, right, top, bottom, header, footer, gutter, w, h, space
        # Pattern: attribute="123.456"
        # We target specific attributes in w: namespace usually.
        # But simply replacing any quote-enclosed float with int is risky?
        # Let's target the known offender: w:left, w:right, w:top, w:bottom, w:header, w:footer, w:gutter
        # Also w:w, w:h (page size), w:space (cols)
        
        attributes = ["left", "right", "top", "bottom", "header", "footer", "gutter", "w", "h", "space"]
        
        def replace_float(match):
            full_str = match.group(0) # e.g. w:left="1077.165..."
            val = match.group(2) # 1077.165...
            try:
                int_val = int(float(val))
                return full_str.replace(val, str(int_val))
            except:
                return full_str

        for attr in attributes:
            # Pattern: w:attr="123.456"
            # We match strict structure
            pattern = rf'(w:{attr}=")(\d+\.\d+)(")'
            content = re.sub(pattern, replace_float, content)
            
        # Write back
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    # Zip back
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_out.write(file_path, arcname)
                
    # Cleanup
    shutil.rmtree(temp_dir)
    print(f"Fixed XML and saved to: {output_path}")

if __name__ == "__main__":
    fix_docx_xml("CONTRATO 2026 sobrevivencia -  plantilla.docx", "CONTRATO_FIXED_SURVIVORSHIP.docx")
    fix_docx_xml("CONTRATO 2026 AP - PLANTILLA.docx", "CONTRATO_FIXED_OLD_AGE.docx")
