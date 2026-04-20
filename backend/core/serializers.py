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


class UnidadOrganizativaSerializer(serializers.ModelSerializer):
    # Permite ver el nombre del "padre" en las consultas GET
    padre_nombre = serializers.ReadOnlyField(source='padre.nombre')

    class Meta:
        model = UnidadOrganizativa
        fields = ['id', 'nombre', 'tipo', 'padre', 'padre_nombre']

# -------------------------
# Persona
# -------------------------
# Este es el nuevo para el buscador (Ligero y con el nombre de la unidad)
class VinculacionResumenSerializer(serializers.ModelSerializer):
    nombre_unidad = serializers.ReadOnlyField(source='id_unidad_organizativa.nombre')

    class Meta:
        model = Vinculacion
        fields = ['id_vinculacion', 'tipo_estamento', 'nombre_unidad', 'semestre']

# Luego lo usas dentro de Persona
class PersonaSerializer(serializers.ModelSerializer):
    # Relación inversa: trae las vinculaciones de esta persona
    vinculaciones = VinculacionResumenSerializer(source='vinculacion_set', many=True, read_only=True)
    
    unidadOrganizativa_detalle = UnidadOrganizativaSerializer(source='unidadOrganizativa', read_only=True)

    class Meta:
        model = Persona
        fields = [
            'id_persona', 'nombre', 'nombre_original', 'tipo_documento', 
            'numero_documento', 'correo', 'sexo', 'vinculaciones', 'edad',
            'unidadOrganizativa_detalle'
        ]


class VinculacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vinculacion
        fields = '__all__'

# -------------------------
# Núcleo del modelo
# -------------------------
class EstrategiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estrategia
        fields = '__all__'


class AccionSerializer(serializers.ModelSerializer):
    # IDs para creación manual en el método create o vía lógica directa
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
        # Extraemos las relaciones que van a tablas intermedias
        prioridad = validated_data.pop('id_prioridad', None)
        linea_estrategia = validated_data.pop('id_linea_estrategia', None)

        # Crear la acción
        accion = Accion.objects.create(**validated_data)

        # Crear las relaciones asociadas si se enviaron los IDs
        if prioridad:
            PrioridadAsociada.objects.create(accion=accion, prioridad=prioridad)
        
        if linea_estrategia:
            EstrategiaAsociada.objects.create(accion=accion, linea_estrategia=linea_estrategia)

        return accion


class ActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividad
        fields = '__all__'


class SeccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seccion
        fields = '__all__'

# -------------------------
# Participación (clave)
# -------------------------
class ParticipacionSerializer(serializers.ModelSerializer):
    semestre = serializers.IntegerField(read_only=True)

    class Meta:
        model = Participacion
        fields = [
            'id_participacion', 'persona', 'vinculacion', 
            'accion', 'actividad', 'seccion', 'fecha', 
            'anio', 'sede', 'semestre'
        ]
    
    # Opcional: Si quieres validar que la vinculación pertenezca a la persona
    def validate(self, data):
        vinculacion = data.get('vinculacion')
        persona = data.get('persona')
        
        if vinculacion and vinculacion.id_persona != persona:
            raise serializers.ValidationError(
                {"vinculacion": "La vinculación seleccionada no pertenece a esta persona."}
            )
        return data

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