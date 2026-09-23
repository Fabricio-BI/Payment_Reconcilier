# Análisis detallado de novedades

[← Volver al README principal](Readme.md)

Detalle completo de las 3 novedades que detecta el Conciliador de Pasarelas de Pago: qué significa cada una, por qué ocurre, su impacto contable, y cómo el contador la resuelve en la práctica.

---

## Novedad 1 — Comisiones cobradas de más por la pasarela

**Qué significa**

La pasarela cobró un porcentaje de comisión mayor al acordado en el contrato. Por ejemplo, el contrato con Datafast establece una tasa del 3.5%, pero en 45 transacciones cobró entre 4.0% y 5.0%.

**Por qué ocurre**

Las pasarelas aplican tarifas distintas según el tipo de tarjeta, el país de emisión o la categoría del comercio. Cuando el sistema clasifica incorrectamente una transacción, aplica una tarifa más alta. Sin un sistema de verificación, ese sobrecargo pasa desapercibido.

**El impacto económico**

En el período analizado las pasarelas cobraron $100.70 más de lo estipulado en los contratos. Este monto es completamente recuperable mediante un reclamo formal.

**Cómo lo resuelve el contador**

El reporte muestra por cada transacción el monto de la factura, la comisión que debía cobrarse según contrato, la comisión que se cobró realmente y la diferencia a reclamar.

Con esa información el contador:

1. Agrupa las diferencias por pasarela para obtener el total a reclamar a cada una.
2. Genera una carta de reclamo formal con el detalle de cada transacción afectada, la referencia del contrato y el monto total a devolver.
3. Una vez que la pasarela procesa la devolución, registra el ajuste contable correspondiente.

---

## Novedad 2 — Chargebacks no registrados en el ERP

**Qué es un chargeback**

Un chargeback ocurre cuando un cliente disputa un cobro con su banco. El cliente llama a su banco — el banco emisor — y dice "no reconozco este cargo" o "el producto nunca llegó". El banco emisor investiga y, si considera válida la disputa, devuelve el dinero al cliente y se lo descuenta al comercio.

Este proceso es completamente automático y unilateral — el banco no pide autorización al comercio. Simplemente revierte el depósito y lo notifica después mediante el reporte de liquidación, donde la transacción aparece con un monto negativo.

**Cómo se modela en este proyecto**

A diferencia de una simplificación ingenua (donde la venta original simplemente "desaparecería"), el generador de datos simula el escenario real: la venta ocurre y se factura con normalidad, y entre 15 y 45 días después llega la reversión como una transacción nueva e independiente en el reporte bancario — vinculada a la venta original mediante un identificador de referencia. Esto permite que el sistema recupere automáticamente el cliente y el monto de la factura original, exactamente como lo haría un contador al investigar el caso.

**El problema**

El banco revirtió 24 transacciones por un total de $5,060.69. Esas reversiones aparecen en el reporte bancario como montos negativos. Sin embargo, el ERP nunca fue actualizado — las facturas correspondientes siguen marcadas como pagadas.

Esto significa que el sistema contable muestra $5,060.69 en ingresos que en realidad ya no existen en la cuenta bancaria.

**El impacto contable**

Si este error no se corrige antes del cierre contable, el estado de resultados está inflado en $5,060.69. La empresa cree que cobró ese dinero cuando en realidad ya fue devuelto al cliente.

**Cómo lo resuelve el contador**

El reporte muestra cada chargeback con su fecha, cliente, pasarela y monto revertido — recuperado automáticamente desde la factura original mediante el cruce por identificador de transacción.

Con esa información el contador:

1. Localiza cada factura en el ERP usando el código de transacción.
2. Registra una nota de crédito o asiento de reversión para anular el ingreso contabilizado.
3. Verifica si el chargeback puede ser disputado — el comercio tiene un plazo definido para presentar evidencia ante la pasarela y recuperar el dinero si el cobro era legítimo.
4. Si el plazo venció o la disputa no procede, registra la pérdida definitiva.

---

## Novedad 3 — Transacciones sin confirmar en la pasarela

**Qué significa**

Son 30 transacciones que el banco liquidó y el ERP registró correctamente — los montos cuadran — pero que no aparecen en el reporte de la pasarela.

A diferencia de los dos casos anteriores, aquí no hay una diferencia de dinero. El problema es de trazabilidad: no hay evidencia de que la pasarela participó en el procesamiento de esas transacciones.

**Por qué importa**

Sin la confirmación de la pasarela no es posible verificar qué comisión cobró ni auditar si el procesamiento fue correcto. En una revisión externa o auditoría tributaria, esa falta de trazabilidad genera observaciones de control interno.

Además, en casos extremos puede indicar que el pago llegó por un canal no autorizado o que hubo un error en el procesamiento que requiere investigación.

**Cómo lo resuelve el contador**

El reporte muestra cada transacción con su fecha, pasarela asignada y los montos registrados en banco y ERP.

Con esa información el contador:

1. Contacta a la pasarela con el listado de transacciones sin confirmar y solicita una explicación.
2. Si la pasarela confirma que las procesó y fue un error de reporte, solicita el reporte corregido y verifica que las comisiones sean correctas.
3. Si la pasarela no tiene registro de esas transacciones, investiga el canal real del pago — puede ser una transferencia directa, un depósito en efectivo u otro medio — y actualiza el registro en el ERP con el canal correcto.

---

[← Volver al README principal](Readme.md)
