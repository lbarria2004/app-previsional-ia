
import io
import logging
from pathlib import Path
from docx import Document
from contract_utils import generate_contract_docx, BASE_DIR, TEMPLATE_SMART_SURVIVORSHIP
import sys
import contract_utils

# Setup logging
logging.basicConfig(level=logging.INFO)
print(f"DEBUG: contract_utils file: {contract_utils.__file__}")

def test_beneficiary_replacement():
    print("Testing beneficiary replacement...")
    
    # Mock data
    context = {
        "nombre_afiliado": "Juan Perez",
        "rut_afiliado": "11.111.111-1",
        "fecha_actual": "13 de Febrero de 2026"
    }
    
    beneficiaries = [
        {
            "nombre": "Maria Gonzalez",
            "rut": "22.222.222-2", 
            "fecha_nacimiento": "01/01/1980",
            "parentesco": "Conyuge",
            "sexo": "F",
            "invalidez": "No"
        },
        {
            "nombre": "Pedro Perez",
            "rut": "33.333.333-3",
            "fecha_nacimiento": "01/01/2010", 
            "parentesco": "Hijo",
            "sexo": "M",
            "invalidez": "Si"
        }
    ]
    
    # Ensure template exists
    template_path = BASE_DIR / TEMPLATE_SMART_SURVIVORSHIP
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        return

    try:
        # Generate contract
        docx_bytes = generate_contract_docx(template_path, context, beneficiaries)
        
        # Save to file for manual inspection if needed
        output_path = BASE_DIR / "TEST_BENEFICIARY_OUTPUT.docx"
        with open(output_path, "wb") as f:
            f.write(docx_bytes)
            
        print(f"Contract generated at {output_path}")
        
        # Verify content
        doc = Document(io.BytesIO(docx_bytes))
        found_maria = False
        found_pedro = False
        
        for table in doc.tables:
            for row in table.rows:
                row_text = " ".join(cell.text for cell in row.cells)
                if "Maria Gonzalez" in row_text and "22.222.222-2" in row_text:
                    found_maria = True
                if "Pedro Perez" in row_text and "33.333.333-3" in row_text:
                    found_pedro = True
        
        if found_maria:
            print("✅ SUCCESS: Found Beneficiary 1 (Maria)")
        else:
            print("❌ FAILURE: Did not find Beneficiary 1 (Maria)")
            
        if found_pedro:
            print("✅ SUCCESS: Found Beneficiary 2 (Pedro)")
        else:
            print("❌ FAILURE: Did not find Beneficiary 2 (Pedro)")
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_beneficiary_replacement()
