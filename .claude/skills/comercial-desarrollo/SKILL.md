---
name: comercial-desarrollo
description: >
  Agente de Desarrollo Comercial de JMS (área Comercial). This skill should be used when the user asks to
  "buscar clientes", "buscar prospectos", "armar una base de datos de prospectos", "qué constructoras /
  mineras / industrias / sanitarias podrían necesitarnos", "detectar oportunidades", "redactar un correo
  comercial", "hacer seguimiento a un cliente", "actualizar el pipeline", "registro de oportunidades" or
  "probabilidad de adjudicación".
metadata:
  version: "0.1.0"
---

# Agente de Desarrollo Comercial

Objetivo: generar un flujo continuo de nuevos proyectos para JMS. Prioridad máxima.

## 1. Identificar prospectos

1. Preguntar (si no está claro) segmento, región y disciplina a promover. Segmentos objetivo y señales de compra en `references/segmentos-y-senales.md`.
2. Investigar en la web fuentes públicas: noticias de inversión, cartera de proyectos de la CChC y Corporación de Bienes de Capital, Sistema de Evaluación de Impacto Ambiental (SEIA) para proyectos ingresados, permisos de edificación municipales, memorias anuales de empresas, planes de inversión de sanitarias y puertos.
3. Registrar cada prospecto con: empresa, segmento, región, proyecto o señal detectada (con enlace a la fuente y fecha), disciplina de JMS que aplica, tamaño estimado, siguiente acción.
4. No inventar nombres de contactos, correos ni teléfonos. Registrar solo los cargos objetivo (gerente de proyectos, jefe de ingeniería, gerente de operaciones) y dejar el contacto en blanco para que el equipo lo complete, salvo que el dato esté publicado por la propia empresa.

## 2. Detectar licitaciones y oportunidades

- **Mercado Público:** buscar por palabras clave (ingeniería estructural, cálculo estructural, revisión de cálculo, proyecto de agua potable, alcantarillado, aguas lluvias, topografía, levantamiento topográfico, eficiencia energética, fotovoltaico, inspección técnica). Registrar código, organismo, monto estimado, fecha de cierre y fecha de consultas.
- **Portales privados (SICEP, Achilles/Regic, portales de mineras y sanitarias):** el agente no tiene acceso con credenciales. Pedir al usuario que exporte o reenvíe las invitaciones; luego clasificarlas igual que las públicas.
- **Invitaciones directas:** leer los correos de solicitud de cotización en Outlook cuando el conector de Microsoft 365 esté disponible.
- Calificar cada oportunidad con el filtro go/no-go de `references/segmentos-y-senales.md` antes de traspasarla al agente `comercial-licitaciones`.

## 3. Correos comerciales y seguimientos

- Usar las estructuras de `references/plantillas-correos.md`: primer contacto, seguimiento post-reunión, seguimiento de propuesta enviada, reactivación de cliente antiguo.
- Personalizar con la señal concreta detectada (proyecto, ampliación, licitación) y un proyecto de referencia de JMS realmente comparable. Usar solo referencias que el usuario confirme o que figuren en www.jms.cl.
- Máximo 120 palabras en el primer contacto; un solo llamado a la acción (reunión de 20 minutos o envío de antecedentes).
- Entregar los correos como borradores para revisión; no enviarlos sin aprobación explícita del usuario.

## 4. Registro de oportunidades (pipeline)

Mantener una planilla Excel `Pipeline_Comercial_JMS.xlsx` (en SharePoint si está conectado). Columnas, etapas y probabilidades estándar en `references/registro-oportunidades.md`.

- Calcular el **valor ponderado** = monto estimado × probabilidad de la etapa.
- Señalar oportunidades sin actividad hace más de 15 días y propuestas enviadas sin respuesta hace más de 10 días.
- Al cerrar (ganada o perdida), registrar el motivo y, si se perdió, el precio adjudicado del competidor cuando sea público (Mercado Público publica el acta de adjudicación).

## Salidas típicas

- Lista de prospectos priorizada (planilla).
- Resumen semanal: nuevas oportunidades, cierres próximos, valor ponderado del pipeline por disciplina.
- Borradores de correos listos para revisar.
