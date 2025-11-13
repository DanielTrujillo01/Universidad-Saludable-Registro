import pandas as pd
from django.core.management.base import BaseCommand
from datetime import datetime
from rapidfuzz import fuzz
from django.db.models import Q
import re
from core.models import (
    Persona, Estudiante, Escuela, Facultad, Actividad, Indicador,
    Participacion, Lugar, Sede, Tema, TemaAsociado, Prioridad,
    PrioridadAsociada, LineaEstrategia, EstrategiaAsociada,
    LineaProyecto, AsociacionProyecto, ActividadConsolidada,
    Consolidacion
)

def limpiar(valor):
    """
    Convierte '', 'NULL', NaN, 'NAN' y variaciones en None.
    Asegura que solo cadenas no nulas ni vacías sean devueltas.
    """
    if pd.isna(valor):
        return None

    s = str(valor).strip()
    
    # Lista de representaciones comunes de Nulo (case insensitive)
    if not s or s.upper() in ['', 'NULL', 'NONE', 'NAN', 'N/A', 'NA', '#N/A']:
        return None
    
    return s


def convertir_fecha(fecha_str):
    """
    Normaliza diferentes separadores y formatos de fecha comunes.
    Devuelve objeto date o None si no se puede parsear.
    """
    if not fecha_str or str(fecha_str).strip() == "":
        return None

    s = str(fecha_str).strip()

    # Reemplazar cualquier caracter no numérico por '/' (acepta '-', '.', ' ', etc.)
    s_norm = re.sub(r"[^\d]", "/", s) 

    formatos = [
        "%d/%m/%Y",  # 24/05/2024
        "%d/%m/%y",  # 24/05/24
        "%Y/%m/%d",  # 2024/05/24
    ]

    for fmt in formatos:
        try:
            fecha = datetime.strptime(s_norm, fmt).date() 
            if 1900 < fecha.year < 2150: 
                return fecha
            else:
                continue
        except ValueError:
            continue

    # self.stdout.write(self.style.WARNING(f"⚠ Fecha inválida encontrada: {fecha_str} → se asigna NULL"))
    return None


class Command(BaseCommand):
    help = "Importa datos desde un CSV y llena la base de datos."

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', type=str, help='Ruta del archivo CSV')

    def handle(self, *args, **options):
        archivo = options['archivo_csv']

        self.stdout.write(self.style.SUCCESS(f"Leyendo archivo: {archivo}"))

        # Intenta leer con coma, luego con punto y coma (comportamiento robusto)
        try:
            df = pd.read_csv(archivo, dtype=str)
        except Exception:
            df = pd.read_csv(archivo, sep=";", dtype=str)

        # =========================================================================
        # 🔥 FIX CRÍTICO 1: Normalizar encabezados de columna y rellenar NaN
        # Esto previene problemas si las columnas tienen espacios extra o valores NaN
        # =========================================================================
        df.columns = df.columns.str.strip() 
        df = df.fillna('') 

        self.stdout.write(self.style.WARNING(f"Total filas a procesar: {len(df)}"))
        
        self.filas_vacias = 0
        self.personas_creadas = 0
        self.personas_actualizadas = 0

        # Función de conversión numérica local para evitar pasar nulos a int/float
        def safe_int(val):
            """Convierte el valor limpio (del CSV) a entero de forma segura."""
            try:
                if val is None:
                    return None
                
                # Reemplaza ',' por '.' para manejar formatos decimales europeos (e.g., '1.000,50')
                val_str = str(val).replace(',', '.') 
                
                # Se limpia la parte decimal si existe (.0) y se convierte a entero
                return int(float(val_str))
            except (ValueError, TypeError):
                # self.stdout.write(self.style.WARNING(f"⚠ Valor no numérico: {val}"))
                return None


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
            
            # Los campos numéricos se limpian a string/None primero
            numero_documento_str = limpiar(row.get("N° Documento de Identidad"))
            edad_str = limpiar(row.get("Edad"))
            telefono_str = limpiar(row.get("Telefono"))
            
            correo = limpiar(row.get("Correo"))
            sexo = limpiar(row.get("Sexo"))
            semestre_str = limpiar(row.get("Semestre"))

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
            # ✅ 3. Conversión de valores numéricos
            # Se aplica safe_int a las variables limpiadas (que son string o None)
            # ---------------------------------------------------------
            numero_documento = safe_int(numero_documento_str)
            edad = safe_int(edad_str)
            telefono = safe_int(telefono_str)
            semestre = safe_int(semestre_str)


            # ==========================================
            # 🧩 CREACIÓN / ACTUALIZACIÓN DE PERSONA
            # ==========================================

            persona_obj = None

            # 1️⃣ Buscar por número de documento
            if numero_documento:
                persona_obj = Persona.objects.filter(numero_documento=numero_documento).first()

            # 2️⃣ Buscar por correo si no hay documento
            if not persona_obj and correo:
                persona_obj = Persona.objects.filter(correo__iexact=correo).first()

            # 3️⃣ Coincidencia difusa si no hay documento ni correo
            if not persona_obj and nombre_persona:
                nombre_base = nombre_persona.split()[0]
                posibles = Persona.objects.filter(
                    Q(nombre__icontains=nombre_base)
                )[:100]

                mejor_match = None
                mejor_score = 0

                for p in posibles:
                    total = 0
                    coincidencias = 0

                    if p.nombre and nombre_persona:
                        total += 1
                        if fuzz.token_sort_ratio(p.nombre, nombre_persona) > 85: 
                            coincidencias += 1

                    if p.tipo_documento and tipo_documento:
                        total += 1
                        if p.tipo_documento.lower() == tipo_documento.lower():
                            coincidencias += 1

                    if p.edad and edad:
                        total += 1
                        if abs(p.edad - edad) <= 1:
                            coincidencias += 1

                    if p.sexo and sexo:
                        total += 1
                        if p.sexo and sexo and p.sexo.lower()[0] == sexo.lower()[0]:
                             coincidencias += 1

                    if p.estamento and estamento:
                        total += 1
                        if p.estamento.lower() == estamento.lower():
                            coincidencias += 1

                    if p.escuela and escuela_obj:
                        total += 1
                        if p.escuela.nombre.lower() == escuela_obj.nombre.lower():
                            coincidencias += 1

                    if total > 0:
                        score = coincidencias / total
                        if score > mejor_score:
                            mejor_score = score
                            mejor_match = p

                if mejor_match and mejor_score >= 0.8:
                    persona_obj = mejor_match


            # ==========================================
            # 📋 PREPARAR DATOS LIMPIOS DE PERSONA
            # ==========================================
            campos_persona = {
                "nombre": nombre_persona,
                "tipo_documento": tipo_documento,
                "numero_documento": numero_documento,
                "edad": edad,
                "sexo": sexo,
                "telefono": telefono,
                "correo": correo,
                "estamento": estamento,
                "escuela": escuela_obj,
            }

            # ==========================================
            # ✅ CREAR O ACTUALIZAR PERSONA
            # ==========================================
            if persona_obj:
                cambios = 0
                for campo, valor in campos_persona.items():
                    # Solo actualiza si el valor del CSV es diferente y NO es None (para no borrar datos existentes)
                    if valor is not None and getattr(persona_obj, campo) != valor:
                        setattr(persona_obj, campo, valor)
                        cambios += 1
                
                if cambios > 0:
                    persona_obj.save()
                    self.personas_actualizadas += 1
                
            else:
                # ⚠️ Crear solo si tiene nombre o algún identificador
                if any([nombre_persona, correo, numero_documento]):
                    persona_obj = Persona.objects.create(**campos_persona)
                    self.personas_creadas += 1
                else:
                    self.filas_vacias += 1
                    # self.stdout.write(self.style.WARNING(f"⚠ Fila {i+1}: ignorada (sin datos de persona)"))
                    continue

            # ==========================================
            # 🎓 CREACIÓN / ACTUALIZACIÓN DE ESTUDIANTE
            # ==========================================
            if estamento and estamento.lower() == "estudiante" and persona_obj:
                
                try:
                    # Usamos get o create para evitar problemas de concurrencia
                    estudiante_obj, created = Estudiante.objects.get_or_create(
                        id_persona=persona_obj.id_persona,
                        defaults={"semestre": semestre}
                    )
                except Exception as e:
                    # En caso de que el estudiante ya exista sin que se haya podido recuperar
                    self.stdout.write(self.style.ERROR(f"Error al obtener/crear Estudiante para {persona_obj.nombre}: {e}"))
                    continue


                if not created and semestre and estudiante_obj.semestre != semestre:
                    estudiante_obj.semestre = semestre
                    estudiante_obj.save()


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
            try:
                anio_int = int(float(anio)) if anio else None
            except (ValueError, TypeError):
                anio_int = None
                
            actividad_obj, _ = Actividad.objects.get_or_create(
                nombre=actividad_nombre,
                anio=anio_int,
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
            part_obj, part_created = None, False
            if persona_obj and actividad_obj:
                part_obj, part_created = Participacion.objects.get_or_create(
                    persona=persona_obj,
                    actividad=actividad_obj,
                    fecha=fecha
                )

            # ---------------------------------------------------------
            # ✅ 10. Lugar (Participación ↔ Sede)
            # ---------------------------------------------------------
            if sede_obj and part_obj:
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

            # Mensaje de progreso cada 100 filas
            if (i + 1) % 100 == 0:
                 self.stdout.write(self.style.SUCCESS(f"--- Fila {i+1} procesada ---"))

        # Resumen final
        self.stdout.write(self.style.SUCCESS("\n=== RESUMEN DE IMPORTACIÓN FINAL ==="))
        self.stdout.write(self.style.SUCCESS(f"👥 Personas creadas: {self.personas_creadas}"))
        self.stdout.write(self.style.SUCCESS(f"🔁 Personas actualizadas: {self.personas_actualizadas}"))
        self.stdout.write(self.style.WARNING(f"⚠ Filas ignoradas (sin datos de persona): {self.filas_vacias}"))
        self.stdout.write(self.style.SUCCESS("✅ Importación completada"))