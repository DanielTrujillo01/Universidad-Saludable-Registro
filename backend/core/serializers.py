from rest_framework import serializers
from .models import (
    Sede, LineaProyecto, Facultad, Escuela, Persona, Estudiante,
    Indicador, Actividad, AsociacionProyecto, Participacion, Lugar,
    ActividadConsolidada, Consolidacion, Tema, TemaAsociado,
    Prioridad, PrioridadAsociada, LineaEstrategia, EstrategiaAsociada
)

# ---------------------------------------
# Sede
# ---------------------------------------
class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'


# ---------------------------------------
# Línea de Proyecto
# ---------------------------------------
class LineaProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaProyecto
        fields = '__all__'


# ---------------------------------------
# Facultad y Escuela
# ---------------------------------------
class FacultadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facultad
        fields = '__all__'


class EscuelaSerializer(serializers.ModelSerializer):
    facultad = FacultadSerializer(read_only=True)
    facultad_id = serializers.PrimaryKeyRelatedField(
        queryset=Facultad.objects.all(), source='facultad', write_only=True
    )

    class Meta:
        model = Escuela
        fields = ['id_escuela', 'nombre', 'facultad', 'facultad_id']


# ---------------------------------------
# Persona y Estudiante
# ---------------------------------------
class PersonaSerializer(serializers.ModelSerializer):
    escuela = EscuelaSerializer(read_only=True)
    escuela_id = serializers.PrimaryKeyRelatedField(
        queryset=Escuela.objects.all(), source='escuela', write_only=True,
        required=False, allow_null=True
    )

    class Meta:
        model = Persona
        fields = [
            'id_persona', 'nombre', 'tipo_documento', 'numero_documento',
            'edad', 'correo', 'sexo', 'telefono', 'estamento',
            'escuela', 'escuela_id'
        ]


class EstudianteSerializer(PersonaSerializer):
    class Meta(PersonaSerializer.Meta):
        model = Estudiante
        fields = PersonaSerializer.Meta.fields + ['semestre']


# ---------------------------------------
# Indicador
# ---------------------------------------
class IndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicador
        fields = '__all__'


# ---------------------------------------
# Actividad
# ---------------------------------------
class ActividadSerializer(serializers.ModelSerializer):
    indicador = IndicadorSerializer(read_only=True)
    indicador_id = serializers.PrimaryKeyRelatedField(
        queryset=Indicador.objects.all(), source='indicador',
        write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = Actividad
        fields = ['id_actividad', 'nombre', 'anio', 'indicador', 'indicador_id']


# ---------------------------------------
# Asociación Proyecto
# ---------------------------------------
class AsociacionProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsociacionProyecto
        fields = '__all__'


# ---------------------------------------
# Lugar (intermedia)
# ---------------------------------------
class LugarSerializer(serializers.ModelSerializer):
    sede = SedeSerializer(read_only=True)
    sede_id = serializers.PrimaryKeyRelatedField(
        queryset=Sede.objects.all(),
        source='sede',
        write_only=True
    )

    class Meta:
        model = Lugar
        fields = ['id_lugar', 'participacion', 'sede', 'sede_id']


# ---------------------------------------
# Participación
# ---------------------------------------
class ParticipacionSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer(read_only=True)
    persona_id = serializers.PrimaryKeyRelatedField(
        queryset=Persona.objects.all(), source='persona',
        write_only=True
    )

    actividad = ActividadSerializer(read_only=True)
    actividad_id = serializers.PrimaryKeyRelatedField(
        queryset=Actividad.objects.all(), source='actividad',
        write_only=True
    )

    sedes = SedeSerializer(many=True, read_only=True)  # lectura
    sedes_id = serializers.PrimaryKeyRelatedField(     # escritura
        queryset=Sede.objects.all(),
        many=True,
        write_only=True
    )

    class Meta:
        model = Participacion
        fields = [
            'id_participacion', 'persona', 'persona_id',
            'actividad', 'actividad_id', 'fecha',
            'sedes', 'sedes_id'
        ]

    def create(self, validated_data):
        sedes_ids = validated_data.pop('sedes_id', [])
        participacion = Participacion.objects.create(**validated_data)

        # llenar tabla intermedia Lugar
        for sede in sedes_ids:
            Lugar.objects.create(participacion=participacion, sede=sede)

        return participacion


# ---------------------------------------
# Actividad Consolidada
# ---------------------------------------
class ActividadConsolidadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadConsolidada
        fields = '__all__'


# ---------------------------------------
# Consolidación
# ---------------------------------------
class ConsolidacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consolidacion
        fields = '__all__'


# ---------------------------------------
# Tema y Tema Asociado
# ---------------------------------------
class TemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tema
        fields = '__all__'


class TemaAsociadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemaAsociado
        fields = '__all__'


# ---------------------------------------
# Prioridad y Prioridad Asociada
# ---------------------------------------
class PrioridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prioridad
        fields = '__all__'


class PrioridadAsociadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrioridadAsociada
        fields = '__all__'


# ---------------------------------------
# Línea de Estrategia y Estrategia Asociada
# ---------------------------------------
class LineaEstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaEstrategia
        fields = '__all__'


class EstrategiaAsociadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstrategiaAsociada
        fields = '__all__'
