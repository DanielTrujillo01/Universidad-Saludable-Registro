from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action    
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Avg
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.db import transaction

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
    
    # -------------------------------------------------------------------------
    # 10. DETALLE DINÁMICO: ACTIVIDAD ESPECÍFICA
    # URL: /api/dashboard-stats/detalle_actividad/?id=ID_DE_LA_ACTIVIDAD
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_actividad(self, request):
        activity_id = request.query_params.get('id')
        
        if not activity_id:
            return Response({"error": "ID requerido"}, status=400)

        try:
            actividad = Actividad.objects.get(pk=activity_id)
            
            # A. Personas únicas que asistieron al evento macro
            total_unicos = Participacion.objects.filter(actividad=actividad).values('persona').distinct().count()

            # B. Conteos granulares por taller (Tema)
            # Buscamos los temas que pertenecen a esta actividad
            temas_asociados = TemaAsociado.objects.filter(actividad=actividad).select_related('tema')
            
            temas_data = []
            for ta in temas_asociados:
                # Contamos cuántas personas registraron asistencia específica a este tema
                conteo_real = Participacion.objects.filter(
                    actividad=actividad, 
                    tema=ta.tema
                ).count()

                temas_data.append({
                    "tema__nombre": ta.tema.nombre,
                    "total_participantes": conteo_real
                })

            return Response({
                "id_actividad": actividad.id_actividad,
                "nombre": actividad.nombre,
                "total_participantes": total_unicos,
                "indicador": {"nombre": actividad.indicador.nombre if actividad.indicador else "N/A"},
                # ... prioridad y estrategia (igual que antes) ...
                "temas_asociados": temas_data
            })

        except Actividad.DoesNotExist:
            return Response({"error": "Actividad no encontrada"}, status=404)
        
    # -------------------------------------------------------------------------
    # 11. ESTADÍSTICAS TEMPORALES (Gráficos)
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_tiempo_stats(self, request):
        view_mode = request.query_params.get('mode', 'monthly') # monthly o yearly
        
        if view_mode == 'monthly':
            anio = request.query_params.get('anio', 2024)
            qs = Participacion.objects.filter(anio=anio).annotate(
                periodo=TruncMonth('fecha')
            ).values('periodo').annotate(
                actividades=Count('actividad', distinct=True),
                participantes=Count('persona', distinct=True)
            ).order_by('periodo')
        else:
            qs = Participacion.objects.annotate(
                periodo=TruncYear('fecha')
            ).values('periodo').annotate(
                actividades=Count('actividad', distinct=True),
                participantes=Count('persona', distinct=True)
            ).order_by('periodo')

        data = []
        for item in qs:
            # VALIDACIÓN DE SEGURIDAD:
            # Si 'periodo' es None (fecha nula en BD), lo saltamos o le ponemos un nombre default
            if not item['periodo']:
                continue 

            nombre_periodo = item['periodo'].strftime('%b') if view_mode == 'monthly' else item['periodo'].strftime('%Y')
            
            data.append({
                "name": nombre_periodo,
                "actividades": item['actividades'],
                "participantes": item['participantes']
            })
            
        return Response(data)

    # -------------------------------------------------------------------------
    # 12. DETALLE DE RANGO TEMPORAL (Tarjeta de Detalles)
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_rango_tiempo(self, request):
        inicio_raw = request.query_params.get('inicio')
        fin_raw = request.query_params.get('fin')
        
        try:
            # Validamos que las fechas sean reales antes de filtrar
            inicio = parse_date(inicio_raw)
            fin = parse_date(fin_raw)
            
            if not inicio or not fin:
                return Response({"error": "Fechas inválidas o mal formadas"}, status=400)
                
            participaciones = Participacion.objects.filter(fecha__range=[inicio, fin]).select_related('actividad', 'tema')

            actividades_dict = {}
            total_p = 0
            
            for p in participaciones:
                act_id = p.actividad.id_actividad
                if act_id not in actividades_dict:
                    actividades_dict[act_id] = {
                        "nombre": p.actividad.nombre,
                        "participantes_actividad": 0,
                        "temas": {}
                    }
                
                # Conteo de temas
                tema_nombre = p.tema.nombre if p.tema else "Asistencia General"
                actividades_dict[act_id]["temas"][tema_nombre] = actividades_dict[act_id]["temas"].get(tema_nombre, 0) + 1
                actividades_dict[act_id]["participantes_actividad"] += 1
                total_p += 1

            return Response({
                "total_actividades": len(actividades_dict),
                "total_participantes": total_p,
                "listado": list(actividades_dict.values())
            })
        
        except (ValidationError, ValueError):
            return Response({"error": "Una de las fechas proporcionadas no existe en el calendario"}, status=400)
        



# ------------------------------------------
# CRUD ViewSets
# ------------------------------------------

class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class LineaProyectoViewSet(viewsets.ModelViewSet):
    queryset = LineaProyecto.objects.all()
    serializer_class = LineaProyectoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre']

class FacultadViewSet(viewsets.ModelViewSet):
    queryset = Facultad.objects.all()
    serializer_class = FacultadSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class EscuelaViewSet(viewsets.ModelViewSet):
    queryset = Escuela.objects.all()
    serializer_class = EscuelaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer
    filter_backends = [SearchFilter] 
    search_fields = ["nombre", "numero_documento", "nombre_original"]

class EstudianteViewSet(viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer
    filter_backends = [SearchFilter]
    search_fields = ["nombre", "numero_documento"]

class IndicadorViewSet(viewsets.ModelViewSet):
    queryset = Indicador.objects.all()
    serializer_class = IndicadorSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class ActividadViewSet(viewsets.ModelViewSet):
    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def temas(self, request, pk=None):
        """
        Devuelve la lista de temas asociados a una actividad específica.
        Accesible públicamente.
        """
        # Buscamos los temas a través de la tabla intermedia 'TemaAsociado'
        # Filtramos los temas donde exista una asociación con la actividad 'pk'
        temas = Tema.objects.filter(temaasociado__actividad_id=pk).values('id_tema', 'nombre')
        
        # Devolvemos una lista limpia
        return Response(list(temas))
    
    def create(self, request, *args, **kwargs):
        # 1. Extraemos los IDs de las relaciones opcionales
        linea_proyecto_id = request.data.get('id_linea_proyecto')
        prioridad_id = request.data.get('id_prioridad')
        linea_estrategia_id = request.data.get('id_linea_estrategia')

        # 2. Usamos una transacción atómica para garantizar integridad
        with transaction.atomic():
            # A. Crear la Actividad base
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            actividad_instance = serializer.instance

            # B. Crear Relación: Línea de Proyecto (AsociacionProyecto)
            if linea_proyecto_id:
                try:
                    lp_instance = LineaProyecto.objects.get(pk=linea_proyecto_id)
                    AsociacionProyecto.objects.create(
                        actividad=actividad_instance,
                        linea_proyecto=lp_instance
                    )
                except LineaProyecto.DoesNotExist:
                    pass # O lanzar error según tu lógica de negocio

            # C. Crear Relación: Prioridad (PrioridadAsociada)
            if prioridad_id:
                try:
                    p_instance = Prioridad.objects.get(pk=prioridad_id)
                    PrioridadAsociada.objects.create(
                        actividad=actividad_instance,
                        prioridad=p_instance
                    )
                except Prioridad.DoesNotExist:
                    pass

            # D. Crear Relación: Estrategia (EstrategiaAsociada)
            if linea_estrategia_id:
                try:
                    le_instance = LineaEstrategia.objects.get(pk=linea_estrategia_id)
                    EstrategiaAsociada.objects.create(
                        actividad=actividad_instance,
                        linea_estrategia=le_instance
                    )
                except LineaEstrategia.DoesNotExist:
                    pass

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class ConsolidacionViewSet(viewsets.ModelViewSet):
    queryset = Consolidacion.objects.all()
    serializer_class = ConsolidacionSerializer

# --------------------------------------------------------
# TEMA VIEWSET (MODIFICADO PARA CREACIÓN CONJUNTA)
# --------------------------------------------------------
class TemaViewSet(viewsets.ModelViewSet):
    queryset = Tema.objects.all()
    serializer_class = TemaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre']

    def create(self, request, *args, **kwargs):
        # 1. Extraemos el id_actividad del cuerpo de la petición (si viene)
        actividad_id = request.data.get('id_actividad')
        
        # Usamos atomic para asegurar que si falla la asociación, no se cree el tema suelto
        with transaction.atomic():
            # 2. Creamos el Tema normalmente usando el método del padre
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            tema_instance = serializer.instance
            
            # 3. Si se envió una actividad, creamos la relación en TemaAsociado
            if actividad_id:
                try:
                    actividad_instance = Actividad.objects.get(pk=actividad_id)
                    TemaAsociado.objects.create(
                        tema=tema_instance,
                        actividad=actividad_instance
                    )
                except Actividad.DoesNotExist:
                    # Puedes decidir si lanzar error o solo ignorarlo. 
                    # Aquí retornamos error para que el frontend sepa que el ID era malo.
                    return Response(
                        {"error": "La actividad especificada no existe"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class TemaAsociadoViewSet(viewsets.ModelViewSet):
    queryset = TemaAsociado.objects.all()
    serializer_class = TemaAsociadoSerializer

class PrioridadViewSet(viewsets.ModelViewSet):
    queryset = Prioridad.objects.all()
    serializer_class = PrioridadSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class PrioridadAsociadaViewSet(viewsets.ModelViewSet):
    queryset = PrioridadAsociada.objects.all()
    serializer_class = PrioridadAsociadaSerializer

class LineaEstrategiaViewSet(viewsets.ModelViewSet):
    queryset = LineaEstrategia.objects.all()
    serializer_class = LineaEstrategiaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

class EstrategiaAsociadaViewSet(viewsets.ModelViewSet):
    queryset = EstrategiaAsociada.objects.all()
    serializer_class = EstrategiaAsociadaSerializer
