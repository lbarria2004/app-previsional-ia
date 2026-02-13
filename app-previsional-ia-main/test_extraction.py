from contract_utils import extract_beneficiaries_from_report
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

def test_extraction():
    sample_report = """
# Informe de Pensión

## 1. Antecedentes del Afiliado
...

## 2) Antecedentes del beneficiario

El afiliado declara a los siguientes beneficiarios legales de pensión:

| Nombre Completo | RUT | Parentesco | Sexo | Invalidez | Fecha de Nacimiento |
|---|---|---|---|---|---|
| LAGOS CAAMANO CRISTOBAL ANDRES | 21.851.177-5 | Hijo de cónyuge con derecho a pensión | M | N | 03/06/2005 |
| CAAMANO JARA NATALIA ESTER | 9.800.454-8 | Cónyuge con hijos con derecho a pensión | F | N | 11/08/1964 |

## 3. Otra Sección
...
    """
    
    print("Testing Extraction...")
    beneficiaries = extract_beneficiaries_from_report(sample_report)
    
    expected_count = 2
    if len(beneficiaries) == expected_count:
        print(f"SUCCESS: Extracted {len(beneficiaries)} beneficiaries.")
        for b in beneficiaries:
            print(f" - {b['nombre']} ({b['rut']}) - {b['parentesco']}")
            
        # Verify specific data
        if beneficiaries[0]['rut'] == "21.851.177-5":
            print(" - Data verification PASS")
        else:
            print(f" - Data verification FAIL: Expected 21.851.177-5, got {beneficiaries[0]['rut']}")
    else:
        print(f"FAIL: Expected {expected_count}, got {len(beneficiaries)}")

if __name__ == "__main__":
    test_extraction()
