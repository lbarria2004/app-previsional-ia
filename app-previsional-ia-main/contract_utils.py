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
