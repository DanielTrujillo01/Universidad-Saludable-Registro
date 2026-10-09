from rest_framework import serializers
from django.db import transaction
from .models import *

# -------------------------
# Básicos
# -------------------------

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
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
class EstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estrategia
        fields = '__all__'


from rest_framework import serializers
from django.db import transaction

class AccionSerializer(serializers.ModelSerializer):
    id_prioridad = serializers.PrimaryKeyRelatedField(
        queryset=Prioridad.objects.all(),
        write_only=True,
        required=True
    )
    
    id_linea_estrategia = serializers.PrimaryKeyRelatedField(
        queryset=LineaEstrategia.objects.all(),
        write_only=True,
        required=True
    )

    class Meta:
        model = Accion
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        prioridad = validated_data.pop('id_prioridad')
        linea_estrategia = validated_data.pop('id_linea_estrategia')

        # Crear la acción (la FK de estrategia ya viene en el modelo ✔)
        accion = Accion.objects.create(**validated_data)

        # Relación con prioridad
        PrioridadAsociada.objects.create(
            accion=accion,
            prioridad=prioridad
        )

        # Relación con línea estratégica
        EstrategiaAsociada.objects.create(
            accion=accion,
            linea_estrategia=linea_estrategia
        )

        return accion


class ActividadSerializer(serializers.ModelSerializer):
    id_accion = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = Actividad
        fields = '__all__'

    def validate_id_accion(self, value):
        try:
            accion = Accion.objects.get(pk=value)
        except Accion.DoesNotExist:
            raise serializers.ValidationError("La acción especificada no existe")
        
        return accion  # 👈 devolvemos la instancia, no el id

    @transaction.atomic
    def create(self, validated_data):
        # Sacamos la acción ya validada
        accion = validated_data.pop('id_accion')

        # Creamos la actividad
        actividad = Actividad.objects.create(**validated_data)

        # Creamos la relación
        ActividadAsociada.objects.create(
            accion=accion,
            actividad=actividad
        )

        return actividad


class TemaSerializer(serializers.ModelSerializer):
    id_actividad = serializers.PrimaryKeyRelatedField(
        queryset=Actividad.objects.all(),
        write_only=True,
        required=True
    )

    class Meta:
        model = Tema
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        actividad = validated_data.pop('id_actividad')

        # Crear el tema
        tema = Tema.objects.create(**validated_data)

        # Crear la relación
        TemaAsociado.objects.create(
            tema=tema,
            actividad=actividad
        )

        return tema


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