from django.urls import path, include # <--- 1. NECESITAS IMPORTAR ESTO
from rest_framework.routers import DefaultRouter
# 1. IMPORTAR LAS VISTAS DE JWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    DashboardViewSet, UnidadOrganizativaViewSet, VinculacionViewSet,
    SedeViewSet, PersonaViewSet, AccionViewSet,
    ParticipacionViewSet, ActividadViewSet, SeccionViewSet,
    PrioridadViewSet, PrioridadAsociadaViewSet,
    LineaEstrategiaViewSet, EstrategiaAsociadaViewSet,EstrategiaViewSet
)

router = DefaultRouter()

router.register(r'sedes', SedeViewSet)
router.register(r'personas', PersonaViewSet)
router.register(r'unidades-organizativas', UnidadOrganizativaViewSet)
router.register(r'vinculaciones', VinculacionViewSet)
router.register(r'acciones', AccionViewSet)
router.register(r'participaciones', ParticipacionViewSet)
router.register(r'actividades', ActividadViewSet )
router.register(r'secciones', SeccionViewSet)
router.register(r'estrategia', EstrategiaViewSet)
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