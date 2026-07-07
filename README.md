# Driftmoon Sleep 🌙 — canal de sueño automatizado

- **Canal:** Driftmoon Sleep · handle `@driftmoonsleep` (verificado libre el 2026-07-07)
- **Email del proyecto:** `driftmoonsleep@gmail.com` (créalo como cuenta Google nueva)
- **Tagline:** Rain · Ocean · Deep-Sleep Soundscapes

Genera vídeos de sonidos para dormir (audio procedural + imagen única +
metadata variada), los renderiza y los sube a YouTube. Todo corre en
GitHub Actions: **nada en local, coste 0 €/mes**.

```
audio procedural (numpy/scipy) ─┐
imagen nocturna única (PIL)     ├─→ ffmpeg → vídeo 3-10 h → YouTube API
títulos/tags con variación      ─┘         (cron diario en GitHub Actions)
```

---

## Puesta en marcha (una sola vez, ~45-60 min)

### Paso 0 — Cuenta Google del proyecto (5 min)
Crea una cuenta Google nueva: `driftmoonsleep@gmail.com` (si está pillado,
variantes: `driftmoonsleep.yt`, `driftmoon.sleep`). Separa el proyecto de tu
cuenta personal: si algún día vendes el canal, se transfiere entero.

### Paso 1 — Canal de YouTube (5 min)
1. Entra en youtube.com con esa cuenta → icono de perfil → **Crear canal**.
   Nombre: **Driftmoon Sleep** · handle: **@driftmoonsleep**.
2. Verifica la cuenta por teléfono en **youtube.com/verify** (necesario para
   miniaturas personalizadas y vídeos >15 min). Sin esto el pipeline falla.
3. Branding: ejecuta el workflow **"Generar branding"** (pestaña Actions, tras
   el paso 2) y descarga el zip `branding-driftmoon-sleep`: avatar, banner,
   watermark, 3 miniaturas de ejemplo y el texto para la pestaña "Información".
   Súbelos en YouTube Studio → Personalización. El banner tiene el contenido
   dentro de la zona segura (se ve bien en móvil, TV y escritorio).

### Paso 2 — Cuenta GitHub y repositorio (10 min)
1. Crea cuenta en github.com.
2. **New repository** → nombre `sleep-channel` → **Public** (minutos de Actions
   ilimitados; en privado el límite gratis es 2.000 min/mes y este pipeline usa ~600-900).
3. Sube esta carpeta: en el repo vacío → *uploading an existing file* → arrastra
   TODOS los archivos (incluida la carpeta `.github`, ver nota abajo)*.
4. Crea un token: Settings (tu perfil) → Developer settings → Personal access
   tokens → **Fine-grained** → solo este repo, permiso **Secrets: Read and write**
   y **Actions: Read and write**. Guárdalo para el paso 4.

\* La web de GitHub no sube carpetas ocultas por arrastre: crea el archivo
`.github/workflows/daily.yml` con *Add file → Create new file* (escribiendo la
ruta completa) y pega el contenido; igual con `authorize.yml`. O pídemelo y lo
subo yo por API con tu token.

### Paso 3 — Google Cloud + credenciales OAuth (15 min)
1. console.cloud.google.com → acepta términos → **Create project** (nombre libre).
2. Menú → **APIs & Services → Library** → busca **YouTube Data API v3** → Enable.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External** → rellena nombre de app y tu email (lo mínimo).
   - Scopes: no hace falta añadir ninguno aquí.
   - **IMPORTANTE:** al terminar, pulsa **Publish app** (estado *In production*).
     Si lo dejas en *Testing*, el token caduca cada 7 días y el pipeline morirá.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **TVs and Limited Input devices** (imprescindible: es lo
     que permite autorizar sin ordenador local).
   - Copia el **Client ID** y el **Client Secret**.

### Paso 4 — Secrets del repositorio (5 min)
En el repo: Settings → Secrets and variables → Actions → **New repository secret**:

| Nombre             | Valor                                  |
|--------------------|----------------------------------------|
| `YT_CLIENT_ID`     | Client ID del paso 3                   |
| `YT_CLIENT_SECRET` | Client Secret del paso 3               |
| `GH_PAT`           | Token fine-grained del paso 2          |

### Paso 5 — Autorizar el canal (5 min)
1. Pestaña **Actions** → workflow **"Autorizar canal de YouTube"** → Run workflow.
2. Abre el log del job: verás una URL (google.com/device) y un código.
3. Ábrela en el móvil, mete el código, elige el canal y acepta.
4. El workflow guarda solo el `YT_REFRESH_TOKEN` como secret. Listo.

### Paso 6 — Primera prueba
Actions → **"Vídeo diario"** → Run workflow (deja `skip_upload = 0`).
En ~20-40 min tendrás el primer vídeo en YouTube Studio, **en privado** (ver abajo).
A partir de ahí, corre solo cada día a las 19:00.

---

## La auditoría de la API (el único peaje real)

Política de YouTube: los vídeos subidos por API desde proyectos no auditados
quedan **bloqueados en privado**. Dos fases:

- **Mientras tanto:** el pipeline sube todo en privado; publicar = abrir YouTube
  Studio (app del móvil) → vídeo → visibilidad → Público. 2 clics al día.
- **Solución definitiva:** rellena el formulario de auditoría (gratuito):
  https://support.google.com/youtube/contact/yt_api_form
  Di la verdad: herramienta de uso personal para subir vídeos originales a tu
  propio canal, sin terceros. Suelen tardar de días a semanas.
  Cuando te aprueben, cambia `privacy_status: public` en `config.yaml`.

## Riesgos que ya conoces (resumen honesto)

- **Monetización:** requiere 1.000 suscriptores + 4.000 h de visionado público
  en 12 meses. Meses de ingresos cero, sin garantía.
- **Política "contenido inauténtico" (jul 2025):** contenido en masa con mínima
  variación puede perder la monetización de todo el canal. Mitigación integrada:
  audio, imagen, título y descripción únicos por vídeo, divulgación de contenido
  sintético activada (`containsSyntheticMedia`) y declarada en la descripción.
  Riesgo residual real: existe.
- **Cuota API:** la subida diaria consume una fracción mínima de la cuota gratuita.

## Operación

Nada. Cron a las 17:00 UTC los domingos, lunes, miércoles y viernes
(**mes 1: 4 vídeos/semana** — un canal nuevo subiendo a diario dispara la señal
de "cadencia anormal" del detector de contenido en masa). **En el mes 2**, si no
hay flags, cambia el cron a `"0 17 * * *"` (diario). Manualmente: Actions →
Vídeo diario → Run workflow (puedes forzar `theme` y `hours`).

## Decisiones tomadas por estudio de nicho (2026-07-07)

- **Pantalla negra al minuto 10** (`black_screen_minutes`): formato estándar
  del nicho; se anuncia en el título ("Black Screen") y en los capítulos.
- **Capítulos en descripción**: ≥3 marcas de tiempo → señal de estructura
  frente al detector de contenido inauténtico.
- **3 layouts de miniatura rotativos + marca del canal**: miniaturas casi
  idénticas son señal de flag; referentes (Cozy Rain, Nightpour) marcan branding.
- **Micro-nicho**: escena concreta por vídeo (lluvia en ventana, olas...), no
  "relaxing sounds" genérico. Los canales referencia facturan ~2-5k$/mes tras
  años de catálogo; expectativa realista primer mes: cientos de vistas.

## Ajustes rápidos

- Idioma de títulos/desc: `language` en `config.yaml` (en/es).
- Temas y duraciones: listas `themes` y `hours_pool`.
- Pantalla negra: `black_screen_minutes` (0 = desactivada).
- Hora/frecuencia de publicación: `cron` en `.github/workflows/daily.yml` (UTC).
