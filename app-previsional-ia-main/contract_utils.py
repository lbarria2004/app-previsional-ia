import re
import io
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from docx import Document  # type: ignore
from docx.text.paragraph import Paragraph  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
# Using absolute paths or relative to the script location is safer
BASE_DIR = Path(__file__).parent.resolve()
TEMPLATE_OLD_AGE_FILENAME = "CONTRATO 2026 AP - PLANTILLA.docx"
TEMPLATE_SURVIVORSHIP_FILENAME = "CONTRATO 2026 sobrevivencia -  plantilla.docx"

def get_contract_template_path(contract_type: str) -> Path:
    """
    Returns the path to the DOCX template based on the contract type.
    
    Args:
        contract_type: The type of contract (e.g., "Vejez o Invalidez").
        
    Returns:
        Path object to the template file.
        
    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    if contract_type == "Vejez o Invalidez":
        filename = TEMPLATE_OLD_AGE_FILENAME
    else:
        filename = TEMPLATE_SURVIVORSHIP_FILENAME
        
    template_path = BASE_DIR / filename
    
    if not template_path.exists():
        logger.error(f"Template not found at: {template_path}")
        raise FileNotFoundError(f"Template file not found: {filename}")
        
    return template_path

def extract_contract_data(markdown_text: str) -> Dict[str, str]:
    """
    Extracts relevant contract data (Name, RUT, Address, etc.) from a Markdown report.
    
    Args:
        markdown_text: The content of the markdown report.
        
    Returns:
        A dictionary with extracted fields.
    """
    data: Dict[str, str] = {}
    if not markdown_text:
        return data

    # Regex patterns for extraction
    # Using case-insensitive search and handling potential markdown formatting variations
    patterns = {
        "Nombre Completo": r"\*\*Nombre Completo:?\*\*\s*(.*)",
        "RUT": r"\*\*RUT:?\*\*\s*(.*)",
        # Updated to catch "Dirección", "Direccion", "Domicilio", etc.
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
        # New Fields for Solicitud de Ofertas
        "Fecha Solicitud de Ofertas": r"\*\*Fecha Solicitud de Ofertas:?\*\*\s*(.*)",
        "Modalidades Solicitadas": r"\*\*Modalidades Solicitadas:?\*\*\s*(.*)",
        # Survivorship Specifics
        "Causante Nombre": r"\*\*Causante Nombre:?\*\*\s*(.*)",
        "Causante RUT": r"\*\*Causante RUT:?\*\*\s*(.*)",
        "Consultante Nombre": r"\*\*Consultante Nombre:?\*\*\s*(.*)",
        "Consultante RUT": r"\*\*Consultante RUT:?\*\*\s*(.*)",
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, markdown_text, re.IGNORECASE)
        if match:
            # Clean up the extracted text (remove trailing periods, markdown artifacts)
            val = match.group(1).strip()
            # Filter out placeholder or invalid values
            if val and "No informada" not in val and "[Extraer" not in val:
                data[field] = val
            
    # Fallback for RUT if not found by specific label
    if "RUT" not in data:
         # Looks for standard Chilean RUT format: XX.XXX.XXX-X
         rut_match = re.search(r"\b(\d{1,2}\.\d{3}\.\d{3}-[\dkK])\b", markdown_text)
         if rut_match:
             data["RUT"] = rut_match.group(1)

    # --- Beneficiary Extraction ---
    # Looks for "Beneficiario X [Nombre|RUT|Parentesco|Sexo|Invalidez|Fecha de Nacimiento]: Value"
    # We iterate to find up to 5 beneficiaries (arbitrary limit)
    for i in range(1, 6):
        # Regex for specific beneficiary fields
        ben_patterns = {
            f"Beneficiario {i} Nombre": rf"\*\*Beneficiario {i} Nombre:?\*\*\s*(.*)",
            f"Beneficiario {i} RUT": rf"\*\*Beneficiario {i} RUT:?\*\*\s*(.*)",
            f"Beneficiario {i} Parentesco": rf"\*\*Beneficiario {i} Parentesco:?\*\*\s*(.*)",
            f"Beneficiario {i} Sexo": rf"\*\*Beneficiario {i} Sexo:?\*\*\s*(.*)",
            f"Beneficiario {i} Invalidez": rf"\*\*Beneficiario {i} Invalidez:?\*\*\s*(.*)",
            f"Beneficiario {i} Fecha de Nacimiento": rf"\*\*Beneficiario {i} Fecha de Nacimiento:?\*\*\s*(.*)",
        }
        
        found_any = False
        for field_key, pattern in ben_patterns.items():
             match = re.search(pattern, markdown_text, re.IGNORECASE)
             if match:
                 val = match.group(1).strip()
                 if val and "No informada" not in val and "[Extraer" not in val:
                    data[field_key] = val
                    found_any = True
        
        # If we didn't find any data for Beneficiary X, we assume there are no more
        if not found_any:
            break

    return data

def _replace_text_in_paragraph(paragraph: Paragraph, replacements: Dict[str, str]) -> None:
    """
    Helper function to replace text within a DOCX paragraph.
    Handles both {{KEY}} placeholders and underscore lines (e.g., "Name: _______").
    
    Args:
        paragraph: The paragraph object from python-docx.
        replacements: Dictionary of keys to replace.
    """
    text = paragraph.text
    original_text = text
    
    # 1. Direct Placeholder Replacement {{KEY}}
    for key, value in replacements.items():
        if key in text and value:
            text = text.replace(key, str(value))
            
    # 2. Underscore Line Replacement
    # Example: "Nombre: ________________" -> "Nombre: Juan Perez"
    if "_" * 5 in text:
        # Map labels in the doc to keys in our data dictionary
        # This mapping covers common labels found in the templates
        label_map = {
            "Nombre": replacements.get("{{NOMBRE}}", ""),
            "Señor": replacements.get("{{NOMBRE}}", ""),
            "RUT": replacements.get("{{RUT}}", ""),
            "Dirección": replacements.get("{{DIRECCION}}", ""),
            "Domicilio": replacements.get("{{DIRECCION}}", ""),
            "Comuna": replacements.get("{{COMUNA}}", ""),
            "Teléfono": replacements.get("{{TELEFONO}}", ""),
            "Fecha": replacements.get("{{FECHA}}", ""),
        }
        
        for label, val in label_map.items():
            if val and label in text:
                # Regex to find label followed by dots or underscores
                # e.g., "Nombre: ..........." or "Nombre: ________"
                # using a raw string for regex pattern
                pattern = rf"({label}.*?)([_\\.]+)"
                regex = re.compile(pattern, re.IGNORECASE)
                # Replace with captured label + value
                text = regex.sub(rf"\1 {val}", text)

    # Only update paragraph text if changes were made
    if text != original_text:
        paragraph.text = text

def generate_contract_docx(template_path: Path, data: Dict[str, str]) -> bytes:
    """
    Generates a filled DOCX contract based on a template and data.
    
    Args:
        template_path: Path to the .docx template file.
        data: Dictionary of data to insert. Keys should match placeholders (e.g., "{{NOMBRE}}").
        
    Returns:
        Bytes of the generated DOCX file.
        
    Raises:
        Exception: Captures and re-raises any errors during processing.
    """
    try:
        if not template_path.exists():
             raise FileNotFoundError(f"Template not found at {template_path}")

        doc = Document(str(template_path))
        
        # Process all paragraphs in the document body
        for paragraph in doc.paragraphs:
            _replace_text_in_paragraph(paragraph, data)
            
        # Process all tables (common in forms)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                         _replace_text_in_paragraph(paragraph, data)
                        
        # Save to memory buffer
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating contract: {e}", exc_info=True)
        raise e
