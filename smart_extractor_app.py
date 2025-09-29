#!/usr/bin/env python3
"""
Smart RFQ Extractor App using Advanced Extraction
"""

import streamlit as st
import pandas as pd
import re
import os
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, List

from advanced_extractor import AdvancedRFQExtractor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

st.set_page_config(
    page_title="Smart RFQ Extractor",
    page_icon="🚢",
    layout="wide"
)

st.title("🚢 Smart RFQ Extractor")
st.markdown("**Advanced AI-powered extraction with confidence scoring**")

# Initialize extractor
@st.cache_resource
def get_extractor():
    return AdvancedRFQExtractor()

extractor = get_extractor()

def create_pdf_quote(extraction_results: Dict, quote_options: List[Dict]) -> str:
    """Generate professional PDF quotation"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf_path = tmp_file.name

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue
    )

    # Header
    story.append(Paragraph("COTIZACIÓN DE TRANSPORTE INTERNACIONAL", title_style))
    story.append(Spacer(1, 20))

    # Company info
    company_info = """
    <b>IBERLOGISTICS S.L.</b><br/>
    C/ Gran Vía 123, 28013 Madrid<br/>
    Tel: +34 91 123 4567 | Email: quotes@iberlogistics.es<br/>
    CIF: B12345678
    """
    story.append(Paragraph(company_info, styles['Normal']))
    story.append(Spacer(1, 20))

    # Quote details
    quote_date = datetime.now().strftime("%d/%m/%Y")
    validity = (datetime.now() + timedelta(days=15)).strftime("%d/%m/%Y")

    quote_info = f"""
    <b>Fecha de cotización:</b> {quote_date}<br/>
    <b>Válida hasta:</b> {validity}<br/>
    <b>Referencia:</b> QT-{datetime.now().strftime('%Y%m%d-%H%M')}<br/>
    <b>Confianza de extracción:</b> {extraction_results.get('extraction_confidence', 0):.1%}
    """
    story.append(Paragraph(quote_info, styles['Normal']))
    story.append(Spacer(1, 20))

    # Shipment details
    story.append(Paragraph("<b>DETALLES DEL ENVÍO</b>", styles['Heading2']))

    shipment_details = [
        ['Mercancía:', extraction_results.get('commodity', 'No especificada')],
        ['Origen:', extraction_results.get('origin', 'No especificado')],
        ['Destino:', extraction_results.get('destination', 'No especificado')],
        ['Peso:', extraction_results.get('weight', 'No especificado')],
        ['Urgencia:', extraction_results.get('urgency', 'Normal').title()],
        ['Contacto:', extraction_results.get('contact_name', 'No especificado')],
        ['Teléfono:', extraction_results.get('contact_info', 'No especificado')]
    ]

    details_table = Table(shipment_details, colWidths=[2*inch, 4*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(details_table)
    story.append(Spacer(1, 30))

    # Options table
    story.append(Paragraph("<b>OPCIONES DE TRANSPORTE</b>", styles['Heading2']))

    options_data = [['Servicio', 'Precio', 'Tiempo Tránsito', 'Ruta', 'Recomendado Para']]
    for option in quote_options:
        options_data.append([
            option['Service'],
            option['Price'],
            option['Transit Time'],
            option['Route'],
            option['Best For']
        ])

    options_table = Table(options_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1.5*inch, 1.5*inch])
    options_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(options_table)
    story.append(Spacer(1, 30))

    # Terms and conditions
    terms = """
    <b>TÉRMINOS Y CONDICIONES:</b><br/>
    • Precios válidos por 15 días<br/>
    • Sujeto a disponibilidad de espacio<br/>
    • Documentación requerida: factura comercial, packing list<br/>
    • Seguro de mercancías opcional (2% del valor CIF)<br/>
    • Tiempos de tránsito aproximados, no garantizados<br/>
    • Aplican términos FIATA estándar<br/>
    • Cotización generada automáticamente con IA avanzada
    """
    story.append(Paragraph(terms, styles['Normal']))

    # Build PDF
    doc.build(story)
    return pdf_path

def draft_spanish_email(extraction_results: Dict, quote_options: List[Dict]) -> str:
    """Generate professional follow-up email in Spanish"""
    contact_name = extraction_results.get('contact_name', 'Estimado/a cliente')
    if not contact_name or contact_name == "❌ Not found":
        contact_name = 'Estimado/a cliente'

    commodity = extraction_results.get('commodity', 'su mercancía')
    origin = extraction_results.get('origin', 'origen')
    destination = extraction_results.get('destination', 'destino')

    # Create options summary
    options_text = ""
    for i, option in enumerate(quote_options, 1):
        options_text += f"{i}. {option['Service']}: {option['Price']} - {option['Transit Time']}\n"

    email_content = f"""Asunto: Cotización transporte {origin} → {destination} - Ref: QT-{datetime.now().strftime('%Y%m%d')}

{contact_name},

Gracias por contactar con IberLogistics para el transporte de {commodity} desde {origin} hasta {destination}.

Hemos analizado su solicitud con nuestro sistema de IA avanzado (confianza: {extraction_results.get('extraction_confidence', 0):.1%}) y adjunto encontrará nuestra cotización detallada.

OPCIONES RECOMENDADAS:
{options_text}
CARACTERÍSTICAS DEL ENVÍO:
• Mercancía: {commodity}
• Peso: {extraction_results.get('weight', 'N/A')}
• Urgencia: {extraction_results.get('urgency', 'Normal').title()}
• Contacto: {extraction_results.get('contact_name', 'N/A')}
• Teléfono: {extraction_results.get('contact_info', 'N/A')}

PRÓXIMOS PASOS:
1. Revise las opciones adjuntas en el PDF
2. Confirme la opción de su preferencia
3. Envíenos la documentación requerida
4. Procederemos con la reserva

Nuestro equipo está disponible para resolver cualquier duda. Los precios son válidos por 15 días.

Quedamos a su disposición.

Saludos cordiales,

María González
Departamento Comercial
IberLogistics S.L.
Tel: +34 91 123 4567
Email: maria.gonzalez@iberlogistics.es
www.iberlogistics.es

---
Esta cotización ha sido generada automáticamente por nuestro sistema de IA avanzada.
Confianza de extracción: {extraction_results.get('extraction_confidence', 0):.1%}
"""
    return email_content

def send_email_with_pdf(recipient_email: str, subject: str, body: str, pdf_path: str = None) -> bool:
    """Send email with optional PDF attachment"""
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')

        if not smtp_user or not smtp_pass:
            st.error("❌ SMTP credentials not configured. Please add SMTP_USER and SMTP_PASS to your .env file.")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Add PDF attachment if provided
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= cotizacion_smart_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
            msg.attach(part)

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        server.sendmail(smtp_user, recipient_email, text)
        server.quit()

        return True

    except Exception as e:
        st.error(f"❌ Error sending email: {str(e)}")
        return False

# Sample RFQ
sample_rfq = """hola buenos dias!!

necesitamos cotizar un envio URGENTE de valencia españa al puerto de SANTOS brasil... son maquinarias pesadas de segunda mano aprox 2.5 toneladas + o -

tengo 3 maquinas:
- una cortadora que mide algo asi como 180x90x120 cm pesa 890kg mas o menos
- soldadora de 65kg (pequeña) 40x30x80
- compresor grande PESADO!!! 950kg aprox dimensiones 200x110x140 creo q son

TOTAL= mas o menos 1900kg pero pueden ser hasta 2200kg dependiendo de los accesorios

necesitamos que llegue antes del 15 de octubre por fabor es MUY urgente nuestro cliente ya esta esperando

pueden incluir SEGURO??? y el transporte hasta la fabrica en santos??

presupuesto???

saludos
juan martinez
WhatsApp: +34 666 123 456
Maquilogistics SL
valencia

PD: algunas maquinas tienen aceite residual pero ya las limpiamos"""

# Input section
st.header("📧 1. RFQ Input")

input_method = st.radio(
    "Input method:",
    ["Use sample RFQ", "Enter custom RFQ"],
    horizontal=True
)

if input_method == "Use sample RFQ":
    rfq_text = sample_rfq
    st.text_area("RFQ Text (read-only):", value=rfq_text, height=200, disabled=True)
else:
    rfq_text = st.text_area(
        "Paste your RFQ here:",
        height=200,
        placeholder="Enter the RFQ email content..."
    )

# Initialize session state for extracted results
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = None
if 'quote_options' not in st.session_state:
    st.session_state.quote_options = None

if st.button("🔍 Extract Information", type="primary"):
    if not rfq_text.strip():
        st.warning("Please enter RFQ text")
        st.stop()

    with st.spinner("Extracting information with advanced AI..."):
        results = extractor.extract_all(rfq_text)
        st.session_state.extraction_results = results

# Display results if available (either just extracted or from session state)
if st.session_state.extraction_results:
    results = st.session_state.extraction_results
    st.header("📊 2. Extraction Results")

    # Overall confidence
    confidence = results.get('extraction_confidence', 0)
    confidence_color = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
    st.metric("Overall Confidence", f"{confidence:.1%}", help="How confident we are in the extraction accuracy")

    # Results table
    extraction_data = []
    for field, value in results.items():
        if field != 'extraction_confidence':
            # Determine field confidence (simplified)
            field_confidence = "High" if value and len(str(value)) > 3 else "Low" if value else "Missing"
            extraction_data.append({
                'Field': field.replace('_', ' ').title(),
                'Value': value or "❌ Not found",
                'Status': "✅ Found" if value else "❌ Missing",
                'Confidence': field_confidence
            })

    df = pd.DataFrame(extraction_data)
    st.dataframe(df, use_container_width=True)

    # Generate quote if we have minimum info
    st.header("💰 3. Quote Generation")

    if results.get('origin') and results.get('destination') and results.get('weight'):
        st.success("✅ Sufficient information for quote generation")

        # Parse weight for calculations
        weight_str = results.get('weight', '1000 kg')
        weight_nums = re.findall(r'\d+', weight_str)
        weight_kg = int(weight_nums[0]) if weight_nums else 1000

        # Check if intercontinental
        is_intercontinental = any(
            country in (results.get('origin', '') + results.get('destination', '')).lower()
            for country in ['brasil', 'brazil', 'america', 'usa', 'asia']
        )

        # Check if urgent
        is_urgent = results.get('urgency', '').lower() == 'urgent'

        # Calculate realistic prices
        if is_intercontinental:
            air_rate = 8.5 if not is_urgent else 12.0
            sea_lcl_rate = 320
            sea_fcl_base = 2800
        else:
            air_rate = 3.2 if not is_urgent else 4.5
            sea_lcl_rate = 150
            sea_fcl_base = 1200

        # Heavy machinery premium
        is_machinery = 'maquina' in results.get('commodity', '').lower()
        heavy_premium = 1.3 if is_machinery else 1.0

        # Calculate options
        air_price = (weight_kg * air_rate + 450) * heavy_premium
        sea_lcl_price = max(680, weight_kg * 0.4 * heavy_premium) if is_intercontinental else max(290, weight_kg * 0.3)

        quote_options = [
            {
                'Service': f"Air Freight {'(Urgent)' if is_urgent else '(Standard)'}",
                'Price': f"€{air_price:,.0f}",
                'Transit Time': '3-5 days' if is_urgent else '5-7 days',
                'Route': f"{results.get('origin', 'Origin')} → {results.get('destination', 'Destination')}",
                'Best For': 'Speed and reliability'
            },
            {
                'Service': 'Sea Freight LCL',
                'Price': f"€{sea_lcl_price:,.0f}",
                'Transit Time': '22-28 days' if is_intercontinental else '8-12 days',
                'Route': f"{results.get('origin', 'Origin')} → {results.get('destination', 'Destination')}",
                'Best For': 'Cost optimization'
            }
        ]

        # Add FCL option for heavy shipments
        if weight_kg > 8000:  # ~8+ tons suggests FCL
            fcl_price = sea_fcl_base * heavy_premium
            quote_options.append({
                'Service': 'Sea Freight FCL 20ft',
                'Price': f"€{fcl_price:,.0f}",
                'Transit Time': '20-25 days' if is_intercontinental else '7-10 days',
                'Route': f"{results.get('origin', 'Origin')} → {results.get('destination', 'Destination')}",
                'Best For': 'Large shipments'
            })

        quote_df = pd.DataFrame(quote_options)
        st.dataframe(quote_df, use_container_width=True)

        # Store quote options in session state for PDF/email generation
        st.session_state.quote_options = quote_options

        # Additional insights
        st.header("🎯 4. Insights & Recommendations")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Shipment Summary")
            st.write(f"**Commodity:** {results.get('commodity', 'Unknown')}")
            st.write(f"**Route:** {results.get('origin', 'Unknown')} → {results.get('destination', 'Unknown')}")
            st.write(f"**Weight:** {results.get('weight', 'Unknown')}")
            st.write(f"**Urgency:** {results.get('urgency', 'Normal').title()}")
            if results.get('contact_name'):
                st.write(f"**Contact:** {results.get('contact_name')}")
            if results.get('contact_info'):
                st.write(f"**Phone:** {results.get('contact_info')}")

        with col2:
            st.subheader("💡 Recommendations")

            if is_urgent:
                st.warning("⚠️ **Urgent shipment** - Air freight recommended despite higher cost")

            if is_machinery:
                st.info("🔧 **Heavy machinery** detected - Special handling may be required")

            if weight_kg > 5000:
                st.info("📦 **Heavy cargo** - Consider FCL for better rates")

            if is_intercontinental:
                st.info("🌍 **Intercontinental route** - Allow extra time for customs")

        # Missing information warnings
        missing_info = [field for field, value in results.items()
                       if not value and field != 'extraction_confidence']
        if missing_info:
            st.header("⚠️ 9. Missing Information")
            st.warning("The following information could not be extracted and may be needed for accurate quotes:")
            for field in missing_info:
                st.write(f"• {field.replace('_', ' ').title()}")

    else:
        st.warning("⚠️ Insufficient information for quote generation")
        st.write("Need at least: Origin, Destination, and Weight")

# PDF and Email sections - moved outside conditional blocks to prevent UI issues
if st.session_state.extraction_results and st.session_state.quote_options:
    results = st.session_state.extraction_results
    quote_options = st.session_state.quote_options

    st.markdown("---")

    # PDF Generation Section
    st.header("📄 5. Generate Professional PDF Quote")

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("📄 Generate PDF Quote", key="pdf_gen_btn_v2"):
            try:
                with st.spinner("Generating professional PDF quote..."):
                    pdf_path = create_pdf_quote(results, quote_options)
                    st.session_state.pdf_path = pdf_path
                    st.session_state.pdf_generated = True

                st.success("✅ PDF quote generated successfully!")
            except Exception as e:
                st.error(f"❌ PDF generation failed: {str(e)}")
                st.info("💡 This might be due to missing dependencies. The email feature will still work without PDF.")

    # Download button (separate from generation to avoid crashes)
    if st.session_state.get('pdf_generated', False) and 'pdf_path' in st.session_state:
        try:
            with open(st.session_state.pdf_path, 'rb') as pdf_file:
                st.download_button(
                    label="⬇️ Download PDF Quote",
                    data=pdf_file.read(),
                    file_name=f"smart_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    key="pdf_download_btn_v2"
                )
        except Exception as e:
            st.error(f"❌ PDF download failed: {str(e)}")

    # Email Generation Section
    st.header("✉️ 6. Professional Spanish Email")

    email_content = draft_spanish_email(results, quote_options)
    st.text_area("Email content (Spanish):", value=email_content, height=400, key="email_content_display")

    # Email Sending Section
    st.header("📤 7. Send Quote via Email")

    # Initialize session state for email
    if 'recipient_email' not in st.session_state:
        st.session_state.recipient_email = ""
    if 'email_sent_status' not in st.session_state:
        st.session_state.email_sent_status = None

    col1, col2 = st.columns([2, 1])

    with col1:
        # Use session state directly with on_change callback
        def update_email():
            st.session_state.recipient_email = st.session_state.email_input_widget_v2

        recipient_email = st.text_input(
            "Cliente email address:",
            value=st.session_state.recipient_email,
            placeholder="cliente@empresa.com",
            help="Enter the client's email address to send the quote",
            key="email_input_widget_v2",
            on_change=update_email
        )

    with col2:
        send_email_clicked = st.button("📧 Send Email + PDF", key="send_email_btn_v2")

    # Display previous status if available
    if st.session_state.email_sent_status:
        if st.session_state.email_sent_status == "success":
            st.success("✅ Last email sent successfully!")
        elif st.session_state.email_sent_status == "error":
            st.error("❌ Last email failed to send")

    # Handle email sending
    if send_email_clicked:
        current_email = st.session_state.recipient_email
        if current_email:
            if 'pdf_path' not in st.session_state:
                st.warning("⚠️ No PDF generated - sending email without attachment")
                pdf_path_to_send = None
            else:
                pdf_path_to_send = st.session_state.pdf_path

            try:
                with st.spinner("Sending email..."):
                    subject = f"Cotización transporte {results.get('origin', '')} → {results.get('destination', '')}"
                    success = send_email_with_pdf(
                        current_email,
                        subject,
                        email_content,
                        pdf_path_to_send
                    )

                if success:
                    st.success("✅ Email sent successfully!")
                    st.info(f"📧 Sent to: {current_email}")
                    st.session_state.email_sent_status = "success"
                    # Keep email in field for potential resend
                else:
                    st.error("❌ Failed to send email")
                    st.session_state.email_sent_status = "error"
            except Exception as e:
                st.error(f"❌ Email sending error: {str(e)}")
                st.session_state.email_sent_status = "error"
        else:
            st.error("❌ Please enter an email address")
            st.session_state.email_sent_status = None

# Footer
st.markdown("---")
st.markdown("**🚀 Powered by Advanced AI Extraction** • Confidence scoring • Multi-strategy parsing")

with st.expander("ℹ️ How it works"):
    st.markdown("""
    **Advanced RFQ Extractor uses multiple strategies:**

    1. **🤖 OpenAI GPT** - Context-aware AI extraction
    2. **📍 Location Database** - 20+ cities/ports with variations
    3. **⚖️ Smart Weight Parsing** - Handles units, ranges, multiple items
    4. **🎯 Pattern Matching** - Regex patterns for commodity types
    5. **📊 Confidence Scoring** - Reliability assessment per field
    6. **🔄 Fallback Systems** - Multiple extraction strategies per field

    **Confidence Levels:**
    - 🟢 **High (70%+)**: Very reliable extraction
    - 🟡 **Medium (40-70%)**: Good extraction, minor uncertainty
    - 🔴 **Low (<40%)**: Uncertain extraction, manual review recommended
    """)

with st.expander("⚙️ Email Configuration"):
    st.markdown("""
    **Email Setup Instructions:**

    **1. Gmail Setup (Recommended):**
    - Enable 2-factor authentication on Gmail
    - Generate an "App Password" (not your regular password)
    - Add to `.env` file:
      ```
      SMTP_SERVER=smtp.gmail.com
      SMTP_PORT=587
      SMTP_USER=your.email@gmail.com
      SMTP_PASS=your_16_char_app_password
      ```

    **2. Current Configuration:**
    """)

    # Show current email config
    smtp_configured = bool(os.getenv('SMTP_USER') and os.getenv('SMTP_PASS'))
    if smtp_configured:
        st.success(f"✅ Email configured: {os.getenv('SMTP_USER')}")
    else:
        st.warning("⚠️ Email not configured - PDF generation will work, but email sending won't")

    st.code(f"""
SMTP_SERVER: {os.getenv('SMTP_SERVER', 'Not set')}
SMTP_PORT: {os.getenv('SMTP_PORT', 'Not set')}
SMTP_USER: {os.getenv('SMTP_USER', 'Not set')}
SMTP_PASS: {'✅ Configured' if os.getenv('SMTP_PASS') else '❌ Not set'}
""")

with st.expander("🚀 Features Overview"):
    st.markdown("""
    **Complete Freight Forwarding Workflow:**

    **📧 Smart Extraction:**
    - Multi-language support (Spanish/English)
    - Confidence scoring for reliability
    - Fallback strategies for robustness

    **💰 Intelligent Quoting:**
    - Route-specific pricing (EU-Brazil vs domestic)
    - Urgency premiums for rush orders
    - Cargo-type adjustments (machinery, textiles, etc.)
    - Realistic market rates (2024)

    **📄 Professional Output:**
    - PDF quotes with company branding
    - Spanish business emails
    - Complete shipment details
    - Terms and conditions

    **📤 Automation:**
    - Direct email sending with attachments
    - Professional follow-up templates
    - Contact information extraction
    - Reference number generation

    **🎯 Business Intelligence:**
    - Missing information identification
    - Confidence-based recommendations
    - Route optimization suggestions
    - Special handling alerts
    """)