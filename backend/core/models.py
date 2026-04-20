from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# -------------------------
# Sede
# -------------------------
class Sede(models.Model):
    id_sede = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300,unique=True)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre
    

# -------------------------
# Unidad Organizativa (Facultad, Escuela, Dependencia Administrativa)
# -------------------------
class UnidadOrganizativa(models.Model):
    TIPO_CHOICES = [
        ('FACULTAD', 'Facultad'),
        ('ESCUELA', 'Escuela'),
        ('DEPENDENCIA', 'Dependencia Administrativa'),
    ]

    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    padre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subunidades'
    )

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Unidad Organizativa"
        verbose_name_plural = "Unidades Organizativas"

# -------------------------
# Persona y Estudiante (herencia)
# -------------------------
class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)

    # Valores normalizados
    nombre = models.CharField(max_length=300, null=True, blank=False)
    tipo_documento = models.CharField(max_length=100, null=True, blank=True)

    # Valores originales
    nombre_original = models.CharField(max_length=300, null=False, blank=False)
    tipo_documento_original = models.CharField(max_length=150, null=True, blank=True)

    numero_documento = models.PositiveBigIntegerField(
        validators=[MinValueValidator(100000), MaxValueValidator(9999999999)],
        unique=True,
        null=True,
        blank=True,
    )
    edad = models.PositiveIntegerField(null=True, blank=True)
    correo = models.EmailField(null=True, blank=True, unique=True)
    sexo = models.CharField(max_length=20, null=True, blank=False)
    unidadOrganizativa = models.ForeignKey(
        UnidadOrganizativa, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.nombre

class Vinculacion(models.Model):
    id_vinculacion = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(Persona, on_delete=models.CASCADE,null=False, blank=False)
    id_unidad_organizativa = models.ForeignKey(UnidadOrganizativa, on_delete=models.CASCADE,null=False, blank=False)
    tipo_estamento = models.CharField(max_length=100, null=True, blank=True)
    estado = models.BooleanField(default=True) 
    semestre = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.id_persona} - {self.tipo_estamento}"

# -------------------------
# Estrategia 
# -------------------------
class Estrategia(models.Model):
    id_estrategia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre
    
# -------------------------
# Acción 
# -------------------------
class Accion(models.Model):
    id_accion = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    estrategia = models.ForeignKey(
        Estrategia, on_delete=models.CASCADE,null=False, blank=False
)

    def __str__(self):
        return self.nombre

# -------------------------
# Actividad 
# -------------------------
class Actividad(models.Model):
    id_actividad = models.AutoField(primary_key=True)
    id_accion = models.ForeignKey(Accion, on_delete=models.CASCADE,null=False,blank=False)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre
    

# -------------------------
# Seccion
# -------------------------
class Seccion(models.Model):
    id_seccion = models.AutoField(primary_key=True)
    id_actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE,null=False,blank=False)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre
    
# -------------------------
# Participación (intermedia entre Persona y Actividad)
# -------------------------
class Participacion(models.Model):
    id_participacion = models.AutoField(primary_key=True)

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    vinculacion = models.ForeignKey(Vinculacion, on_delete=models.SET_NULL, null=True, blank=True)

    semestre = models.IntegerField(null=True, blank=True)

    accion = models.ForeignKey(Accion, on_delete=models.CASCADE)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.SET_NULL, null=True, blank=True)

    fecha = models.DateField()
    anio = models.PositiveIntegerField()

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.vinculacion and self.vinculacion.semestre:
            self.semestre = self.vinculacion.semestre
        
        super(Participacion, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.persona} - {self.actividad}"

# -------------------------
# Prioridad y Prioridad Asociada
# -------------------------
class Prioridad(models.Model):
    id_prioridad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre


class PrioridadAsociada(models.Model):
    id_prioridad_asociada = models.AutoField(primary_key=True)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE,null=False,blank=False)
    prioridad = models.ForeignKey(Prioridad, on_delete=models.CASCADE,null=False,blank=False)

    def __str__(self):
        return f"PrioridadAsociada {self.id_prioridad_asociada}"


# -------------------------
# Línea de Estrategia y Estrategia Asociada
# -------------------------
class LineaEstrategia(models.Model):
    id_linea_estrategia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return self.nombre


class EstrategiaAsociada(models.Model):
    id_estrategia_asociada = models.AutoField(primary_key=True)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE,null=False,blank=False)
    linea_estrategia = models.ForeignKey(LineaEstrategia, on_delete=models.CASCADE,null=False,blank=False)

    def __str__(self):
        return f"EstrategiaAsociada {self.id_estrategia_asociada}"