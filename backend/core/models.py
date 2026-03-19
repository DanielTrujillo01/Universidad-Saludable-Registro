from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# -------------------------
# Sede
# -------------------------
class Sede(models.Model):
    id_sede = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300,unique=True)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


# -------------------------
# Línea de proyecto
# -------------------------
class LineaProyecto(models.Model):
    id_linea_proyecto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300,)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


# -------------------------
# Facultad y Escuela
# -------------------------
class Facultad(models.Model):
    id_facultad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


class Escuela(models.Model):
    id_escuela = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)
    facultad = models.ForeignKey(
        Facultad, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return self.nombre


# -------------------------
# Persona y Estudiante (herencia)
# -------------------------
class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)

    # Valores normalizados
    nombre = models.CharField(max_length=300, null=True, blank=False)
    tipo_documento = models.CharField(max_length=100, null=True, blank=True)

    # Valores originales
    nombre_original = models.CharField(max_length=300, null=True, blank=True)
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
    telefono = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)],
        null=True,
        blank=True
    )
    estamento = models.CharField(max_length=50, null=True, blank=False)
    escuela = models.ForeignKey(
        Escuela, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.nombre


class Estudiante(Persona):
    semestre = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Estudiante: {self.nombre}"


# -------------------------
# Indicador
# -------------------------
class Indicador(models.Model):
    id_indicador = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


# -------------------------
# Estrategia 
# -------------------------
class Estrategia(models.Model):
    id_estrategia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)

    def __str__(self):
        return self.nombre
    
# -------------------------
# Acción 
# -------------------------
class Accion(models.Model):
    id_accion = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    indicador = models.ForeignKey(
        Indicador, on_delete=models.SET_NULL, null=True, blank=True
    )

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
    nombre = models.CharField(max_length=300)

    def __str__(self):
        return self.nombre
    

# -------------------------
# Actividad asociada 
# -------------------------
class ActividadAsociada(models.Model):
    id_actividad_asociada = models.AutoField(primary_key=True)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE,null=False,blank=False)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE,null=False,blank=False)

    def __str__(self):
        return f"ActividadAsociada {self.id_actividad_asociada}"
    
# -------------------------
# Tema
# -------------------------
class Tema(models.Model):
    id_tema = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)

    def __str__(self):
        return self.nombre
    
# -------------------------
# Tema asociado 
# -------------------------
class TemaAsociado(models.Model):
    id_tema_asociado = models.AutoField(primary_key=True)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE,null=False,blank=False)
    tema = models.ForeignKey(Tema, on_delete=models.CASCADE,null=False,blank=False)

    def __str__(self):
        return f"TemaAsociado {self.id_tema_asociado}"
    

# -------------------------
# Asociación Proyecto 
# -------------------------
class AsociacionProyecto(models.Model):
    id_asociacion_proyecto = models.AutoField(primary_key=True)
    accion = models.ForeignKey(
    Accion,
    on_delete=models.CASCADE,
    null=False,
    blank=False
    )
    linea_proyecto = models.ForeignKey(
    LineaProyecto,
    on_delete=models.CASCADE,
    null=False,
    blank=False
    )


    def __str__(self):
        return f"Asociación {self.id_asociacion_proyecto}"


# -------------------------
# Participación (intermedia entre Persona y Actividad)
# -------------------------
class Participacion(models.Model):
    id_participacion = models.AutoField(primary_key=True)

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)

    accion = models.ForeignKey(Accion, on_delete=models.CASCADE)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE)
    tema = models.ForeignKey(Tema, on_delete=models.SET_NULL, null=True, blank=True)

    fecha = models.DateField()
    anio = models.PositiveIntegerField()

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.persona} - {self.actividad}"


# -------------------------
# Actividad Consolidada
# -------------------------
class ActividadConsolidada(models.Model):
    id_actividad_consolidada = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


class Consolidacion(models.Model):
    id_consolidacion = models.AutoField(primary_key=True)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE)
    actividad_consolidada = models.ForeignKey(
        ActividadConsolidada, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Consolidación {self.id_consolidacion}"


# -------------------------
# Prioridad y Prioridad Asociada
# -------------------------
class Prioridad(models.Model):
    id_prioridad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=300)
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

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
    nombre_original = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.nombre


class EstrategiaAsociada(models.Model):
    id_estrategia_asociada = models.AutoField(primary_key=True)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE,null=False,blank=False)
    linea_estrategia = models.ForeignKey(LineaEstrategia, on_delete=models.CASCADE,null=False,blank=False)

    def __str__(self):
        return f"EstrategiaAsociada {self.id_estrategia_asociada}"