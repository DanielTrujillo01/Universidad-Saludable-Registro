from django.urls import path, include # <--- 1. NECESITAS IMPORTAR ESTO
from rest_framework.routers import DefaultRouter
# 1. IMPORTAR LAS VISTAS DE JWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    DashboardViewSet, # <--- 2. IMPORTA TU NUEVA VISTA AQUÍ
    SedeViewSet, LineaProyectoViewSet, FacultadViewSet, EscuelaViewSet,
    PersonaViewSet, EstudianteViewSet, IndicadorViewSet, ActividadViewSet,
    AsociacionProyectoViewSet, ParticipacionViewSet, LugarViewSet,
    ActividadConsolidadaViewSet, ConsolidacionViewSet, TemaViewSet,
    TemaAsociadoViewSet, PrioridadViewSet, PrioridadAsociadaViewSet,
    LineaEstrategiaViewSet, EstrategiaAsociadaViewSet
)

router = DefaultRouter()

# ... tus registros existentes ...
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
router.register(r'dashboard-stats', DashboardViewSet, basename='dashboard-stats')

urlpatterns = [
    # En esta ruta envías {username, password} y recibes {access, refresh}
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # En esta ruta envías {refresh} y recibes un nuevo {access}
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Rutas automáticas del Router (CRUDs)
    path('', include(router.urls)),
]