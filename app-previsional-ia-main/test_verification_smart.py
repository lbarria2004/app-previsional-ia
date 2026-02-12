from contract_utils import generate_contract_docx, get_contract_template_path
from datetime import datetime
import os

def test_smart_generation():
    print("Testing Smart Contract Generation...")
    
    # 1. Test Survivorship (Smart Template)
    context_surv = {
        "nombre_afiliado": "JUAN PEREZ (AFILIADO)",
        "rut_afiliado": "11.111.111-1",
        "direccion_afiliado": "CALLE FALSA 123",
        "comuna_afiliado": "SANTIAGO",
        "telefono_afiliado": "+56912345678",
        "fecha_actual": datetime.now().strftime("%d de %B de %Y"),
        "nombre_causante": "PEDRO CAUSANTE",
        "rut_causante": "22.222.222-2",
        "nombre_consultante": "MARIA CONSULTANTE",
        "rut_consultante": "33.333.333-3",
        "beneficiaries": [
            {"nombre": "HIJO UNO", "rut": "44.444.444-4", "parentesco": "HIJO"},
            {"nombre": "HIJO DOS", "rut": "55.555.555-5", "parentesco": "HIJO"},
            {"nombre": "ESPOSA TRES", "rut": "66.666.666-6", "parentesco": "CONYUGE"},
        ]
    }
    
    try:
        template_path = get_contract_template_path("Sobrevivencia")
        print(f" [Survivorship] Using template: {template_path}")
        
        docx_bytes = generate_contract_docx(template_path, context_surv)
        
        output_filename = "TEST_SMART_SURVIVORSHIP_OUTPUT.docx"
        with open(output_filename, "wb") as f:
            f.write(docx_bytes)
        print(f" [Survivorship] Generated {output_filename}")
        
    except Exception as e:
        print(f" [Survivorship] FAILED: {e}")

    # 2. Test Old Age (Converted Smart Template)
    context_old_age = {
        "nombre_afiliado": "ALBERTO VIEJO",
        "rut_afiliado": "99.999.999-9",
        "direccion_afiliado": "AVENIDA SIEMPRE VIVA 742",
        "comuna_afiliado": "SPRINGFIELD",
        "telefono_afiliado": "+56987654321",
        "fecha_actual": datetime.now().strftime("%d de %B de %Y"),
        # Beneficiaries might not be used or stripped if empty
        "beneficiaries": [] 
    }
    
    try:
        template_path = get_contract_template_path("Vejez o Invalidez")
        print(f" [Old Age] Using template: {template_path}")
        
        docx_bytes = generate_contract_docx(template_path, context_old_age)
        
        output_filename = "TEST_SMART_OLD_AGE_OUTPUT.docx"
        with open(output_filename, "wb") as f:
            f.write(docx_bytes)
        print(f" [Old Age] Generated {output_filename}")
        
    except Exception as e:
        print(f" [Old Age] FAILED: {e}")

if __name__ == "__main__":
    test_smart_generation()
