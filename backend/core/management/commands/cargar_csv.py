import pandas as pd
from django.core.management.base import BaseCommand
from datetime import datetime
from django.db.models import Q
import re
from core.models import (
    Persona, Estudiante, Escuela, Facultad, Actividad, Indicador,
    Participacion, Lugar, Sede, Tema, TemaAsociado, Prioridad,
    PrioridadAsociada, LineaEstrategia, EstrategiaAsociada,
    LineaProyecto, AsociacionProyecto, ActividadConsolidada,
    Consolidacion
)
from fuzzywuzzy import fuzz

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

# -------------------------
# Nuevo helper para ints
# -------------------------
def parse_int(valor):
    """Convierte valores tipo '1', '1.0', '3203661144.0' a int. Devuelve None si no es entero."""
    if valor is None:
        return None
    s = str(valor).strip()
    if s == "":
        return None
    s = s.replace(",", "").replace(" ", "")
    try:
        f = float(s)
    except Exception:
        return None
    i = int(f)
    if abs(f - i) < 1e-9:
        return i
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

            # Campos "Original" (mantener copia de los valores originales)
            actividad_nombre_original = limpiar(row.get("Actividad Original"))
            actividad_consolidada_nombre_original = limpiar(row.get("Actividad consolidada Original"))
            linea_proyecto_nombre_original = limpiar(row.get("Linea del Proyecto Original"))
            indicador_nombre_original = limpiar(row.get("Indicador Original"))
            sede_nombre_original = limpiar(row.get("Sede Original"))
            estamento_original = limpiar(row.get("Estamento Original"))
            facultad_nombre_original = limpiar(row.get("Facultad/Instituto/Área Original"))
            escuela_nombre_original = limpiar(row.get("Escuela/Programa Académico Original"))
            nombre_persona_original = limpiar(row.get("Nombre Original"))
            tipo_documento_original = limpiar(row.get("Tipo de Documento Original"))
            tema_nombre_original = limpiar(row.get("Tema Original"))
            prioridad_nombre_original = limpiar(row.get("Prioridad Original"))
            estrategia_nombre_original = limpiar(row.get("Linea de estrategia Original"))

            # ---------------------------------------------------------
            # ✅ 2. Facultad y Escuela
            # ---------------------------------------------------------
            facultad_obj = None
            if facultad_nombre:
                facultad_obj, _ = Facultad.objects.get_or_create(
                    nombre=facultad_nombre,
                    defaults={"nombre_original": facultad_nombre_original}
                )

            escuela_obj = None
            if escuela_nombre:
                escuela_obj, _ = Escuela.objects.get_or_create(
                    nombre=escuela_nombre,
                    facultad=facultad_obj,
                    defaults={"nombre_original": escuela_nombre_original}
                )

            # ---------------------------------------------------------
            # ✅ 3. Persona o Estudiante (LÓGICA UNIFICADA CON FUZZY)
            # ---------------------------------------------------------
            # Normalizar valores
            correo_normalizado = (correo or "").strip().lower() if correo else None
            numero_documento_int = parse_int(numero_documento)
            telefono_int = parse_int(telefono)
            semestre_int = parse_int(semestre)

            # ---- PASO 1: Búsqueda por documento O correo (si existen)
            persona_obj = None

            if numero_documento_int:
                persona_obj = Persona.objects.filter(numero_documento=numero_documento_int).first()

            if not persona_obj and correo_normalizado:
                persona_obj = Persona.objects.filter(correo__iexact=correo_normalizado).first()

            # ---- PASO 2: Si no encontró Y NO tiene documento ni correo, buscar por FUZZY MATCHING
            # Solo fuzzy si AMBOS están vacíos
            identificadores_fila = 0
            if nombre_persona: identificadores_fila += 1
            if tipo_documento: identificadores_fila += 1
            if sexo: identificadores_fila += 1
            if parse_int(edad) is not None: identificadores_fila += 1
            if telefono_int: identificadores_fila += 1
            if estamento: identificadores_fila += 1
            if escuela_obj: identificadores_fila += 1

            if not persona_obj and not numero_documento_int and not correo_normalizado and identificadores_fila >= 2:
                # Sólo intentar fuzzy si la fila tiene al menos 2 campos identificadores
                identificadores_fila = 0
                if nombre_persona: identificadores_fila += 1
                if tipo_documento: identificadores_fila += 1
                if sexo: identificadores_fila += 1
                if edad and str(edad).isdigit(): identificadores_fila += 1
                if telefono_int: identificadores_fila += 1
                if estamento: identificadores_fila += 1
                if escuela_obj: identificadores_fila += 1

                if identificadores_fila >= 2:
                    # Buscar candidatos (limitar búsqueda por nombre si existe)
                    candidatos = Persona.objects.all()
                    if nombre_persona:
                        primer_token = nombre_persona.split()[0]
                        candidatos = candidatos.filter(nombre__icontains=primer_token)
                    else:
                        # Sin nombre, limitar a últimos registros para no iterar todo
                        candidatos = candidatos.order_by('-id_persona')[:1000]

                    mejor_match = None
                    mejor_score = 0.0

                    for p in candidatos:
                        campos_comparados = 0
                        campos_coinciden = 0

                        # Comparar NOMBRE (si ambos tienen valor)
                        if p.nombre and nombre_persona:
                            campos_comparados += 1
                            if fuzz.token_sort_ratio(p.nombre.lower(), nombre_persona.lower()) >= 85:
                                campos_coinciden += 1

                        # Comparar TIPO_DOCUMENTO
                        if p.tipo_documento and tipo_documento:
                            campos_comparados += 1
                            if p.tipo_documento.lower() == tipo_documento.lower():
                                campos_coinciden += 1

                        # Comparar SEXO
                        if p.sexo and sexo:
                            campos_comparados += 1
                            if p.sexo.lower()[:1] == sexo.lower()[:1]:
                                campos_coinciden += 1

                        # Comparar EDAD (permitir ±1 año)
                        if p.edad and edad and str(edad).isdigit():
                            campos_comparados += 1
                            if abs(p.edad - int(edad)) <= 1:
                                campos_coinciden += 1

                        # Comparar ESTAMENTO
                        if p.estamento and estamento:
                            campos_comparados += 1
                            if p.estamento.lower() == estamento.lower():
                                campos_coinciden += 1

                        # Comparar ESCUELA
                        if p.escuela and escuela_obj:
                            campos_comparados += 1
                            if p.escuela.id_escuela == escuela_obj.id_escuela:
                                campos_coinciden += 1

                        # Calcular score solo si comparamos al menos 2 campos
                        if campos_comparados >= 2:
                            score = campos_coinciden / campos_comparados
                            if score > mejor_score:
                                mejor_score = score
                                mejor_match = p

                    # Aceptar match si ≥80% coincide
                    if mejor_match and mejor_score >= 0.80:
                        persona_obj = mejor_match

            # ---- PASO 3: Actualizar o crear Persona
            if persona_obj:
                # 🔄 ACTUALIZAR EXISTENTE (solo sobrescribe si CSV aporta valor)
                if nombre_persona and (not persona_obj.nombre or persona_obj.nombre.strip() == ""):
                    persona_obj.nombre = nombre_persona
                # mantener nombre_original si CSV aporta valor original
                if nombre_persona_original and (not persona_obj.nombre_original or persona_obj.nombre_original.strip() == ""):
                    persona_obj.nombre_original = nombre_persona_original
                if tipo_documento and (not persona_obj.tipo_documento or persona_obj.tipo_documento.strip() == ""):
                    persona_obj.tipo_documento = tipo_documento
                if tipo_documento_original and (not persona_obj.tipo_documento_original or persona_obj.tipo_documento_original.strip() == ""):
                    persona_obj.tipo_documento_original = tipo_documento_original
                if sexo and (not persona_obj.sexo or persona_obj.sexo.strip() == ""):
                    persona_obj.sexo = sexo
                if edad and parse_int(edad) is not None and not persona_obj.edad:
                    persona_obj.edad = parse_int(edad)
                if telefono_int and not persona_obj.telefono:
                    persona_obj.telefono = telefono_int
                # Antes de asignar correo/verificar único
                if correo_normalizado and not persona_obj.correo:
                    conflicto = Persona.objects.filter(correo__iexact=correo_normalizado).exclude(pk=persona_obj.pk).exists()
                    if not conflicto:
                        persona_obj.correo = correo_normalizado
                if estamento and (not persona_obj.estamento or persona_obj.estamento.strip() == ""):
                    persona_obj.estamento = estamento
                # guardar estamento original si viene
                if estamento_original and (not getattr(persona_obj, "estamento_original", None)):
                    try:
                        persona_obj.estamento_original = estamento_original
                    except Exception:
                        pass
                if escuela_obj and not persona_obj.escuela:
                    persona_obj.escuela = escuela_obj
                # Igual para número de documento: sólo asignar si no existe en otra persona
                if numero_documento_int and not persona_obj.numero_documento:
                    conflicto_doc = Persona.objects.filter(numero_documento=numero_documento_int).exclude(pk=persona_obj.pk).exists()
                    if not conflicto_doc:
                        persona_obj.numero_documento = numero_documento_int

                persona_obj.save()
            else:
                # 🆕 CREAR NUEVO (solo con valores que existen)
                crear_datos = {}
                if nombre_persona:
                    crear_datos["nombre"] = nombre_persona
                else:
                    crear_datos["nombre"] = "SIN NOMBRE"
                # siempre intentar conservar el original si existe
                if nombre_persona_original:
                    crear_datos["nombre_original"] = nombre_persona_original

                if tipo_documento:
                    crear_datos["tipo_documento"] = tipo_documento
                if tipo_documento_original:
                    crear_datos["tipo_documento_original"] = tipo_documento_original
                if sexo:
                    crear_datos["sexo"] = sexo
                if edad and parse_int(edad) is not None:
                    crear_datos["edad"] = parse_int(edad)
                if telefono_int:
                    crear_datos["telefono"] = telefono_int
                if correo_normalizado:
                    crear_datos["correo"] = correo_normalizado
                if estamento:
                    crear_datos["estamento"] = estamento
                if escuela_obj:
                    crear_datos["escuela"] = escuela_obj
                if numero_documento_int:
                    crear_datos["numero_documento"] = numero_documento_int

                # Determinar si es Estudiante o Persona normal al crear
                if semestre_int is not None:
                    crear_datos["semestre"] = semestre_int
                    persona_obj = Estudiante.objects.create(**crear_datos)
                else:
                    persona_obj = Persona.objects.create(**crear_datos)

            # -----------------------------
            # Asegurar existencia de Estudiante si corresponde
            # -----------------------------
            # Si la fila trae semestre y la persona ya existía como Persona, crear/actualizar Estudiante
            if semestre_int is not None:
                try:
                    est_obj, created = Estudiante.objects.get_or_create(
                        id_persona=persona_obj.id_persona,
                        defaults={"semestre": semestre_int}
                    )
                    if not created and est_obj.semestre != semestre_int:
                        est_obj.semestre = semestre_int
                        est_obj.save()
                except Exception:
                    # si el modelo usa otra relación, intentar por pk (ajusta según tu modelo)
                    try:
                        est_obj, created = Estudiante.objects.get_or_create(
                            persona_ptr_id=persona_obj.pk,
                            defaults={"semestre": semestre_int}
                        )
                        if not created and est_obj.semestre != semestre_int:
                            est_obj.semestre = semestre_int
                            est_obj.save()
                    except Exception:
                        # log mínimo para depuración
                        self.stdout.write(self.style.WARNING(f"No se pudo crear/actualizar Estudiante para persona {persona_obj.pk} (fila {i+1})"))

            # ---------------------------------------------------------
            # ✅ 4. Indicador
            # ---------------------------------------------------------
            indicador_obj = None
            if indicador_nombre:
                indicador_obj, _ = Indicador.objects.get_or_create(
                    nombre=indicador_nombre,
                    defaults={"nombre_original": indicador_nombre_original}
                )

            # ---------------------------------------------------------
            # ✅ 5. Actividad
            # ---------------------------------------------------------
            actividad_defaults = {"indicador": indicador_obj}
            if actividad_nombre_original:
                actividad_defaults["nombre_original"] = actividad_nombre_original
            actividad_obj, _ = Actividad.objects.get_or_create(
                nombre=actividad_nombre,
                defaults=actividad_defaults
            )

            # ---------------------------------------------------------
            # ✅ 6. Actividad consolidada and su relación
            # ---------------------------------------------------------
            if actividad_consolidada_nombre:
                act_con_defaults = {}
                if actividad_consolidada_nombre_original:
                    act_con_defaults["nombre_original"] = actividad_consolidada_nombre_original
                act_con_obj, _ = ActividadConsolidada.objects.get_or_create(
                    nombre=actividad_consolidada_nombre,
                    defaults=act_con_defaults
                )
                Consolidacion.objects.get_or_create(
                    actividad=actividad_obj,
                    actividad_consolidada=act_con_obj
                )

            # ---------------------------------------------------------
            # ✅ 7. Línea de proyecto
            # ---------------------------------------------------------
            if linea_proyecto_nombre:
                linea_proj_defaults = {}
                if linea_proyecto_nombre_original:
                    linea_proj_defaults["nombre_original"] = linea_proyecto_nombre_original
                linea_proj_obj, _ = LineaProyecto.objects.get_or_create(
                    nombre=linea_proyecto_nombre,
                    defaults=linea_proj_defaults
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
                anio=int(float(anio)) if anio else None,
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
                prioridad_defaults = {}
                if prioridad_nombre_original:
                    prioridad_defaults["nombre_original"] = prioridad_nombre_original
                prioridad_obj, _ = Prioridad.objects.get_or_create(
                    nombre=prioridad_nombre,
                    defaults=prioridad_defaults
                )
                PrioridadAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    prioridad=prioridad_obj
                )

            # ---------------------------------------------------------
            # ✅ 13. Línea de estrategia
            # ---------------------------------------------------------
            if estrategia_nombre:
                est_defaults = {}
                if estrategia_nombre_original:
                    est_defaults["nombre_original"] = estrategia_nombre_original
                est_obj, _ = LineaEstrategia.objects.get_or_create(
                    nombre=estrategia_nombre,
                    defaults=est_defaults
                )
                EstrategiaAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    linea_estrategia=est_obj
                )

            # ---------------------------------------------------------
            self.stdout.write(self.style.SUCCESS(f"Fila {i+1} procesada"))

        self.stdout.write(self.style.SUCCESS("✅ Importación completada"))