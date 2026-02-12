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
    # The header might vary slightly: "2) Antecedentes...", "## Antecedentes...", etc.
    # We look for the phrase "Antecedentes del beneficiario"
    
    match = re.search(r"(?:##|\d+\))\s*Antecedentes del beneficiario", report_text, re.IGNORECASE)
    if not match:
        logger.warning("Could not find 'Antecedentes del beneficiario' section.")
        return []
        
    start_index = match.end()
    
    # 2. Find the table after this section
    # A markdown table starts with | ... | and a separator line |---|
    
    # We scan lines after the header
    lines = report_text[start_index:].split('\n')
    table_lines = []
    headers = []
    
    in_table = False
    for line in lines:
        line = line.strip()
        if not line:
            if in_table: break # End of table
            continue
            
        if line.startswith('|') and line.endswith('|'):
            if not in_table:
                # This could be headers or separator
                # If it's the separator line (only - and |), we ignore it but mark start
                if set(line.replace("|", "").strip()) == {'-'}:
                    continue
                
                # Assume first row found is header if we haven't found separator yet?
                # Actually standard markdown table:
                # Header
                # Separator
                # Data
                
                # Let's collect all table-like lines and then process
                in_table = True
                table_lines.append(line)
            else:
                table_lines.append(line)
        elif in_table:
            break # Stop if we hit a non-table line after starting
            
    # Process table lines
    # We expect the first line to be headers if it's not a separator
    # But usually extract logic is: find header row, then data rows.
    
    # Let's refine:
    # 1. Identify Header Row (contains "Nombre", "RUT", "Parentesco")
    # 2. Identify Data Rows
    
    data_rows = []
    header_map = {} # Col Index -> Key
    
    for i, line in enumerate(table_lines):
        # Skip separator lines
        if set(line.replace("|", "").strip()).issubset({'-', ':', ' '}):
            continue
            
        cells = [c.strip() for c in line.strip('|').split('|')]
        
        # Check if it's a header row
        lower_cells = [c.lower() for c in cells]
        if "nombre" in lower_cells[0] or "nombre completo" in lower_cells[0]:
            # Map columns
            for idx, cell in enumerate(lower_cells):
                if "nombre" in cell: header_map[idx] = "nombre"
                elif "rut" in cell: header_map[idx] = "rut"
                elif "parentesco" in cell: header_map[idx] = "parentesco"
                elif "sexo" in cell: header_map[idx] = "sexo"
                elif "invalidez" in cell: header_map[idx] = "invalidez"
                elif "nacimiento" in cell or "f. nac" in cell: header_map[idx] = "fecha_nacimiento"
        else:
            # Data row
            if header_map:
                row_data = {}
                # Default values
                row_data["nombre"] = ""
                row_data["rut"] = ""
                row_data["parentesco"] = ""
                
                for idx, cell in enumerate(cells):
                    if idx in header_map:
                        key = header_map[idx]
                        row_data[key] = cell
                
                if row_data["nombre"]: # Only add if we have a name
                    # Clean up data
                    beneficiaries.append(row_data)
    
    logger.info(f"Extracted {len(beneficiaries)} beneficiaries from report.")
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
            if val and "No informada" not in val and "[Extraer" not in val:
                data[field] = val
            
    # Fallback for RUT
    if "RUT" not in data:
         rut_match = re.search(r"\b(\d{1,2}\.\d{3}\.\d{3}-[\dkK])\b", markdown_text)
         if rut_match:
             data["RUT"] = rut_match.group(1)

    # --- Beneficiary Extraction ---
    # Parse Markdown table for beneficiaries
    section_2_match = re.search(r"### 2\) Antecedentes del beneficiario.*?(?=### 3\))", markdown_text, re.DOTALL)
    if section_2_match:
        section_2_text = section_2_match.group(0)
        lines = section_2_text.split('\n')
        ben_index = 1
        
        for line in lines:
            if "|" in line and "Nombre Completo" not in line and "---" not in line:
                cols = [c.strip() for c in line.split('|') if c.strip()]
                if len(cols) >= 3:
                     data[f"Beneficiario {ben_index} Nombre"] = cols[0]
                     data[f"Beneficiario {ben_index} RUT"] = cols[1]
                     data[f"Beneficiario {ben_index} Parentesco"] = cols[2]
                     
                     if len(cols) >= 4: data[f"Beneficiario {ben_index} Sexo"] = cols[3]
                     if len(cols) >= 5: data[f"Beneficiario {ben_index} Invalidez"] = cols[4]
                     if len(cols) >= 6: data[f"Beneficiario {ben_index} Fecha de Nacimiento"] = cols[5]
                     
                     ben_index += 1
                     if ben_index > 10: break
    
    return data

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
