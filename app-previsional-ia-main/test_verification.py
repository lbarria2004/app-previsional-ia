
import unittest
import os
from pathlib import Path
from docx import Document
from contract_utils import extract_contract_data, _fill_beneficiary_table, _replace_text_in_paragraph

class TestBeneficiaryLogic(unittest.TestCase):

    def test_extraction_from_markdown_table(self):
        print("\n--- Testing Markdown Extraction ---")
        markdown_sample = """
### 2) Antecedentes del beneficiario
El afiliado declara a la siguiente beneficiaria legal de pensión:
| Nombre Completo | RUT | Parentesco | Sexo | Invalidez | Fecha de Nacimiento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Juan Perez | 11.111.111-1 | Hijo | M | N | 01/01/2000 |
| Maria Gomez | 22.222.222-2 | Conyuge | F | N | 02/02/1980 |

### 3) Situación previsional
"""
        data = extract_contract_data(markdown_sample)
        
        # Check Beneficiary 1
        self.assertEqual(data.get("Beneficiario 1 Nombre"), "Juan Perez")
        self.assertEqual(data.get("Beneficiario 1 RUT"), "11.111.111-1")
        self.assertEqual(data.get("Beneficiario 1 Parentesco"), "Hijo")
        self.assertEqual(data.get("Beneficiario 1 Sexo"), "M")
        
        # Check Beneficiary 2
        self.assertEqual(data.get("Beneficiario 2 Nombre"), "Maria Gomez")
        self.assertEqual(data.get("Beneficiario 2 RUT"), "22.222.222-2")
        self.assertEqual(data.get("Beneficiario 2 Parentesco"), "Conyuge")
        
        print("✅ Extraction Verified!")

    def test_docx_table_filling(self):
        print("\n--- Testing DOCX Paragraph Filling (Fake Table) ---")
        # 1. Create a dummy DOCX with "paragraphs" acting as rows
        doc = Document()
        doc.add_paragraph("Contrato de Prueba")
        
        # Header (just text)
        doc.add_paragraph("Nombre\tRUT\tParentesco")
        
        # Data Rows with Placeholders (Simulating the user's template)
        # We create 3 rows of placeholders
        doc.add_paragraph("{NOMBRE BENEFICIARIO}\t{RUT BENEFICIARIO}\t{PARENTESCO BENEFICIARIO}")
        doc.add_paragraph("{NOMBRE BENEFICIARIO}\t{RUT BENEFICIARIO}\t{PARENTESCO BENEFICIARIO}")
        doc.add_paragraph("{NOMBRE BENEFICIARIO}\t{RUT BENEFICIARIO}\t{PARENTESCO BENEFICIARIO}")
            
        # 2. Define Beneficiaries Data
        beneficiaries_list = [
            {
                "{NOMBRE BENEFICIARIO}": "BENEFICIARIO_UNO",
                "{RUT BENEFICIARIO}": "1-9",
                "{PARENTESCO BENEFICIARIO}": "MADRE"
            },
            {
                "{NOMBRE BENEFICIARIO}": "BENEFICIARIO_DOS",
                "{RUT BENEFICIARIO}": "2-9",
                "{PARENTESCO BENEFICIARIO}": "PADRE"
            }
        ]
        
        # 3. Run the filling function
        _fill_beneficiary_table(doc, beneficiaries_list)
        
        # 4. Assertions
        # Check Paragraphs
        # Paragraph 0: Title
        # Paragraph 1: Header
        # Paragraph 2: Ben 1
        p2_text = doc.paragraphs[2].text
        self.assertIn("BENEFICIARIO_UNO", p2_text)
        self.assertIn("MADRE", p2_text)
        
        # Paragraph 3: Ben 2
        p3_text = doc.paragraphs[3].text
        self.assertIn("BENEFICIARIO_DOS", p3_text)
        self.assertIn("PADRE", p3_text)
        
        # Paragraph 4: Should be EMPTY (Clearing logic)
        p4_text = doc.paragraphs[4].text
        self.assertNotIn("{NOMBRE BENEFICIARIO}", p4_text) # Placeholder should be gone
        self.assertNotIn("BENEFICIARIO", p4_text) # Should be empty
        self.assertEqual(p4_text.replace('\t', '').strip(), "") # Structure might remain (tabs), but text gone
        
        print("✅ DOCX Paragraph Filling Verified!")
        
        # Optional: Save for manual inspection if needed
        # doc.save("test_output.docx")

if __name__ == '__main__':
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)

