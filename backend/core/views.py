from django.shortcuts import render
from rest_framework import viewsets
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
class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet Híbrido:
    - /resumen: Carga rápida inicial (KPIs, Prioridades, Indicadores).
    - /escuelas: Carga bajo demanda (Estadísticas por Escuela).
    - /evolucion: Carga bajo demanda (Línea de tiempo).
    """
    permission_classes = [IsAdminUser]

    # -------------------------------------------------------------------------
    # 1. CARGA LIGERA (Al iniciar el Dashboard)
    # URL: /api/dashboard/resumen/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def resumen(self, request):
        # A. KPIs
        total_actividades = Actividad.objects.count()
        total_participantes = Participacion.objects.count()
        promedio = round(total_participantes / total_actividades) if total_actividades > 0 else 0

        # B. Gráfica: PRIORIDADES
        prioridades_qs = Actividad.objects.values('prioridadasociada__prioridad__nombre').annotate(total=Count('id_actividad'))
        grafica_prioridades = [
            {"name": item['prioridadasociada__prioridad__nombre'] or "Sin Prioridad", "value": item['total']}
            for item in prioridades_qs if item['prioridadasociada__prioridad__nombre']
        ]

        # C. Gráfica: INDICADORES
        indicadores_qs = Actividad.objects.values('indicador__nombre').annotate(total=Count('id_actividad'))
        grafica_indicadores = [
            {"name": item['indicador__nombre'] or "Sin Indicador", "value": item['total']}
            for item in indicadores_qs
        ]

        return Response({
            "kpis": {
                "total_actividades": total_actividades,
                "total_participantes": total_participantes,
                "promedio_participantes": promedio,
            },
            "graficas": {
                "prioridades": grafica_prioridades,
                "indicadores": grafica_indicadores,
                # Nota: Escuelas ya no está aquí para aligerar la carga inicial
            }
        })

    # -------------------------------------------------------------------------
    # 2. CARGA MEDIA (Separada porque usa Join de 3 tablas)
    # URL: /api/dashboard/escuelas/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def escuelas(self, request):
        # Ruta: Participacion -> Persona -> Escuela -> Nombre
        escuelas_qs = Participacion.objects.values('persona__escuela__nombre').annotate(total=Count('id_participacion'))
        
        grafica_escuelas = [
            {"name": item['persona__escuela__nombre'] or "Sin Escuela", "value": item['total']}
            for item in escuelas_qs if item['persona__escuela__nombre']
        ]
        
        # Ordenamos de mayor a menor y tomamos el top 10 (para optimizar visualización)
        grafica_escuelas = sorted(grafica_escuelas, key=lambda x: x['value'], reverse=True)[:10]

        return Response(grafica_escuelas)

    # -------------------------------------------------------------------------
    # 3. CARGA PESADA (Análisis Temporal)
    # URL: /api/dashboard/evolucion/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def evolucion(self, request):
        # Agrupa actividades por Mes. Esto es costoso en DB grandes.
        # Asumiendo que Actividad tiene 'fecha_inicio' o usamos Participacion 'fecha'
        
        # Ejemplo usando Participacion (Evolución de asistencia):
        evolucion_qs = Participacion.objects.annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(total=Count('id_participacion')).order_by('mes')

        grafica_tiempo = [
            {
                "name": item['mes'].strftime('%Y-%m') if item['mes'] else "Sin Fecha", 
                "value": item['total']
            }
            for item in evolucion_qs
        ]

        return Response(grafica_tiempo)
    
    # -------------------------------------------------------------------------
    # 4. CARGA ESPECÍFICA: INDICADORES
    # URL: /api/dashboard/por_indicador/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_indicador(self, request):
        total_actividades = Actividad.objects.count()
        
        # Agrupamos por nombre de indicador y contamos
        # Order_by('-total') asegura que el primero sea el "Top Indicator"
        qs = Actividad.objects.values('indicador__nombre').annotate(
            total=Count('id_actividad')
        ).order_by('-total')

        data_list = []
        for item in qs:
            cantidad = item['total']
            nombre = item['indicador__nombre'] or "Sin Indicador"
            
            # Calculamos porcentaje
            porcentaje = 0
            if total_actividades > 0:
                porcentaje = round((cantidad / total_actividades) * 100, 1)

            data_list.append({
                "name": nombre,
                "actividades": cantidad,
                "porcentaje": porcentaje
            })

        # Extraemos el "Top Indicator" (el primero de la lista ya ordenada)
        top_indicator = data_list[0] if data_list else {"name": "N/A", "porcentaje": 0}

        return Response({
            "total_actividades": total_actividades,
            "total_indicadores": len(data_list),
            "top_indicator": top_indicator,
            "data": data_list # Lista detallada para la tabla y gráficas
        })
    
    # -------------------------------------------------------------------------
    # 5. CARGA ESPECÍFICA: PRIORIDADES
    # URL: /api/dashboard-stats/por_prioridad/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_prioridad(self, request):
        total_actividades = Actividad.objects.count()

        # Agrupamos usando la relación inversa de la tabla intermedia
        # Actividad -> prioridadasociada -> prioridad -> nombre
        qs = Actividad.objects.values('prioridadasociada__prioridad__nombre').annotate(
            total=Count('id_actividad')
        ).order_by('-total')

        data_list = []
        for item in qs:
            nombre = item['prioridadasociada__prioridad__nombre']
            
            # Filtramos actividades que no tengan prioridad asignada (None)
            if not nombre:
                continue

            cantidad = item['total']
            
            # Cálculo de porcentaje
            porcentaje = 0
            if total_actividades > 0:
                porcentaje = round((cantidad / total_actividades) * 100, 1)

            data_list.append({
                "name": nombre,
                "actividades": cantidad,
                "porcentaje": porcentaje
            })

        # Extraer la prioridad más común (Top 1)
        top_priority = data_list[0] if data_list else {"name": "N/A", "porcentaje": 0}

        return Response({
            "total_actividades": total_actividades,
            "total_prioridades": len(data_list),
            "top_priority": top_priority,
            "data": data_list
        })
    
    # -------------------------------------------------------------------------
    # 6. CARGA ESPECÍFICA: LÍNEAS ESTRATÉGICAS
    # URL: /api/dashboard-stats/por_estrategia/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_estrategia(self, request):
        total_actividades = Actividad.objects.count()

        # Ruta: Actividad -> estrategiaasociada -> linea_estrategia -> nombre
        qs = Actividad.objects.values('estrategiaasociada__linea_estrategia__nombre').annotate(
            total=Count('id_actividad')
        ).order_by('-total')

        data_list = []
        for item in qs:
            nombre = item['estrategiaasociada__linea_estrategia__nombre']
            
            # Filtramos si es None (actividad sin estrategia)
            if not nombre: continue

            cantidad = item['total']
            
            # Porcentaje relativo al total de actividades del sistema
            porcentaje = 0
            if total_actividades > 0:
                porcentaje = round((cantidad / total_actividades) * 100, 1)

            data_list.append({
                "name": nombre,
                "actividades": cantidad,
                "porcentaje": porcentaje
            })

        # Top Strategy
        top_strategy = data_list[0] if data_list else {"name": "N/A", "porcentaje": 0}

        return Response({
            "total_actividades": total_actividades,
            "total_estrategias": len(data_list),
            "top_strategy": top_strategy,
            "data": data_list
        })
    
    # -------------------------------------------------------------------------
    # 7. CARGA ESPECÍFICA: SEDES (CAMPUS)
    # URL: /api/dashboard-stats/por_sede/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_sede(self, request):
        # Agrupamos por Sede basándonos en la tabla Participación
        qs = Participacion.objects.values('sede__nombre').annotate(
            total_participantes=Count('id_participacion'),
            total_actividades=Count('actividad', distinct=True)
        ).order_by('-total_participantes')

        data_list = []
        for item in qs:
            nombre = item['sede__nombre']
            if not nombre: continue

            data_list.append({
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes']
                # Eliminado campo 'ubicacion'
            })

        return Response({
            "total_sedes": len(data_list),
            "data": data_list
        })
    
    # -------------------------------------------------------------------------
    # 8. CARGA ESPECÍFICA: ESCUELAS
    # URL: /api/dashboard-stats/por_escuela/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_escuela(self, request):
        # Agrupamos Participaciones por la Escuela de la Persona
        qs = Participacion.objects.values('persona__escuela__nombre').annotate(
            total_participantes=Count('id_participacion'),
            total_actividades=Count('actividad', distinct=True)
        ).order_by('-total_participantes')

        data_list = []
        for item in qs:
            nombre = item['persona__escuela__nombre']
            if not nombre: 
                nombre = "Sin Escuela Asignada"

            data_list.append({
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes'],
            })

        return Response({
            "total_escuelas": len(data_list),
            "data": data_list
        })
    
    # -------------------------------------------------------------------------
    # 9. CARGA ESPECÍFICA: FACULTADES
    # URL: /api/dashboard-stats/por_facultad/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_facultad(self, request):
        # Agrupamos Participaciones por la Facultad de la Escuela de la Persona
        qs = Participacion.objects.values('persona__escuela__facultad__nombre').annotate(
            total_participantes=Count('id_participacion'),
            total_actividades=Count('actividad', distinct=True)
        ).order_by('-total_participantes')

        data_list = []
        for item in qs:
            nombre = item['persona__escuela__facultad__nombre']
            if not nombre: 
                nombre = "Sin Facultad Asignada"

            data_list.append({
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes'],
            })

        return Response({
            "total_facultades": len(data_list),
            "data": data_list
        })


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

