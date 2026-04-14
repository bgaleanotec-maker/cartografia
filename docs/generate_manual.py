"""Genera el PDF del Manual de Operacion - Gestor Cartografico Vanti"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)

DARK = HexColor('#0f172a')
ACCENT = HexColor('#3b82f6')
GREEN = HexColor('#10b981')
YELLOW = HexColor('#f59e0b')
RED = HexColor('#ef4444')
GRAY = HexColor('#64748b')
LIGHT_BG = HexColor('#f1f5f9')
WHITE = HexColor('#ffffff')
DARK_BG = HexColor('#1e293b')

output_path = 'docs/Manual_GestorCartografico_Vanti.pdf'

doc = SimpleDocTemplate(
    output_path, pagesize=letter,
    topMargin=1*inch, bottomMargin=0.8*inch,
    leftMargin=0.8*inch, rightMargin=0.8*inch
)

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle('CoverTitle', parent=styles['Title'],
    fontSize=28, textColor=DARK, spaceAfter=6, alignment=TA_CENTER,
    fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('CoverSub', parent=styles['Normal'],
    fontSize=14, textColor=ACCENT, spaceAfter=20, alignment=TA_CENTER,
    fontName='Helvetica'))
styles.add(ParagraphStyle('SectionTitle', parent=styles['Heading1'],
    fontSize=18, textColor=DARK, spaceBefore=20, spaceAfter=10,
    fontName='Helvetica-Bold', borderColor=ACCENT, borderWidth=2,
    borderPadding=5, leftIndent=0))
styles.add(ParagraphStyle('SubTitle', parent=styles['Heading2'],
    fontSize=13, textColor=ACCENT, spaceBefore=14, spaceAfter=6,
    fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('Body', parent=styles['Normal'],
    fontSize=10, textColor=DARK, spaceAfter=6, leading=14,
    alignment=TA_JUSTIFY, fontName='Helvetica'))
styles.add(ParagraphStyle('BulletItem', parent=styles['Normal'],
    fontSize=10, textColor=DARK, spaceAfter=4, leading=13,
    leftIndent=20, bulletIndent=10, fontName='Helvetica'))
styles.add(ParagraphStyle('SmallGray', parent=styles['Normal'],
    fontSize=8, textColor=GRAY, alignment=TA_CENTER))
styles.add(ParagraphStyle('TableHeader', parent=styles['Normal'],
    fontSize=9, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER))
styles.add(ParagraphStyle('TableCell', parent=styles['Normal'],
    fontSize=9, textColor=DARK, fontName='Helvetica', leading=11))
styles.add(ParagraphStyle('TableCellCenter', parent=styles['Normal'],
    fontSize=9, textColor=DARK, fontName='Helvetica', alignment=TA_CENTER, leading=11))
styles.add(ParagraphStyle('ANSGreen', parent=styles['Normal'],
    fontSize=9, textColor=GREEN, fontName='Helvetica-Bold', alignment=TA_CENTER))
styles.add(ParagraphStyle('ANSRed', parent=styles['Normal'],
    fontSize=9, textColor=RED, fontName='Helvetica-Bold', alignment=TA_CENTER))

story = []

# ========== COVER PAGE ==========
story.append(Spacer(1, 2*inch))
story.append(Paragraph('Manual de Operacion', styles['CoverTitle']))
story.append(Paragraph('Gestor Cartografico Vanti', styles['CoverTitle']))
story.append(Spacer(1, 0.3*inch))
story.append(HRFlowable(width='60%', thickness=3, color=ACCENT, spaceAfter=15, spaceBefore=5))
story.append(Paragraph('Plataforma de Gestion de Expansion de Redes de Gas', styles['CoverSub']))
story.append(Spacer(1, 0.5*inch))
story.append(Paragraph('Vanti S.A. ESP', styles['CoverSub']))
story.append(Paragraph('Abril 2026 - Version 1.0', styles['SmallGray']))
story.append(Spacer(1, 1*inch))
story.append(Paragraph('URL: https://gestor-cartografico-app.onrender.com', styles['SmallGray']))
story.append(Paragraph('Documento Confidencial', styles['SmallGray']))
story.append(PageBreak())

# ========== TABLE OF CONTENTS ==========
story.append(Paragraph('Contenido', styles['SectionTitle']))
toc_items = [
    '1. Introduccion',
    '2. Roles del Sistema',
    '3. Flujo Cartografia (11 pasos)',
    '4. Flujo Proyectos (7 pasos)',
    '5. Flujo Ejecutivo (5 pasos)',
    '6. Modulo Campo Lite (PWA Offline)',
    '7. Seguimiento ANS (Semaforo)',
    '8. Backlog y Clusterizacion de Proyectos',
    '9. Credenciales de Acceso',
]
for item in toc_items:
    story.append(Paragraph(item, styles['Body']))
story.append(PageBreak())

# ========== 1. INTRODUCCION ==========
story.append(Paragraph('1. Introduccion', styles['SectionTitle']))
story.append(Paragraph(
    'El Gestor Cartografico es una plataforma web desarrollada para Vanti S.A. ESP, '
    'disenada para gestionar el ciclo completo de proyectos de expansion de redes de gas natural. '
    'El sistema permite el levantamiento cartografico en campo, seguimiento de Acuerdos de Nivel '
    'de Servicio (ANS), aprobaciones, y cierre tecnico-financiero de proyectos.',
    styles['Body']))
story.append(Paragraph(
    'Caracteristicas principales:', styles['SubTitle']))
bullets = [
    'Trabajo en zonas veredales sin cobertura de datos moviles (PWA Offline)',
    'Captura GPS de nodos con datos de campo y fotos georeferenciadas',
    'Exportacion en formatos compatibles con ArcGIS (GeoJSON, CSV, GPX, KMZ)',
    'Seguimiento automatico de ANS con semaforo de colores',
    'Flujos de trabajo por rol: Cartografia, Proyectos, Ejecutivo',
    'Almacenamiento robusto con IndexedDB (100+ MB)',
    'Backlog de proyectos con clusterizacion por zona y departamento',
]
for b in bullets:
    story.append(Paragraph(f'<bullet>&bull;</bullet> {b}', styles['BulletItem']))
story.append(PageBreak())

# ========== 2. ROLES ==========
story.append(Paragraph('2. Roles del Sistema', styles['SectionTitle']))
roles_data = [
    [Paragraph('Rol', styles['TableHeader']),
     Paragraph('Descripcion', styles['TableHeader']),
     Paragraph('Acceso', styles['TableHeader'])],
    [Paragraph('SuperAdmin', styles['TableCell']),
     Paragraph('Acceso total al sistema, gestion de usuarios y configuracion', styles['TableCell']),
     Paragraph('Todo', styles['TableCellCenter'])],
    [Paragraph('Admin', styles['TableCell']),
     Paragraph('Gestion de usuarios y configuracion de formularios', styles['TableCell']),
     Paragraph('Usuarios, Config', styles['TableCellCenter'])],
    [Paragraph('Comercial', styles['TableCell']),
     Paragraph('Visitas de prospeccion, creacion de proyectos, censo', styles['TableCell']),
     Paragraph('Visitas, Proyectos', styles['TableCellCenter'])],
    [Paragraph('Cartografia', styles['TableCell']),
     Paragraph('Levantamiento GPS, validacion KMZ, censo de clientes y lotes', styles['TableCell']),
     Paragraph('Bandeja, Campo Lite', styles['TableCellCenter'])],
    [Paragraph('Proyectos', styles['TableCell']),
     Paragraph('Seguimiento ANS, ordenes de construccion, verificacion documental', styles['TableCell']),
     Paragraph('Dashboard, Control', styles['TableCellCenter'])],
    [Paragraph('Ejecutivo', styles['TableCell']),
     Paragraph('Presupuestos, kick-off, cierre tecnico y financiero', styles['TableCell']),
     Paragraph('Dashboard, Cierre', styles['TableCellCenter'])],
    [Paragraph('Analista', styles['TableCell']),
     Paragraph('Reportes GIS, analisis de datos georreferenciados', styles['TableCell']),
     Paragraph('Reportes', styles['TableCellCenter'])],
    [Paragraph('Gerente', styles['TableCell']),
     Paragraph('Aprobaciones de proyectos, revision financiera', styles['TableCell']),
     Paragraph('Aprobaciones', styles['TableCellCenter'])],
]

t = Table(roles_data, colWidths=[1.2*inch, 3.5*inch, 1.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), DARK),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
]))
story.append(t)
story.append(PageBreak())

# ========== 3. FLUJO CARTOGRAFIA ==========
story.append(Paragraph('3. Flujo Cartografia (11 pasos)', styles['SectionTitle']))
story.append(Paragraph(
    'El rol de Cartografia ejecuta el levantamiento en campo, validacion de KMZ, '
    'y gestion de solicitudes de actualizacion cartografica y diseno de red.',
    styles['Body']))

cart_data = [
    [Paragraph('Paso', styles['TableHeader']),
     Paragraph('Actividad', styles['TableHeader']),
     Paragraph('ANS', styles['TableHeader']),
     Paragraph('Aprobacion', styles['TableHeader'])],
    ['a', 'Visita de reconocimiento inicial. Recibir zonas del ejecutivo para prospeccion', '-', 'No'],
    ['b', 'Validacion disponibilidad del servicio y afectaciones ambientales (Signatural, Sinupot, Mapas Bogota)', '-', 'No'],
    ['c', 'Visita levantamiento y validacion KMZ inicial. Reconocimiento de clientes y lotes (censo)', '-', 'No'],
    ['d', 'Solicitar actualizacion cartografica en Laserfiche. Insumos para loteo (JPEG/Word)', '15 dias', 'No'],
    ['e', 'Recibir actualizacion cartografica. Rechazo: <3 dias = 8d resp. >3 dias = 15d nuevos', '15 dias', 'Si'],
    ['f', 'Solicitar diseno de red en Laserfiche. KMZ trazado propuesto (JPEG)', '15 dias', 'No'],
    ['g', 'Recibir diseno de red a satisfaccion. Rechazo dentro de 3 dias habiles', '15 dias', 'Si'],
    ['h', 'Solicitar firma y autorizacion del ejecutivo para Informe Tecnico', '-', 'Si'],
    ['i', 'Solicitar Informe Tecnico. Coordenadas, potencial, consumos, metros, mallas, tuberia', '18 dias', 'No'],
    ['j', 'Visita cotizacion transversal con Ing. Obra, ambiental, permisos', '-', 'No'],
    ['k', 'Modificaciones post-visita. Regresa a paso d o f si aplica', '-', 'No'],
]

cart_table_data = [cart_data[0]]
for row in cart_data[1:]:
    cart_table_data.append([
        Paragraph(row[0], styles['TableCellCenter']),
        Paragraph(row[1], styles['TableCell']),
        Paragraph(row[2], styles['ANSRed'] if row[2] != '-' else styles['TableCellCenter']),
        Paragraph(row[3], styles['TableCellCenter']),
    ])

t = Table(cart_table_data, colWidths=[0.5*inch, 4*inch, 0.8*inch, 0.8*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), DARK),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(PageBreak())

# ========== 4. FLUJO PROYECTOS ==========
story.append(Paragraph('4. Flujo Proyectos (7 pasos)', styles['SectionTitle']))
proj_rows = [
    [Paragraph('Paso', styles['TableHeader']),
     Paragraph('Actividad', styles['TableHeader']),
     Paragraph('Aprobacion', styles['TableHeader'])],
    [Paragraph('a', styles['TableCellCenter']),
     Paragraph('Seguimiento al cumplimiento del ANS sobre entrega de Informes Tecnicos', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('b', styles['TableCellCenter']),
     Paragraph('Recepcion y verificacion con ejecutivo comercial del Informe Tecnico (tiempos, afectaciones, metros, ubicacion)', styles['TableCell']),
     Paragraph('Si', styles['TableCellCenter'])],
    [Paragraph('c', styles['TableCellCenter']),
     Paragraph('Garantizar entrega de evaluacion financiera para presentacion a gerencia (matriz aprobacion/modelo financiero)', styles['TableCell']),
     Paragraph('Si', styles['TableCellCenter'])],
    [Paragraph('d', styles['TableCellCenter']),
     Paragraph('Diligenciar formato de orden de construccion y solicitar firma al equipo comercial (Ejecutivo y Gerente)', styles['TableCell']),
     Paragraph('Si', styles['TableCellCenter'])],
    [Paragraph('e', styles['TableCellCenter']),
     Paragraph('Verificacion documental: diseno actualizado y cantidades de obra vs cotizacion', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('f', styles['TableCellCenter']),
     Paragraph('Remitir orden de construccion firmada a Proyectos de Ingenieria. Solicitar consecutivo de mascara', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('g', styles['TableCellCenter']),
     Paragraph('Recepcion de numero de mascara y carga de presupuesto en SAP', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
]
t = Table(proj_rows, colWidths=[0.5*inch, 4.5*inch, 0.8*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#065f46')),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(t)
story.append(Spacer(1, 0.3*inch))

# ========== 5. FLUJO EJECUTIVO ==========
story.append(Paragraph('5. Flujo Ejecutivo (5 pasos)', styles['SectionTitle']))
exec_rows = [
    [Paragraph('Paso', styles['TableHeader']),
     Paragraph('Actividad', styles['TableHeader']),
     Paragraph('Aprobacion', styles['TableHeader'])],
    [Paragraph('h', styles['TableCellCenter']),
     Paragraph('Solicitar liberacion del presupuesto al responsable del area comercial', styles['TableCell']),
     Paragraph('Si', styles['TableCellCenter'])],
    [Paragraph('i', styles['TableCellCenter']),
     Paragraph('Recepcion de liberacion del presupuesto y reenvio al area de proyectos de ingenieria', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('j', styles['TableCellCenter']),
     Paragraph('Seguimiento de asignacion (Kick-Off) a areas: ambiental, predial, construccion', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('k', styles['TableCellCenter']),
     Paragraph('Seguimiento al cumplimiento del ANS segun cada una de las actividades', styles['TableCell']),
     Paragraph('No', styles['TableCellCenter'])],
    [Paragraph('l', styles['TableCellCenter']),
     Paragraph('Cierre tecnico y financiero: metros, CAPEX, clientes, m3/cliente, artefactos, % financiacion, % II', styles['TableCell']),
     Paragraph('Si', styles['TableCellCenter'])],
]
t = Table(exec_rows, colWidths=[0.5*inch, 4.5*inch, 0.8*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#581c87')),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(t)
story.append(PageBreak())

# ========== 6. CAMPO LITE ==========
story.append(Paragraph('6. Modulo Campo Lite (PWA Offline)', styles['SectionTitle']))
story.append(Paragraph(
    'Campo Lite es el modulo movil disenado para cartografos que trabajan en zonas veredales '
    'sin cobertura de red celular. Funciona como una Progressive Web App (PWA) que se instala '
    'en el celular y opera 100% offline.',
    styles['Body']))
story.append(Paragraph('Flujo de trabajo en campo:', styles['SubTitle']))
campo_steps = [
    ('En oficina (con WiFi)', 'Instalar app desde Chrome. Navegar a la zona objetivo. Descargar mapa offline.'),
    ('En vereda (sin senal)', 'Capturar nodos GPS, tomar fotos, registrar datos de campo. Todo se guarda en IndexedDB (100+ MB).'),
    ('De vuelta (con senal)', 'Exportar en formato ArcGIS (GeoJSON, CSV, GPX, KMZ) o sincronizar con el servidor.'),
]
for title, desc in campo_steps:
    story.append(Paragraph(f'<b>{title}:</b> {desc}', styles['BulletItem']))
story.append(Spacer(1, 0.2*inch))

story.append(Paragraph('Formatos de exportacion para ArcGIS:', styles['SubTitle']))
export_data = [
    [Paragraph('Formato', styles['TableHeader']),
     Paragraph('Uso en ArcGIS', styles['TableHeader']),
     Paragraph('Offline', styles['TableHeader'])],
    [Paragraph('GeoJSON', styles['TableCell']),
     Paragraph('ArcGIS Pro > Add Data > JSON. Import directo', styles['TableCell']),
     Paragraph('Si', styles['ANSGreen'])],
    [Paragraph('CSV (XY)', styles['TableCell']),
     Paragraph('ArcGIS > Add Data > Add XY Data (campos Latitud/Longitud)', styles['TableCell']),
     Paragraph('Si', styles['ANSGreen'])],
    [Paragraph('GPX', styles['TableCell']),
     Paragraph('Conversion Tools > GPX to Features', styles['TableCell']),
     Paragraph('Si', styles['ANSGreen'])],
    [Paragraph('KMZ', styles['TableCell']),
     Paragraph('Conversion Tools > KML to Layer (Google Earth compatible)', styles['TableCell']),
     Paragraph('Si', styles['ANSGreen'])],
    [Paragraph('Backup ZIP', styles['TableCell']),
     Paragraph('Todos los formatos + fotos georeferenciadas en un solo archivo', styles['TableCell']),
     Paragraph('Si', styles['ANSGreen'])],
]
t = Table(export_data, colWidths=[1.2*inch, 3.5*inch, 0.8*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), DARK),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(t)
story.append(PageBreak())

# ========== 7. SEGUIMIENTO ANS ==========
story.append(Paragraph('7. Seguimiento ANS (Semaforo)', styles['SectionTitle']))
story.append(Paragraph(
    'El sistema calcula automaticamente los dias habiles restantes para cada tarea con ANS '
    'y muestra un semaforo de colores. Los fines de semana se excluyen del calculo.',
    styles['Body']))
ans_data = [
    [Paragraph('Estado', styles['TableHeader']),
     Paragraph('Condicion', styles['TableHeader']),
     Paragraph('Accion', styles['TableHeader'])],
    [Paragraph('VERDE', styles['ANSGreen']),
     Paragraph('Mas de 7 dias habiles restantes', styles['TableCell']),
     Paragraph('Dentro de plazo normal', styles['TableCell'])],
    [Paragraph('AMARILLO', styles['TableCell']),
     Paragraph('Entre 3 y 7 dias habiles restantes', styles['TableCell']),
     Paragraph('Alerta preventiva', styles['TableCell'])],
    [Paragraph('ROJO', styles['ANSRed']),
     Paragraph('Menos de 3 dias habiles restantes', styles['TableCell']),
     Paragraph('Atencion urgente requerida', styles['TableCell'])],
    [Paragraph('VENCIDO', styles['ANSRed']),
     Paragraph('Plazo expirado', styles['TableCell']),
     Paragraph('Escalamiento inmediato', styles['TableCell'])],
]
t = Table(ans_data, colWidths=[1.2*inch, 2.5*inch, 2.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), DARK),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph('Regla especial de rechazo (pasos CART_E y CART_G):', styles['SubTitle']))
story.append(Paragraph(
    '<bullet>&bull;</bullet> Si se rechaza DENTRO de los primeros 3 dias habiles: la respuesta es de 8 dias habiles',
    styles['BulletItem']))
story.append(Paragraph(
    '<bullet>&bull;</bullet> Si se rechaza FUERA de los primeros 3 dias habiles: arrancan nuevamente 15 dias habiles completos',
    styles['BulletItem']))
story.append(PageBreak())

# ========== 8. BACKLOG Y CLUSTERIZACION ==========
story.append(Paragraph('8. Backlog y Clusterizacion de Proyectos', styles['SectionTitle']))
story.append(Paragraph(
    'El modulo de Backlog permite gestionar el inventario de proyectos con informacion '
    'geografica y de demanda, facilitando la priorizacion y clusterizacion por zonas.',
    styles['Body']))
story.append(Paragraph('Campos del Backlog:', styles['SubTitle']))
backlog_fields = [
    'Estado del proyecto (prospeccion, cartografia, viabilidad, aprobacion, ejecucion, terminado)',
    'Cantidad de clientes potenciales',
    'Departamento y Municipio',
    'Punto de inicio/llegada con Latitud y Longitud',
    'Metros de red estimados',
    'Tipo de proyecto (expansion, conexion, mantenimiento)',
    'Cluster/zona asociada',
]
for b in backlog_fields:
    story.append(Paragraph(f'<bullet>&bull;</bullet> {b}', styles['BulletItem']))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph('Modelo de Clusterizacion:', styles['SubTitle']))
story.append(Paragraph(
    'Los proyectos se agrupan automaticamente por proximidad geografica y departamento/municipio. '
    'Esto permite identificar rutas optimas de trabajo, priorizar zonas con mayor potencial '
    'de clientes, y optimizar la asignacion de cuadrillas de campo.',
    styles['Body']))
story.append(PageBreak())

# ========== 9. CREDENCIALES ==========
story.append(Paragraph('9. Credenciales de Acceso', styles['SectionTitle']))
story.append(Paragraph(
    'URL del sistema: <b>https://gestor-cartografico-app.onrender.com</b>',
    styles['Body']))
story.append(Spacer(1, 0.1*inch))
cred_data = [
    [Paragraph('Usuario', styles['TableHeader']),
     Paragraph('Contrasena', styles['TableHeader']),
     Paragraph('Rol', styles['TableHeader'])],
    [Paragraph('bgaleanotec', styles['TableCell']),
     Paragraph('Vanti2026*', styles['TableCell']),
     Paragraph('SuperAdmin', styles['TableCellCenter'])],
    [Paragraph('admin', styles['TableCell']),
     Paragraph('Vanti2026*', styles['TableCell']),
     Paragraph('Admin', styles['TableCellCenter'])],
    [Paragraph('comercial', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Comercial', styles['TableCellCenter'])],
    [Paragraph('cartografo', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Cartografia', styles['TableCellCenter'])],
    [Paragraph('ingeniero', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Proyectos', styles['TableCellCenter'])],
    [Paragraph('analista', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Analista', styles['TableCellCenter'])],
    [Paragraph('gerente', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Gerente', styles['TableCellCenter'])],
    [Paragraph('ejecutivo', styles['TableCell']),
     Paragraph('password', styles['TableCell']),
     Paragraph('Ejecutivo', styles['TableCellCenter'])],
]
t = Table(cred_data, colWidths=[1.8*inch, 1.8*inch, 1.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), DARK),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 10),
]))
story.append(t)
story.append(Spacer(1, 0.5*inch))
story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph(
    'Documento generado automaticamente por el Gestor Cartografico - Vanti S.A. ESP - Abril 2026',
    styles['SmallGray']))

# Build PDF
doc.build(story)
print(f'PDF generado: {output_path}')
