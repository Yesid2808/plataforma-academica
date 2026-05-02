# Configuracion de correo para reportes

El modulo de reportes ya permite enviar correos reales a los acudientes. Para que funcione fuera de consola, configura SMTP en el archivo `.env`.

## Opcion recomendada para empezar: Gmail

1. Activa verificacion en dos pasos en la cuenta de Gmail.
2. Genera una clave de aplicacion de 16 caracteres.
3. Usa estos valores en `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_clave_de_aplicacion
EMAIL_TIMEOUT=30
DEFAULT_FROM_EMAIL=Plataforma Academica <tu_correo@gmail.com>
```

## Opcion profesional para produccion

Si quieres mejorar entregabilidad y evitar bloqueos por politicas de Gmail, conviene usar un proveedor SMTP transaccional como Brevo o SendGrid. En ese caso cambian `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` segun el proveedor.

## Como validar desde la app

1. Inicia el servidor.
2. Entra al modulo `Reportes`.
3. Usa el boton `Probar conexion SMTP`.
4. Si todo esta correcto, el sistema mostrara un mensaje de conexion exitosa.

## Verificaciones importantes

- `DEFAULT_FROM_EMAIL` debe coincidir con una direccion valida del remitente.
- Los estudiantes deben tener `correo_acudiente` diligenciado.
- Si el correo falla, el historial del modulo guardara el error.

## Reinicio recomendado

Despues de cambiar `.env`, reinicia el servidor Django para que cargue la nueva configuracion.
