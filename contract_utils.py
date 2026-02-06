import fitz  # PyMuPDF
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import streamlit as st

# --- CONSTANTES DE PLANTILLAS ---
TEMPLATE_VEJEZ = "CONTRATO 2026 AP - PLANTILLA vejez-invalidez.pdf"
TEMPLATE_SOBREVIVENCIA = "CONTRATO 2026 sobrevivencia -  plantilla.pdf"

def load_contract_template(template_name):
    """
    Lee el texto de un archivo PDF de plantilla local.
    """
    try:
        text = ""
        with fitz.open(template_name) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        return f"Error al cargar plantilla {template_name}: {str(e)}"

# Prompt especializado para CONTRATOS
PROMPT_CONTRATO = """
Eres un Asistente Legal y Previsional experto.
Tu tarea es redactar un **Contrato de Asesoría Previsional** completo y listo para firmar.

INSTRUCCIONES:
1.  Toma el texto de la **PLANTILLA** que te doy abajo.
2.  Rellena los espacios en blanco, variables o datos faltantes usando la **INFORMACIÓN DEL CLIENTE**.
3.  Si falta algún dato (ej. Dirección, Comuna, Teléfono), complétalo con "____________________" para que el cliente lo llene a mano, NO inventes datos.
4.  Si hay datos en el informe (Nombre, RUT), úsalos obligatoriamente.
5.  Mantén el tono formal y legal de la plantilla.
6.  La salida debe ser el TEXTO COMPLETO del contrato, sin interrupciones, listo para pasar a Word. No agregues saludos ni explicaciones, solo el contrato.

DATOS DEL CLIENTE (Extraídos del análisis):
{CLIENTE_DATA}

TEXTO DE LA PLANTILLA:
{TEMPLATE_TEXT}

CONTRATO FINAL:
"""

def generate_contract_content_ia(client_data_md, template_text, api_key):
    """
    Usa Gemini para fusionar la data del cliente con la plantilla.
    """
    if not api_key:
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        
        prompt = PROMPT_CONTRATO.format(
            CLIENTE_DATA=client_data_md,
            TEMPLATE_TEXT=template_text
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error AI generando contrato: {e}")
        return None

def create_contract_docx(contract_text):
    """
    Convierte el texto del contrato generado a un archivo .docx limpio.
    """
    doc = Document()
    
    # Configurar fuente base
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Roboto' # O Arial si Roboto falla en el sistema local, pero python-docx maneja nombres bien
    font.size = Pt(11)
    
    # Procesar línea a línea para limpiar markdown básico
    for line in contract_text.split('\n'):
        line_clean = line.strip().replace('**', '').replace('##', '').replace('###', '')
        
        if not line_clean:
            continue
            
        # Detectar títulos (simple heurística por mayúsculas o longitud corta y bold en md)
        if line.strip().startswith('#') or (len(line_clean) < 50 and line_clean.isupper()):
            p = doc.add_heading(line_clean, level=2)
            p.alignment = 1 # Centrado para títulos
        else:
            p = doc.add_paragraph(line_clean)
            p.alignment = 3 # Justificado (docx enum 3 es justify generalmente, o 0 left)
            # Vamos a usar left por seguridad si justify da error, o default.
            # python-docx alignment: LEFT=0, CENTER=1, RIGHT=2, JUSTIFY=3
            p.alignment = 3 

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
