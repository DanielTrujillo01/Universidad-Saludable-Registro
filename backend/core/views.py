from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
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


#--------------------------------------------------
# VISTA PERSONALIZADA: Estadísticas del Dashboard
#--------------------------------------------------
class DashboardStatsView(APIView):
    # Todo lo que pase aquí requiere ser Admin
    permission_classes = [IsAdminUser] 

    def get(self, request):
        data_response = {}

        # ---------------------------------------------------
        # A. LÓGICA DE ESTADÍSTICAS GENERALES (Siempre se envían)
        # ---------------------------------------------------
        total_personas = Persona.objects.count()
        data_response['resumen_general'] = {
            "total_personas": total_personas,
            "total_actividades": Actividad.objects.count(),
        }

        # ---------------------------------------------------
        # B. TU FILTRO ESPECÍFICO (Copiado de PersonaViewSet)
        # ---------------------------------------------------
        # Verificamos si el admin mandó un parámetro de búsqueda
        nombre_actividad = request.query_params.get('nombre_actividad')

        if nombre_actividad:
            # Hacemos la query exacta que tenías antes
            personas_filtradas = Persona.objects.filter(
                participacion__actividad__nombre__icontains=nombre_actividad
            ).distinct()

            # Serializamos la data manualmente
            # Nota: context={'request': request} es buena práctica por si el serializer usa URLs
            serializer = PersonaSerializer(personas_filtradas, many=True, context={'request': request})
            
            # Agregamos los resultados al JSON de respuesta
            data_response['resultados_busqueda'] = serializer.data
            data_response['mensaje_busqueda'] = f"Resultados para '{nombre_actividad}'"
        else:
            # Si no hay búsqueda, enviamos lista vacía o null
            data_response['resultados_busqueda'] = []

        return Response(data_response)


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
    filter_backends = [SearchFilter] 
    search_fields = ["nombre", "numero_documento"]


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

