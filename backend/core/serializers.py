from rest_framework import serializers
from .models import (
    Sede, LineaProyecto, Facultad, Escuela, Persona, Estudiante,
    Indicador, Actividad, AsociacionProyecto, Participacion, Lugar,
    ActividadConsolidada, Consolidacion, Tema, TemaAsociado,
    Prioridad, PrioridadAsociada, LineaEstrategia, EstrategiaAsociada
)

# -------------------------
# Sede
# -------------------------
class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__' # Incluye: id_sede, nombre

# -------------------------
# Línea de proyecto
# -------------------------
class LineaProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaProyecto
        fields = '__all__' # Incluye: id_linea_proyecto, nombre

# -------------------------
# Facultad y Escuela
# -------------------------
class FacultadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facultad
        fields = '__all__' # Incluye: id_facultad, nombre

class EscuelaSerializer(serializers.ModelSerializer):
    # Opcionalmente, para mostrar el nombre de la facultad en lugar de solo su ID
    # facultad_nombre = serializers.CharField(source='facultad.nombre', read_only=True)

    class Meta:
        model = Escuela
        fields = '__all__' # Incluye: id_escuela, nombre, facultad

# -------------------------
# Persona y Estudiante (herencia)
# -------------------------
class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = '__all__'
        # Incluye: id_persona, nombre, tipo_documento, numero_documento, edad,
        # correo, sexo, telefono, estamento, escuela

class EstudianteSerializer(serializers.ModelSerializer):
    # Si quieres que herede todos los campos de Persona y añada 'semestre'
    class Meta:
        model = Estudiante
        fields = '__all__' # Incluye todos los campos de Persona + semestre
        # Alternativamente, para incluir solo los campos específicos y el ID:
        # fields = ('id_persona', 'semestre', 'nombre', 'correo', 'escuela', ...)


# -------------------------
# Indicador
# -------------------------
class IndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicador
        fields = '__all__' # Incluye: id_indicador, nombre


# -------------------------
# Actividad
# -------------------------
class ActividadSerializer(serializers.ModelSerializer):
    # Opcional: mostrar el nombre del indicador en el detalle de la actividad
    # indicador_nombre = serializers.CharField(source='indicador.nombre', read_only=True)

    class Meta:
        model = Actividad
        fields = '__all__' # Incluye: id_actividad, nombre, indicador


# -------------------------
# Asociación Proyecto
# -------------------------
class AsociacionProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsociacionProyecto
        fields = '__all__' # Incluye: id_asociacion_proyecto, linea_proyecto, actividad


# -------------------------
# Lugar (tabla intermedia Participación ↔ Sede)
# -------------------------
class LugarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lugar
        fields = '__all__' # Incluye: id_lugar, participacion, sede


# -------------------------
# Participación (intermedia entre Persona y Actividad)
# -------------------------
class ParticipacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participacion
        fields = '__all__'
        # Incluye: id_participacion, persona, actividad, fecha, anio, sedes


# -------------------------
# Actividad Consolidada
# -------------------------
class ActividadConsolidadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadConsolidada
        fields = '__all__' # Incluye: id_actividad_consolidada, nombre


# -------------------------
# Consolidación
# -------------------------
class ConsolidacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consolidacion
        fields = '__all__' # Incluye: id_consolidacion, actividad, actividad_consolidada


# -------------------------
# Tema y Tema Asociado
# -------------------------
class TemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tema
        fields = '__all__' # Incluye: id_tema, nombre

class TemaAsociadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemaAsociado
        fields = '__all__' # Incluye: id_tema_asociado, actividad, tema


# -------------------------
# Prioridad y Prioridad Asociada
# -------------------------
class PrioridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prioridad
        fields = '__all__' # Incluye: id_prioridad, nombre

class PrioridadAsociadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrioridadAsociada
        fields = '__all__' # Incluye: id_prioridad_asociada, actividad, prioridad


# -------------------------
# Línea de Estrategia y Estrategia Asociada
# -------------------------
class LineaEstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaEstrategia
        fields = '__all__' # Incluye: id_linea_estrategia, nombre

class EstrategiaAsociadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstrategiaAsociada
        fields = '__all__' # Incluye: id_estrategia_asociada, actividad, linea_estrategia