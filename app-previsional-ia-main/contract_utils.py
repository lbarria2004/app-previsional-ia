import re
import io
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from docxtpl import DocxTemplate
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
BASE_DIR = Path(__file__).parent.resolve()
TEMPLATE_OLD_AGE_FILENAME = "CONTRATO_SMART_OLD_AGE.docx" 
TEMPLATE_SMART_SURVIVORSHIP = "CONTRATO_SMART_SURVIVORSHIP.docx"

def extract_beneficiaries_from_report(report_text: str) -> List[Dict[str, str]]:
    """
    Extracts beneficiary data from the Markdown table in the report.
    Uses a flexible regex to find the section and parse the table rows.
    """
    beneficiaries = []
    
    # 1. Locate the section (Flexible regex for section title)
    match = re.search(r"Antecedentes del beneficiario", report_text, re.IGNORECASE)
    if not match:
        logger.warning("Could not find 'Antecedentes del beneficiario' section.")
        return []
        
    start_index = match.end()
    lines = report_text[start_index:].split('\n')
    table_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table: break
            continue
            
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                # Ignore separator lines like |---| or |:---:|
                if set(stripped.replace("|", "").replace(":", "").replace(" ", "").replace("-", "")) == set():
                   in_table = True
                   continue
                in_table = True
                table_lines.append(stripped)
            else:
                 # Check if it's another separator line
                 if set(stripped.replace("|", "").replace(":", "").replace(" ", "").replace("-", "")) == set():
                     continue
                 table_lines.append(stripped)
        elif in_table:
             break

    if not table_lines:
        return []

    # 2. Process Table
    header_map = {}
    data_lines = []
    
    col_keywords = {
        "nombre": "nombre",
        "rut": "rut",
        "parentesco": "parentesco",
        "sexo": "sexo",
        "inv": "invalidez",
        "nac": "fecha_nacimiento",
        "f. nac": "fecha_nacimiento"
    }
    
    header_found = False
    
    for i, line in enumerate(table_lines):
        cells = [c.strip() for c in line.strip('|').split('|')]
        lower_cells = [c.lower() for c in cells]
        
        # Detect if this is the header row
        if ("nombre" in " ".join(lower_cells)) and ("rut" in " ".join(lower_cells)):
            header_found = True
            for idx, cell_text in enumerate(lower_cells):
                 for kw, std_key in col_keywords.items():
                     if kw in cell_text:
                         header_map[idx] = std_key
                         break
            continue
        
        if header_found:
             data_lines.append(cells)
             
    # Fallback if no clear header was found
    if not header_found and table_lines:
         # Assume fixed order: Nombre, RUT, ... 
         header_map = {0: "nombre", 1: "rut", 2: "fecha_nacimiento", 3: "parentesco", 4: "sexo", 5: "invalidez"}
         data_lines = [ [c.strip() for c in l.strip('|').split('|')] for l in table_lines ]

    for cells in data_lines:
        row_data = {
            "nombre": "", 
            "rut": "", 
            "parentesco": "", 
            "fecha_nacimiento": "", 
            "sexo": "", 
            "invalidez": ""
        }
        for idx, cell_val in enumerate(cells):
            if idx in header_map:
                row_data[header_map[idx]] = cell_val
        
        # Only add rows that have at least a name or RUT
        if row_data.get("nombre") or row_data.get("rut"):
             beneficiaries.append(row_data)
             
    return beneficiaries

def get_contract_template_path(contract_type: str) -> Path:
    """Returns the absolute path to the requested DOCX template."""
    if contract_type == "Vejez o Invalidez":
        filename = TEMPLATE_OLD_AGE_FILENAME
    else:
        filename = TEMPLATE_SMART_SURVIVORSHIP
        
    template_path = BASE_DIR / filename
    
    if not template_path.exists():
        logger.error(f"Template not found at: {template_path}")
        # Try finding in root if BASE_DIR is subfolder
        root_path = Path("c:/Users/56951/Desktop/app-previsional-ia-main") / filename
        if root_path.exists():
            return root_path
        raise FileNotFoundError(f"Template file not found: {filename}")
        
    return template_path

def extract_contract_data(markdown_text: str) -> Dict[str, str]:
    """
    Extracts all possible fields from the Markdown report using robust regex patterns.
    This version restores all the detailed fields from the original implementation.
    """
    data: Dict[str, str] = {}
    if not markdown_text: return data

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
        "Fecha de Nacimiento": r"\*\*Fecha de Nacimiento:?\*\*\s*(.*)",
        "AFP de Origen": r"\*\*AFP de Origen:?\*\*\s*(.*)",
        "Institución de Salud": r"\*\*Institución de Salud:?\*\*\s*(.*)",
        "Sistema de Salud": r"\*\*Sistema de Salud:?\*\*\s*(.*)",
        "Tipo de Pensión Solicitada": r"\*\*Tipo de Pensión Solicitada:?\*\*\s*(.*)",
        "Oficio": r"\*\*(?:Oficio|Profesi[óo]n|Ocupaci[óo]n):?\*\*\s*(.*)",
        "Causante Nombre": r"\*\*Causante Nombre:?\*\*\s*(.*)",
        "Causante RUT": r"\*\*Causante RUT:?\*\*\s*(.*)",
        "Consultante Nombre": r"\*\*Consultante Nombre:?\*\*\s*(.*)",
        "Consultante RUT": r"\*\*Consultante RUT:?\*\*\s*(.*)",
        "Modalidades Solicitadas": r"\*\*Modalidades Solicitadas:?\*\*\s*(.*)",
        "Fecha Solicitud Ofertas": r"\*\*Fecha Solicitud de Ofertas:?\*\*\s*(.*)",
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, markdown_text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean up common placeholder or empty values
            if val and "No informada" not in val and "[Extraer" not in val:
                data[field] = val
            
    # Fallback for RUT if standard label fails
    if "RUT" not in data:
         rut_match = re.search(r"\b(\d{1,2}\.\d{3}\.\d{3}-[\dkK])\b", markdown_text)
         if rut_match:
             data["RUT"] = rut_match.group(1)

    # Extract beneficiaries and flatten them for form compatibility
    extracted_bens = extract_beneficiaries_from_report(markdown_text)
    for i, ben in enumerate(extracted_bens):
        idx = i + 1
        data[f"Beneficiario {idx} Nombre"] = ben.get("nombre", "")
        data[f"Beneficiario {idx} RUT"] = ben.get("rut", "")
        data[f"Beneficiario {idx} Parentesco"] = ben.get("parentesco", "")
        data[f"Beneficiario {idx} Fecha Nacimiento"] = ben.get("fecha_nacimiento", "")
        data[f"Beneficiario {idx} Sexo"] = ben.get("sexo", "")
        data[f"Beneficiario {idx} Invalidez"] = ben.get("invalidez", "")
    
    return data

def fill_beneficiary_placeholders(doc: DocxTemplate, beneficiaries: List[Dict[str, str]]):
    """
    Manually fills beneficiary placeholders in the document.
    Supports both Tables (with dynamic expansion) and Paragraphs (fallback for first beneficiary).
    """
    if not beneficiaries: beneficiaries = []
        
    placeholders_map = {
        "{NOMBRE BENEFICIARIO}": "nombre",
        "{RUT BENEFICIARIO}": "rut",
        "{FECHA NACIMIENTO  BENEFICIARIO}": "fecha_nacimiento", 
        "{FECHA NACIMIENTO BENEFICIARIO}": "fecha_nacimiento",
        "{PARENTESCO}": "parentesco",
        "{F o M}": "sexo",
        "{SI o No}": "invalidez"
    }
    
    # 1. PROCESS TABLES (Preferred for dynamic listing)
    if hasattr(doc, 'tables'):
        tables = doc.tables
    elif hasattr(doc, 'docx') and hasattr(doc.docx, 'tables'):
        tables = doc.docx.tables
    else:
        tables = []

    for table in tables:
        is_beneficiary_table = False
        template_row = None
        
        for i, row in enumerate(table.rows):
            row_text = "".join(cell.text for cell in row.cells)
            if "{NOMBRE BENEFICIARIO}" in row_text:
                is_beneficiary_table = True
                template_row = row
                break
        
        if is_beneficiary_table and template_row:
            # Fill the template line with the first beneficiary
            if len(beneficiaries) > 0:
                _fill_row(template_row, beneficiaries[0], placeholders_map)
            else:
                 _fill_row(template_row, {}, placeholders_map)

            # Add rows for subsequent beneficiaries
            for i in range(1, len(beneficiaries)):
                ben = beneficiaries[i]
                new_row = table.add_row()
                # Copy cell structure/text from template row
                for j, cell in enumerate(template_row.cells):
                    if j < len(new_row.cells):
                        new_row.cells[j].text = cell.text
                _fill_row(new_row, ben, placeholders_map)

    # 2. PROCESS PARAGRAPHS (Fallback for templates without tables)
    if len(beneficiaries) > 0:
        first_ben = beneficiaries[0]
        # Get paragraphs robustly
        if hasattr(doc, 'paragraphs') and doc.paragraphs is not None:
            paragraphs = doc.paragraphs
        elif hasattr(doc, 'docx') and doc.docx is not None and hasattr(doc.docx, 'paragraphs'):
            paragraphs = doc.docx.paragraphs
        else:
            paragraphs = []
            
        for paragraph in paragraphs:
            _replace_placeholders_in_paragraph(paragraph, first_ben, placeholders_map)

def _fill_row(row, data: Dict[str, str], placeholders_map: Dict[str, str]):
    """Helper for table rows that replaces placeholders in each cell."""
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            _replace_placeholders_in_paragraph(paragraph, data, placeholders_map)

def _replace_placeholders_in_paragraph(paragraph, data: Dict[str, str], placeholders_map: Dict[str, str]):
    """
    Substitutes text in a paragraph. Uses the 'run-clearing' technique to prevent
    formatting issues or split placeholders (proposed by user).
    """
    text = paragraph.text
    if not text: return
    
    # Check if any placeholder exists in this paragraph
    has_any = any(ph in text for ph in placeholders_map.keys())
    
    if has_any:
        new_text = text
        for ph, key in placeholders_map.items():
            val = data.get(key, "")
            if val is None: val = ""
            new_text = new_text.replace(ph, str(val))
        
        # CLEAR ALL EXISTING RUNS to avoid split tags (User proposal)
        if paragraph.runs:
            for run in paragraph.runs:
                run.text = ""
            # Set target text in the first run
            paragraph.runs[0].text = new_text
        else:
            # Create a new run if none exist
            paragraph.add_run(new_text)

def generate_contract_docx(template_path: Path, context: Dict[str, Any], beneficiaries_list: Optional[List[Dict[str, str]]] = None) -> bytes:
    """
    Orchestrates the DOCX generation using DocxTpl and manual placeholder replacement.
    Ensures Jinja2 rendering happens before manual filling as per user proposal.
    """
    try:
        if not template_path.exists():
             raise FileNotFoundError(f"Template not found at {template_path}")

        # Load template
        doc = DocxTemplate(str(template_path))
        
        # Ensure beneficiaries list is in context
        if beneficiaries_list:
            context['beneficiaries'] = beneficiaries_list
        
        # 1. RENDER JINJA2 VARIABLES (e.g., {{ nombre_afiliado }})
        # This is done first so simple tags are cleared before manual logic starts.
        doc.render(context)
        
        # 2. MANUAL REPLACEMENT (e.g., {NOMBRE BENEFICIARIO})
        # This handles table expansion and paragraph fallbacks.
        if beneficiaries_list:
             fill_beneficiary_placeholders(doc, beneficiaries_list)
        else:
             # Even with no beneficiaries, clean up placeholders in the doc
             fill_beneficiary_placeholders(doc, [])
                        
        # Save to memory buffer
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating contract: {e}", exc_info=True)
        raise e
