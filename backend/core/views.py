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
from django_filters.rest_framework import DjangoFilterBackend


from .models import (
    Sede, Facultad, Escuela, Persona, Estudiante, Actividad, ActividadAsociada, Participacion,
    Tema, TemaAsociado,
    Prioridad, PrioridadAsociada, LineaEstrategia, EstrategiaAsociada,Estrategia,Accion,
)
from .serializers import (
    SedeSerializer, FacultadSerializer, EscuelaSerializer,
    PersonaSerializer, EstudianteSerializer,  ActividadSerializer,
    ParticipacionSerializer,AccionSerializer, TemaSerializer,
    TemaAsociadoSerializer, PrioridadSerializer, PrioridadAsociadaSerializer,
    LineaEstrategiaSerializer, EstrategiaAsociadaSerializer,EstrategiaSerializer
)


#--------------------------------------------------
# VISTA PERSONALIZADA: Estadísticas del Dashboard
#--------------------------------------------------
class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet Híbrido:
    - /resumen: Carga rápida inicial (KPIs, Prioridades).
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

        return Response({
            "kpis": {
                "total_actividades": total_actividades,
                "total_participantes": total_participantes,
                "promedio_participantes": promedio,
            },
            "graficas": {
                "prioridades": grafica_prioridades
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

        start_date_raw = request.query_params.get('start_date')
        end_date_raw = request.query_params.get('end_date')

        qs = Participacion.objects.all()

        if start_date_raw and end_date_raw:
            start_date = parse_date(start_date_raw)
            end_date = parse_date(end_date_raw)

            if start_date and end_date:
                qs = qs.filter(fecha__range=[start_date, end_date])
            else:
                return Response({"error": "Fechas inválidas"}, status=400)

        # ----------------------------
        # TOTAL SEDES
        # ----------------------------
        total_sedes = qs.values('sede').distinct().count()

        # ----------------------------
        # DATOS POR SEDE
        # ----------------------------
        agrupado = (
            qs.values('sede','sede__nombre')
            .annotate(
                total_participantes=Count('id_participacion'),
                total_actividades=Count('actividad', distinct=True)
            )
            .order_by('-total_participantes')
        )

        data_list = []

        for item in agrupado:
            nombre = item['sede__nombre']
            if not nombre:
                continue

            data_list.append({
                "id": item['sede'],
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes']
            })

        # ----------------------------
        # DISTRIBUCIÓN GLOBAL ESTAMENTO
        # ----------------------------
        total_personas = qs.values('persona').distinct().count()

        estamentos = (
            qs.values('persona__estamento')
            .annotate(total=Count('persona', distinct=True))
        )

        estamento_data = []

        for e in estamentos:
            cantidad = e['total']
            porcentaje = round((cantidad / total_personas) * 100, 2) if total_personas > 0 else 0

            estamento_data.append({
                "estamento": e['persona__estamento'] or "Sin estamento",
                "cantidad": cantidad,
                "porcentaje": porcentaje
            })

        return Response({
            "total_sedes": total_sedes,
            "filtro_aplicado": bool(start_date_raw and end_date_raw),
            "data": data_list,
            "estamento_global": estamento_data
        })
    


    # -------------------------------------------------------------------------
    # 8. DETALLE DINÁMICO: SEDE ESPECÍFICA
    # URL:
    # /api/dashboard-stats/detalle_sede/?id=ID_SEDE&fecha_inicio=2026-01-01&fecha_fin=2026-12-31
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_sede(self, request):

        sede_id = request.query_params.get('id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        if not sede_id:
            return Response({"error": "ID de sede requerido"}, status=400)

        try:
            sede = Sede.objects.get(pk=sede_id)

            # 🔹 Filtro base por sede
            participaciones = Participacion.objects.filter(sede=sede)

            # 🔹 Filtro por rango de fechas (AHORA sobre Participacion)
            if fecha_inicio and fecha_fin:
                participaciones = participaciones.filter(
                    fecha__range=[fecha_inicio, fecha_fin]
                )

            # ---------------------------------------
            # 1️⃣ TOTAL PARTICIPANTES ÚNICOS
            # ---------------------------------------
            total_unicos = participaciones.values('persona').distinct().count()

            # ---------------------------------------
            # 2️⃣ TOTAL ACTIVIDADES
            # ---------------------------------------
            total_actividades = participaciones.values('actividad').distinct().count()

            # ---------------------------------------
            # 3️⃣ DISTRIBUCIÓN POR ESTAMENTO
            # ---------------------------------------
            conteo_por_estamento = (
                participaciones
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )

            estamentos_data = []

            for item in conteo_por_estamento:
                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                estamento_nombre = item['persona__estamento'] or "Sin Estamento"

                estamentos_data.append({
                    "estamento": estamento_nombre,
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })

            return Response({
                "id_sede": sede.id_sede,
                "nombre": sede.nombre,
                "total_actividades": total_actividades,
                "total_participantes": total_unicos,
                "estamento_participantes": estamentos_data
            })

        except Sede.DoesNotExist:
            return Response({"error": "Sede no encontrada"}, status=404)
    
    # -------------------------------------------------------------------------
    # 9. CARGA DINAMICA: ESCUELAS
    # URL: /api/dashboard-stats/por_escuela/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_escuela(self, request):

        start_date_raw = request.query_params.get('start_date')
        end_date_raw = request.query_params.get('end_date')

        qs = Participacion.objects.all()

        # 🔹 Filtro por rango
        if start_date_raw and end_date_raw:
            start_date = parse_date(start_date_raw)
            end_date = parse_date(end_date_raw)

            if not start_date or not end_date:
                return Response({"error": "Fechas inválidas"}, status=400)

            qs = qs.filter(fecha__range=[start_date, end_date])

        # ----------------------------
        # TOTAL ESCUELAS
        # ----------------------------
        total_escuelas = (
            qs.values('persona__escuela')
            .distinct()
            .count()
        )

        # ----------------------------
        # DATOS POR ESCUELA
        # ----------------------------
        agrupado = (
            qs.values('persona__escuela','persona__escuela__nombre')
            .annotate(
                total_participantes=Count('id_participacion'),
                total_actividades=Count('actividad', distinct=True)
            )
            .order_by('-total_participantes')
        )

        data_list = []

        for item in agrupado:

            nombre = item['persona__escuela__nombre'] or "Sin Escuela"

            data_list.append({
                "id": item['persona__escuela'],
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes']
            })

        # ----------------------------
        # DISTRIBUCIÓN GLOBAL ESTAMENTO
        # ----------------------------
        total_personas = qs.values('persona').distinct().count()

        estamentos = (
            qs.values('persona__estamento')
            .annotate(total=Count('persona', distinct=True))
        )

        estamento_data = []

        for e in estamentos:

            cantidad = e['total']
            porcentaje = round((cantidad / total_personas) * 100, 2) if total_personas > 0 else 0

            estamento_data.append({
                "estamento": e['persona__estamento'] or "Sin estamento",
                "cantidad": cantidad,
                "porcentaje": porcentaje
            })

        return Response({
            "total_escuelas": total_escuelas,
            "filtro_aplicado": bool(start_date_raw and end_date_raw),
            "data": data_list,
            "estamento_global": estamento_data
        })
    

     # -------------------------------------------------------------------------
    # 10. DETALLE DINÁMICO: ESCUELA ESPECÍFICA
    # URL:
    # /api/dashboard-stats/detalle_escuela/?id=ID_ESCUELA&fecha_inicio=2026-01-01&fecha_fin=2026-12-31
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_escuela(self, request):

        escuela_id = request.query_params.get('id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        if not escuela_id:
            return Response({"error": "ID de escuela requerido"}, status=400)

        try:

            escuela = Escuela.objects.get(pk=escuela_id)

            participaciones = Participacion.objects.filter(
                persona__escuela=escuela
            )

            # 🔹 filtro por fechas
            if fecha_inicio and fecha_fin:
                participaciones = participaciones.filter(
                    fecha__range=[fecha_inicio, fecha_fin]
                )

            # ----------------------------
            # TOTAL PARTICIPANTES ÚNICOS
            # ----------------------------
            total_unicos = participaciones.values('persona').distinct().count()

            # ----------------------------
            # TOTAL ACTIVIDADES
            # ----------------------------
            total_actividades = participaciones.values('actividad').distinct().count()

            # ----------------------------
            # DISTRIBUCIÓN ESTAMENTO
            # ----------------------------
            conteo = (
                participaciones
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )

            estamentos_data = []

            for item in conteo:

                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                estamentos_data.append({
                    "estamento": item['persona__estamento'] or "Sin Estamento",
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })

            return Response({
                "id_escuela": escuela.id_escuela,
                "nombre": escuela.nombre,
                "total_actividades": total_actividades,
                "total_participantes": total_unicos,
                "estamento_participantes": estamentos_data
            })

        except Escuela.DoesNotExist:
            return Response({"error": "Escuela no encontrada"}, status=404)
    
    # -------------------------------------------------------------------------
    # 10. CARGA ESPECIFICA: FACULTADES
    # URL: /api/dashboard-stats/por_facultad/
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def por_facultad(self, request):

        start_date_raw = request.query_params.get('start_date')
        end_date_raw = request.query_params.get('end_date')

        qs = Participacion.objects.all()

        # 🔹 Filtro por rango
        if start_date_raw and end_date_raw:
            start_date = parse_date(start_date_raw)
            end_date = parse_date(end_date_raw)

            if not start_date or not end_date:
                return Response({"error": "Fechas inválidas"}, status=400)

            qs = qs.filter(fecha__range=[start_date, end_date])

        # ----------------------------
        # TOTAL FACULTADES
        # ----------------------------
        total_facultades = (
            qs.values('persona__escuela__facultad')
            .distinct()
            .count()
        )

        # ----------------------------
        # DATOS POR FACULTAD
        # ----------------------------
        agrupado = (
            qs.values('persona__escuela__facultad','persona__escuela__facultad__nombre')
            .annotate(
                total_participantes=Count('id_participacion'),
                total_actividades=Count('actividad', distinct=True)
            )
            .order_by('-total_participantes')
        )

        data_list = []

        for item in agrupado:

            nombre = item['persona__escuela__facultad__nombre'] or "Sin Facultad"

            data_list.append({
                "id": item['persona__escuela__facultad'],
                "name": nombre,
                "actividades": item['total_actividades'],
                "participantes": item['total_participantes']
            })

        # ----------------------------
        # DISTRIBUCIÓN GLOBAL ESTAMENTO
        # ----------------------------
        total_personas = qs.values('persona').distinct().count()

        estamentos = (
            qs.values('persona__estamento')
            .annotate(total=Count('persona', distinct=True))
        )

        estamento_data = []

        for e in estamentos:

            cantidad = e['total']
            porcentaje = round((cantidad / total_personas) * 100, 2) if total_personas > 0 else 0

            estamento_data.append({
                "estamento": e['persona__estamento'] or "Sin estamento",
                "cantidad": cantidad,
                "porcentaje": porcentaje
            })

        return Response({
            "total_facultades": total_facultades,
            "filtro_aplicado": bool(start_date_raw and end_date_raw),
            "data": data_list,
            "estamento_global": estamento_data
        })
    
    # -------------------------------------------------------------------------
    # 11. DETALLE DINÁMICO: FACULTAD ESPECÍFICA
    # URL:
    # /api/dashboard-stats/detalle_facultad/?id=ID_FACULTAD&fecha_inicio=2026-01-01&fecha_fin=2026-12-31
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_facultad(self, request):

        facultad_id = request.query_params.get('id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        if not facultad_id:
            return Response({"error": "ID de facultad requerido"}, status=400)

        try:

            facultad = Facultad.objects.get(pk=facultad_id)

            participaciones = Participacion.objects.filter(
                persona__escuela__facultad=facultad
            )

            # 🔹 filtro por fechas
            if fecha_inicio and fecha_fin:
                participaciones = participaciones.filter(
                    fecha__range=[fecha_inicio, fecha_fin]
                )

            # ----------------------------
            # TOTAL PARTICIPANTES ÚNICOS
            # ----------------------------
            total_unicos = participaciones.values('persona').distinct().count()

            # ----------------------------
            # TOTAL ACTIVIDADES
            # ----------------------------
            total_actividades = participaciones.values('actividad').distinct().count()

            # ----------------------------
            # DISTRIBUCIÓN ESTAMENTO
            # ----------------------------
            conteo = (
                participaciones
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )

            estamentos_data = []

            for item in conteo:

                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                estamentos_data.append({
                    "estamento": item['persona__estamento'] or "Sin Estamento",
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })

            return Response({
                "id_facultad": facultad.id_facultad,
                "nombre": facultad.nombre,
                "total_actividades": total_actividades,
                "total_participantes": total_unicos,
                "estamento_participantes": estamentos_data
            })

        except Facultad.DoesNotExist:
            return Response({"error": "Facultad no encontrada"}, status=404)
    
    # -------------------------------------------------------------------------
    # 11. DETALLE DINÁMICO: ACTIVIDAD ESPECÍFICA
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

            conteo_por_estamento = (
                Participacion.objects
                .filter(actividad=actividad)
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )
            estamentos_data = []

            for item in conteo_por_estamento:
                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                if item['persona__estamento'] is None:
                    estamento_nombre = "Sin Estamento"
                else:                    
                    estamento_nombre = item['persona__estamento']  

                estamentos_data.append({
                    "estamento": estamento_nombre,
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })
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

                
            prioridad_nombre = "N/A"

            estrategia_nombre = "N/A"

            estrategia_rel = actividad.estrategiaasociada_set.first()
            if estrategia_rel and estrategia_rel.linea_estrategia:
                estrategia_nombre = estrategia_rel.linea_estrategia.nombre

            prioridad_rel = actividad.prioridadasociada_set.first()
            if prioridad_rel and prioridad_rel.prioridad:
                prioridad_nombre = prioridad_rel.prioridad.nombre

            return Response({
                "id_actividad": actividad.id_actividad,
                "nombre": actividad.nombre,
                "total_participantes": total_unicos,
                "prioridad": {
                    "nombre": prioridad_nombre
                },
                "estrategia": {
                    "nombre": estrategia_nombre
                },
                "temas_asociados": temas_data,
                "estamento_participantes": estamentos_data
            })

        except Actividad.DoesNotExist:
            return Response({"error": "Actividad no encontrada"}, status=404)
        
    # -------------------------------------------------------------------------
    # 12. ESTADÍSTICAS TEMPORALES (Gráficos)
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
    # 13. DETALLE DE RANGO TEMPORAL (Tarjeta de Detalles)
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

            total_unicos = (
            participaciones
            .values('persona')
            .distinct()
            .count()
            )

            conteo_por_estamento = (
                participaciones
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )

            estamentos_data = []

            for item in conteo_por_estamento:
                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                estamento_nombre = (
                    item['persona__estamento']
                    if item['persona__estamento'] is not None
                    else "Sin Estamento"
                )

                estamentos_data.append({
                    "estamento": estamento_nombre,
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })
            actividades_dict = {}
            total_p = 0
            
            for p in participaciones:
                act_id = p.actividad.id_actividad
                if act_id not in actividades_dict:
                    actividades_dict[act_id] = {
                        "id_actividad": act_id,
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
                "total_participantes": total_unicos,
                "estamento_participantes": estamentos_data,
                "listado": list(actividades_dict.values())
            })
        
        except (ValidationError, ValueError):
            return Response({"error": "Una de las fechas proporcionadas no existe en el calendario"}, status=400)
        
    # -------------------------------------------------------------------------
    # 14. DETALLE ACTIVIDAD POR RANGO DE TIEMPO (Tarjeta de Detalles)
    # -------------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def detalle_actividad_range(self, request):
        activity_id = request.query_params.get('id')
        inicio_raw = request.query_params.get('inicio')
        fin_raw = request.query_params.get('fin')

        if not activity_id:
            return Response({"error": "ID requerido"}, status=400)

        try:
            actividad = Actividad.objects.get(pk=activity_id)

            inicio = parse_date(inicio_raw) if inicio_raw else None
            fin = parse_date(fin_raw) if fin_raw else None

            participaciones = Participacion.objects.filter(actividad=actividad)

            if inicio and fin:
                participaciones = participaciones.filter(fecha__range=[inicio, fin])

            # A. Personas únicas
            total_unicos = (
                participaciones
                .values('persona')
                .distinct()
                .count()
            )

            conteo_por_estamento = (
                participaciones
                .values('persona__estamento')
                .annotate(total=Count('persona', distinct=True))
            )

            estamentos_data = []

            for item in conteo_por_estamento:
                cantidad = item['total']
                porcentaje = round((cantidad / total_unicos) * 100, 2) if total_unicos > 0 else 0

                estamento_nombre = (
                    item['persona__estamento']
                    if item['persona__estamento'] is not None
                    else "Sin Estamento"
                )

                estamentos_data.append({
                    "estamento": estamento_nombre,
                    "cantidad": cantidad,
                    "porcentaje": porcentaje
                })

            # B. Temas
            conteo_por_tema = (
                participaciones
                .values('tema__nombre')
                .annotate(total_participantes=Count('id_participacion'))
            )

            temas_data = []

            for item in conteo_por_tema:
                nombre_tema = item['tema__nombre'] if item['tema__nombre'] else "Asistencia General"

                temas_data.append({
                    "tema__nombre": nombre_tema,
                    "total_participantes": item['total_participantes']
                })

            return Response({
                "id_actividad": actividad.id_actividad,
                "nombre": actividad.nombre,
                "total_participantes": participaciones.count(),
                "total_participantes_unicos": total_unicos,
                "temas_asociados": temas_data,
                "estamento_participantes": estamentos_data,
            })

        except Actividad.DoesNotExist:
            return Response({"error": "Actividad no encontrada"}, status=404)

    # -------------------------------------------------------------------------
    # 14. DETALLES PERSONA (Resumen de actividades)
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def participaciones_persona(self, request, pk=None):

        try:
            persona = Persona.objects.select_related("escuela__facultad").get(pk=pk)

            # Actividades en las que participó
            actividades = (
                Participacion.objects
                .filter(persona=persona)
                .values(
                    "actividad__id_actividad",
                    "actividad__nombre"
                )
                .annotate(participaciones=Count("id_participacion"))
                .order_by("-participaciones")
            )

            # Participaciones por año
            participaciones_anio = (
                Participacion.objects
                .filter(persona=persona)
                .values("anio")
                .annotate(total=Count("id_participacion"))
                .order_by("anio")
            )

            total = Participacion.objects.filter(persona=persona).count()

            data = {
                "persona": persona.nombre,
                "estamento": persona.estamento,
                "escuela": persona.escuela.nombre if persona.escuela else None,
                "facultad": persona.escuela.facultad.nombre if persona.escuela and persona.escuela.facultad else None,
                "total_participaciones": total,
                "actividades": list(actividades),
                "participaciones_por_anio": list(participaciones_anio)
            }

            return Response(data)

        except Persona.DoesNotExist:
            return Response({"error": "Persona no encontrada"}, status=404)

# ------------------------------------------
# CRUD ViewSets
# ------------------------------------------

class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

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

class AccionViewSet(viewsets.ModelViewSet):
    queryset = Accion.objects.all()
    serializer_class = AccionSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def actividades(self, request, pk=None):
        actividades = Actividad.objects.filter(
            actividadasociada__accion_id=pk
        ).values('id_actividad', 'nombre').distinct()

        return Response(list(actividades))

class ParticipacionViewSet(viewsets.ModelViewSet):
    queryset = Participacion.objects.all()
    serializer_class = ParticipacionSerializer


# --------------------------------------------------------
# ACTIVIDAD VIEWSET (MODIFICADO PARA CREACIÓN CONJUNTA)
# --------------------------------------------------------
class ActividadViewSet(viewsets.ModelViewSet):
    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend] # Agregamos el backend de filtros
    search_fields = ['nombre']
    # Definimos por qué campos se puede filtrar exactamente
    filterset_fields = {
        'actividadasociada__accion_id': ['exact'], # Esto permite filtrar por el ID del padre
    }

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def temas(self, request, pk=None):
        temas = Tema.objects.filter(
            temaasociado__actividad_id=pk
        ).values('id_tema', 'nombre').distinct()

        return Response(list(temas))
        
# --------------------------------------------------------
# TEMA VIEWSET (MODIFICADO PARA CREACIÓN CONJUNTA)
# --------------------------------------------------------
class TemaViewSet(viewsets.ModelViewSet):
    queryset = Tema.objects.all()
    serializer_class = TemaSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre']
    filterset_fields = {
        'temaasociado__actividad_id': ['exact'], # Filtro exacto por ID de actividad
    }


class TemaAsociadoViewSet(viewsets.ModelViewSet):
    queryset = TemaAsociado.objects.all()
    serializer_class = TemaAsociadoSerializer

class EstrategiaViewSet(viewsets.ModelViewSet):
    queryset = Estrategia.objects.all()
    serializer_class = EstrategiaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nombre_original']

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
