# Agentes JMS en VS Code

Esta carpeta trae los 7 agentes de JMS Ingenieros Consultores (más el coordinador), organizados en cuatro áreas: Comercial, Técnica, Gestión y Administración. Funciona con dos asistentes de VS Code: **Claude Code** y **GitHub Copilot**.

## Cómo abrirla

1. Descomprime `jms-agentes-vscode.zip` en una carpeta, por ejemplo `Documentos\JMS\agentes`.
2. En VS Code: **Archivo → Abrir carpeta…** y elige esa carpeta.
3. VS Code te sugerirá instalar las extensiones recomendadas (Claude Code y GitHub Copilot Chat). Instala la que uses.

## Con Claude Code

- Abre el panel de Claude Code. Al abrir la carpeta, lee `CLAUDE.md` automáticamente.
- Pide en lenguaje natural ("analiza estas bases de licitación", "compara las HH del proyecto X") y Claude elige el agente adecuado.
- También puedes nombrar un agente: "usa el agente comercial-licitaciones para…". Escribe `/agents` para ver la lista.

| Área | Agente |
|---|---|
| Comercial | `comercial-desarrollo`, `comercial-licitaciones` |
| Técnica | `tecnica-asistencia`, `tecnica-documentacion`, `tecnica-estimacion-inversion` |
| Gestión | `gestion-control-proyectos` |
| Administración | `administracion-finanzas` |

## Con GitHub Copilot

- Abre el chat de Copilot y, en el selector de modo o agente, elige uno de los agentes **JMS ·** (por ejemplo, "jms-comercial-licitaciones").
- Copilot también lee `AGENTS.md` con las reglas comunes.

## Dónde dejar los archivos

Guarda bases, planillas de horas, facturas exportadas del SII e informes en `trabajo/<área>/<proyecto>/`. Los agentes leen y escriben ahí.

## Estructura

```
CLAUDE.md / AGENTS.md         Reglas comunes y mapa de agentes
.claude/skills/<agente>/      Instrucciones completas y material de referencia
.claude/agents/               Agentes para Claude Code
.github/agents/               Agentes para GitHub Copilot
.vscode/                      Extensiones recomendadas y configuración
trabajo/                      Tus archivos de trabajo, por área
```

Para cambiar el comportamiento de un agente, edita su `SKILL.md` en `.claude/skills/`. Para Copilot, edita también su archivo en `.github/agents/`.
