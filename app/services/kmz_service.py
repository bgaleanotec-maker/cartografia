"""
KMZ Generation Service for Gestor Cartográfico
================================================
Generates KMZ (Google Earth) files from project nodes.
KMZ = ZIP archive containing a doc.kml file + optional assets.
Uses only stdlib (zipfile, io) + lxml (already in requirements).
"""

import io
import zipfile
from datetime import datetime
from lxml import etree


# KML Namespace
KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"


def _color_for_condition(has_water: bool, is_rocky: bool) -> str:
    """Return KML color (AABBGGRR) based on node condition."""
    if has_water:
        return "ffff5500"   # Blue (water)
    if is_rocky:
        return "ff0055ff"   # Orange (rocky)
    return "ff00aa00"       # Green (normal)


def _make_kml(project) -> bytes:
    """Build KML XML document from project and its nodes."""
    kml = etree.Element("kml", xmlns=KML_NS)
    doc = etree.SubElement(kml, "Document")

    # --- Document metadata ---
    etree.SubElement(doc, "name").text = f"Proyecto: {project.name}"
    etree.SubElement(doc, "description").text = (
        f"Exportado el {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"Dirección: {project.address or 'N/A'}\n"
        f"Estado: {project.phase}\n"
        f"Viabilidad: {project.viability_status}"
    )
    etree.SubElement(doc, "open").text = "1"

    # --- Styles ---
    # Node Normal
    def make_style(style_id: str, icon_color: str, line_color: str):
        style = etree.SubElement(doc, "Style", id=style_id)
        icon_style = etree.SubElement(style, "IconStyle")
        etree.SubElement(icon_style, "color").text = icon_color
        etree.SubElement(icon_style, "scale").text = "1.2"
        icon = etree.SubElement(icon_style, "Icon")
        etree.SubElement(icon, "href").text = (
            "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
        )
        line_style = etree.SubElement(style, "LineStyle")
        etree.SubElement(line_style, "color").text = line_color
        etree.SubElement(line_style, "width").text = "3"
        label_style = etree.SubElement(style, "LabelStyle")
        etree.SubElement(label_style, "scale").text = "0.8"

    make_style("node_normal", "ff00aa00", "ffff5500")
    make_style("node_water",  "ffff5500", "ffff5500")
    make_style("node_rocky",  "ff0055ff", "ff0055ff")
    make_style("route_line",  "ffff8800", "ffff8800")

    # --- Folder: Nodes ---
    folder_nodes = etree.SubElement(doc, "Folder")
    etree.SubElement(folder_nodes, "name").text = "Nodos de Levantamiento"
    etree.SubElement(folder_nodes, "open").text = "1"

    sorted_nodes = sorted(project.nodes, key=lambda n: n.sequence)
    coords_for_line = []

    for node in sorted_nodes:
        pm = etree.SubElement(folder_nodes, "Placemark")
        etree.SubElement(pm, "name").text = f"Nodo #{node.sequence}"

        # Style reference
        if node.has_water_source:
            style_url = "#node_water"
        elif node.is_rocky_ground:
            style_url = "#node_rocky"
        else:
            style_url = "#node_normal"
        etree.SubElement(pm, "styleUrl").text = style_url

        # Extended data / description
        desc_parts = [
            f"Clientes Potenciales: {node.potential_clients}",
            f"Puntos Gas: {node.gas_points}",
            f"Longitud Manual: {node.manual_length} m",
            f"Afectación Hídrica: {'Sí' if node.has_water_source else 'No'}",
            f"Terreno Rocoso: {'Sí' if node.is_rocky_ground else 'No'}",
        ]
        if node.observations:
            desc_parts.append(f"Observaciones: {node.observations}")
        etree.SubElement(pm, "description").text = "\n".join(desc_parts)

        # Extended Data for GIS apps
        ext_data = etree.SubElement(pm, "ExtendedData")
        fields = {
            "sequence": str(node.sequence),
            "potential_clients": str(node.potential_clients),
            "gas_points": str(node.gas_points),
            "manual_length_m": str(node.manual_length),
            "has_water_source": str(node.has_water_source),
            "is_rocky_ground": str(node.is_rocky_ground),
            "observations": node.observations or "",
        }
        for k, v in fields.items():
            data_el = etree.SubElement(ext_data, "Data", name=k)
            etree.SubElement(data_el, "value").text = v

        # Point geometry
        point = etree.SubElement(pm, "Point")
        etree.SubElement(point, "coordinates").text = (
            f"{node.longitude},{node.latitude},0"
        )

        coords_for_line.append((node.longitude, node.latitude))

    # --- Folder: Route Line ---
    if len(coords_for_line) >= 2:
        folder_route = etree.SubElement(doc, "Folder")
        etree.SubElement(folder_route, "name").text = "Trazado de Red"

        pm_line = etree.SubElement(folder_route, "Placemark")
        etree.SubElement(pm_line, "name").text = f"Trazado: {project.name}"
        etree.SubElement(pm_line, "styleUrl").text = "#route_line"

        # Calculate total distance
        total_m = sum(n.manual_length for n in sorted_nodes if n.manual_length)
        etree.SubElement(pm_line, "description").text = (
            f"Longitud Total: {total_m:.1f} m ({total_m/1000:.3f} km)\n"
            f"Nodos: {len(sorted_nodes)}\n"
            f"Clientes Totales: {sum(n.potential_clients for n in sorted_nodes)}\n"
            f"Puntos Gas Totales: {sum(n.gas_points for n in sorted_nodes)}"
        )

        line_string = etree.SubElement(pm_line, "LineString")
        etree.SubElement(line_string, "tessellate").text = "1"
        coords_str = " ".join(f"{lng},{lat},0" for lng, lat in coords_for_line)
        etree.SubElement(line_string, "coordinates").text = coords_str

    return etree.tostring(kml, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def generate_kmz(project) -> bytes:
    """
    Generate a KMZ binary from a Project model instance.
    Returns raw bytes of the ZIP archive ready to send as download.
    """
    kml_bytes = _make_kml(project)

    # Build ZIP (KMZ)
    kmz_buffer = io.BytesIO()
    with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)

    return kmz_buffer.getvalue()
