# Actualizar SakbeLab

El mismo comando que instala SakbeLab también lo actualiza. Conserva tus labs, imágenes y plantillas.

1. Entrá a la VM como root, por consola o por SSH.
2. Ejecutá:

```bash
curl -fsSL https://raw.githubusercontent.com/SakbeLab/sakbelab/main/tools/install.sh | bash
```

3. En el navegador, recargá la página forzando la caché: `Ctrl + F5` (o `Cmd + Shift + R` en Mac).

El instalador descarga la última versión, actualiza las plantillas incluidas (sin tocar la imagen que hayas elegido en cada una) y reinicia el servicio. Los equipos encendidos se apagan durante la actualización: guardá antes sus configuraciones si las necesitás.

Para ver qué versión tenés, abrí `http://<ip>/api/v1/health`.
