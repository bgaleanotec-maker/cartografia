"""Genera el PDF del Manual con capturas de pantalla y casos de uso."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
import os

DARK = HexColor('#0f172a')
ACCENT = HexColor('#3b82f6')
GREEN = HexColor('#10b981')
RED = HexColor('#ef4444')
GRAY = HexColor('#64748b')
LIGHT_BG = HexColor('#f1f5f9')
WHITE = HexColor('#ffffff')

SS_DIR = 'docs/screenshots'
OUTPUT = 'app/static/manual/Manual_GestorCartografico_Vanti.pdf'

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

doc = SimpleDocTemplate(OUTPUT, pagesize=letter,
    topMargin=0.8*inch, bottomMargin=0.7*inch,
    leftMargin=0.7*inch, rightMargin=0.7*inch)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('CoverTitle', fontSize=28, textColor=DARK, spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('CoverSub', fontSize=14, textColor=ACCENT, spaceAfter=10, alignment=TA_CENTER))
styles.add(ParagraphStyle('Section', fontSize=18, textColor=DARK, spaceBefore=16, spaceAfter=8, fontName='Helvetica-Bold', borderColor=ACCENT, borderWidth=2, borderPadding=4))
styles.add(ParagraphStyle('Sub', fontSize=13, textColor=ACCENT, spaceBefore=12, spaceAfter=5, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('Body', fontSize=10, textColor=DARK, spaceAfter=5, leading=14, alignment=TA_JUSTIFY))
styles.add(ParagraphStyle('BulletCustom', fontSize=10, textColor=DARK, spaceAfter=3, leading=13, leftIndent=20, bulletIndent=10))
styles.add(ParagraphStyle('Caption', fontSize=8, textColor=GRAY, alignment=TA_CENTER, spaceAfter=8, spaceBefore=2, fontName='Helvetica-Oblique'))
styles.add(ParagraphStyle('SmallGray', fontSize=8, textColor=GRAY, alignment=TA_CENTER))
styles.add(ParagraphStyle('TH', fontSize=9, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER))
styles.add(ParagraphStyle('TD', fontSize=9, textColor=DARK, leading=11))
styles.add(ParagraphStyle('TDC', fontSize=9, textColor=DARK, alignment=TA_CENTER, leading=11))
styles.add(ParagraphStyle('CaseTitle', fontSize=11, textColor=HexColor('#1e40af'), spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('CaseStep', fontSize=10, textColor=DARK, spaceAfter=3, leftIndent=15, leading=13))

story = []

def add_screenshot(filename, caption, width=5.5*inch):
    path = os.path.join(SS_DIR, filename)
    if os.path.exists(path):
        img = Image(path, width=width, height=width*0.625)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Paragraph(caption, styles['Caption']))
    else:
        story.append(Paragraph(f'[Imagen: {caption}]', styles['Caption']))

def table(data, col_widths, header_color=DARK):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), header_color),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, GRAY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

# ============================
# PORTADA
# ============================
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph('Manual de Operacion', styles['CoverTitle']))
story.append(Paragraph('Gestor Cartografico', styles['CoverTitle']))
story.append(Spacer(1, 0.2*inch))
story.append(HRFlowable(width='60%', thickness=3, color=ACCENT, spaceAfter=12))
story.append(Paragraph('Plataforma de Gestion de Expansion de Redes de Gas', styles['CoverSub']))
story.append(Paragraph('Vanti S.A. ESP', styles['CoverSub']))
story.append(Spacer(1, 0.8*inch))
story.append(Paragraph('Elaborado por:', styles['SmallGray']))
story.append(Paragraph('<b>Brayan G. y Equipo de Herramientas</b>', styles['CoverSub']))
story.append(Spacer(1, 0.5*inch))
story.append(Paragraph('Abril 2026 - Version 2.0', styles['SmallGray']))
story.append(Paragraph('https://gestor-cartografico-app.onrender.com', styles['SmallGray']))
story.append(Paragraph('Documento Confidencial', styles['SmallGray']))
story.append(PageBreak())

# ============================
# CONTENIDO
# ============================
story.append(Paragraph('Contenido', styles['Section']))
toc = ['1. Introduccion al Sistema', '2. Acceso y Login', '3. Dashboard General',
       '4. Roles y Permisos', '5. Flujo Cartografia — Caso de Uso Practico',
       '6. Flujo Proyectos — Caso de Uso Practico', '7. Flujo Ejecutivo — Caso de Uso Practico',
       '8. Campo Lite (Trabajo Offline en Veredas)', '9. Backlog y Clusterizacion',
       '10. Ruta Optima', '11. Seguimiento ANS', '12. Credenciales de Acceso']
for t in toc:
    story.append(Paragraph(t, styles['Body']))
story.append(PageBreak())

# ============================
# 1. INTRODUCCION
# ============================
story.append(Paragraph('1. Introduccion al Sistema', styles['Section']))
story.append(Paragraph(
    'El Gestor Cartografico es una plataforma web para Vanti S.A. ESP que gestiona el ciclo completo '
    'de proyectos de expansion de redes de gas natural: desde la prospeccion en campo hasta el cierre '
    'tecnico y financiero, con seguimiento de ANS automatizado.',
    styles['Body']))
story.append(Paragraph('Capacidades principales:', styles['Sub']))
for b in [
    'Trabajo en zonas veredales SIN cobertura de datos (PWA Offline)',
    'Captura GPS con fotos georeferenciadas y export a ArcGIS',
    'Flujos de trabajo por rol con seguimiento ANS (semaforo)',
    'Backlog de proyectos con clustering por zona geografica',
    'Ruta optima para planificacion de visitas de campo',
    'Exportacion: GeoJSON, CSV, GPX, KMZ compatible con ArcGIS Desktop/Online',
]:
    story.append(Paragraph(f'<bullet>&bull;</bullet> {b}', styles['BulletCustom']))
story.append(PageBreak())

# ============================
# 2. ACCESO Y LOGIN
# ============================
story.append(Paragraph('2. Acceso y Login', styles['Section']))
story.append(Paragraph('Acceda al sistema desde cualquier navegador:', styles['Body']))
story.append(Paragraph('<b>URL:</b> https://gestor-cartografico-app.onrender.com', styles['Body']))
add_screenshot('01_login.png', 'Figura 1: Pantalla de inicio de sesion del Gestor Cartografico')
story.append(Paragraph(
    'Ingrese su usuario y contrasena. El sistema redirigira automaticamente al dashboard '
    'correspondiente segun su rol asignado.', styles['Body']))
story.append(PageBreak())

# ============================
# 3. DASHBOARD
# ============================
story.append(Paragraph('3. Dashboard General', styles['Section']))
story.append(Paragraph(
    'Al ingresar, el dashboard muestra un resumen del estado de los proyectos con accesos '
    'rapidos a las funciones mas utilizadas segun el rol.', styles['Body']))
add_screenshot('02_dashboard.png', 'Figura 2: Dashboard principal con acciones rapidas y actividad reciente')
story.append(Paragraph('Elementos del dashboard:', styles['Sub']))
for b in ['Acciones rapidas: Nueva Visita, Bandeja Cartografia, Gestion Obras',
          'Actividad reciente: ultimos movimientos en proyectos',
          'Menu lateral con acceso a Flujos PMO, Backlog y Herramientas']:
    story.append(Paragraph(f'<bullet>&bull;</bullet> {b}', styles['BulletCustom']))
story.append(PageBreak())

# ============================
# 4. ROLES
# ============================
story.append(Paragraph('4. Roles y Permisos', styles['Section']))
roles = [
    [Paragraph('Rol', styles['TH']), Paragraph('Funcion Principal', styles['TH']), Paragraph('Acceso', styles['TH'])],
    [Paragraph('SuperAdmin', styles['TD']), Paragraph('Acceso total, gestion de usuarios y configuracion global', styles['TD']), Paragraph('Todo', styles['TDC'])],
    [Paragraph('Cartografia', styles['TD']), Paragraph('Levantamiento GPS, validacion KMZ, censo de clientes y lotes', styles['TD']), Paragraph('Campo Lite, Bandeja', styles['TDC'])],
    [Paragraph('Proyectos', styles['TD']), Paragraph('Seguimiento ANS, ordenes de construccion, verificacion documental', styles['TD']), Paragraph('Dashboard, Control', styles['TDC'])],
    [Paragraph('Ejecutivo', styles['TD']), Paragraph('Presupuestos, kick-off, cierre tecnico y financiero', styles['TD']), Paragraph('Aprobaciones, Cierre', styles['TDC'])],
    [Paragraph('Comercial', styles['TD']), Paragraph('Visitas de prospeccion y creacion de proyectos nuevos', styles['TD']), Paragraph('Visitas, Proyectos', styles['TDC'])],
    [Paragraph('Gerente', styles['TD']), Paragraph('Aprobacion de proyectos y revision financiera', styles['TD']), Paragraph('Aprobaciones', styles['TDC'])],
]
story.append(table(roles, [1.2*inch, 3.3*inch, 1.5*inch]))
add_screenshot('08_superadmin.png', 'Figura 3: Panel SuperAdmin con gestion de usuarios')
story.append(PageBreak())

# ============================
# 5. FLUJO CARTOGRAFIA — CASO DE USO
# ============================
story.append(Paragraph('5. Flujo Cartografia — Caso de Uso Practico', styles['Section']))
story.append(Paragraph(
    '<b>Escenario:</b> El ejecutivo comercial asigna la zona "Vereda La Esperanza" en Soacha '
    'al cartografo Juan para levantar la informacion de campo.', styles['Body']))

story.append(Paragraph('Caso de Uso: Levantamiento de Vereda La Esperanza', styles['CaseTitle']))
steps = [
    '<b>Paso 1 (CART_A):</b> Juan recibe la asignacion en la bandeja. Click "Iniciar" en la tarea.',
    '<b>Paso 2 (CART_B):</b> Juan valida en Signatural que la zona tiene disponibilidad de servicio y no hay afectaciones ambientales. Agrega nota: "Sin restricciones ambientales".',
    '<b>Paso 3 (CART_C):</b> Juan va a campo con Campo Lite. Captura 15 nodos GPS, 8 fotos, identifica 42 clientes potenciales y 3 lotes sin lotear.',
    '<b>Paso 4 (CART_D):</b> Juan solicita actualizacion cartografica para los 3 lotes. <b>ANS: 15 dias habiles.</b> El semaforo queda en VERDE.',
    '<b>Paso 5 (CART_E):</b> A los 12 dias recibe la actualizacion. Revisa y aprueba. Si hubiera rechazado dentro de 3 dias, tendria 8 dias de respuesta.',
    '<b>Paso 6 (CART_F):</b> Juan solicita diseno de red con el KMZ del trazado propuesto. <b>ANS: 15 dias.</b>',
    '<b>Paso 7 (CART_G):</b> Recibe el diseno, lo valida contra el levantamiento de campo. Aprueba.',
    '<b>Paso 8 (CART_H):</b> Solicita firma del ejecutivo. El ejecutivo revisa y aprueba.',
    '<b>Paso 9 (CART_I):</b> Monta la solicitud de Informe Tecnico con coordenadas, potencial (42 clientes), metros (850m). <b>ANS: 18 dias.</b>',
    '<b>Paso 10 (CART_J):</b> Visita de cotizacion transversal con Ingeniero de Obra y area ambiental.',
    '<b>Paso 11 (CART_K):</b> No se requieren modificaciones. Flujo completado.',
]
for s in steps:
    story.append(Paragraph(s, styles['CaseStep']))
story.append(Spacer(1, 0.1*inch))
add_screenshot('06_cartografia.png', 'Figura 4: Bandeja de cartografia con proyectos asignados')
story.append(Spacer(1, 0.1*inch))
# Tabla de flujo
cart_data = [
    [Paragraph('Paso', styles['TH']), Paragraph('Actividad', styles['TH']), Paragraph('ANS', styles['TH'])],
]
cart_steps = [
    ('a', 'Visita reconocimiento inicial', '-'),
    ('b', 'Validacion disponibilidad y afectaciones', '-'),
    ('c', 'Levantamiento KMZ y censo', '-'),
    ('d', 'Solicitar actualizacion cartografica', '15d'),
    ('e', 'Recibir actualizacion (aprobacion/rechazo)', '15d'),
    ('f', 'Solicitar diseno de red', '15d'),
    ('g', 'Recibir diseno de red', '15d'),
    ('h', 'Firma ejecutivo para Informe Tecnico', '-'),
    ('i', 'Solicitar Informe Tecnico', '18d'),
    ('j', 'Visita cotizacion transversal', '-'),
    ('k', 'Modificaciones post-visita', '-'),
]
for paso, act, ans in cart_steps:
    cart_data.append([Paragraph(paso, styles['TDC']), Paragraph(act, styles['TD']),
        Paragraph(f'<b><font color="red">{ans}</font></b>' if ans != '-' else '-', styles['TDC'])])
story.append(table(cart_data, [0.4*inch, 4.3*inch, 0.6*inch]))
story.append(PageBreak())

# ============================
# 6. FLUJO PROYECTOS — CASO DE USO
# ============================
story.append(Paragraph('6. Flujo Proyectos — Caso de Uso Practico', styles['Section']))
story.append(Paragraph(
    '<b>Escenario:</b> Maria (rol Proyectos) recibe el Informe Tecnico de "Vereda La Esperanza" '
    'y gestiona la orden de construccion.', styles['Body']))
story.append(Paragraph('Caso de Uso: Gestion de Orden de Construccion', styles['CaseTitle']))
proj_steps = [
    '<b>PROY_A:</b> Maria verifica que el Informe Tecnico llego dentro del ANS (18 dias). Semaforo VERDE.',
    '<b>PROY_B:</b> Revisa con el ejecutivo: 850m de red, 42 clientes, sin afectaciones ambientales. Aprueba.',
    '<b>PROY_C:</b> Solicita evaluacion financiera al ejecutivo. El modelo muestra TIR del 15%. Se presenta a gerencia.',
    '<b>PROY_D:</b> Con la aprobacion, diligencia la orden de construccion. Solicita firma al gerente.',
    '<b>PROY_E:</b> Verifica que el diseno actualizado coincida con las cantidades de obra cotizadas.',
    '<b>PROY_F:</b> Remite la orden firmada a Proyectos de Ingenieria por email. Solicita consecutivo de mascara.',
    '<b>PROY_G:</b> Recibe mascara #12345 y carga el presupuesto en SAP. Flujo completado.',
]
for s in proj_steps:
    story.append(Paragraph(s, styles['CaseStep']))
add_screenshot('09_proyectos.png', 'Figura 5: Dashboard de proyectos')
story.append(PageBreak())

# ============================
# 7. FLUJO EJECUTIVO — CASO DE USO
# ============================
story.append(Paragraph('7. Flujo Ejecutivo — Caso de Uso Practico', styles['Section']))
story.append(Paragraph(
    '<b>Escenario:</b> Carlos (rol Ejecutivo) gestiona la liberacion de presupuesto y el seguimiento '
    'hasta el cierre tecnico-financiero del proyecto.', styles['Body']))
story.append(Paragraph('Caso de Uso: Cierre de Proyecto', styles['CaseTitle']))
exec_steps = [
    '<b>EJEC_H:</b> Carlos solicita liberacion del presupuesto ($120M) al gerente comercial.',
    '<b>EJEC_I:</b> Recibe confirmacion y reenvia a Proyectos de Ingenieria para inicio de obra.',
    '<b>EJEC_J:</b> Realiza kick-off con areas: ambiental (permiso ANLA), predial (servidumbre), construccion.',
    '<b>EJEC_K:</b> Hace seguimiento semanal al ANS de cada area. Ambiental: 30d, Predial: 15d, Construccion: 60d.',
    '<b>EJEC_L:</b> Al finalizar, verifica cierre: 850m construidos, CAPEX $118M (2% ahorro), 42 clientes conectados, 1.2 m3/dia/cliente, 68 artefactos, 85% financiacion, 12% II.',
]
for s in exec_steps:
    story.append(Paragraph(s, styles['CaseStep']))
add_screenshot('03_workflow.png', 'Figura 6: Panel de flujos de trabajo con seguimiento ANS')
story.append(PageBreak())

# ============================
# 8. CAMPO LITE
# ============================
story.append(Paragraph('8. Campo Lite — Trabajo Offline en Veredas', styles['Section']))
story.append(Paragraph(
    'Campo Lite es el modulo para cartografos en zonas rurales SIN senal de celular. '
    'Se instala como app en el celular (PWA) y funciona 100% offline.', styles['Body']))

story.append(Paragraph('Caso de Uso: Levantamiento en Vereda sin Senal', styles['CaseTitle']))
campo_steps = [
    '<b>En oficina (con WiFi):</b> El cartografo abre Campo Lite, navega al mapa de la zona, y presiona "Descargar mapa de esta zona" para cachear los tiles. Instala la app desde Chrome.',
    '<b>En la vereda (SIN senal):</b> Abre la app. El GPS del celular funciona por satelite (no necesita datos). Captura nodos tocando + en el mapa. Toma fotos con la camara. Llena datos por nodo: clientes, gas, condicion terreno. Todo se guarda en IndexedDB (100+ MB).',
    '<b>De vuelta (con senal):</b> Exporta los datos: GeoJSON para ArcGIS Pro, CSV para Add XY Data, GPX para intercambio GPS, KMZ para Google Earth. O descarga el Backup ZIP con todos los formatos + fotos.',
]
for s in campo_steps:
    story.append(Paragraph(s, styles['CaseStep']))
story.append(Spacer(1, 0.1*inch))
add_screenshot('07_campo_lite.png', 'Figura 7: Campo Lite en vista movil con mapa y captura GPS', width=3*inch)

story.append(Paragraph('Formatos de exportacion:', styles['Sub']))
exp_data = [
    [Paragraph('Formato', styles['TH']), Paragraph('Uso en ArcGIS', styles['TH'])],
    [Paragraph('GeoJSON', styles['TD']), Paragraph('ArcGIS Pro > Add Data > JSON', styles['TD'])],
    [Paragraph('CSV', styles['TD']), Paragraph('Add Data > Add XY Data (Latitud/Longitud)', styles['TD'])],
    [Paragraph('GPX', styles['TD']), Paragraph('Conversion Tools > GPX to Features', styles['TD'])],
    [Paragraph('KMZ', styles['TD']), Paragraph('Conversion Tools > KML to Layer', styles['TD'])],
    [Paragraph('Backup ZIP', styles['TD']), Paragraph('Todos los formatos + fotos georeferenciadas', styles['TD'])],
]
story.append(table(exp_data, [1.2*inch, 4.5*inch]))
story.append(PageBreak())

# ============================
# 9. BACKLOG Y CLUSTERING
# ============================
story.append(Paragraph('9. Backlog y Clusterizacion de Proyectos', styles['Section']))
story.append(Paragraph(
    'El modulo Backlog centraliza el inventario de proyectos con datos geograficos y de demanda '
    'para priorizar y agrupar por zonas.', styles['Body']))
add_screenshot('04_backlog.png', 'Figura 8: Backlog de proyectos con filtros y clustering')
story.append(Paragraph('Campos del Backlog:', styles['Sub']))
for b in ['Estado del proyecto (prospeccion a terminado)', 'Clientes potenciales y metros de red',
          'Departamento y Municipio', 'Coordenadas inicio/llegada (lat/lng)',
          'Prioridad (1-Critico a 4-Bajo)', 'Cluster asignado automaticamente']:
    story.append(Paragraph(f'<bullet>&bull;</bullet> {b}', styles['BulletCustom']))
story.append(Paragraph(
    '<b>Clustering:</b> El boton "Clusterizar" agrupa proyectos por proximidad geografica (radio configurable en km). '
    'Permite identificar zonas con mayor concentracion de potencial.', styles['Body']))
story.append(PageBreak())

# ============================
# 10. RUTA OPTIMA
# ============================
story.append(Paragraph('10. Ruta Optima', styles['Section']))
story.append(Paragraph(
    'El modulo calcula la secuencia optima de visitas usando el algoritmo nearest-neighbor, '
    'minimizando la distancia total de recorrido.', styles['Body']))
add_screenshot('05_ruta_optima.png', 'Figura 9: Mapa con ruta optima entre proyectos')
story.append(Paragraph('Caso de Uso: Planificar semana de campo', styles['CaseTitle']))
story.append(Paragraph(
    'El coordinador abre Ruta Optima, ve los 8 proyectos pendientes de visita en el mapa con la ruta '
    'trazada y la distancia total (47 km). Asigna la secuencia al cartografo para la semana.',
    styles['CaseStep']))
story.append(PageBreak())

# ============================
# 11. SEGUIMIENTO ANS
# ============================
story.append(Paragraph('11. Seguimiento ANS (Semaforo)', styles['Section']))
story.append(Paragraph(
    'Cada tarea con ANS tiene un semaforo automatico que calcula dias habiles restantes '
    '(excluyendo fines de semana).', styles['Body']))
ans = [
    [Paragraph('Semaforo', styles['TH']), Paragraph('Condicion', styles['TH']), Paragraph('Accion', styles['TH'])],
    [Paragraph('<font color="#10b981"><b>VERDE</b></font>', styles['TDC']), Paragraph('Mas de 7 dias habiles', styles['TD']), Paragraph('Normal', styles['TD'])],
    [Paragraph('<font color="#f59e0b"><b>AMARILLO</b></font>', styles['TDC']), Paragraph('3 a 7 dias habiles', styles['TD']), Paragraph('Alerta preventiva', styles['TD'])],
    [Paragraph('<font color="#ef4444"><b>ROJO</b></font>', styles['TDC']), Paragraph('Menos de 3 dias', styles['TD']), Paragraph('Atencion urgente', styles['TD'])],
    [Paragraph('<font color="#ef4444"><b>VENCIDO</b></font>', styles['TDC']), Paragraph('Plazo expirado', styles['TD']), Paragraph('Escalamiento inmediato', styles['TD'])],
]
story.append(table(ans, [1.2*inch, 2.3*inch, 2.3*inch]))
story.append(Spacer(1, 0.15*inch))
story.append(Paragraph('<b>Regla especial de rechazo (CART_E y CART_G):</b>', styles['Body']))
story.append(Paragraph('<bullet>&bull;</bullet> Rechazo dentro de 3 dias habiles: 8 dias de respuesta', styles['BulletCustom']))
story.append(Paragraph('<bullet>&bull;</bullet> Rechazo fuera de 3 dias habiles: 15 dias habiles nuevos', styles['BulletCustom']))
story.append(PageBreak())

# ============================
# 12. CREDENCIALES
# ============================
story.append(Paragraph('12. Credenciales de Acceso', styles['Section']))
story.append(Paragraph('<b>URL:</b> https://gestor-cartografico-app.onrender.com', styles['Body']))
cred = [
    [Paragraph('Usuario', styles['TH']), Paragraph('Contrasena', styles['TH']), Paragraph('Rol', styles['TH'])],
    [Paragraph('bgaleanotec', styles['TD']), Paragraph('Vanti2026*', styles['TD']), Paragraph('SuperAdmin', styles['TDC'])],
    [Paragraph('admin', styles['TD']), Paragraph('Vanti2026*', styles['TD']), Paragraph('Admin', styles['TDC'])],
    [Paragraph('comercial', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Comercial', styles['TDC'])],
    [Paragraph('cartografo', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Cartografia', styles['TDC'])],
    [Paragraph('ingeniero', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Proyectos', styles['TDC'])],
    [Paragraph('analista', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Analista', styles['TDC'])],
    [Paragraph('gerente', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Gerente', styles['TDC'])],
    [Paragraph('ejecutivo', styles['TD']), Paragraph('password', styles['TD']), Paragraph('Ejecutivo', styles['TDC'])],
]
story.append(table(cred, [1.6*inch, 1.6*inch, 1.4*inch]))
story.append(Spacer(1, 1*inch))
story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
story.append(Spacer(1, 0.15*inch))
story.append(Paragraph('<b>Elaborado por: Brayan G. y Equipo de Herramientas</b>', styles['SmallGray']))
story.append(Paragraph('Vanti S.A. ESP - Abril 2026 - Version 2.0', styles['SmallGray']))
story.append(Paragraph('Generado automaticamente por el Gestor Cartografico', styles['SmallGray']))

doc.build(story)
print(f'PDF generado: {OUTPUT}')
