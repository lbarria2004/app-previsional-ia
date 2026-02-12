from docxtpl import DocxTemplate

try:
    doc = DocxTemplate("CONTRATO 2026 sobrevivencia -  plantilla.docx")
    print("Success! DocxTemplate opened the file.")
except Exception as e:
    print(f"Error opening with DocxTemplate: {e}")
