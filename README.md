# 💱 ForexManager

Sistema de gestión para casas de cambio de divisas, desarrollado para **Odoo v18.0**.

---

## 🧩 REQUERIMIENTOS

- **Odoo v18.0**
- **PostgreSQL**

---

## ⚙️ PROCESO DE INSTALACIÓN

1. Copia la carpeta del módulo **ForexManager** en la carpeta `odoo/custom_addons`.
2. Ve al menú **Apps / Apps** y busca **ForexManager** para instalarlo.
3. Activa el **modo desarrollador**:
   - Dirígete a `Apps / Settings / Users & Companies / Groups`.
   - Si no ves el submenú *Groups*, añade `?debug=1` al final de la URL y presiona **Enter**.
4. En el submenú **Groups**, busca *Forex Manager*:
   - **Admin** → acceso total, incluyendo configuración del módulo.
   - **Users** → acceso limitado, solo para la operativa diaria.
5. Entra en cada grupo y, en la pestaña **Users**, haz clic en *Add a line* para añadir los usuarios correspondientes.
6. Refresca la página. Si no ves el menú **ForexManager**, vuelve a *Apps*, busca **ForexManager** y haz clic en **Actualizar**.
7. ✅ ¡Listo! El módulo quedará instalado y visible en el panel principal.

---

## 👥 GRUPOS DE SEGURIDAD

- **Forex Manager Admin** → Acceso completo
- **Forex Manager Users** → Acceso limitado

---

## 🛠️ PROCESO DE CONFIGURACIÓN

1. Con un usuario del grupo **Admin**, entra al menú **CONFIGURACIÓN** y sigue estos pasos:

### 🔸 Administrar Divisas
Crea las divisas que tu empresa de cambio va a manejar.
- En el desglose de **Billetes y Monedas**, define las denominaciones aceptadas (valor, tipo e imágenes).
- En **Centros que utilizan esta moneda**, puedes asignar los centros de trabajo correspondientes.

### 🔸 Administrar Centros de Trabajo
Crea los centros de trabajo.  
Cada centro tendrá sus divisas aceptadas y ventanillas asociadas.  
Al añadir una nueva divisa, se genera automáticamente su inventario correspondiente.

### 🔸 Administrar Ventanillas
Crea las ventanillas vinculadas a un centro de trabajo.
- Define un **código único** de vinculación (usado por los empleados al iniciar sesión).
- Se crearán automáticamente inventarios iniciales para cada divisa aceptada.

Hasta aquí llega el **Proceso de Configuración Inicial**.  
El resto de menús se explican a continuación.

---

## 💼 FLUJO DE TRABAJO

### 👤 Usuarios con acceso limitado (Grupo: Users)

1. **Vincular ventanilla**
   - Sube un archivo `.txt` con el código de vinculación proporcionado por el administrador.
   - Si cambias de ventanilla, repite el proceso desde el nuevo ordenador.

2. **Iniciar sesión / Arqueo**
   - Dirígete al menú **Sesión / Arqueo**.
   - En tu primera sesión, completa el arqueo de divisas para poder operar.

3. **Realizar operación**
   - Accede al menú **Realizar Operación**.
   - Añade una línea de cambio (ejemplo: 100 EUR a USD).  
     El sistema calculará el equivalente y ajustará los importes según los billetes disponibles.
   - Escanea el documento del cliente, guárdalo localmente y súbelo al sistema.
   - Pulsa **Leer Datos** para intentar obtener automáticamente la información del documento.

4. **Traspasos**
   - Desde el menú **Traspasos**, puedes transferir fondos entre ventanillas.
   - Solo podrás emitir traspasos si tu sesión está abierta y el arqueo completado.
   - El traspaso puede:
     - **Cancelarse** si el destinatario no lo ha recibido.
     - **Rechazarse** por el destinatario (en cuyo caso un admin deberá reasignarlo).

5. **Mi historial**
   - Aquí podrás ver tus operaciones realizadas durante la sesión actual.
   - No se puede modificar nada.

### 👤 Usuarios con acceso ilimitado (Grupo: Admin)

1. **Administrar inventarios**
   - Solo visualización o eliminación (solo si el balance es **0.00**).

2. **Administrar arqueos**
   - Los arqueos se crean automáticamente.
   - Los admins pueden añadir notas y cerrarlos en caso de diferencias.

3. **Administrar traspasos**
   - Solo los admins pueden modificar traspasos no recibidos.

4. **Historial de operaciones**
   - Permite consultar todas las operaciones (solo lectura).

---

## 🧑‍💻 PARA DESARROLLADORES

   - Para cambiar el margen comercial, ve al modelo Calculation, y cambia el valor de la variable MARGIN (por defecto 1.4)
   - Para cambiar la divisa base, ve a los modelos Calculation y Currency (debes hacerlo en ambos), y en la variable currency_base_id cambia el valor de default con el ID de la divisa, por defecto 125. Para saber el ID de la divisa, consulta en PostreSQL utilizando: SELECT * FROM res_currency y sustituye "default" con el valor deseado de la columna ID.

### ⚠️ Limitaciones actuales

   - La **vinculación de ventanilla** se realiza manualmente mediante un archivo `.txt`.
   - El **escaneo de documentos** se hace fuera de Odoo; el archivo debe subirse manualmente.
   - La **API gratuita** usada para tipos de cambio admite principalmente divisas europeas y norteamericanas.
   - Para ampliarla, modifica `get_base_rate()` en `utils.py` usando otra API.
   - La **lectura automática de pasaportes/DNI** está en fase experimental.  
   - Si deseas mejorarla, revisa `operation.py` → método `get_passport_info()`.

---

## 🧾 NOTAS FINALES

   - ForexManager está pensado para entornos de casas de cambio pequeñas o medianas.
   - Requiere que **Odoo** y **PostgreSQL** estén correctamente instalados y configurados.
   - Para dudas o mejoras, consulta el código fuente dentro de cada módulo (`models`, `views`, `security`).

---

💡 *Desarrollado con cariño y mucho café, para optimizar la gestión de divisas.*
