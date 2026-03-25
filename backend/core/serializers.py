from rest_framework import serializers
from .models import *

# -------------------------
# Básicos
# -------------------------

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'


class LineaProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaProyecto
        fields = '__all__'


class FacultadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facultad
        fields = '__all__'


class EscuelaSerializer(serializers.ModelSerializer):
    facultad = FacultadSerializer(read_only=True)

    facultad_id = serializers.PrimaryKeyRelatedField(
        queryset=Facultad.objects.all(),
        source='facultad',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Escuela
        fields = '__all__'


# -------------------------
# Persona / Estudiante
# -------------------------

class PersonaSerializer(serializers.ModelSerializer):
    escuela = EscuelaSerializer(read_only=True)

    escuela_id = serializers.PrimaryKeyRelatedField(
        queryset=Escuela.objects.all(),
        source='escuela',
        write_only=True,
        required=False, 
        allow_null=True
    )

    class Meta:
        model = Persona
        fields = '__all__'


class EstudianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estudiante
        fields = '__all__'


# -------------------------
# Núcleo del modelo
# -------------------------

class IndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicador
        fields = '__all__'


class EstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estrategia
        fields = '__all__'


class AccionSerializer(serializers.ModelSerializer):
    indicador = IndicadorSerializer(read_only=True)
    estrategia = EstrategiaSerializer(read_only=True)

    indicador_id = serializers.PrimaryKeyRelatedField(
        queryset=Indicador.objects.all(),
        source='indicador',
        write_only=True,
        required=False,
        allow_null=True
    )

    estrategia_id = serializers.PrimaryKeyRelatedField(
        queryset=Estrategia.objects.all(),
        source='estrategia',
        write_only=True
    )

    class Meta:
        model = Accion
        fields = '__all__'


class ActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividad
        fields = '__all__'


class TemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tema
        fields = '__all__'


# -------------------------
# Tablas intermedias
# -------------------------

class ActividadAsociadaSerializer(serializers.ModelSerializer):
    accion = AccionSerializer(read_only=True)
    actividad = ActividadSerializer(read_only=True)

    class Meta:
        model = ActividadAsociada
        fields = '__all__'


class TemaAsociadoSerializer(serializers.ModelSerializer):
    actividad = ActividadSerializer(read_only=True)
    tema = TemaSerializer(read_only=True)

    class Meta:
        model = TemaAsociado
        fields = '__all__'


class AsociacionProyectoSerializer(serializers.ModelSerializer):
    linea_proyecto = LineaProyectoSerializer(read_only=True)
    accion = AccionSerializer(read_only=True)

    class Meta:
        model = AsociacionProyecto
        fields = '__all__'


# -------------------------
# Participación (clave)
# -------------------------

class ParticipacionSerializer(serializers.ModelSerializer):
    # Lectura (nested)
    persona = PersonaSerializer(read_only=True)
    accion = AccionSerializer(read_only=True)
    actividad = ActividadSerializer(read_only=True)
    tema = TemaSerializer(read_only=True)
    sede = SedeSerializer(read_only=True)

    # Escritura (IDs)
    persona_id = serializers.PrimaryKeyRelatedField(
        queryset=Persona.objects.all(), source='persona', write_only=True
    )
    accion_id = serializers.PrimaryKeyRelatedField(
        queryset=Accion.objects.all(), source='accion', write_only=True
    )
    actividad_id = serializers.PrimaryKeyRelatedField(
        queryset=Actividad.objects.all(), source='actividad', write_only=True
    )
    tema_id = serializers.PrimaryKeyRelatedField(
        queryset=Tema.objects.all(), source='tema', write_only=True, required=False, allow_null=True
    )
    sede_id = serializers.PrimaryKeyRelatedField(
        queryset=Sede.objects.all(), source='sede', write_only=True
    )

    class Meta:
        model = Participacion
        fields = '__all__'


# -------------------------
# Consolidación
# -------------------------

class ActividadConsolidadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadConsolidada
        fields = '__all__'


class ConsolidacionSerializer(serializers.ModelSerializer):
    accion = AccionSerializer(read_only=True)
    actividad_consolidada = ActividadConsolidadaSerializer(read_only=True)

    class Meta:
        model = Consolidacion
        fields = '__all__'


# -------------------------
# Prioridad
# -------------------------

class PrioridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prioridad
        fields = '__all__'


class PrioridadAsociadaSerializer(serializers.ModelSerializer):
    accion = AccionSerializer(read_only=True)
    prioridad = PrioridadSerializer(read_only=True)

    class Meta:
        model = PrioridadAsociada
        fields = '__all__'


# -------------------------
# Estrategia extendida
# -------------------------

class LineaEstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaEstrategia
        fields = '__all__'


class EstrategiaAsociadaSerializer(serializers.ModelSerializer):
    accion = AccionSerializer(read_only=True)
    linea_estrategia = LineaEstrategiaSerializer(read_only=True)

    class Meta:
        model = EstrategiaAsociada
        fields = '__all__'