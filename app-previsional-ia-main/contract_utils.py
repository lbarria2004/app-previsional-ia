import re
import io
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from docxtpl import DocxTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
BASE_DIR = Path(__file__).parent.resolve()
# We now use the smart template for survivorship
TEMPLATE_OLD_AGE_FILENAME = "CONTRATO_SMART_OLD_AGE.docx" 
TEMPLATE_SMART_SURVIVORSHIP = "CONTRATO_SMART_SURVIVORSHIP.docx"
import re

def extract_beneficiaries_from_report(report_text: str) -> List[Dict[str, str]]:
    """
    Extracts beneficiary data from the 'Antecedentes del beneficiario' Markdown table in the report.
    Returns a list of dictionaries with keys: 'nombre', 'rut', 'parentesco', etc.
    """
    beneficiaries = []
    
    # 1. Locate the section
    # The header might vary: "2) Antecedentes...", "## Antecedentes...", "2. Antecedentes"
    # We look for "Antecedentes del beneficiario" case-insensitive
    
    match = re.search(r"(?:##|\d+[\.\)])\s*Antecedentes del beneficiario", report_text, re.IGNORECASE)
    if not match:
        logger.warning("Could not find 'Antecedentes del beneficiario' section.")
        return []
        
    start_index = match.end()
    
    # 2. Find the table after this section
    # We look for the next markdown table
    # A markdown table row starts and ends with |
    
    lines = report_text[start_index:].split('\n')
    table_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table: break # End of table (empty line after table)
            continue
            
        # Check if it's a table row (starts and ends with |)
        # Note: sometimes whitespace exists before/after |
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                # Is it a separator line? |---|
                # If so, we are in table but this line is skipped
                if set(stripped.replace("|", "").replace(":", "").replace(" ", "")) == {'-'}:
                   in_table = True # Use this as confirmation we are in table
                   continue
                
                # It's a header or data row
                in_table = True
                table_lines.append(stripped)
            else:
                 # Standard data row or separator
                 if set(stripped.replace("|", "").replace(":", "").replace(" ", "")) == {'-'}:
                     continue
                 table_lines.append(stripped)
        elif in_table:
             # We met a non-table line after being in table
             break
        elif len(table_lines) > 0 and not in_table:
             # Should not happen if logic matches above
             break

    if not table_lines:
        logger.warning("Found section but no table found.")
        return []

    # 3. Process the table
    # Attempt to identify headers
    # We look for a row containing "Nombre" and "RUT"
    
    header_map = {} # Col Match Index -> Standard Key
    data_lines = []
    
    # Keywords to identify columns
    col_keywords = {
        "nombre": "nombre",
        "rut": "rut",
        "parentesco": "parentesco",
        # Optional fields
        "sexo": "sexo",
        "inv": "invalidez", # Covers "Inv", "Invalidez"
        "nac": "fecha_nacimiento", # Covers "F. Nac", "Nacimiento", "Fecha N"
    }
    
    header_found = False
    
    for i, line in enumerate(table_lines):
        cells = [c.strip() for c in line.strip('|').split('|')]
        lower_cells = [c.lower() for c in cells]
        
        # Heuristic: Is this a header row?
        # Check if it contains at least "nombre" and "rut" (or "parentesco")
        if ("nombre" in lower_cells[0] or "nombre" in " ".join(lower_cells)) and \
           ("rut" in " ".join(lower_cells)):
            
            # This is the header row
            header_found = True
            for idx, cell_text in enumerate(lower_cells):
                 for kw, std_key in col_keywords.items():
                     if kw in cell_text:
                         header_map[idx] = std_key
                         break # Map to first match
            continue
        
        # If it's not a header, treat as data IF we found a header OR if we have to guess
        if header_found:
             data_lines.append(cells)
        else:
             # If we haven't found a header yet, keep looking.
             # But if this is the ONLY row, maybe it's data without header? Unlikely in markdown.
             # Let's assume strict markdown table with header.
             pass
             
    # If no header found, try to use default mapping (0:Name, 1:RUT, 2:Parentesco)
    if not header_map and table_lines:
         logger.warning("No header row identified. Using default mapping (0:Name, 1:RUT, 2:Parentesco).")
         header_map = {0: "nombre", 1: "rut", 2: "parentesco"}
         data_lines = [ [c.strip() for c in l.strip('|').split('|')] for l in table_lines ]

    # Verify we caught data
    for cells in data_lines:
        row_data = {}
        # Default empty strings
        for k in ["nombre", "rut", "parentesco"]: row_data[k] = ""
        
        for idx, cell_val in enumerate(cells):
            if idx in header_map:
                row_data[header_map[idx]] = cell_val
        
        # Validation: Must have at least a Name or RUT
        if row_data.get("nombre") or row_data.get("rut"):
             beneficiaries.append(row_data)
             
    logger.info(f"Extracted {len(beneficiaries)} beneficiaries.")
    return beneficiaries

def get_contract_template_path(contract_type: str) -> Path:
    """
    Returns the path to the DOCX template based on the contract type.
    """
    if contract_type == "Vejez o Invalidez":
        filename = TEMPLATE_OLD_AGE_FILENAME
    else:
        # Use the new smart template for Survivorship
        filename = TEMPLATE_SMART_SURVIVORSHIP
        
    template_path = BASE_DIR / filename
    
    if not template_path.exists():
        logger.error(f"Template not found at: {template_path}")
        raise FileNotFoundError(f"Template file not found: {filename}")
        
    return template_path

def extract_contract_data(markdown_text: str) -> Dict[str, str]:
    """
    Extracts relevant contract data from Markdown report.
    Returns raw data. The mapping to template keys happens later.
    """
    data: Dict[str, str] = {}
    if not markdown_text:
        return data

    # Regex patterns for extraction
    patterns = {
        "Nombre Completo": r"\*\*Nombre Completo:?\*\*\s*(.*)",
        "RUT": r"\*\*RUT:?\*\*\s*(.*)",
        "Dirección": r"\*\*(?:Direcci[óo]n|Domicilio):?\*\*\s*(.*)", 
        "Comuna": r"\*\*Comuna:?\*\*\s*(.*)",
        "Ciudad": r"\*\*Ciudad:?\*\*\s*(.*)",
        "Teléfono": r"\*\*Tel[ée]fono:?\*\*\s*(.*)",
        "Celular": r"\*\*Celular:?\*\*\s*(.*)",
        "Correo Electrónico": r"\*\*Correo.*?:?\*\*\s*(.*)",
        "Estado Civil": r"\*\*Estado Civil:?\*\*\s*(.*)",
        "Cédula de Identidad": r"\*\*Cédula.*?:?\*\*\s*(.*)",
        "Fecha de Nacimiento": r"\*\*Fecha de Nacimiento:?\*\*\s*(.*)",
        "AFP de Origen": r"\*\*AFP de Origen:?\*\*\s*(.*)",
        "Institución de Salud": r"\*\*Institución de Salud:?\*\*\s*(.*)",
        "Sistema de Salud": r"\*\*Sistema de Salud:?\*\*\s*(.*)",
        "Tipo de Pensión Solicitada": r"\*\*Tipo de Pensión Solicitada:?\*\*\s*(.*)",
        "Oficio": r"\*\*(?:Oficio|Profesi[óo]n|Ocupaci[óo]n):?\*\*\s*(.*)",
        # Survivorship Specifics
        "Causante Nombre": r"\*\*Causante Nombre:?\*\*\s*(.*)",
        "Causante RUT": r"\*\*Causante RUT:?\*\*\s*(.*)",
        "Consultante Nombre": r"\*\*Consultante Nombre:?\*\*\s*(.*)",
        "Consultante RUT": r"\*\*Consultante RUT:?\*\*\s*(.*)",
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, markdown_text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean up placeholders if extraction failed
            if val and "No informada" not in val and "[Extraer" not in val:
                data[field] = val
            
    # Fallback for RUT if pattern match failed or wasn't found
    if "RUT" not in data:
         rut_match = re.search(r"\b(\d{1,2}\.\d{3}\.\d{3}-[\dkK])\b", markdown_text)
         if rut_match:
             data["RUT"] = rut_match.group(1)

    # --- Beneficiary Extraction (Unified) ---
    extracted_bens = extract_beneficiaries_from_report(markdown_text)
    
    # Flatten for session_state/form compatibility
    for i, ben in enumerate(extracted_bens):
        idx = i + 1
        data[f"Beneficiario {idx} Nombre"] = ben.get("nombre", "")
        data[f"Beneficiario {idx} RUT"] = ben.get("rut", "")
        data[f"Beneficiario {idx} Parentesco"] = ben.get("parentesco", "")
        if ben.get("sexo"): data[f"Beneficiario {idx} Sexo"] = ben.get("sexo")
        if ben.get("invalidez"): data[f"Beneficiario {idx} Invalidez"] = ben.get("invalidez")
        if ben.get("fecha_nacimiento"): data[f"Beneficiario {idx} Fecha de Nacimiento"] = ben.get("fecha_nacimiento")
    
    return data

def fill_beneficiary_placeholders(doc: DocxTemplate, beneficiaries: List[Dict[str, str]]):
    """
    Manually replaces placeholders like {NOMBRE BENEFICIARIO} in the document tables
    with data from the beneficiaries list.
    """
    if not beneficiaries:
        beneficiaries = []
        
    # Standardize keys for replacement
    # User requested specific placeholders:
    # {NOMBRE BENEFICIARIO} -> nombre
    # {RUT BENEFICIARIO} -> rut
    # {FECHA NACIMIENTO  BENEFICIARIO} -> fecha_nacimiento
    # {PARENTESCO} -> parentesco
    # {F o M} -> sexo
    # {SI o No} -> invalidez
    
    placeholders_map = {
        "{NOMBRE BENEFICIARIO}": "nombre",
        "{RUT BENEFICIARIO}": "rut",
        "{FECHA NACIMIENTO  BENEFICIARIO}": "fecha_nacimiento", # Double space in user prompt
        "{FECHA NACIMIENTO BENEFICIARIO}": "fecha_nacimiento", # Single space variant
        "{PARENTESCO}": "parentesco",
        "{F o M}": "sexo",
        "{SI o No}": "invalidez"
    }
    
    # We iterate over tables to find rows with these placeholders
    # We treat the beneficiaries list as a queue.
    # Each time we find a row with {NOMBRE BENEFICIARIO}, we consume one beneficiary.
    
    ben_idx = 0
    
    # Check for tables attribute, fallback to doc.docx.tables if needed (for older docxtpl)
    if hasattr(doc, 'tables'):
        tables = doc.tables
    elif hasattr(doc, 'docx') and hasattr(doc.docx, 'tables'):
        tables = doc.docx.tables
    else:
        logger.error(f"Doc object {type(doc)} has no 'tables' attribute. Dir: {dir(doc)}")
        return

    for table in tables:
        # Check if this table is the beneficiary table
        is_beneficiary_table = False
        template_row = None
        template_row_index = -1
        
        for i, row in enumerate(table.rows):
            row_text = "".join(cell.text for cell in row.cells)
            if "{NOMBRE BENEFICIARIO}" in row_text:
                is_beneficiary_table = True
                template_row = row
                template_row_index = i
                break
        
        if is_beneficiary_table and template_row:
            # Found the table and the template row.
            # We will use this row for the first beneficiary, 
            # and append copies for subsequent ones.
            
            # 1. Fill the FIRST beneficiary (using the existing template row)
            if len(beneficiaries) > 0:
                first_ben = beneficiaries[0]
                _fill_row(template_row, first_ben, placeholders_map)
            else:
                 # No beneficiaries: Clear the placeholders in the template row
                 _fill_row(template_row, {}, placeholders_map)

            # 2. Add rows for REMAINING beneficiaries
            for i in range(1, len(beneficiaries)):
                ben = beneficiaries[i]
                # Add a new row to the table
                new_row = table.add_row()
                
                # Copy cells from template row to new row
                # We need to copy content/style if possible, but for simplicity
                # we just ensure we have the same number of cells and copy the text with placeholders
                # effectively cloning the structure to then replace placeholders.
                
                # However, add_row() creates empty cells. We need to match the grid.
                # Since we want to copy the *structure* of the template row (placeholders):
                
                for j, cell in enumerate(template_row.cells):
                    # Ensure new row has enough cells (it should matches columns)
                    if j < len(new_row.cells):
                        new_cell = new_row.cells[j]
                        # Copy text from template (which has placeholders)
                        # We copy the verification text so we can replace it
                        new_cell.text = cell.text
                
                # Now fill the new row with the beneficiary data
                _fill_row(new_row, ben, placeholders_map)

def _fill_row(row, data: Dict[str, str], placeholders_map: Dict[str, str]):
    """Helper to replace placeholders in a specific row object."""
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            modified = False
            # Run-level replacement (preserves formatting)
            for run in paragraph.runs:
                for ph, key in placeholders_map.items():
                    if ph in run.text:
                        val = data.get(key, "")
                        if val is None: val = ""
                        run.text = run.text.replace(ph, str(val))
                        modified = True
            
            # Paragraph-level fallback
            if not modified and any(ph in paragraph.text for ph in placeholders_map):
                original_text = paragraph.text
                new_text = original_text
                for ph, key in placeholders_map.items():
                    val = data.get(key, "")
                    if val is None: val = ""
                    new_text = new_text.replace(ph, str(val))
                
                if new_text != original_text:
                    paragraph.text = new_text

def generate_contract_docx(template_path: Path, context: Dict[str, Any], beneficiaries_list: Optional[List[Dict[str, str]]] = None) -> bytes:
    """
    Generates a filled DOCX contract using docxtpl.
    
    Args:
        template_path: Path to the .docx template file.
        context: Dictionary of data to insert (Jinja2 context).
        beneficiaries_list: Optional list of beneficiaries. 
                            If provided, it should be under key 'beneficiaries' in context,
                            but we accept it as arg for compatibility.
        
    Returns:
        Bytes of the generated DOCX file.
    """
    try:
        if not template_path.exists():
             raise FileNotFoundError(f"Template not found at {template_path}")

        # Load with DocxTemplate
        doc = DocxTemplate(str(template_path))
        
        # Merge beneficiaries into context if provided separately
        if beneficiaries_list:
            context['beneficiaries'] = beneficiaries_list
        
        # --- CUSTOM FIX FOR BENEFICIARIES ---
        # Manually fill the custom placeholders {NOMBRE BENEFICIARIO} etc.
        # We pass the list of beneficiaries to fill sequentially.
        if beneficiaries_list:
             fill_beneficiary_placeholders(doc, beneficiaries_list)
        # ------------------------------------

        # Debug: Log the context keys
        logger.info(f"Generating contract with keys: {list(context.keys())}")
        if 'beneficiaries' in context:
            logger.info(f"Beneficiaries count: {len(context['beneficiaries'])}")

        # Render
        doc.render(context)
                        
        # Save to memory buffer
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating contract: {e}", exc_info=True)
        raise e
