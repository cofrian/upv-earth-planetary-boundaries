# Vídeo de lanzamiento — próximos pasos

Checklist de lo que falta antes de empezar a animar.

## Antes de tocar código

- [ ] Confirmar URL local de mi web (mockup frontend en marcha, p. ej. `http://localhost:3000`)
- [ ] Confirmar nombre del producto, tagline (1 línea) y descripción corta (2-3 líneas)
- [ ] Definir estilo de música de fondo (Apple-cinematic / OpenAI-ambient / Linear-techno / sin música)
- [ ] Aprobar las 6 frases que aparecen en pantalla (una por acto) antes de animarlas
- [ ] Extraer paleta + tipografía desde `mockup/frontend` y volcarlas en `brand/tokens.ts`

## Captura de assets

- [ ] Instalar el MCP de Playwright (ver comando manual más abajo)
- [ ] Decidir qué pantallas del mockup grabar (dashboard, charts, nav, etc.)
- [ ] Capturar screenshots estáticos → `public/captures/`
- [ ] Capturar recordings de interacción → `public/recordings/`

## Implementación

- [ ] Acto 1 — Hook (~0-8s) en `src/scenes/Act1Hook.tsx`
- [ ] Acto 2 — Manifiesto (~8-20s) en `src/scenes/Act2Manifesto.tsx`
- [ ] Acto 3 — Reveal (~20-32s) en `src/scenes/Act3Reveal.tsx`
- [ ] Acto 4 — Features (~32-50s) en `src/scenes/Act4Features.tsx`
- [ ] Acto 5 — Visión (~50-60s) en `src/scenes/Act5Vision.tsx`
- [ ] Acto 6 — CTA (~60-70s) en `src/scenes/Act6CTA.tsx`
- [ ] Componentes reutilizables: `SimulatedCursor`, `MacBookFrame`, `SpringText`
- [ ] Orquestar actos en `src/Root.tsx` con `<Series>` + transitions

## Revisión y entrega

- [ ] Revisar en Remotion Studio (`npm run dev`)
- [ ] Ajustar pacing, springs, blur, sombras
- [ ] Renderizar a MP4 (`npx remotion render LaunchVideo out/video.mp4`)
- [ ] Exportar también versión vertical 1080x1920 para redes si se necesita

## Comando manual pendiente (Playwright MCP)

El MCP de Playwright se instala fuera de Claude Code con scope user.
Ejecutar en una terminal normal:

```bash
claude mcp add playwright -s user -- npx -y @playwright/mcp@latest
```

Después, reiniciar Claude Code para que cargue el servidor.
