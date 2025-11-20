from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from .models import (
    Sede, LineaProyecto, Facultad, Escuela, Persona, Estudiante,
    Indicador, Actividad, AsociacionProyecto, Participacion, Lugar,
    ActividadConsolidada, Consolidacion, Tema, TemaAsociado,
    Prioridad, PrioridadAsociada, LineaEstrategia, EstrategiaAsociada
)
from .serializers import (
    SedeSerializer, LineaProyectoSerializer, FacultadSerializer, EscuelaSerializer,
    PersonaSerializer, EstudianteSerializer, IndicadorSerializer, ActividadSerializer,
    AsociacionProyectoSerializer, ParticipacionSerializer, LugarSerializer,
    ActividadConsolidadaSerializer, ConsolidacionSerializer, TemaSerializer,
    TemaAsociadoSerializer, PrioridadSerializer, PrioridadAsociadaSerializer,
    LineaEstrategiaSerializer, EstrategiaAsociadaSerializer
)


# ------------------------------------------
# CRUD ViewSets
# ------------------------------------------

class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer


class LineaProyectoViewSet(viewsets.ModelViewSet):
    queryset = LineaProyecto.objects.all()
    serializer_class = LineaProyectoSerializer


class FacultadViewSet(viewsets.ModelViewSet):
    queryset = Facultad.objects.all()
    serializer_class = FacultadSerializer


class EscuelaViewSet(viewsets.ModelViewSet):
    queryset = Escuela.objects.all()
    serializer_class = EscuelaSerializer


class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer

    # ----------------------------------------------------------------------
    # FUNCIÓN DE CONSULTA: Personas que asistieron a una Actividad (por Nombre)
    # ----------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='asistentes-por-nombre-actividad')
    def asistentes_por_nombre_actividad(self, request):
        """
        Obtiene una lista de Personas que participaron en una Actividad
        específica, filtrando por el nombre de la actividad.
        Ej: /api/personas/asistentes-por-nombre-actividad/?nombre_actividad=Taller%20de%20Liderazgo
        """
        # 1. Obtener el nombre de la actividad del parámetro de consulta (query parameter)
        nombre_actividad = request.query_params.get('nombre_actividad')

        if not nombre_actividad:
            return Response(
                {"error": "Debe proporcionar el parámetro 'nombre_actividad'."},
                status=400 # Bad Request
            )

        # 2. Lógica del Modelo (Consulta con Django ORM)
        # Usamos icontains para buscar el nombre de la actividad de forma insensible a mayúsculas
        # y que funcione incluso con nombres parciales (puedes cambiarlo a exact si deseas coincidencia exacta).
        personas = Persona.objects.filter(
            participacion__actividad__nombre__icontains=nombre_actividad
        ).distinct() # Usamos distinct() para asegurar que cada Persona aparezca solo una vez.

        # Verificar si se encontraron resultados
        if not personas.exists():
             return Response(
                {"mensaje": f"No se encontraron personas que hayan asistido a la actividad que contenga el nombre: '{nombre_actividad}'."},
                status=200 # OK, pero la lista está vacía
            )

        # 3. Vista (Serialización)
        serializer = self.get_serializer(personas, many=True)

        # 4. Retorno de la Respuesta
        return Response(serializer.data)


class EstudianteViewSet(viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer


class IndicadorViewSet(viewsets.ModelViewSet):
    queryset = Indicador.objects.all()
    serializer_class = IndicadorSerializer


class ActividadViewSet(viewsets.ModelViewSet):
    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer


class AsociacionProyectoViewSet(viewsets.ModelViewSet):
    queryset = AsociacionProyecto.objects.all()
    serializer_class = AsociacionProyectoSerializer


class ParticipacionViewSet(viewsets.ModelViewSet):
    queryset = Participacion.objects.all()
    serializer_class = ParticipacionSerializer


class LugarViewSet(viewsets.ModelViewSet):
    queryset = Lugar.objects.all()
    serializer_class = LugarSerializer


class ActividadConsolidadaViewSet(viewsets.ModelViewSet):
    queryset = ActividadConsolidada.objects.all()
    serializer_class = ActividadConsolidadaSerializer


class ConsolidacionViewSet(viewsets.ModelViewSet):
    queryset = Consolidacion.objects.all()
    serializer_class = ConsolidacionSerializer


class TemaViewSet(viewsets.ModelViewSet):
    queryset = Tema.objects.all()
    serializer_class = TemaSerializer


class TemaAsociadoViewSet(viewsets.ModelViewSet):
    queryset = TemaAsociado.objects.all()
    serializer_class = TemaAsociadoSerializer


class PrioridadViewSet(viewsets.ModelViewSet):
    queryset = Prioridad.objects.all()
    serializer_class = PrioridadSerializer


class PrioridadAsociadaViewSet(viewsets.ModelViewSet):
    queryset = PrioridadAsociada.objects.all()
    serializer_class = PrioridadAsociadaSerializer


class LineaEstrategiaViewSet(viewsets.ModelViewSet):
    queryset = LineaEstrategia.objects.all()
    serializer_class = LineaEstrategiaSerializer


class EstrategiaAsociadaViewSet(viewsets.ModelViewSet):
    queryset = EstrategiaAsociada.objects.all()
    serializer_class = EstrategiaAsociadaSerializer

