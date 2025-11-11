import pandas as pd
from django.core.management.base import BaseCommand
from datetime import datetime
import re
from core.models import (
    Persona, Estudiante, Escuela, Facultad, Actividad, Indicador,
    Participacion, Lugar, Sede, Tema, TemaAsociado, Prioridad,
    PrioridadAsociada, LineaEstrategia, EstrategiaAsociada,
    LineaProyecto, AsociacionProyecto, ActividadConsolidada,
    Consolidacion
)

def limpiar(valor):
    """Convierte '', 'NULL', NaN en None."""
    if pd.isna(valor) or str(valor).strip().upper() in ['', 'NULL', 'NONE']:
        return None
    return str(valor).strip()


def convertir_fecha(fecha_str):
    """
    Normaliza diferentes separadores y formatos de fecha comunes.
    Devuelve objeto date o None si no se puede parsear.
    Asume formato día/mes/año (day-first) para ambigüedades como 01/02/03.
    """
    if not fecha_str or str(fecha_str).strip() == "":
        return None

    s = str(fecha_str).strip()

    # Reemplazar cualquier caracter no numérico por '/' (acepta '-', '.', ' ', etc.)
    s_norm = re.sub(r"[^\d]", "/", s)

    # Lista de formatos a probar (day-first preferido)
    formatos = [
        "%d/%m/%Y",  # 24/05/2024
        "%d/%m/%y",  # 24/05/24
        "%Y/%m/%d",  # 2024/05/24
        "%d/%m",     # 24/05 -> si quieres asumir año actual (opcional)
    ]

    for fmt in formatos:
        try:
            fecha = datetime.strptime(s_norm, fmt).date()
            # Opcional: si %y produce año muy antiguo, ajustar (raro con %y moderno)
            if fecha.year < 1900 or fecha.year > 2100:
                # protección adicional si llega algo raro
                continue
            return fecha
        except ValueError:
            continue

    # Si no pudo parsear, informar y devolver None
    print(f"⚠ Fecha inválida encontrada: {fecha_str} → se asigna NULL")
    return None



class Command(BaseCommand):
    help = "Importa datos desde un CSV y llena la base de datos."

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', type=str, help='Ruta del archivo CSV')

    def handle(self, *args, **options):
        archivo = options['archivo_csv']

        self.stdout.write(self.style.SUCCESS(f"Leyendo archivo: {archivo}"))

        try:
            df = pd.read_csv(archivo, dtype=str)
        except:
            df = pd.read_csv(archivo, sep=";", dtype=str)

        self.stdout.write(self.style.WARNING(f"Total filas: {len(df)}"))

        for i, row in df.iterrows():

            # ---------------------------------------------------------
            # ✅ 1. Limpieza de columnas del CSV
            # ---------------------------------------------------------
            anio = limpiar(row.get("Año"))
            actividad_nombre = limpiar(row.get("Actividad"))
            actividad_consolidada_nombre = limpiar(row.get("Actividad consolidada"))
            linea_proyecto_nombre = limpiar(row.get("Linea del Proyecto"))
            indicador_nombre = limpiar(row.get("Indicador"))

            fecha = convertir_fecha(limpiar(row.get("Fecha")))
            sede_nombre = limpiar(row.get("Sede"))
            estamento = limpiar(row.get("Estamento"))

            facultad_nombre = limpiar(row.get("Facultad/Instituto/Área"))
            escuela_nombre = limpiar(row.get("Escuela/Programa Académico"))

            nombre_persona = limpiar(row.get("Nombre"))
            tipo_documento = limpiar(row.get("Tipo de Documento"))
            numero_documento = limpiar(row.get("N° Documento de Identidad"))
            edad = limpiar(row.get("Edad"))
            telefono = limpiar(row.get("Telefono"))
            correo = limpiar(row.get("Correo"))
            sexo = limpiar(row.get("Sexo"))
            semestre = limpiar(row.get("Semestre"))

            tema_nombre = limpiar(row.get("Tema"))
            prioridad_nombre = limpiar(row.get("Prioridad"))
            estrategia_nombre = limpiar(row.get("Linea de estrategia"))

            # ---------------------------------------------------------
            # ✅ 2. Facultad y Escuela
            # ---------------------------------------------------------
            facultad_obj = None
            if facultad_nombre:
                facultad_obj, _ = Facultad.objects.get_or_create(
                    nombre=facultad_nombre
                )

            escuela_obj = None
            if escuela_nombre:
                escuela_obj, _ = Escuela.objects.get_or_create(
                    nombre=escuela_nombre,
                    facultad=facultad_obj
                )

            # ---------------------------------------------------------
            # ✅ 3. Persona o Estudiante
            # ---------------------------------------------------------
# ---------------------------------------------------------
# ✅ 3. Persona o Estudiante
# ---------------------------------------------------------

            # ---- Caso 1: Es estudiante (tiene semestre)
            if semestre:
                # Si NO hay documento → crear estudiante nuevo siempre
                if not numero_documento:
                    persona_obj = Estudiante.objects.create(
                        nombre=nombre_persona,
                        tipo_documento=tipo_documento,
                        sexo=sexo,
                        edad=int(edad) if edad and edad.isdigit() else None,
                        telefono=telefono,
                        correo=correo,
                        estamento=estamento,
                        escuela=escuela_obj,
                        semestre=int(semestre) if semestre.isdigit() else None
                    )

                else:
                    # Documento existe → update_or_create
                    persona_obj, created = Estudiante.objects.update_or_create(
                        numero_documento=numero_documento,
                        defaults={
                            "nombre": nombre_persona,
                            "tipo_documento": tipo_documento,
                            "sexo": sexo,
                            "edad": int(edad) if edad and edad.isdigit() else None,
                            "telefono": telefono,
                            "correo": correo,
                            "estamento": estamento,
                            "escuela": escuela_obj,
                            "semestre": int(semestre) if semestre.isdigit() else None
                        }
                    )

            # ---- Caso 2: Persona normal
            else:
                # Si NO hay documento → crear persona nueva siempre
                if not numero_documento:
                    persona_obj = Persona.objects.create(
                        nombre=nombre_persona,
                        tipo_documento=tipo_documento,
                        sexo=sexo,
                        edad=int(edad) if edad and edad.isdigit() else None,
                        telefono=telefono,
                        correo=correo,
                        estamento=estamento,
                        escuela=escuela_obj
                    )

                else:
                    # Documento existe → update_or_create
                    persona_obj, created = Persona.objects.update_or_create(
                        numero_documento=numero_documento,
                        defaults={
                            "nombre": nombre_persona,
                            "tipo_documento": tipo_documento,
                            "sexo": sexo,
                            "edad": int(edad) if edad and edad.isdigit() else None,
                            "telefono": telefono,
                            "correo": correo,
                            "estamento": estamento,
                            "escuela": escuela_obj
                        }
                    )



            # ---------------------------------------------------------
            # ✅ 4. Indicador
            # ---------------------------------------------------------
            indicador_obj = None
            if indicador_nombre:
                indicador_obj, _ = Indicador.objects.get_or_create(
                    nombre=indicador_nombre
                )

            # ---------------------------------------------------------
            # ✅ 5. Actividad
            # ---------------------------------------------------------
            actividad_obj, _ = Actividad.objects.get_or_create(
                nombre=actividad_nombre,
                anio=int(float(anio)) if anio else None,
                defaults={
                    "indicador": indicador_obj
                }
            )

            # ---------------------------------------------------------
            # ✅ 6. Actividad consolidada y su relación
            # ---------------------------------------------------------
            if actividad_consolidada_nombre:
                act_con_obj, _ = ActividadConsolidada.objects.get_or_create(
                    nombre=actividad_consolidada_nombre
                )
                Consolidacion.objects.get_or_create(
                    actividad=actividad_obj,
                    actividad_consolidada=act_con_obj
                )

            # ---------------------------------------------------------
            # ✅ 7. Línea de proyecto
            # ---------------------------------------------------------
            if linea_proyecto_nombre:
                linea_proj_obj, _ = LineaProyecto.objects.get_or_create(
                    nombre=linea_proyecto_nombre
                )
                AsociacionProyecto.objects.get_or_create(
                    actividad=actividad_obj,
                    linea_proyecto=linea_proj_obj
                )

            # ---------------------------------------------------------
            # ✅ 8. Sede
            # ---------------------------------------------------------
            sede_obj = None
            if sede_nombre:
                sede_obj, _ = Sede.objects.get_or_create(nombre=sede_nombre)

            # ---------------------------------------------------------
            # ✅ 9. Participación
            # ---------------------------------------------------------
            part_obj, _ = Participacion.objects.get_or_create(
                persona=persona_obj,
                actividad=actividad_obj,
                fecha=fecha
            )

            # ---------------------------------------------------------
            # ✅ 10. Lugar (Participación ↔ Sede)
            # ---------------------------------------------------------
            if sede_obj:
                Lugar.objects.get_or_create(
                    participacion=part_obj,
                    sede=sede_obj
                )

            # ---------------------------------------------------------
            # ✅ 11. Tema
            # ---------------------------------------------------------
            if tema_nombre:
                tema_obj, _ = Tema.objects.get_or_create(nombre=tema_nombre)
                TemaAsociado.objects.get_or_create(
                    actividad=actividad_obj,
                    tema=tema_obj
                )

            # ---------------------------------------------------------
            # ✅ 12. Prioridad
            # ---------------------------------------------------------
            if prioridad_nombre:
                prioridad_obj, _ = Prioridad.objects.get_or_create(nombre=prioridad_nombre)
                PrioridadAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    prioridad=prioridad_obj
                )

            # ---------------------------------------------------------
            # ✅ 13. Línea de estrategia
            # ---------------------------------------------------------
            if estrategia_nombre:
                est_obj, _ = LineaEstrategia.objects.get_or_create(nombre=estrategia_nombre)
                EstrategiaAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    linea_estrategia=est_obj
                )

            # ---------------------------------------------------------
            self.stdout.write(self.style.SUCCESS(f"Fila {i+1} procesada"))

        self.stdout.write(self.style.SUCCESS("✅ Importación completada"))