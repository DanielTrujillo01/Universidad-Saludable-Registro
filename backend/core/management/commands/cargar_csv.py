import pandas as pd
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.db.models import Q
from rapidfuzz import fuzz
from core.models import (
    Persona, Estudiante, Escuela, Facultad, Actividad, Indicador,
    Participacion, Lugar, Sede, Tema, TemaAsociado, Prioridad,
    PrioridadAsociada, LineaEstrategia, EstrategiaAsociada,
    LineaProyecto, AsociacionProyecto, ActividadConsolidada,
    Consolidacion
)


# -------------------------
# Utilidades de limpieza
# -------------------------
def limpiar(valor):
    """Convierte '', 'NULL', NaN en None y trim."""
    if pd.isna(valor) or str(valor).strip().upper() in ['', 'NULL', 'NONE']:
        return None
    return str(valor).strip()


def normalizar_nombre(nombre):
    if not nombre:
        return None
    s = str(nombre).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s


def limpiar_telefono(tel):
    if not tel:
        return None
    s = str(tel)
    s = re.sub(r'\D', '', s)
    if len(s) < 7 or len(s) > 10:
        return None
    return int(s)


def convertir_fecha(fecha_str):
    """
    Normaliza diferentes separadores y formatos de fecha comunes.
    Devuelve objeto date o None si no se puede parsear.
    Asume formato día/mes/año (day-first) para ambigüedades.
    """
    if not fecha_str or str(fecha_str).strip() == "":
        return None

    s = str(fecha_str).strip()
    s_norm = re.sub(r"[^\d]", "/", s)

    formatos = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y/%m/%d",
        "%d/%m",
    ]

    for fmt in formatos:
        try:
            fecha = datetime.strptime(s_norm, fmt).date()
            if fecha.year < 1900 or fecha.year > 2100:
                continue
            return fecha
        except ValueError:
            continue

    # Aviso (stdout) en vez de print
    return None


# -------------------------
# Fuzzy matching
# -------------------------
def calcular_score_fuzzy(p_obj, row):
    """
    Pondera nombre, sexo y estamento (puedes ajustar pesos).
    Retorna un score 0..100.
    """
    nombre_row = normalizar_nombre(row.get("Nombre"))
    nombre_p = normalizar_nombre(p_obj.nombre) if p_obj.nombre else None
    score_nombre = fuzz.ratio(nombre_p, nombre_row) if nombre_p and nombre_row else 0

    sexo_row = (row.get("Sexo") or "").strip().lower()
    sexo_p = (p_obj.sexo or "").strip().lower()
    score_sexo = 100 if sexo_row and sexo_p and sexo_row == sexo_p else 0

    est_row = (row.get("Estamento") or "").strip().lower()
    est_p = (p_obj.estamento or "").strip().lower()
    score_estamento = 100 if est_row and est_p and est_row == est_p else 0

    # Ponderaciones (ajustables)
    score = score_nombre * 0.65 + score_sexo * 0.15 + score_estamento * 0.20
    return score


def buscar_persona_existente_unificada(row):
    """
    Busca persona o estudiante existente siguiendo prioridad:
    1) documento (estudiante -> persona)
    2) correo (estudiante -> persona)
    3) fuzzy match (solo si no hay doc ni correo y hay nombre)
    Retorna instancia (Persona o Estudiante) o None.
    """
    numero_documento = row.get("N° Documento de Identidad") or row.get("Numero_documento") or None
    correo = (row.get("Correo") or None)
    nombre = row.get("Nombre") or None

    # normalizar correo
    correo_norm = correo.strip().lower() if correo else None

    # 1) documento exacto
    if numero_documento:
        # intentar como entero si viene con .0 u otros
        num_str = str(numero_documento).strip()
        num_digits = re.sub(r'\D', '', num_str)
        if num_digits:
            try:
                num_int = int(num_digits)
            except ValueError:
                num_int = None
        else:
            num_int = None

        if num_int:
            est = Estudiante.objects.filter(numero_documento=num_int).first()
            if est:
                return est
            pers = Persona.objects.filter(numero_documento=num_int).first()
            if pers:
                return pers

    # 2) correo exacto
    if correo_norm:
        est = Estudiante.objects.filter(correo__iexact=correo_norm).first()
        if est:
            return est
        pers = Persona.objects.filter(correo__iexact=correo_norm).first()
        if pers:
            return pers

    # 3) fuzzy match (solo si hay nombre)
    if nombre:
        nombre_norm = normalizar_nombre(nombre)
        # Buscar posibles por primer token del nombre para acotar
        primer_token = nombre_norm.split()[0] if nombre_norm.split() else nombre_norm
        posibles = Persona.objects.filter(nombre__icontains=primer_token)[:500]  # limitar
        mejor = None
        mejor_score = 0
        for p in posibles:
            score = calcular_score_fuzzy(p, row)
            if score > mejor_score:
                mejor_score = score
                mejor = p
        if mejor_score >= 82:
            return mejor

    return None


# -------------------------
# Validaciones CSV
# -------------------------
def detectar_correos_duplicados_csv(df):
    # Normaliza correos y cuenta
    if 'Correo' not in df.columns:
        return {}
    s = df['Correo'].fillna("").astype(str).str.strip().str.lower()
    counts = s[s != ""].value_counts()
    dup = counts[counts > 1].to_dict()
    return dup


# -------------------------
# COMMAND
# -------------------------
class Command(BaseCommand):
    help = "Importa datos desde CSV y llena DB (mejorado: persona fuzzy, validaciones y entidades relacionadas)."

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', type=str, help='Ruta del archivo CSV')

    @transaction.atomic
    def handle(self, *args, **options):
        archivo = options['archivo_csv']
        self.stdout.write(self.style.WARNING(f"Leyendo archivo: {archivo}"))

        try:
            df = pd.read_csv(archivo, dtype=str)
        except Exception:
            df = pd.read_csv(archivo, sep=";", dtype=str)

        total = len(df)
        self.stdout.write(self.style.SUCCESS(f"Total filas: {total}"))

        # Pre-check: correos duplicados en CSV
        dup_correo = detectar_correos_duplicados_csv(df)
        if dup_correo:
            self.stdout.write(self.style.WARNING("⚠ Correos repetidos detectados en CSV (correo: ocurrencias):"))
            for correo, cnt in list(dup_correo.items())[:50]:
                self.stdout.write(self.style.WARNING(f"  - {correo}: {cnt} filas"))
            # no abortamos: solo avisamos; lógica posterior tratará colisiones según reglas

        # Iterar filas
        for i, raw_row in df.iterrows():
            # Mapear claves según tu CSV original
            row = {k: limpiar(v) for k, v in raw_row.items()}

            # Campos básicos
            anio = row.get("Año") or row.get("Anio")
            actividad_nombre = row.get("Actividad")
            actividad_consolidada_nombre = row.get("Actividad consolidada")
            linea_proyecto_nombre = row.get("Linea del Proyecto")
            indicador_nombre = row.get("Indicador")

            fecha = convertir_fecha(limpiar(row.get("Fecha")))
            sede_nombre = row.get("Sede")
            estamento = row.get("Estamento")

            facultad_nombre = row.get("Facultad/Instituto/Área") or row.get("Facultad")
            escuela_nombre = row.get("Escuela/Programa Académico") or row.get("Escuela/Programa") or row.get("Escuela/Programa Académico")

            nombre_persona = row.get("Nombre")
            tipo_documento = row.get("Tipo de Documento") or row.get("Tipo_documento")
            numero_documento_raw = row.get("N° Documento de Identidad") or row.get("Numero_documento")
            edad = row.get("Edad")
            telefono_raw = row.get("Telefono")
            correo_raw = row.get("Correo")
            sexo = row.get("Sexo")
            semestre_raw = row.get("Semestre")

            tema_nombre = row.get("Tema")
            prioridad_nombre = row.get("Prioridad")
            estrategia_nombre = row.get("Linea de estrategia") or row.get("Linea de Estrategia")

            # Normalizaciones/parseos
            correo_normalizado = correo_raw.strip().lower() if correo_raw else None

            # numero_documento -> int si es posible
            numero_documento = None
            if numero_documento_raw:
                s = re.sub(r'[^\d]', '', str(numero_documento_raw))
                if s.isdigit():
                    try:
                        numero_documento = int(s)
                    except ValueError:
                        numero_documento = None

            telefono = limpiar_telefono(telefono_raw)

            # Semestre/edad -> int si es digito
            semestre = None
            if semestre_raw and str(semestre_raw).isdigit():
                try:
                    semestre = int(float(semestre_raw))
                except Exception:
                    semestre = None

            edad_int = None
            if edad and str(edad).isdigit():
                try:
                    edad_int = int(float(edad))
                except Exception:
                    edad_int = None

            # ---------------------------------------------------------
            # Facultad y Escuela
            # ---------------------------------------------------------
            facultad_obj = None
            if facultad_nombre:
                facultad_obj, _ = Facultad.objects.get_or_create(nombre=facultad_nombre)

            escuela_obj = None
            if escuela_nombre:
                escuela_obj, _ = Escuela.objects.get_or_create(
                    nombre=escuela_nombre,
                    facultad=facultad_obj
                )

            # ---------------------------------------------------------
            # Persona / Estudiante (Lógica robusta)
            # ---------------------------------------------------------
            persona_obj = None

            # Construir una fila simplificada para la función de búsqueda
            search_row = {
                "Nombre": nombre_persona,
                "Correo": correo_normalizado,
                "N° Documento de Identidad": numero_documento_raw,
                "Sexo": sexo,
                "Estamento": estamento,
            }

            persona_obj = buscar_persona_existente_unificada(search_row)

            # Si existen duplicados en CSV por correo y este correo aparece con diferentes documentos,
            # preferimos registrar advertencia y saltar el update para evitar mezclar identidades.
            if correo_normalizado and correo_normalizado in dup_correo:
                # Verificar si los documentos asociados a ese correo en CSV difieren
                rows_mismo_correo = df[df['Correo'].fillna("").astype(str).str.strip().str.lower() == correo_normalizado]
                documentos = set()
                for _, r in rows_mismo_correo.iterrows():
                    nd = limpiar(r.get("N° Documento de Identidad") or r.get("Numero_documento"))
                    if nd:
                        nd_digits = re.sub(r'[^\d]', '', str(nd))
                        if nd_digits:
                            documentos.add(nd_digits)
                if len(documentos) > 1:
                    # advertencia y no intentar unificar por correo
                    self.stdout.write(self.style.WARNING(
                        f"Fila {i+1}: correo {correo_normalizado} aparece con múltiples documentos en CSV {documentos}. Evitando unificación por correo."
                    ))
                    # Forzar que no se utilice persona_obj encontrada por correo (si la hubo)
                    if persona_obj and getattr(persona_obj, 'correo', None) and str(getattr(persona_obj, 'correo')).strip().lower() == correo_normalizado:
                        persona_obj = None

            # Si se encontró persona/estudiante -> actualizar sin sobreescribir datos buenos
            if persona_obj:
                updated = False
                # Si es instancia de Estudiante, usamos sus campos; si es Persona también funciona
                if not persona_obj.nombre and nombre_persona:
                    persona_obj.nombre = normalizar_nombre(nombre_persona)
                    updated = True
                if not persona_obj.tipo_documento and tipo_documento:
                    persona_obj.tipo_documento = tipo_documento
                    updated = True
                if not persona_obj.numero_documento and numero_documento:
                    persona_obj.numero_documento = numero_documento
                    updated = True
                if not getattr(persona_obj, "correo", None) and correo_normalizado:
                    persona_obj.correo = correo_normalizado
                    updated = True
                if not getattr(persona_obj, "telefono", None) and telefono:
                    persona_obj.telefono = telefono
                    updated = True
                if not getattr(persona_obj, "sexo", None) and sexo:
                    persona_obj.sexo = sexo
                    updated = True
                if not getattr(persona_obj, "estamento", None) and estamento:
                    persona_obj.estamento = estamento
                    updated = True
                # Si es Estudiante y tenemos semestre
                if hasattr(persona_obj, "semestre") and (persona_obj.semestre in (None, "") ) and semestre:
                    try:
                        persona_obj.semestre = int(semestre)
                        updated = True
                    except Exception:
                        pass

                try:
                    if updated:
                        persona_obj.save()
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"Fila {i+1}: IntegrityError al actualizar persona: {e}"))
                    # continuar sin abortar

            else:
                # Crear nuevo (Estudiante si trae semestre, sino Persona)
                nombre_guardar = normalizar_nombre(nombre_persona) or "SIN NOMBRE"
                if semestre:
                    # Crear Estudiante
                    try:
                        Estudiante.objects.create(
                            nombre=nombre_guardar,
                            tipo_documento=tipo_documento,
                            numero_documento=numero_documento,
                            edad=edad_int,
                            telefono=telefono,
                            correo=correo_normalizado,
                            sexo=sexo,
                            estamento=estamento,
                            escuela=escuela_obj,
                            semestre=semestre
                        )
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f"Fila {i+1}: Error creando Estudiante (IntegrityError): {e}"))
                else:
                    try:
                        Persona.objects.create(
                            nombre=nombre_guardar,
                            tipo_documento=tipo_documento,
                            numero_documento=numero_documento,
                            edad=edad_int,
                            telefono=telefono,
                            correo=correo_normalizado,
                            sexo=sexo,
                            estamento=estamento,
                            escuela=escuela_obj
                        )
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f"Fila {i+1}: Error creando Persona (IntegrityError): {e}"))

            # ---------------------------------------------------------
            # Indicador
            # ---------------------------------------------------------
            indicador_obj = None
            if indicador_nombre:
                indicador_obj, _ = Indicador.objects.get_or_create(nombre=indicador_nombre)

            # ---------------------------------------------------------
            # Actividad
            # ---------------------------------------------------------
            actividad_obj, _ = Actividad.objects.get_or_create(
                nombre=actividad_nombre,
                anio=int(float(anio)) if anio else None,
                defaults={"indicador": indicador_obj}
            )

            # ---------------------------------------------------------
            # Actividad consolidada y su relación
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
            # Línea de proyecto
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
            # Sede
            # ---------------------------------------------------------
            sede_obj = None
            if sede_nombre:
                sede_obj, _ = Sede.objects.get_or_create(nombre=sede_nombre)

            # ---------------------------------------------------------
            # Participación -> vinculada a la persona/estudiante creada o encontrada
            # ---------------------------------------------------------
            # Rebuscar la persona objetiva por correo o documento para la relación (por si se creó arriba)
            participante = None
            if numero_documento:
                participante = Estudiante.objects.filter(numero_documento=numero_documento).first() or Persona.objects.filter(numero_documento=numero_documento).first()
            if not participante and correo_normalizado:
                participante = Estudiante.objects.filter(correo__iexact=correo_normalizado).first() or Persona.objects.filter(correo__iexact=correo_normalizado).first()

            # Si sigue sin participante, intentar fuzzy search (no ideal, pero para asegurar enlace)
            if not participante and nombre_persona:
                participante = Persona.objects.filter(nombre__icontains=normalizar_nombre(nombre_persona).split()[0]).first()

            if participante:
                part_obj, _ = Participacion.objects.get_or_create(
                    persona=participante,
                    actividad=actividad_obj,
                    fecha=fecha
                )

                # Lugar (Participación ↔ Sede)
                if sede_obj:
                    Lugar.objects.get_or_create(
                        participacion=part_obj,
                        sede=sede_obj
                    )

            else:
                # Si no se pudo ligar la participación a persona alguna, crear una participación "huérfana" con persona NULL no es posible
                # Opcional: podríamos crear una Persona "SIN NOMBRE" y ligarla, pero ya lo hicimos arriba en creación.
                self.stdout.write(self.style.WARNING(f"Fila {i+1}: No se encontró/creó participante para ligar la Participación."))

            # ---------------------------------------------------------
            # Tema
            # ---------------------------------------------------------
            if tema_nombre:
                tema_obj, _ = Tema.objects.get_or_create(nombre=tema_nombre)
                TemaAsociado.objects.get_or_create(
                    actividad=actividad_obj,
                    tema=tema_obj
                )

            # ---------------------------------------------------------
            # Prioridad
            # ---------------------------------------------------------
            if prioridad_nombre:
                prioridad_obj, _ = Prioridad.objects.get_or_create(nombre=prioridad_nombre)
                PrioridadAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    prioridad=prioridad_obj
                )

            # ---------------------------------------------------------
            # Línea de estrategia
            # ---------------------------------------------------------
            if estrategia_nombre:
                est_obj, _ = LineaEstrategia.objects.get_or_create(nombre=estrategia_nombre)
                EstrategiaAsociada.objects.get_or_create(
                    actividad=actividad_obj,
                    linea_estrategia=est_obj
                )

            self.stdout.write(self.style.SUCCESS(f"Fila {i+1} procesada"))

        self.stdout.write(self.style.SUCCESS("✅ Importación completada"))
