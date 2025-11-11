from rest_framework.routers import DefaultRouter
from .views import (
    SedeViewSet, LineaProyectoViewSet, FacultadViewSet, EscuelaViewSet,
    PersonaViewSet, EstudianteViewSet, IndicadorViewSet, ActividadViewSet,
    AsociacionProyectoViewSet, ParticipacionViewSet, LugarViewSet,
    ActividadConsolidadaViewSet, ConsolidacionViewSet, TemaViewSet,
    TemaAsociadoViewSet, PrioridadViewSet, PrioridadAsociadaViewSet,
    LineaEstrategiaViewSet, EstrategiaAsociadaViewSet
)

router = DefaultRouter()

router.register(r'sedes', SedeViewSet)
router.register(r'lineas-proyecto', LineaProyectoViewSet)
router.register(r'facultades', FacultadViewSet)
router.register(r'escuelas', EscuelaViewSet)
router.register(r'personas', PersonaViewSet)
router.register(r'estudiantes', EstudianteViewSet)
router.register(r'indicadores', IndicadorViewSet)
router.register(r'actividades', ActividadViewSet)
router.register(r'asociaciones-proyecto', AsociacionProyectoViewSet)
router.register(r'participaciones', ParticipacionViewSet)
router.register(r'lugares', LugarViewSet)
router.register(r'actividades-consolidadas', ActividadConsolidadaViewSet)
router.register(r'consolidaciones', ConsolidacionViewSet)
router.register(r'temas', TemaViewSet)
router.register(r'temas-asociados', TemaAsociadoViewSet)
router.register(r'prioridades', PrioridadViewSet)
router.register(r'prioridades-asociadas', PrioridadAsociadaViewSet)
router.register(r'lineas-estrategia', LineaEstrategiaViewSet)
router.register(r'estrategias-asociadas', EstrategiaAsociadaViewSet)

urlpatterns = router.urls
