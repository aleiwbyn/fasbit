# fasbit — Control de entregas

Aplicación para registrar a qué hora llegan las empresas proveedoras, comprobar si cumplieron el horario acordado, decidir qué hacer con cada entrega y calcular las multas en soles (`S/`).

## Requisitos e inicio rápido

- **Python 3.11** o superior.

```powershell
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar la aplicación
python src/fasbit/__main__.py
```

- También puedes abrir `src/fasbit/__main__.py` en VS Code y presionar el botón ▶ **Run**.
- Si `pip` no está en el `PATH`, ejecuta `python -m pip install -r requirements.txt`.
- Una vez iniciada, abre en el navegador: **http://127.0.0.1:5000**

## Cuentas de prueba

| Usuario | Contraseña | Tipo de cuenta | Estado inicial | Qué puede hacer |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | Administrador | Activo | Ver entregas, registrar llegadas, eliminar entregas y gestionar usuarios |
| `operador` | `operador123` | Operador | Activo | Ver entregas, filtrar, buscar y registrar o probar llegadas |
| `operador2` | `lucia123` | Operador | Inactivo | Cuenta desactivada para probar bloqueo de acceso |

## Acotaciones relevantes

- **Uso sin internet:** una vez instaladas las dependencias, toda la aplicación funciona de forma local sin conexión.
- **Datos iniciales incluidos:** trae 10 entregas precargadas de empresas peruanas reales (`Alicorp S.A.A.`, `Leche Gloria S.A.`, `San Fernando S.A.`, `Trupal S.A.`, `Química Suiza S.A.C.` y `Molitalia S.A.`).
- **Cambios guardados:** las llegadas, entregas nuevas y cuentas que registres se conservan aunque reinicies la aplicación.
- **Probar sin guardar:** permite ver el estado, la decisión y el monto de multa de una entrega antes de guardar cambios.
- **Puerto ocupado:** si el puerto `5000` ya está en uso, puedes definir la variable de entorno `FASBIT_PORT` con otro número antes de iniciar.
- **Pruebas del sistema:** si deseas verificar que todo funcione correctamente, ejecuta `pytest -v`.
